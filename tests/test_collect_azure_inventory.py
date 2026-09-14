"""Tests for the read-only Azure inventory collector."""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
COLLECTOR_PATH = REPOSITORY_ROOT / "scripts" / "python" / "collect_azure_inventory.py"

INVENTORY_SCHEMA_PATH = REPOSITORY_ROOT / "templates" / "azure-inventory.schema.json"

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


def test_build_inventory_document_marks_evidence_unconfirmed(
    collector_module: ModuleType,
) -> None:
    """Collected Azure state remains evidence pending human confirmation."""
    account = {
        "subscriptionId": SUBSCRIPTION_ID,
        "subscriptionName": "Production",
        "tenantId": TENANT_ID,
    }
    resources = [
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
    ]
    collected_at = datetime(
        2026,
        9,
        14,
        8,
        30,
        tzinfo=timezone.utc,
    )

    document = collector_module.build_inventory_document(
        account,
        resources,
        collected_at=collected_at,
    )

    assert document == {
        "schemaVersion": "1.0",
        "evidenceStatus": "unconfirmed",
        "collectedAt": "2026-09-14T08:30:00Z",
        "source": {
            "type": "azure",
            "provider": "Azure Resource Graph",
            "readOnly": True,
            "query": collector_module.RESOURCE_INVENTORY_QUERY,
        },
        "scope": account,
        "resourceCount": 1,
        "resources": resources,
    }


def test_build_inventory_document_copies_mutable_input(
    collector_module: ModuleType,
) -> None:
    """The evidence document must not retain mutable caller-owned collections."""
    account = {
        "subscriptionId": SUBSCRIPTION_ID,
        "subscriptionName": "Production",
        "tenantId": TENANT_ID,
    }
    resources: list[dict[str, object]] = []

    document = collector_module.build_inventory_document(
        account,
        resources,
        collected_at=datetime(
            2026,
            9,
            14,
            8,
            30,
            tzinfo=timezone.utc,
        ),
    )

    account["subscriptionName"] = "Changed"
    resources.append({"name": "unexpected"})

    assert document["scope"]["subscriptionName"] == "Production"
    assert document["resources"] == []
    assert document["resourceCount"] == 0


def test_build_inventory_document_converts_timestamp_to_utc(
    collector_module: ModuleType,
) -> None:
    """Evidence timestamps are normalized to UTC."""
    local_time = datetime.fromisoformat("2026-09-14T10:30:00+02:00")

    document = collector_module.build_inventory_document(
        {
            "subscriptionId": SUBSCRIPTION_ID,
            "subscriptionName": "Production",
            "tenantId": TENANT_ID,
        },
        [],
        collected_at=local_time,
    )

    assert document["collectedAt"] == "2026-09-14T08:30:00Z"


def test_build_inventory_document_rejects_naive_timestamp(
    collector_module: ModuleType,
) -> None:
    """Evidence timestamps must include timezone information."""
    with pytest.raises(ValueError, match="timezone-aware"):
        collector_module.build_inventory_document(
            {
                "subscriptionId": SUBSCRIPTION_ID,
                "subscriptionName": "Production",
                "tenantId": TENANT_ID,
            },
            [],
            collected_at=datetime(2026, 9, 14, 8, 30),
        )


def load_inventory_schema() -> dict[str, object]:
    """Load the Azure inventory JSON Schema."""
    with INVENTORY_SCHEMA_PATH.open("r", encoding="utf-8") as stream:
        schema = json.load(stream)

    assert isinstance(schema, dict)
    return schema


def build_valid_inventory_document(
    collector_module: ModuleType,
) -> dict[str, object]:
    """Build representative inventory evidence for schema tests."""
    account = {
        "subscriptionId": SUBSCRIPTION_ID,
        "subscriptionName": "Production",
        "tenantId": TENANT_ID,
    }
    resources = [
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
    ]

    return collector_module.build_inventory_document(
        account,
        resources,
        collected_at=datetime(
            2026,
            9,
            14,
            8,
            30,
            tzinfo=timezone.utc,
        ),
    )


def test_inventory_document_matches_schema(
    collector_module: ModuleType,
) -> None:
    """Representative inventory evidence must satisfy its JSON Schema."""
    schema = load_inventory_schema()
    document = build_valid_inventory_document(collector_module)
    validator = Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )

    assert list(validator.iter_errors(document)) == []


def test_inventory_schema_requires_unconfirmed_evidence(
    collector_module: ModuleType,
) -> None:
    """Raw inventory cannot claim human confirmation."""
    schema = load_inventory_schema()
    document = build_valid_inventory_document(collector_module)
    document["evidenceStatus"] = "confirmed"
    validator = Draft202012Validator(schema)

    errors = list(validator.iter_errors(document))

    assert any(error.validator == "const" for error in errors)


def test_inventory_schema_rejects_unknown_top_level_property(
    collector_module: ModuleType,
) -> None:
    """Uncontrolled properties must not silently enter the evidence contract."""
    schema = load_inventory_schema()
    document = build_valid_inventory_document(collector_module)
    document["unexpected"] = True
    validator = Draft202012Validator(schema)

    errors = list(validator.iter_errors(document))

    assert any(error.validator == "additionalProperties" for error in errors)


def test_parse_arguments_requires_explicit_scope_and_approval(
    collector_module: ModuleType,
) -> None:
    """The CLI requires approved scope and explicit read-only consent."""
    arguments = collector_module.parse_arguments(
        [
            "--subscription",
            SUBSCRIPTION_ID,
            "--tenant",
            TENANT_ID,
            "--approve-read-only",
        ]
    )

    assert arguments.subscription == SUBSCRIPTION_ID
    assert arguments.tenant == TENANT_ID
    assert arguments.approve_read_only is True
    assert arguments.output == Path(".specify/discovery/azure-inventory.json")
    assert arguments.overwrite is False


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        [
            "--subscription",
            SUBSCRIPTION_ID,
        ],
        [
            "--approve-read-only",
        ],
    ],
)
def test_parse_arguments_rejects_missing_required_consent_or_scope(
    collector_module: ModuleType,
    arguments: list[str],
) -> None:
    """Collection cannot start without both scope and approval."""
    with pytest.raises(SystemExit):
        collector_module.parse_arguments(arguments)


def test_parse_arguments_rejects_invalid_tenant(
    collector_module: ModuleType,
) -> None:
    """Invalid tenant input is rejected before Azure CLI execution."""
    with pytest.raises(SystemExit):
        collector_module.parse_arguments(
            [
                "--subscription",
                SUBSCRIPTION_ID,
                "--tenant",
                "not-a-tenant-id",
                "--approve-read-only",
            ]
        )


def test_parse_arguments_accepts_custom_output_path(
    collector_module: ModuleType,
) -> None:
    """The caller may choose a project-local output path."""
    output_path = Path(".specify/discovery/custom-inventory.json")

    arguments = collector_module.parse_arguments(
        [
            "--subscription",
            SUBSCRIPTION_ID,
            "--approve-read-only",
            "--output",
            str(output_path),
        ]
    )

    assert arguments.output == output_path


def test_validate_output_path_accepts_discovery_json(
    collector_module: ModuleType,
    tmp_path: Path,
) -> None:
    """Inventory output may be written under the project discovery folder."""
    project_root = tmp_path / "project"
    discovery_directory = project_root / ".specify" / "discovery"
    discovery_directory.mkdir(parents=True)

    output_path = collector_module.validate_output_path(
        Path(".specify/discovery/azure-inventory.json"),
        project_root=project_root,
    )

    assert output_path == (discovery_directory / "azure-inventory.json").resolve()


@pytest.mark.parametrize(
    "output_path",
    [
        Path("azure-inventory.json"),
        Path("../azure-inventory.json"),
        Path(".specify/azure-inventory.json"),
        Path(".specify/discovery/azure-inventory.txt"),
    ],
)
def test_validate_output_path_rejects_unsafe_destination(
    collector_module: ModuleType,
    tmp_path: Path,
    output_path: Path,
) -> None:
    """Inventory output must remain a JSON file in the discovery folder."""
    project_root = tmp_path / "project"
    (project_root / ".specify" / "discovery").mkdir(parents=True)

    with pytest.raises(ValueError, match=r"discovery.*JSON"):
        collector_module.validate_output_path(
            output_path,
            project_root=project_root,
        )


def test_validate_output_path_rejects_non_speckit_project(
    collector_module: ModuleType,
    tmp_path: Path,
) -> None:
    """Inventory cannot be written outside a Spec Kit project."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    with pytest.raises(ValueError, match="Spec Kit project"):
        collector_module.validate_output_path(
            Path(".specify/discovery/azure-inventory.json"),
            project_root=project_root,
        )


def test_parse_arguments_accepts_explicit_overwrite(
    collector_module: ModuleType,
) -> None:
    """Existing evidence may be replaced only through explicit consent."""
    arguments = collector_module.parse_arguments(
        [
            "--subscription",
            SUBSCRIPTION_ID,
            "--approve-read-only",
            "--overwrite",
        ]
    )

    assert arguments.overwrite is True


def test_write_inventory_document_creates_json_file(
    collector_module: ModuleType,
    tmp_path: Path,
) -> None:
    """Inventory evidence is written as readable UTF-8 JSON."""
    output_path = tmp_path / ".specify" / "discovery" / "azure-inventory.json"
    document = build_valid_inventory_document(collector_module)

    collector_module.write_inventory_document(
        document,
        output_path,
        overwrite=False,
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == document
    assert output_path.read_bytes().endswith(b"\n")


def test_write_inventory_document_rejects_implicit_overwrite(
    collector_module: ModuleType,
    tmp_path: Path,
) -> None:
    """Existing evidence is preserved without explicit overwrite consent."""
    output_path = tmp_path / "azure-inventory.json"
    output_path.write_text(
        '{"existing": true}\n',
        encoding="utf-8",
    )

    with pytest.raises(FileExistsError, match="--overwrite"):
        collector_module.write_inventory_document(
            build_valid_inventory_document(collector_module),
            output_path,
            overwrite=False,
        )

    assert json.loads(output_path.read_text(encoding="utf-8")) == {"existing": True}


def test_write_inventory_document_allows_explicit_overwrite(
    collector_module: ModuleType,
    tmp_path: Path,
) -> None:
    """Explicit overwrite replaces earlier inventory evidence."""
    output_path = tmp_path / "azure-inventory.json"
    output_path.write_text(
        '{"existing": true}\n',
        encoding="utf-8",
    )
    document = build_valid_inventory_document(collector_module)

    collector_module.write_inventory_document(
        document,
        output_path,
        overwrite=True,
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == document


def test_collect_inventory_runs_scoped_read_only_workflow(
    collector_module: ModuleType,
) -> None:
    """Collection validates context before querying scoped resource metadata."""
    account_response = {
        "id": SUBSCRIPTION_ID,
        "name": "Production",
        "state": "Enabled",
        "tenantId": TENANT_ID,
    }
    graph_response = {
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
        ]
    }
    responses = [
        SimpleNamespace(
            returncode=0,
            stdout=json.dumps(account_response),
            stderr="",
        ),
        SimpleNamespace(
            returncode=0,
            stdout=json.dumps(graph_response),
            stderr="",
        ),
    ]
    observed_commands: list[list[str]] = []

    def fake_runner(
        command: list[str],
        **kwargs: object,
    ) -> SimpleNamespace:
        observed_commands.append(command)
        return responses.pop(0)

    document = collector_module.collect_inventory(
        subscription_id=SUBSCRIPTION_ID,
        tenant_id=TENANT_ID,
        collected_at=datetime(
            2026,
            9,
            14,
            8,
            30,
            tzinfo=timezone.utc,
        ),
        runner=fake_runner,
    )

    assert observed_commands == [
        collector_module.build_account_show_command(),
        collector_module.build_resource_graph_command(
            SUBSCRIPTION_ID,
            collector_module.RESOURCE_INVENTORY_QUERY,
        ),
    ]
    assert document["scope"] == {
        "subscriptionId": SUBSCRIPTION_ID,
        "subscriptionName": "Production",
        "tenantId": TENANT_ID,
    }
    assert document["resourceCount"] == 1
    assert document["evidenceStatus"] == "unconfirmed"
    assert responses == []


def test_collect_inventory_stops_before_query_on_context_mismatch(
    collector_module: ModuleType,
) -> None:
    """Resource Graph is not queried when the active scope is incorrect."""
    wrong_subscription_id = "33333333-3333-4333-8333-333333333333"
    observed_commands: list[list[str]] = []

    def fake_runner(
        command: list[str],
        **kwargs: object,
    ) -> SimpleNamespace:
        observed_commands.append(command)
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "id": wrong_subscription_id,
                    "name": "Wrong subscription",
                    "state": "Enabled",
                    "tenantId": TENANT_ID,
                }
            ),
            stderr="",
        )

    with pytest.raises(
        ValueError,
        match="Active subscription does not match",
    ):
        collector_module.collect_inventory(
            subscription_id=SUBSCRIPTION_ID,
            tenant_id=TENANT_ID,
            collected_at=datetime(
                2026,
                9,
                14,
                8,
                30,
                tzinfo=timezone.utc,
            ),
            runner=fake_runner,
        )

    assert observed_commands == [collector_module.build_account_show_command()]


def test_validate_inventory_document_accepts_valid_evidence(
    collector_module: ModuleType,
) -> None:
    """Valid inventory evidence passes schema and semantic validation."""
    collector_module.validate_inventory_document(
        build_valid_inventory_document(collector_module),
        load_inventory_schema(),
    )


def test_validate_inventory_document_rejects_count_mismatch(
    collector_module: ModuleType,
) -> None:
    """The recorded resource count must match the resource collection."""
    document = build_valid_inventory_document(collector_module)
    document["resourceCount"] = 2

    with pytest.raises(
        ValueError,
        match=r"resourceCount.*actual resource count",
    ):
        collector_module.validate_inventory_document(
            document,
            load_inventory_schema(),
        )


def test_validate_inventory_document_rejects_schema_violation(
    collector_module: ModuleType,
) -> None:
    """Invalid evidence cannot be written to disk."""
    document = build_valid_inventory_document(collector_module)
    document["unexpected"] = True

    with pytest.raises(
        ValueError,
        match="Inventory schema validation failed",
    ):
        collector_module.validate_inventory_document(
            document,
            load_inventory_schema(),
        )


def test_run_collects_validates_and_writes_inventory(
    collector_module: ModuleType,
    tmp_path: Path,
) -> None:
    """The application workflow produces validated project-local evidence."""
    project_root = tmp_path / "project"
    (project_root / ".specify").mkdir(parents=True)

    account_response = {
        "id": SUBSCRIPTION_ID,
        "name": "Production",
        "state": "Enabled",
        "tenantId": TENANT_ID,
    }
    graph_response = {
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
        ]
    }
    responses = [
        SimpleNamespace(
            returncode=0,
            stdout=json.dumps(account_response),
            stderr="",
        ),
        SimpleNamespace(
            returncode=0,
            stdout=json.dumps(graph_response),
            stderr="",
        ),
    ]

    def fake_runner(
        command: list[str],
        **kwargs: object,
    ) -> SimpleNamespace:
        return responses.pop(0)

    output_path = collector_module.run(
        [
            "--subscription",
            SUBSCRIPTION_ID,
            "--tenant",
            TENANT_ID,
            "--approve-read-only",
        ],
        project_root=project_root,
        collected_at=datetime(
            2026,
            9,
            14,
            8,
            30,
            tzinfo=timezone.utc,
        ),
        runner=fake_runner,
    )

    assert (
        output_path == (project_root / ".specify" / "discovery" / "azure-inventory.json").resolve()
    )
    document = json.loads(output_path.read_text(encoding="utf-8"))
    collector_module.validate_inventory_document(
        document,
        load_inventory_schema(),
    )
    assert document["resourceCount"] == 1
    assert document["evidenceStatus"] == "unconfirmed"
    assert responses == []


def test_main_reports_successful_unconfirmed_collection(
    collector_module: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI reports the output path and unconfirmed evidence status."""
    project_root = tmp_path / "project"
    (project_root / ".specify").mkdir(parents=True)

    responses = [
        SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "id": SUBSCRIPTION_ID,
                    "name": "Production",
                    "state": "Enabled",
                    "tenantId": TENANT_ID,
                }
            ),
            stderr="",
        ),
        SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"data": []}),
            stderr="",
        ),
    ]

    def fake_runner(
        command: list[str],
        **kwargs: object,
    ) -> SimpleNamespace:
        return responses.pop(0)

    exit_code = collector_module.main(
        [
            "--subscription",
            SUBSCRIPTION_ID,
            "--tenant",
            TENANT_ID,
            "--approve-read-only",
        ],
        project_root=project_root,
        collected_at=datetime(
            2026,
            9,
            14,
            8,
            30,
            tzinfo=timezone.utc,
        ),
        runner=fake_runner,
    )

    captured = capsys.readouterr()

    assert exit_code == collector_module.EXIT_SUCCESS
    assert "azure-inventory.json" in captured.out
    assert "unconfirmed" in captured.out.lower()
    assert captured.err == ""


def test_main_reports_controlled_execution_error(
    collector_module: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Expected safety failures return a stable execution-error code."""
    project_root = tmp_path / "not-a-speckit-project"
    project_root.mkdir()

    exit_code = collector_module.main(
        [
            "--subscription",
            SUBSCRIPTION_ID,
            "--approve-read-only",
        ],
        project_root=project_root,
    )

    captured = capsys.readouterr()

    assert exit_code == collector_module.EXIT_EXECUTION_ERROR
    assert captured.out == ""
    assert "Spec Kit project" in captured.err
