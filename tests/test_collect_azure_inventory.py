"""Tests for the read-only Azure inventory collector."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COLLECTOR_PATH = REPOSITORY_ROOT / "scripts" / "python" / "collect_azure_inventory.py"

SUBSCRIPTION_ID = "11111111-1111-4111-8111-111111111111"
TENANT_ID = "22222222-2222-4222-8222-222222222222"


def load_collector_module() -> ModuleType:
    """Load the collector script as a testable module."""
    specification = importlib.util.spec_from_file_location(
        "collect_azure_inventory",
        COLLECTOR_PATH,
    )

    if specification is None or specification.loader is None:
        raise RuntimeError(f"Unable to load collector: {COLLECTOR_PATH}")

    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def collector_module() -> ModuleType:
    """Return the loaded collector module."""
    return load_collector_module()


@pytest.mark.parametrize(
    "identifier",
    [
        SUBSCRIPTION_ID,
        TENANT_ID.upper(),
    ],
)
def test_validate_azure_identifier_accepts_canonical_uuid(
    collector_module: ModuleType,
    identifier: str,
) -> None:
    """Canonical Azure tenant and subscription identifiers are accepted."""
    assert collector_module.validate_azure_identifier(identifier) == identifier.lower()


@pytest.mark.parametrize(
    "identifier",
    [
        "",
        "current",
        "11111111-1111-1111-1111-111111111111",
        "11111111-1111-4111-7111-111111111111",
        "11111111-1111-4111-8111-11111111111Z",
        "11111111-1111-4111-8111-111111111111 --all",
    ],
)
def test_validate_azure_identifier_rejects_invalid_scope(
    collector_module: ModuleType,
    identifier: str,
) -> None:
    """Invalid or unsafe Azure scope identifiers are rejected."""
    with pytest.raises(ValueError, match="canonical UUID"):
        collector_module.validate_azure_identifier(identifier)


def test_build_account_show_command_is_read_only(
    collector_module: ModuleType,
) -> None:
    """Account inspection must use a fixed read-only Azure CLI command."""
    command = collector_module.build_account_show_command()

    assert command == [
        "az",
        "account",
        "show",
        "--output",
        "json",
        "--only-show-errors",
    ]


def test_build_resource_graph_command_scopes_query_to_subscription(
    collector_module: ModuleType,
) -> None:
    """Resource Graph queries must remain scoped to the approved subscription."""
    query = "Resources | project id, name, type, location, resourceGroup"
    command = collector_module.build_resource_graph_command(
        SUBSCRIPTION_ID,
        query,
    )

    assert command == [
        "az",
        "graph",
        "query",
        "--subscriptions",
        SUBSCRIPTION_ID,
        "--graph-query",
        query,
        "--output",
        "json",
        "--only-show-errors",
    ]


def test_build_resource_graph_command_rejects_blank_query(
    collector_module: ModuleType,
) -> None:
    """The collector must not execute an empty Resource Graph query."""
    with pytest.raises(ValueError, match="must not be empty"):
        collector_module.build_resource_graph_command(
            SUBSCRIPTION_ID,
            "   ",
        )


def test_validate_account_context_accepts_approved_scope(
    collector_module: ModuleType,
) -> None:
    """The active Azure context is accepted when it matches the approved scope."""
    account = {
        "id": SUBSCRIPTION_ID,
        "name": "Production",
        "state": "Enabled",
        "tenantId": TENANT_ID,
    }

    validated_account = collector_module.validate_account_context(
        account,
        expected_subscription_id=SUBSCRIPTION_ID,
        expected_tenant_id=TENANT_ID,
    )

    assert validated_account == {
        "subscriptionId": SUBSCRIPTION_ID,
        "subscriptionName": "Production",
        "tenantId": TENANT_ID,
    }


def test_validate_account_context_accepts_no_optional_tenant_scope(
    collector_module: ModuleType,
) -> None:
    """Tenant matching is not enforced when the user did not supply a tenant."""
    account = {
        "id": SUBSCRIPTION_ID,
        "name": "Production",
        "state": "Enabled",
        "tenantId": TENANT_ID,
    }

    validated_account = collector_module.validate_account_context(
        account,
        expected_subscription_id=SUBSCRIPTION_ID,
    )

    assert validated_account["tenantId"] == TENANT_ID


def test_validate_account_context_rejects_subscription_mismatch(
    collector_module: ModuleType,
) -> None:
    """Collection stops when the active subscription was not approved."""
    account = {
        "id": "33333333-3333-4333-8333-333333333333",
        "name": "Development",
        "state": "Enabled",
        "tenantId": TENANT_ID,
    }

    with pytest.raises(ValueError, match="Active subscription does not match"):
        collector_module.validate_account_context(
            account,
            expected_subscription_id=SUBSCRIPTION_ID,
            expected_tenant_id=TENANT_ID,
        )


def test_validate_account_context_rejects_tenant_mismatch(
    collector_module: ModuleType,
) -> None:
    """Collection stops when the active tenant was not approved."""
    account = {
        "id": SUBSCRIPTION_ID,
        "name": "Production",
        "state": "Enabled",
        "tenantId": "33333333-3333-4333-8333-333333333333",
    }

    with pytest.raises(ValueError, match="Active tenant does not match"):
        collector_module.validate_account_context(
            account,
            expected_subscription_id=SUBSCRIPTION_ID,
            expected_tenant_id=TENANT_ID,
        )


def test_validate_account_context_rejects_disabled_subscription(
    collector_module: ModuleType,
) -> None:
    """Inventory cannot run against a disabled subscription."""
    account = {
        "id": SUBSCRIPTION_ID,
        "name": "Production",
        "state": "Disabled",
        "tenantId": TENANT_ID,
    }

    with pytest.raises(ValueError, match="must be Enabled"):
        collector_module.validate_account_context(
            account,
            expected_subscription_id=SUBSCRIPTION_ID,
            expected_tenant_id=TENANT_ID,
        )


@pytest.mark.parametrize(
    "missing_property",
    [
        "id",
        "name",
        "state",
        "tenantId",
    ],
)
def test_validate_account_context_rejects_incomplete_response(
    collector_module: ModuleType,
    missing_property: str,
) -> None:
    """Incomplete Azure CLI account responses are rejected."""
    account = {
        "id": SUBSCRIPTION_ID,
        "name": "Production",
        "state": "Enabled",
        "tenantId": TENANT_ID,
    }
    del account[missing_property]

    with pytest.raises(ValueError, match="missing required property"):
        collector_module.validate_account_context(
            account,
            expected_subscription_id=SUBSCRIPTION_ID,
            expected_tenant_id=TENANT_ID,
        )


def test_execute_json_command_uses_no_shell(
    collector_module: ModuleType,
) -> None:
    """Azure CLI commands execute as argument arrays without a shell."""
    observed: dict[str, object] = {}

    def fake_runner(
        command: list[str],
        **kwargs: object,
    ) -> SimpleNamespace:
        observed["command"] = command
        observed["kwargs"] = kwargs
        return SimpleNamespace(
            returncode=0,
            stdout='{"id": "11111111-1111-4111-8111-111111111111"}',
            stderr="",
        )

    command = collector_module.build_account_show_command()
    result = collector_module.execute_json_command(
        command,
        runner=fake_runner,
    )

    assert result == {"id": SUBSCRIPTION_ID}
    assert observed["command"] == command
    assert observed["kwargs"] == {
        "capture_output": True,
        "check": False,
        "shell": False,
        "text": True,
    }


def test_execute_json_command_rejects_cli_failure(
    collector_module: ModuleType,
) -> None:
    """A failed Azure CLI command stops inventory collection."""

    def fake_runner(
        command: list[str],
        **kwargs: object,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="Please run az login.",
        )

    with pytest.raises(RuntimeError, match="Please run az login"):
        collector_module.execute_json_command(
            collector_module.build_account_show_command(),
            runner=fake_runner,
        )


@pytest.mark.parametrize(
    "stdout",
    [
        "",
        "not-json",
        "[]",
        '"text"',
    ],
)
def test_execute_json_command_rejects_invalid_json_object(
    collector_module: ModuleType,
    stdout: str,
) -> None:
    """Azure CLI output must be a valid JSON object."""

    def fake_runner(
        command: list[str],
        **kwargs: object,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    with pytest.raises(RuntimeError, match="valid JSON object"):
        collector_module.execute_json_command(
            collector_module.build_account_show_command(),
            runner=fake_runner,
        )


def test_resource_inventory_query_collects_metadata_only(
    collector_module: ModuleType,
) -> None:
    """The baseline query must collect metadata without configuration payloads."""
    query = collector_module.RESOURCE_INVENTORY_QUERY
    normalized_query = query.lower()

    required_fields = [
        "id",
        "name",
        "type",
        "location",
        "resourcegroup",
        "subscriptionid",
        "kind",
        "managedby",
    ]

    assert normalized_query.startswith("resources")
    assert "| project " in normalized_query
    assert "| order by " in normalized_query

    for field in required_fields:
        assert field in normalized_query

    prohibited_fields = [
        "properties",
        "identity",
        "tags",
        "extendedlocation",
    ]

    for field in prohibited_fields:
        assert field not in normalized_query


def test_extract_resource_records_accepts_scoped_response(
    collector_module: ModuleType,
) -> None:
    """Resource metadata from the approved subscription is normalized."""
    response = {
        "count": 1,
        "data": [
            {
                "id": (
                    "/subscriptions/"
                    f"{SUBSCRIPTION_ID}"
                    "/resourceGroups/rg-platform-weu-prd"
                    "/providers/Microsoft.Network/virtualNetworks/"
                    "vnet-platform-weu-prd"
                ),
                "name": "vnet-platform-weu-prd",
                "type": "microsoft.network/virtualnetworks",
                "location": "westeurope",
                "resourceGroup": "rg-platform-weu-prd",
                "subscriptionId": SUBSCRIPTION_ID,
                "kind": None,
                "managedBy": None,
            }
        ],
        "totalRecords": 1,
    }

    records = collector_module.extract_resource_records(
        response,
        expected_subscription_id=SUBSCRIPTION_ID,
    )

    assert records == response["data"]
    assert records is not response["data"]


def test_extract_resource_records_rejects_cross_subscription_data(
    collector_module: ModuleType,
) -> None:
    """A record outside the approved subscription stops collection."""
    other_subscription_id = "33333333-3333-4333-8333-333333333333"
    response = {
        "data": [
            {
                "id": (
                    "/subscriptions/"
                    f"{other_subscription_id}"
                    "/resourceGroups/rg-other"
                    "/providers/Microsoft.Storage/storageAccounts/stother"
                ),
                "name": "stother",
                "type": "microsoft.storage/storageaccounts",
                "location": "westeurope",
                "resourceGroup": "rg-other",
                "subscriptionId": other_subscription_id,
                "kind": "StorageV2",
                "managedBy": None,
            }
        ]
    }

    with pytest.raises(ValueError, match="outside the approved subscription"):
        collector_module.extract_resource_records(
            response,
            expected_subscription_id=SUBSCRIPTION_ID,
        )


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"data": None},
        {"data": {}},
        {"data": "unexpected"},
    ],
)
def test_extract_resource_records_rejects_invalid_data_collection(
    collector_module: ModuleType,
    response: dict[str, object],
) -> None:
    """Resource Graph data must be represented as an array."""
    with pytest.raises(ValueError, match="'data' array"):
        collector_module.extract_resource_records(
            response,
            expected_subscription_id=SUBSCRIPTION_ID,
        )


def test_extract_resource_records_rejects_incomplete_record(
    collector_module: ModuleType,
) -> None:
    """Every discovered resource must contain stable identifying metadata."""
    response = {
        "data": [
            {
                "id": "/subscriptions/example/resourceGroups/rg-example",
                "name": "incomplete",
            }
        ]
    }

    with pytest.raises(ValueError, match="missing required property"):
        collector_module.extract_resource_records(
            response,
            expected_subscription_id=SUBSCRIPTION_ID,
        )
