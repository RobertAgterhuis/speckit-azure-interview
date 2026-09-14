#!/usr/bin/env python3
"""Collect scoped, read-only Azure inventory evidence."""

from __future__ import annotations

import json
import subprocess
from typing import Any
from uuid import UUID

RESOURCE_INVENTORY_QUERY = """
Resources
| project id, name, type, location, resourceGroup, subscriptionId, kind, managedBy
| order by type asc, name asc
""".strip()


def validate_azure_identifier(identifier: str) -> str:
    """Validate and normalize a canonical Azure UUID."""
    try:
        parsed_identifier = UUID(identifier)
    except (AttributeError, TypeError, ValueError) as exception:
        raise ValueError(
            "Azure tenant and subscription identifiers must be canonical UUIDs."
        ) from exception

    normalized_identifier = str(parsed_identifier)

    if parsed_identifier.version != 4 or identifier.lower() != normalized_identifier:
        raise ValueError("Azure tenant and subscription identifiers must be canonical UUIDs.")

    return normalized_identifier


def validate_account_context(
    account: dict[str, Any],
    *,
    expected_subscription_id: str,
    expected_tenant_id: str | None = None,
) -> dict[str, str]:
    """Validate that the active Azure context matches the approved scope."""
    required_properties = (
        "id",
        "name",
        "state",
        "tenantId",
    )

    for property_name in required_properties:
        value = account.get(property_name)

        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                f"Azure account response is missing required property '{property_name}'."
            )

    active_subscription_id = validate_azure_identifier(account["id"])
    active_tenant_id = validate_azure_identifier(account["tenantId"])
    approved_subscription_id = validate_azure_identifier(expected_subscription_id)

    if active_subscription_id != approved_subscription_id:
        raise ValueError("Active subscription does not match the approved subscription.")

    if expected_tenant_id is not None:
        approved_tenant_id = validate_azure_identifier(expected_tenant_id)

        if active_tenant_id != approved_tenant_id:
            raise ValueError("Active tenant does not match the approved tenant.")

    if account["state"] != "Enabled":
        raise ValueError("The approved Azure subscription must be Enabled.")

    return {
        "subscriptionId": active_subscription_id,
        "subscriptionName": account["name"],
        "tenantId": active_tenant_id,
    }


def execute_json_command(
    command: list[str],
    *,
    runner: Any = subprocess.run,
) -> dict[str, Any]:
    """Execute an Azure CLI command without a shell and return a JSON object."""
    try:
        completed_process = runner(
            command,
            capture_output=True,
            check=False,
            shell=False,
            text=True,
        )
    except FileNotFoundError as exception:
        raise RuntimeError("Azure CLI executable 'az' was not found.") from exception
    except OSError as exception:
        raise RuntimeError(f"Azure CLI command could not be started: {exception}") from exception

    if completed_process.returncode != 0:
        error_message = completed_process.stderr.strip()

        if not error_message:
            error_message = "Azure CLI command failed without an error message."

        raise RuntimeError(error_message)

    try:
        document = json.loads(completed_process.stdout)
    except (json.JSONDecodeError, TypeError) as exception:
        raise RuntimeError("Azure CLI did not return a valid JSON object.") from exception

    if not isinstance(document, dict):
        raise RuntimeError("Azure CLI did not return a valid JSON object.")

    return document


def extract_resource_records(
    response: dict[str, Any],
    *,
    expected_subscription_id: str,
) -> list[dict[str, Any]]:
    """Validate and copy Resource Graph records from the approved subscription."""
    data = response.get("data")

    if not isinstance(data, list):
        raise ValueError("Azure Resource Graph response must contain a 'data' array.")

    approved_subscription_id = validate_azure_identifier(expected_subscription_id)
    required_properties = (
        "id",
        "name",
        "type",
        "location",
        "resourceGroup",
        "subscriptionId",
        "kind",
        "managedBy",
    )
    records: list[dict[str, Any]] = []

    for index, record in enumerate(data):
        if not isinstance(record, dict):
            raise ValueError(f"Resource record at index {index} must be a JSON object.")

        for property_name in required_properties:
            if property_name not in record:
                raise ValueError(
                    f"Resource record at index {index} is missing required "
                    f"property '{property_name}'."
                )

        record_subscription_id = validate_azure_identifier(record["subscriptionId"])

        if record_subscription_id != approved_subscription_id:
            raise ValueError(
                f"Resource record at index {index} is outside the approved subscription."
            )

        expected_resource_id_prefix = f"/subscriptions/{approved_subscription_id}/"

        if not isinstance(record["id"], str) or not record["id"].lower().startswith(
            expected_resource_id_prefix
        ):
            raise ValueError(
                f"Resource record at index {index} is outside the approved subscription."
            )

        records.append(dict(record))

    return records


def build_account_show_command() -> list[str]:
    """Build the read-only command used to inspect the active Azure context."""
    return [
        "az",
        "account",
        "show",
        "--output",
        "json",
        "--only-show-errors",
    ]


def build_resource_graph_command(
    subscription_id: str,
    graph_query: str,
) -> list[str]:
    """Build a subscription-scoped, read-only Azure Resource Graph command."""
    normalized_subscription_id = validate_azure_identifier(subscription_id)

    if not graph_query.strip():
        raise ValueError("Resource Graph query must not be empty.")

    return [
        "az",
        "graph",
        "query",
        "--subscriptions",
        normalized_subscription_id,
        "--graph-query",
        graph_query,
        "--output",
        "json",
        "--only-show-errors",
    ]
