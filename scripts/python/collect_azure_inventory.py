#!/usr/bin/env python3
"""Collect scoped, read-only Azure inventory evidence."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from jsonschema import Draft202012Validator, FormatChecker

RESOURCE_INVENTORY_QUERY = """
Resources
| project id, name, type, location, resourceGroup, subscriptionId, kind, managedBy
| order by type asc, name asc
""".strip()

TOPOLOGY_RELATIONSHIP_TYPES = (
    "vnet-contains-subnet",
    "vnet-peered-with-vnet",
    "subnet-associated-with-nsg",
    "subnet-associated-with-route-table",
    "private-endpoint-placed-in-subnet",
    "private-dns-zone-linked-to-vnet",
)

TOPOLOGY_ENDPOINT_TYPES = {
    "vnet-contains-subnet": (
        "microsoft.network/virtualnetworks",
        "microsoft.network/virtualnetworks/subnets",
    ),
    "vnet-peered-with-vnet": (
        "microsoft.network/virtualnetworks",
        "microsoft.network/virtualnetworks",
    ),
    "subnet-associated-with-nsg": (
        "microsoft.network/virtualnetworks/subnets",
        "microsoft.network/networksecuritygroups",
    ),
    "subnet-associated-with-route-table": (
        "microsoft.network/virtualnetworks/subnets",
        "microsoft.network/routetables",
    ),
    "private-endpoint-placed-in-subnet": (
        "microsoft.network/privateendpoints",
        "microsoft.network/virtualnetworks/subnets",
    ),
    "private-dns-zone-linked-to-vnet": (
        "microsoft.network/privatednszones",
        "microsoft.network/virtualnetworks",
    ),
}

TOPOLOGY_RELATIONSHIP_QUERIES = (
    (
        "vnet-contains-subnet",
        """
Resources
    | where type =~ 'microsoft.network/virtualnetworks'
    | mv-expand subnet = properties.subnets
    | extend relationshipType = 'vnet-contains-subnet'
    | extend sourceResourceId = tostring(id)
    | extend sourceResourceType = 'microsoft.network/virtualnetworks'
    | extend targetResourceId = tostring(subnet.id)
    | extend targetResourceType = 'microsoft.network/virtualnetworks/subnets'
    | where isnotempty(targetResourceId)
| project relationshipType, sourceResourceId, sourceResourceType,
    targetResourceId, targetResourceType
| order by relationshipType asc, sourceResourceId asc,
    targetResourceId asc
""".strip(),
    ),
    (
        "vnet-peered-with-vnet",
        """
Resources
    | where type =~ 'microsoft.network/virtualnetworks'
    | mv-expand peering = properties.virtualNetworkPeerings
    | extend relationshipType = 'vnet-peered-with-vnet'
    | extend sourceResourceId = tostring(id)
    | extend sourceResourceType = 'microsoft.network/virtualnetworks'
    | extend targetResourceId = tostring(
        peering.properties.remoteVirtualNetwork.id
      )
    | extend targetResourceType = 'microsoft.network/virtualnetworks'
| project relationshipType, sourceResourceId, sourceResourceType,
    targetResourceId, targetResourceType
| order by relationshipType asc, sourceResourceId asc,
    targetResourceId asc
""".strip(),
    ),
    (
        "subnet-associated-with-nsg",
        """
Resources
    | where type =~ 'microsoft.network/virtualnetworks'
    | mv-expand subnet = properties.subnets
    | extend relationshipType = 'subnet-associated-with-nsg'
    | extend sourceResourceId = tostring(subnet.id)
    | extend sourceResourceType = 'microsoft.network/virtualnetworks/subnets'
    | extend targetResourceId = tostring(
        subnet.properties.networkSecurityGroup.id
      )
    | extend targetResourceType = 'microsoft.network/networksecuritygroups'
    | where isnotempty(targetResourceId)
| project relationshipType, sourceResourceId, sourceResourceType,
    targetResourceId, targetResourceType
| order by relationshipType asc, sourceResourceId asc,
    targetResourceId asc
""".strip(),
    ),
    (
        "subnet-associated-with-route-table",
        """
Resources
    | where type =~ 'microsoft.network/virtualnetworks'
    | mv-expand subnet = properties.subnets
    | extend relationshipType = 'subnet-associated-with-route-table'
    | extend sourceResourceId = tostring(subnet.id)
    | extend sourceResourceType = 'microsoft.network/virtualnetworks/subnets'
    | extend targetResourceId = tostring(
        subnet.properties.routeTable.id
      )
    | extend targetResourceType = 'microsoft.network/routetables'
    | where isnotempty(targetResourceId)
| project relationshipType, sourceResourceId, sourceResourceType,
    targetResourceId, targetResourceType
| order by relationshipType asc, sourceResourceId asc,
    targetResourceId asc
""".strip(),
    ),
    (
        "private-endpoint-placed-in-subnet",
        """
Resources
    | where type =~ 'microsoft.network/privateendpoints'
    | extend relationshipType = 'private-endpoint-placed-in-subnet'
    | extend sourceResourceId = tostring(id)
    | extend sourceResourceType = 'microsoft.network/privateendpoints'
    | extend targetResourceId = tostring(properties.subnet.id)
    | extend targetResourceType = 'microsoft.network/virtualnetworks/subnets'
| project relationshipType, sourceResourceId, sourceResourceType,
    targetResourceId, targetResourceType
| order by relationshipType asc, sourceResourceId asc,
    targetResourceId asc
""".strip(),
    ),
    (
        "private-dns-zone-linked-to-vnet",
        """
Resources
    | where type =~
        'microsoft.network/privatednszones/virtualnetworklinks'
    | extend relationshipType = 'private-dns-zone-linked-to-vnet'
    | extend sourceResourceId = substring(
        id,
        0,
        indexof(id, '/virtualNetworkLinks/')
      )
    | extend sourceResourceType = 'microsoft.network/privatednszones'
    | extend targetResourceId = tostring(properties.virtualNetwork.id)
    | extend targetResourceType = 'microsoft.network/virtualnetworks'
| project relationshipType, sourceResourceId, sourceResourceType,
    targetResourceId, targetResourceType
| order by relationshipType asc, sourceResourceId asc,
    targetResourceId asc
""".strip(),
    ),
)
EXIT_SUCCESS = 0
EXIT_EXECUTION_ERROR = 2


def parse_arguments(
    arguments: list[str] | None = None,
) -> argparse.Namespace:
    """Parse explicit scope, consent, and output arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Collect subscription-scoped, read-only Azure inventory "
            "evidence through Azure Resource Graph."
        )
    )
    parser.add_argument(
        "--subscription",
        required=True,
        type=validate_azure_identifier,
        help="Approved Azure subscription ID as a canonical UUID.",
    )
    parser.add_argument(
        "--tenant",
        type=validate_azure_identifier,
        help=("Optional approved Microsoft Entra tenant ID as a canonical UUID."),
    )
    parser.add_argument(
        "--approve-read-only",
        required=True,
        action="store_true",
        help=("Confirm approval to run read-only Azure account and Resource Graph commands."),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".specify/discovery/azure-inventory.json"),
        help=("Output path. Defaults to .specify/discovery/azure-inventory.json."),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=("Explicitly replace an existing Azure inventory evidence file."),
    )

    return parser.parse_args(arguments)


def validate_output_path(
    output_path: Path,
    *,
    project_root: Path,
) -> Path:
    """Resolve a JSON output path inside a Spec Kit discovery directory."""
    resolved_project_root = project_root.resolve()
    specify_directory = resolved_project_root / ".specify"

    if not specify_directory.is_dir():
        raise ValueError(f"Current directory is not a Spec Kit project: {resolved_project_root}")

    discovery_directory = (specify_directory / "discovery").resolve()

    if output_path.is_absolute():
        resolved_output_path = output_path.resolve()
    else:
        resolved_output_path = (resolved_project_root / output_path).resolve()

    if (
        not resolved_output_path.is_relative_to(discovery_directory)
        or resolved_output_path.suffix.lower() != ".json"
    ):
        raise ValueError(
            "Inventory output must remain in .specify/discovery and use a JSON file extension."
        )

    return resolved_output_path


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

    def run_process(
        execution_command: list[str],
    ) -> Any:
        return runner(
            execution_command,
            capture_output=True,
            check=False,
            shell=False,
            text=True,
        )

    try:
        completed_process = run_process(command)
    except FileNotFoundError:
        if not command or command[0] != "az":
            raise RuntimeError("Azure CLI executable 'az' was not found.") from None

        windows_command = [
            "az.cmd",
            *command[1:],
        ]

        try:
            completed_process = run_process(windows_command)
        except FileNotFoundError:
            raise RuntimeError("Azure CLI executable 'az' was not found.") from None
        except OSError as exception:
            raise RuntimeError(
                f"Azure CLI command could not be started: {exception}"
            ) from exception
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

        records.append(
            {property_name: record[property_name] for property_name in required_properties}
        )

    return records


def extract_subscription_id_from_resource_id(
    resource_id: str,
) -> str | None:
    """Return a canonical subscription ID from an Azure resource ID."""
    if not isinstance(resource_id, str):
        return None

    segments = resource_id.strip().split("/")

    if len(segments) < 3 or segments[0] != "" or segments[1].casefold() != "subscriptions":
        return None

    try:
        return validate_azure_identifier(segments[2])
    except ValueError:
        return None


def extract_topology_relationship_records(
    response: dict[str, Any],
    *,
    expected_subscription_id: str,
) -> list[dict[str, Any]]:
    """Extract only controlled topology fields from Resource Graph output."""
    data = response.get("data")

    if not isinstance(data, list):
        raise ValueError("Azure topology Resource Graph response must contain a 'data' array.")

    return normalize_topology_relationships(
        data,
        expected_subscription_id=expected_subscription_id,
    )


def normalize_topology_relationships(
    records: list[dict[str, Any]],
    *,
    expected_subscription_id: str,
) -> list[dict[str, Any]]:
    """Validate, classify, deduplicate, and sort topology relationships."""
    if not isinstance(records, list):
        raise ValueError("Topology relationship records must be an array.")

    approved_subscription_id = validate_azure_identifier(expected_subscription_id)
    required_properties = (
        "relationshipType",
        "sourceResourceId",
        "sourceResourceType",
        "targetResourceId",
        "targetResourceType",
    )
    normalized_by_identity: dict[
        tuple[str, str, str, str, str],
        dict[str, Any],
    ] = {}

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"Topology relationship at index {index} must be an object.")

        for property_name in required_properties:
            if property_name not in record:
                raise ValueError(
                    f"Topology relationship at index {index} is missing "
                    f"required property '{property_name}'."
                )

        relationship_type = record["relationshipType"]

        if relationship_type not in TOPOLOGY_RELATIONSHIP_TYPES:
            raise ValueError(f"Unsupported topology relationship type: {relationship_type!r}.")

        source_resource_id = record["sourceResourceId"]
        source_resource_type = record["sourceResourceType"]
        target_resource_id = record["targetResourceId"]
        target_resource_type = record["targetResourceType"]

        if not isinstance(source_resource_id, str) or not source_resource_id:
            raise ValueError(
                f"Topology relationship at index {index} has an invalid sourceResourceId."
            )

        if not isinstance(source_resource_type, str) or not source_resource_type:
            raise ValueError(
                f"Topology relationship at index {index} has an invalid sourceResourceType."
            )

        if not isinstance(target_resource_type, str) or not target_resource_type:
            raise ValueError(
                f"Topology relationship at index {index} has an invalid targetResourceType."
            )

        if target_resource_id is not None and (
            not isinstance(target_resource_id, str) or not target_resource_id
        ):
            raise ValueError(
                f"Topology relationship at index {index} has an invalid targetResourceId."
            )

        source_subscription_id = extract_subscription_id_from_resource_id(source_resource_id)

        if source_subscription_id != approved_subscription_id:
            raise ValueError("Topology relationship source is outside the approved subscription.")

        if target_resource_id is None:
            target_scope = "unresolved"
        else:
            target_subscription_id = extract_subscription_id_from_resource_id(target_resource_id)

            if target_subscription_id is None:
                target_scope = "unresolved"
            elif target_subscription_id == approved_subscription_id:
                target_scope = "in-scope"
            else:
                target_scope = "external-subscription"

        normalized_source_resource_type = source_resource_type.casefold()
        normalized_target_resource_type = target_resource_type.casefold()
        expected_source_type, expected_target_type = TOPOLOGY_ENDPOINT_TYPES[relationship_type]

        if (
            normalized_source_resource_type != expected_source_type
            or normalized_target_resource_type != expected_target_type
        ):
            raise ValueError(
                "Topology endpoint types do not match relationship type "
                f"{relationship_type!r}: expected "
                f"{expected_source_type!r} -> {expected_target_type!r}."
            )

        normalized_source_resource_id = source_resource_id.casefold()
        normalized_target_resource_id = (
            target_resource_id.casefold() if target_resource_id is not None else None
        )

        normalized_relationship = {
            "relationshipType": relationship_type,
            "sourceResourceId": normalized_source_resource_id,
            "sourceResourceType": normalized_source_resource_type,
            "targetResourceId": normalized_target_resource_id,
            "targetResourceType": normalized_target_resource_type,
            "targetScope": target_scope,
        }

        identity = (
            relationship_type.casefold(),
            source_resource_id.casefold(),
            source_resource_type.casefold(),
            (target_resource_id.casefold() if target_resource_id is not None else ""),
            target_resource_type.casefold(),
        )

        normalized_by_identity.setdefault(
            identity,
            normalized_relationship,
        )

    return sorted(
        normalized_by_identity.values(),
        key=lambda relationship: (
            relationship["relationshipType"].casefold(),
            relationship["sourceResourceId"].casefold(),
            relationship["targetScope"],
            (
                relationship["targetResourceId"].casefold()
                if relationship["targetResourceId"] is not None
                else ""
            ),
            relationship["targetResourceType"].casefold(),
        ),
    )


def execute_paged_resource_graph_query(
    subscription_id: str,
    graph_query: str,
    *,
    page_size: int = 1000,
    runner: Any = subprocess.run,
) -> list[dict[str, Any]]:
    """Collect every Resource Graph page without silently truncating evidence."""
    records: list[dict[str, Any]] = []
    skip_token: str | None = None
    observed_skip_tokens: set[str] = set()
    expected_total_records: int | None = None

    while True:
        response = execute_json_command(
            build_resource_graph_command(
                subscription_id,
                graph_query,
                page_size=page_size,
                skip_token=skip_token,
            ),
            runner=runner,
        )

        page_data = response.get("data")

        if not isinstance(page_data, list):
            raise RuntimeError("Azure Resource Graph response did not contain a data array.")

        for record in page_data:
            if not isinstance(record, dict):
                raise RuntimeError("Azure Resource Graph data contained a non-object record.")

            records.append(record)

        reported_total_records = response.get("totalRecords")

        if reported_total_records is None:
            reported_total_records = response.get("total_records")

        if reported_total_records is not None:
            if (
                isinstance(reported_total_records, bool)
                or not isinstance(reported_total_records, int)
                or reported_total_records < 0
            ):
                raise RuntimeError("Azure Resource Graph returned an invalid total record count.")

            if expected_total_records is None:
                expected_total_records = reported_total_records
            elif reported_total_records != expected_total_records:
                raise RuntimeError("Azure Resource Graph total record count changed between pages.")

        next_skip_token = response.get("skipToken")

        if next_skip_token is None:
            next_skip_token = response.get("$skipToken")

        if next_skip_token is None:
            next_skip_token = response.get("skip_token")

        if next_skip_token is None:
            break

        if not isinstance(next_skip_token, str) or not next_skip_token.strip():
            raise RuntimeError("Azure Resource Graph returned an invalid skip token.")

        if next_skip_token in observed_skip_tokens:
            raise RuntimeError("Azure Resource Graph repeated a pagination skip token.")

        observed_skip_tokens.add(next_skip_token)
        skip_token = next_skip_token

    if expected_total_records is not None and len(records) != expected_total_records:
        raise RuntimeError(
            f"Azure Resource Graph returned {len(records)} of {expected_total_records} records."
        )

    return records


def build_inventory_document(
    account: dict[str, str],
    resources: list[dict[str, Any]],
    *,
    collected_at: datetime,
    topology_relationships: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build an unconfirmed, read-only Azure inventory evidence document."""
    if collected_at.tzinfo is None or collected_at.utcoffset() is None:
        raise ValueError("Inventory collection timestamp must be timezone-aware.")

    collected_at_utc = collected_at.astimezone(timezone.utc)
    collected_at_value = collected_at_utc.isoformat(timespec="seconds").replace("+00:00", "Z")

    copied_account = deepcopy(account)
    copied_resources = deepcopy(resources)

    document = {
        "schemaVersion": "1.0",
        "evidenceStatus": "unconfirmed",
        "collectedAt": collected_at_value,
        "source": {
            "type": "azure",
            "provider": "Azure Resource Graph",
            "readOnly": True,
            "query": RESOURCE_INVENTORY_QUERY,
        },
        "scope": copied_account,
        "resourceCount": len(copied_resources),
        "resources": copied_resources,
    }

    if topology_relationships is not None:
        copied_relationships = deepcopy(topology_relationships)
        document["source"]["topologyQueries"] = [
            query for _, query in TOPOLOGY_RELATIONSHIP_QUERIES
        ]
        document["topology"] = {
            "relationshipCount": len(copied_relationships),
            "relationships": copied_relationships,
        }

    return document


def validate_inventory_document(
    document: dict[str, Any],
    schema: dict[str, Any],
) -> None:
    """Validate inventory evidence against schema and semantic rules."""
    Draft202012Validator.check_schema(schema)

    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
    )
    schema_errors = list(validator.iter_errors(document))

    if schema_errors:
        error_messages = sorted(error.message for error in schema_errors)
        raise ValueError("Inventory schema validation failed: " + "; ".join(error_messages))

    recorded_resource_count = document["resourceCount"]
    actual_resource_count = len(document["resources"])

    if recorded_resource_count != actual_resource_count:
        raise ValueError(
            "Inventory resourceCount does not match the "
            f"actual resource count: recorded "
            f"{recorded_resource_count}, actual "
            f"{actual_resource_count}."
        )

    topology = document.get("topology")

    if topology is not None:
        recorded_relationship_count = topology["relationshipCount"]
        actual_relationship_count = len(topology["relationships"])

        if recorded_relationship_count != actual_relationship_count:
            raise ValueError(
                "Inventory topology relationshipCount does not match the "
                f"actual relationship count: recorded "
                f"{recorded_relationship_count}, actual "
                f"{actual_relationship_count}."
            )


def write_inventory_document(
    document: dict[str, Any],
    output_path: Path,
    *,
    overwrite: bool,
) -> None:
    """Atomically write inventory evidence without implicit replacement."""
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"Inventory evidence already exists: {output_path}. "
            "Use --overwrite to replace it explicitly."
        )

    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(
                document,
                temporary_file,
                ensure_ascii=False,
                indent=2,
            )
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        if overwrite:
            os.replace(temporary_path, output_path)
        else:
            try:
                os.link(temporary_path, output_path)
            except FileExistsError as exception:
                raise FileExistsError(
                    f"Inventory evidence already exists: {output_path}. "
                    "Use --overwrite to replace it explicitly."
                ) from exception
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def collect_inventory(
    *,
    subscription_id: str,
    tenant_id: str | None = None,
    collected_at: datetime | None = None,
    runner: Any = subprocess.run,
) -> dict[str, Any]:
    """Collect validated, subscription-scoped Azure inventory evidence."""
    approved_subscription_id = validate_azure_identifier(subscription_id)
    approved_tenant_id = validate_azure_identifier(tenant_id) if tenant_id is not None else None

    account_response = execute_json_command(
        build_account_show_command(),
        runner=runner,
    )
    account = validate_account_context(
        account_response,
        expected_subscription_id=approved_subscription_id,
        expected_tenant_id=approved_tenant_id,
    )

    resource_records = execute_paged_resource_graph_query(
        approved_subscription_id,
        RESOURCE_INVENTORY_QUERY,
        runner=runner,
    )
    resources = extract_resource_records(
        {"data": resource_records},
        expected_subscription_id=approved_subscription_id,
    )

    topology_records: list[dict[str, Any]] = []

    for _, topology_query in TOPOLOGY_RELATIONSHIP_QUERIES:
        topology_records.extend(
            execute_paged_resource_graph_query(
                approved_subscription_id,
                topology_query,
                runner=runner,
            )
        )

    topology_relationships = extract_topology_relationship_records(
        {"data": topology_records},
        expected_subscription_id=approved_subscription_id,
    )

    collection_time = collected_at if collected_at is not None else datetime.now(timezone.utc)

    return build_inventory_document(
        account,
        resources,
        collected_at=collection_time,
        topology_relationships=topology_relationships,
    )


def load_inventory_schema() -> dict[str, Any]:
    """Load the packaged Azure inventory JSON Schema."""
    schema_path = Path(__file__).resolve().parents[2] / "templates" / "azure-inventory.schema.json"

    try:
        with schema_path.open(
            "r",
            encoding="utf-8",
        ) as schema_file:
            schema = json.load(schema_file)
    except FileNotFoundError as exception:
        raise RuntimeError(f"Inventory schema was not found: {schema_path}") from exception
    except json.JSONDecodeError as exception:
        raise RuntimeError(f"Inventory schema is not valid JSON: {schema_path}") from exception

    if not isinstance(schema, dict):
        raise RuntimeError("Inventory schema root must be a JSON object.")

    return schema


def run(
    arguments: list[str] | None = None,
    *,
    project_root: Path | None = None,
    collected_at: datetime | None = None,
    runner: Any = subprocess.run,
) -> Path:
    """Run collection, validation, and safe evidence persistence."""
    parsed_arguments = parse_arguments(arguments)
    effective_project_root = project_root if project_root is not None else Path.cwd()
    output_path = validate_output_path(
        parsed_arguments.output,
        project_root=effective_project_root,
    )

    if output_path.exists() and not parsed_arguments.overwrite:
        raise FileExistsError(
            f"Inventory evidence already exists: {output_path}. "
            "Use --overwrite to replace it explicitly."
        )

    document = collect_inventory(
        subscription_id=parsed_arguments.subscription,
        tenant_id=parsed_arguments.tenant,
        collected_at=collected_at,
        runner=runner,
    )
    schema = load_inventory_schema()
    validate_inventory_document(document, schema)
    write_inventory_document(
        document,
        output_path,
        overwrite=parsed_arguments.overwrite,
    )

    return output_path


def main(
    arguments: list[str] | None = None,
    *,
    project_root: Path | None = None,
    collected_at: datetime | None = None,
    runner: Any = subprocess.run,
) -> int:
    """Run the CLI and return a stable process exit code."""
    try:
        output_path = run(
            arguments,
            project_root=project_root,
            collected_at=collected_at,
            runner=runner,
        )
    except (OSError, RuntimeError, ValueError) as exception:
        print(
            f"Azure inventory collection failed: {exception}",
            file=sys.stderr,
        )
        return EXIT_EXECUTION_ERROR

    print(f"Azure inventory evidence written successfully: {output_path}")
    print(
        "Evidence status: unconfirmed. Review and confirm "
        "findings during the Azure architecture interview."
    )
    return EXIT_SUCCESS


def build_account_show_command() -> list[str]:
    """Build the minimized read-only Azure context inspection command."""
    return [
        "az",
        "account",
        "show",
        "--query",
        "{id:id,name:name,state:state,tenantId:tenantId}",
        "--output",
        "json",
        "--only-show-errors",
    ]


def build_resource_graph_command(
    subscription_id: str,
    graph_query: str,
    *,
    page_size: int = 1000,
    skip_token: str | None = None,
) -> list[str]:
    """Build one bounded, subscription-scoped Resource Graph page request."""
    normalized_subscription_id = validate_azure_identifier(subscription_id)

    if not graph_query.strip():
        raise ValueError("Resource Graph query must not be empty.")

    if (
        isinstance(page_size, bool)
        or not isinstance(page_size, int)
        or page_size < 1
        or page_size > 1000
    ):
        raise ValueError("Resource Graph page size must be between 1 and 1000.")

    if skip_token is not None and not skip_token.strip():
        raise ValueError("Resource Graph skip token must not be empty.")

    normalized_graph_query = " ".join(
        line.strip() for line in graph_query.splitlines() if line.strip()
    )

    if not normalized_graph_query:
        raise ValueError("Resource Graph query must not be empty.")

    command = [
        "az",
        "graph",
        "query",
        "--subscriptions",
        normalized_subscription_id,
        "--graph-query",
        normalized_graph_query,
        "--first",
        str(page_size),
    ]

    if skip_token is not None:
        command.extend(
            [
                "--skip-token",
                skip_token,
            ]
        )

    command.extend(
        [
            "--output",
            "json",
            "--only-show-errors",
        ]
    )

    return command


if __name__ == "__main__":
    raise SystemExit(main())
