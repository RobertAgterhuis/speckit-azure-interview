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
        "--query",
        "{id:id,name:name,state:state,tenantId:tenantId}",
        "--output",
        "json",
        "--only-show-errors",
    ]


def test_build_resource_graph_command_scopes_query_to_subscription(
    collector_module: ModuleType,
) -> None:
    """Resource Graph queries remain scoped and use bounded pages."""
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
        "--first",
        "1000",
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
    """Collection validates context before running seven paged queries."""
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
    responses.extend(
        SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"data": []}),
            stderr="",
        )
        for _ in collector_module.TOPOLOGY_RELATIONSHIP_QUERIES
    )
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

    expected_commands = [
        collector_module.build_account_show_command(),
        collector_module.build_resource_graph_command(
            SUBSCRIPTION_ID,
            collector_module.RESOURCE_INVENTORY_QUERY,
        ),
    ]
    expected_commands.extend(
        collector_module.build_resource_graph_command(
            SUBSCRIPTION_ID,
            query,
        )
        for _, query in collector_module.TOPOLOGY_RELATIONSHIP_QUERIES
    )

    assert observed_commands == expected_commands
    assert document["scope"] == {
        "subscriptionId": SUBSCRIPTION_ID,
        "subscriptionName": "Production",
        "tenantId": TENANT_ID,
    }
    assert document["resourceCount"] == 1
    assert document["evidenceStatus"] == "unconfirmed"
    assert document["topology"] == {
        "relationshipCount": 0,
        "relationships": [],
    }
    assert document["source"]["topologyQueries"] == [
        query for _, query in collector_module.TOPOLOGY_RELATIONSHIP_QUERIES
    ]
    assert "topologyQuery" not in document["source"]
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
        SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"data": []}),
            stderr="",
        ),
    ]
    responses.extend(
        SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"data": []}),
            stderr="",
        )
        for _ in range(len(collector_module.TOPOLOGY_RELATIONSHIP_QUERIES) - 1)
    )

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
        SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"data": []}),
            stderr="",
        ),
    ]
    responses.extend(
        SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"data": []}),
            stderr="",
        )
        for _ in range(len(collector_module.TOPOLOGY_RELATIONSHIP_QUERIES) - 1)
    )

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


def test_execute_json_command_retries_windows_azure_cli_wrapper(
    collector_module: ModuleType,
) -> None:
    """The executor safely retries az.cmd when the az launcher is unavailable."""
    observed_commands: list[list[str]] = []

    def fake_runner(
        command: list[str],
        **kwargs: object,
    ) -> SimpleNamespace:
        observed_commands.append(command)

        if command[0] == "az":
            raise FileNotFoundError

        return SimpleNamespace(
            returncode=0,
            stdout='{"state": "Enabled"}',
            stderr="",
        )

    result = collector_module.execute_json_command(
        collector_module.build_account_show_command(),
        runner=fake_runner,
    )

    assert result == {"state": "Enabled"}
    assert observed_commands[0][0] == "az"
    assert observed_commands[1][0] == "az.cmd"


def test_extract_resource_records_removes_unexpected_fields(
    collector_module: ModuleType,
) -> None:
    """Only explicitly approved metadata enters inventory evidence."""
    response = {
        "data": [
            {
                "id": (
                    "/subscriptions/"
                    f"{SUBSCRIPTION_ID}"
                    "/resourceGroups/rg-platform-weu-prd"
                    "/providers/Microsoft.Storage/storageAccounts/"
                    "stplatformweuprd"
                ),
                "name": "stplatformweuprd",
                "type": "microsoft.storage/storageaccounts",
                "location": "westeurope",
                "resourceGroup": "rg-platform-weu-prd",
                "subscriptionId": SUBSCRIPTION_ID,
                "kind": "StorageV2",
                "managedBy": None,
                "properties": {"unexpected": "must-not-be-copied"},
                "identity": {"principalId": "must-not-be-copied"},
                "tags": {"confidential": "must-not-be-copied"},
                "sku": {"name": "Standard_LRS"},
                "tenantId": TENANT_ID,
                "zones": ["1"],
            }
        ]
    }

    records = collector_module.extract_resource_records(
        response,
        expected_subscription_id=SUBSCRIPTION_ID,
    )

    assert records == [
        {
            "id": response["data"][0]["id"],
            "name": "stplatformweuprd",
            "type": "microsoft.storage/storageaccounts",
            "location": "westeurope",
            "resourceGroup": "rg-platform-weu-prd",
            "subscriptionId": SUBSCRIPTION_ID,
            "kind": "StorageV2",
            "managedBy": None,
        }
    ]


def test_run_stops_before_azure_when_output_exists(
    collector_module: ModuleType,
    tmp_path: Path,
) -> None:
    """Existing evidence blocks Azure calls unless overwrite was approved."""
    project_root = tmp_path / "project"
    output_path = project_root / ".specify" / "discovery" / "azure-inventory.json"
    output_path.parent.mkdir(parents=True)
    output_path.write_text(
        '{"existing": true}\n',
        encoding="utf-8",
    )
    azure_called = False

    def unexpected_runner(
        command: list[str],
        **kwargs: object,
    ) -> SimpleNamespace:
        nonlocal azure_called
        azure_called = True
        raise AssertionError("Azure CLI must not run when output already exists.")

    with pytest.raises(FileExistsError, match="--overwrite"):
        collector_module.run(
            [
                "--subscription",
                SUBSCRIPTION_ID,
                "--approve-read-only",
            ],
            project_root=project_root,
            runner=unexpected_runner,
        )

    assert azure_called is False
    assert json.loads(output_path.read_text(encoding="utf-8")) == {"existing": True}


def build_topology_relationship(
    *,
    relationship_type: str = "vnet-contains-subnet",
    source_resource_id: str | None = None,
    source_resource_type: str = "microsoft.network/virtualnetworks",
    target_resource_id: str | None = None,
    target_resource_type: str = "microsoft.network/virtualnetworks/subnets",
    target_scope: str = "in-scope",
) -> dict[str, object]:
    """Build representative controlled topology evidence."""
    effective_source_id = source_resource_id or (
        "/subscriptions/"
        f"{SUBSCRIPTION_ID}"
        "/resourceGroups/rg-network/providers/"
        "Microsoft.Network/virtualNetworks/vnet-hub"
    )
    effective_target_id = target_resource_id or (
        f"{effective_source_id}/subnets/AzureFirewallSubnet"
    )

    return {
        "relationshipType": relationship_type,
        "sourceResourceId": effective_source_id,
        "sourceResourceType": source_resource_type,
        "targetResourceId": effective_target_id,
        "targetResourceType": target_resource_type,
        "targetScope": target_scope,
    }


def test_inventory_schema_accepts_optional_brownfield_topology(
    collector_module: ModuleType,
) -> None:
    """Topology evidence is an optional backward-compatible inventory extension."""
    schema = load_inventory_schema()
    document = build_valid_inventory_document(collector_module)
    document["topology"] = {
        "relationshipCount": 1,
        "relationships": [
            build_topology_relationship(),
        ],
    }

    validator = Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )

    assert list(validator.iter_errors(document)) == []


@pytest.mark.parametrize(
    "relationship_type",
    [
        "vnet-contains-subnet",
        "vnet-peered-with-vnet",
        "subnet-associated-with-nsg",
        "subnet-associated-with-route-table",
        "private-endpoint-placed-in-subnet",
        "private-dns-zone-linked-to-vnet",
    ],
)
def test_inventory_schema_accepts_supported_topology_relationship_types(
    collector_module: ModuleType,
    relationship_type: str,
) -> None:
    """The schema permits only the explicitly supported topology vocabulary."""
    schema = load_inventory_schema()
    document = build_valid_inventory_document(collector_module)
    document["topology"] = {
        "relationshipCount": 1,
        "relationships": [
            build_topology_relationship(
                relationship_type=relationship_type,
            ),
        ],
    }

    validator = Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )

    assert list(validator.iter_errors(document)) == []


def test_inventory_schema_rejects_unsupported_topology_relationship(
    collector_module: ModuleType,
) -> None:
    """Arbitrary relationships cannot enter controlled inventory evidence."""
    schema = load_inventory_schema()
    document = build_valid_inventory_document(collector_module)
    document["topology"] = {
        "relationshipCount": 1,
        "relationships": [
            build_topology_relationship(
                relationship_type="resource-depends-on-resource",
            ),
        ],
    }

    validator = Draft202012Validator(schema)

    assert list(validator.iter_errors(document))


def test_normalize_topology_relationships_deduplicates_and_sorts(
    collector_module: ModuleType,
) -> None:
    """Topology relationships are deterministic and case-insensitively unique."""
    vnet_id = (
        "/subscriptions/"
        f"{SUBSCRIPTION_ID}"
        "/resourceGroups/rg-network/providers/"
        "Microsoft.Network/virtualNetworks/vnet-hub"
    )
    subnet_id = f"{vnet_id}/subnets/snet-app"
    nsg_id = (
        "/subscriptions/"
        f"{SUBSCRIPTION_ID}"
        "/resourceGroups/rg-network/providers/"
        "Microsoft.Network/networkSecurityGroups/nsg-app"
    )

    records = [
        {
            "relationshipType": "subnet-associated-with-nsg",
            "sourceResourceId": subnet_id,
            "sourceResourceType": "microsoft.network/virtualnetworks/subnets",
            "targetResourceId": nsg_id,
            "targetResourceType": "microsoft.network/networksecuritygroups",
        },
        {
            "relationshipType": "vnet-contains-subnet",
            "sourceResourceId": vnet_id,
            "sourceResourceType": "microsoft.network/virtualnetworks",
            "targetResourceId": subnet_id,
            "targetResourceType": "microsoft.network/virtualnetworks/subnets",
        },
        {
            "relationshipType": "subnet-associated-with-nsg",
            "sourceResourceId": subnet_id.upper(),
            "sourceResourceType": "Microsoft.Network/virtualNetworks/subnets",
            "targetResourceId": nsg_id.upper(),
            "targetResourceType": "Microsoft.Network/networkSecurityGroups",
        },
    ]

    relationships = collector_module.normalize_topology_relationships(
        records,
        expected_subscription_id=SUBSCRIPTION_ID,
    )

    assert len(relationships) == 2
    assert [relationship["relationshipType"] for relationship in relationships] == [
        "subnet-associated-with-nsg",
        "vnet-contains-subnet",
    ]
    assert all(relationship["targetScope"] == "in-scope" for relationship in relationships)


def test_normalize_topology_relationships_classifies_target_scope(
    collector_module: ModuleType,
) -> None:
    """Targets are classified without querying another subscription."""
    other_subscription_id = "33333333-3333-4333-8333-333333333333"
    source_id = (
        "/subscriptions/"
        f"{SUBSCRIPTION_ID}"
        "/resourceGroups/rg-network/providers/"
        "Microsoft.Network/virtualNetworks/vnet-hub"
    )
    external_target_id = (
        "/subscriptions/"
        f"{other_subscription_id}"
        "/resourceGroups/rg-connectivity/providers/"
        "Microsoft.Network/virtualNetworks/vnet-external"
    )

    records = [
        {
            "relationshipType": "vnet-peered-with-vnet",
            "sourceResourceId": source_id,
            "sourceResourceType": "microsoft.network/virtualnetworks",
            "targetResourceId": external_target_id,
            "targetResourceType": "microsoft.network/virtualnetworks",
        },
        {
            "relationshipType": "vnet-peered-with-vnet",
            "sourceResourceId": source_id,
            "sourceResourceType": "microsoft.network/virtualnetworks",
            "targetResourceId": None,
            "targetResourceType": "microsoft.network/virtualnetworks",
        },
    ]

    relationships = collector_module.normalize_topology_relationships(
        records,
        expected_subscription_id=SUBSCRIPTION_ID,
    )

    assert [relationship["targetScope"] for relationship in relationships] == [
        "external-subscription",
        "unresolved",
    ]


def test_normalize_topology_relationships_rejects_external_source(
    collector_module: ModuleType,
) -> None:
    """Every relationship source must belong to the approved subscription."""
    other_subscription_id = "33333333-3333-4333-8333-333333333333"
    external_source_id = (
        "/subscriptions/"
        f"{other_subscription_id}"
        "/resourceGroups/rg-external/providers/"
        "Microsoft.Network/virtualNetworks/vnet-external"
    )

    with pytest.raises(
        ValueError,
        match=r"source.*outside the approved subscription",
    ):
        collector_module.normalize_topology_relationships(
            [
                {
                    "relationshipType": "vnet-contains-subnet",
                    "sourceResourceId": external_source_id,
                    "sourceResourceType": "microsoft.network/virtualnetworks",
                    "targetResourceId": (f"{external_source_id}/subnets/snet-app"),
                    "targetResourceType": ("microsoft.network/virtualnetworks/subnets"),
                }
            ],
            expected_subscription_id=SUBSCRIPTION_ID,
        )


def test_validate_inventory_document_rejects_topology_count_mismatch(
    collector_module: ModuleType,
) -> None:
    """The recorded relationship count must equal the relationship collection."""
    document = build_valid_inventory_document(collector_module)
    document["topology"] = {
        "relationshipCount": 2,
        "relationships": [
            build_topology_relationship(),
        ],
    }

    with pytest.raises(
        ValueError,
        match=r"relationshipCount.*actual relationship count",
    ):
        collector_module.validate_inventory_document(
            document,
            load_inventory_schema(),
        )


def test_topology_relationship_query_projects_only_controlled_fields(
    collector_module: ModuleType,
) -> None:
    """Every topology query emits only the controlled projection."""
    required_projection = (
        "| project relationshiptype, sourceresourceid, "
        "sourceresourcetype, targetresourceid, targetresourcetype"
    )

    assert len(collector_module.TOPOLOGY_RELATIONSHIP_QUERIES) == 6

    for relationship_type, query in collector_module.TOPOLOGY_RELATIONSHIP_QUERIES:
        normalized_query = " ".join(query.split()).casefold()

        assert relationship_type.casefold() in normalized_query
        assert required_projection in normalized_query
        assert "tags" not in normalized_query
        assert "identity" not in normalized_query
        assert "extendedlocation" not in normalized_query
        assert "managedby" not in normalized_query


def test_topology_relationship_query_covers_supported_resource_types(
    collector_module: ModuleType,
) -> None:
    """The isolated queries cover every supported resource family."""
    normalized_queries = "\n".join(
        query for _, query in collector_module.TOPOLOGY_RELATIONSHIP_QUERIES
    ).casefold()

    required_resource_types = [
        "microsoft.network/virtualnetworks",
        "microsoft.network/networksecuritygroups",
        "microsoft.network/routetables",
        "microsoft.network/privateendpoints",
        "microsoft.network/privatednszones/virtualnetworklinks",
    ]

    for resource_type in required_resource_types:
        assert resource_type in normalized_queries


def test_extract_topology_relationship_records_strips_unexpected_payloads(
    collector_module: ModuleType,
) -> None:
    """Query payloads cannot leak into controlled topology evidence."""
    vnet_id = (
        "/subscriptions/"
        f"{SUBSCRIPTION_ID}"
        "/resourceGroups/rg-network/providers/"
        "Microsoft.Network/virtualNetworks/vnet-hub"
    )
    subnet_id = f"{vnet_id}/subnets/snet-app"

    response = {
        "count": 1,
        "data": [
            {
                "relationshipType": "vnet-contains-subnet",
                "sourceResourceId": vnet_id,
                "sourceResourceType": "microsoft.network/virtualnetworks",
                "targetResourceId": subnet_id,
                "targetResourceType": ("microsoft.network/virtualnetworks/subnets"),
                "properties": {
                    "addressPrefix": "10.20.1.0/24",
                    "privateEndpointNetworkPolicies": "Disabled",
                },
                "tags": {
                    "owner": "platform",
                },
                "identity": {
                    "principalId": "must-not-be-copied",
                },
            }
        ],
    }

    relationships = collector_module.extract_topology_relationship_records(
        response,
        expected_subscription_id=SUBSCRIPTION_ID,
    )

    assert relationships == [
        {
            "relationshipType": "vnet-contains-subnet",
            "sourceResourceId": vnet_id.casefold(),
            "sourceResourceType": "microsoft.network/virtualnetworks",
            "targetResourceId": subnet_id.casefold(),
            "targetResourceType": ("microsoft.network/virtualnetworks/subnets"),
            "targetScope": "in-scope",
        }
    ]


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"data": None},
        {"data": {}},
        {"data": "not-an-array"},
    ],
)
def test_extract_topology_relationship_records_rejects_invalid_data(
    collector_module: ModuleType,
    response: dict[str, object],
) -> None:
    """Topology query output must contain a data array."""
    with pytest.raises(
        ValueError,
        match=r"topology.*'data' array",
    ):
        collector_module.extract_topology_relationship_records(
            response,
            expected_subscription_id=SUBSCRIPTION_ID,
        )


def test_collect_inventory_adds_topology_evidence(
    collector_module: ModuleType,
) -> None:
    """Collection combines evidence from six isolated topology queries."""
    vnet_id = (
        "/subscriptions/"
        f"{SUBSCRIPTION_ID}"
        "/resourceGroups/rg-network/providers/"
        "Microsoft.Network/virtualNetworks/vnet-hub"
    )
    subnet_id = f"{vnet_id}/subnets/snet-app"
    observed_commands: list[list[str]] = []

    responses: list[dict[str, object]] = [
        {
            "id": SUBSCRIPTION_ID,
            "name": "Production",
            "state": "Enabled",
            "tenantId": TENANT_ID,
        },
        {
            "count": 0,
            "data": [],
        },
        {
            "count": 1,
            "data": [
                {
                    "relationshipType": "vnet-contains-subnet",
                    "sourceResourceId": vnet_id,
                    "sourceResourceType": ("microsoft.network/virtualnetworks"),
                    "targetResourceId": subnet_id,
                    "targetResourceType": ("microsoft.network/virtualnetworks/subnets"),
                    "properties": {
                        "addressPrefix": "10.20.1.0/24",
                    },
                }
            ],
        },
    ]
    responses.extend(
        {"count": 0, "data": []}
        for _ in range(len(collector_module.TOPOLOGY_RELATIONSHIP_QUERIES) - 1)
    )

    def fake_runner(
        command: list[str],
        **kwargs: object,
    ) -> SimpleNamespace:
        observed_commands.append(command)

        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(responses.pop(0)),
            stderr="",
        )

    document = collector_module.collect_inventory(
        subscription_id=SUBSCRIPTION_ID,
        tenant_id=TENANT_ID,
        collected_at=datetime(
            2026,
            9,
            15,
            14,
            0,
            tzinfo=timezone.utc,
        ),
        runner=fake_runner,
    )

    expected_commands = [
        collector_module.build_account_show_command(),
        collector_module.build_resource_graph_command(
            SUBSCRIPTION_ID,
            collector_module.RESOURCE_INVENTORY_QUERY,
        ),
    ]
    expected_commands.extend(
        collector_module.build_resource_graph_command(
            SUBSCRIPTION_ID,
            query,
        )
        for _, query in collector_module.TOPOLOGY_RELATIONSHIP_QUERIES
    )

    assert observed_commands == expected_commands
    assert responses == []
    assert document["resourceCount"] == 0
    assert document["resources"] == []
    assert document["source"]["query"] == (collector_module.RESOURCE_INVENTORY_QUERY)
    assert document["source"]["topologyQueries"] == [
        query for _, query in collector_module.TOPOLOGY_RELATIONSHIP_QUERIES
    ]
    assert "topologyQuery" not in document["source"]
    assert document["topology"] == {
        "relationshipCount": 1,
        "relationships": [
            {
                "relationshipType": "vnet-contains-subnet",
                "sourceResourceId": vnet_id.casefold(),
                "sourceResourceType": ("microsoft.network/virtualnetworks"),
                "targetResourceId": subnet_id.casefold(),
                "targetResourceType": ("microsoft.network/virtualnetworks/subnets"),
                "targetScope": "in-scope",
            }
        ],
    }

    collector_module.validate_inventory_document(
        document,
        load_inventory_schema(),
    )


def test_topology_normalization_is_independent_of_input_order(
    collector_module: ModuleType,
) -> None:
    """Equivalent Azure IDs produce identical evidence in every input order."""
    vnet_id = (
        "/subscriptions/"
        f"{SUBSCRIPTION_ID}"
        "/resourceGroups/RG-Network/providers/"
        "Microsoft.Network/virtualNetworks/VNET-Hub"
    )
    subnet_id = f"{vnet_id}/subnets/SNET-App"

    lower_case_record = {
        "relationshipType": "vnet-contains-subnet",
        "sourceResourceId": vnet_id.casefold(),
        "sourceResourceType": "microsoft.network/virtualnetworks",
        "targetResourceId": subnet_id.casefold(),
        "targetResourceType": ("microsoft.network/virtualnetworks/subnets"),
    }
    mixed_case_record = {
        "relationshipType": "vnet-contains-subnet",
        "sourceResourceId": vnet_id,
        "sourceResourceType": "Microsoft.Network/virtualNetworks",
        "targetResourceId": subnet_id,
        "targetResourceType": ("Microsoft.Network/virtualNetworks/subnets"),
    }

    forward = collector_module.normalize_topology_relationships(
        [
            mixed_case_record,
            lower_case_record,
        ],
        expected_subscription_id=SUBSCRIPTION_ID,
    )
    reversed_result = collector_module.normalize_topology_relationships(
        [
            lower_case_record,
            mixed_case_record,
        ],
        expected_subscription_id=SUBSCRIPTION_ID,
    )

    assert forward == reversed_result
    assert forward[0]["sourceResourceId"] == vnet_id.casefold()
    assert forward[0]["targetResourceId"] == subnet_id.casefold()


@pytest.mark.parametrize(
    (
        "relationship_type",
        "source_resource_type",
        "target_resource_type",
    ),
    [
        (
            "vnet-contains-subnet",
            "microsoft.network/privateendpoints",
            "microsoft.network/virtualnetworks/subnets",
        ),
        (
            "vnet-peered-with-vnet",
            "microsoft.network/virtualnetworks",
            "microsoft.network/networksecuritygroups",
        ),
        (
            "subnet-associated-with-nsg",
            "microsoft.network/virtualnetworks",
            "microsoft.network/networksecuritygroups",
        ),
        (
            "subnet-associated-with-route-table",
            "microsoft.network/virtualnetworks/subnets",
            "microsoft.network/networksecuritygroups",
        ),
        (
            "private-endpoint-placed-in-subnet",
            "microsoft.network/privateendpoints",
            "microsoft.network/virtualnetworks",
        ),
        (
            "private-dns-zone-linked-to-vnet",
            "microsoft.network/privatednszones/virtualnetworklinks",
            "microsoft.network/virtualnetworks",
        ),
    ],
)
def test_topology_normalization_rejects_incompatible_endpoint_types(
    collector_module: ModuleType,
    relationship_type: str,
    source_resource_type: str,
    target_resource_type: str,
) -> None:
    """Each relationship type has one controlled source and target contract."""
    source_id = (
        "/subscriptions/"
        f"{SUBSCRIPTION_ID}"
        "/resourceGroups/rg-network/providers/"
        "Microsoft.Network/example/source"
    )
    target_id = (
        "/subscriptions/"
        f"{SUBSCRIPTION_ID}"
        "/resourceGroups/rg-network/providers/"
        "Microsoft.Network/example/target"
    )

    with pytest.raises(
        ValueError,
        match=r"endpoint types.*relationship type",
    ):
        collector_module.normalize_topology_relationships(
            [
                {
                    "relationshipType": relationship_type,
                    "sourceResourceId": source_id,
                    "sourceResourceType": source_resource_type,
                    "targetResourceId": target_id,
                    "targetResourceType": target_resource_type,
                }
            ],
            expected_subscription_id=SUBSCRIPTION_ID,
        )


def test_topology_normalization_ignores_claimed_target_scope(
    collector_module: ModuleType,
) -> None:
    """Resource IDs, not caller-provided scope claims, determine target scope."""
    other_subscription_id = "33333333-3333-4333-8333-333333333333"
    source_id = (
        "/subscriptions/"
        f"{SUBSCRIPTION_ID}"
        "/resourceGroups/rg-network/providers/"
        "Microsoft.Network/virtualNetworks/vnet-hub"
    )
    target_id = (
        "/subscriptions/"
        f"{other_subscription_id}"
        "/resourceGroups/rg-external/providers/"
        "Microsoft.Network/virtualNetworks/vnet-external"
    )

    relationships = collector_module.normalize_topology_relationships(
        [
            {
                "relationshipType": "vnet-peered-with-vnet",
                "sourceResourceId": source_id,
                "sourceResourceType": "microsoft.network/virtualnetworks",
                "targetResourceId": target_id,
                "targetResourceType": "microsoft.network/virtualnetworks",
                "targetScope": "in-scope",
            }
        ],
        expected_subscription_id=SUBSCRIPTION_ID,
    )

    assert relationships[0]["targetScope"] == "external-subscription"


def test_topology_queries_are_independent(
    collector_module: ModuleType,
) -> None:
    """Each supported relationship uses an isolated Resource Graph query."""
    expected_relationship_types = (
        "vnet-contains-subnet",
        "vnet-peered-with-vnet",
        "subnet-associated-with-nsg",
        "subnet-associated-with-route-table",
        "private-endpoint-placed-in-subnet",
        "private-dns-zone-linked-to-vnet",
    )

    queries = collector_module.TOPOLOGY_RELATIONSHIP_QUERIES

    assert isinstance(queries, tuple)
    assert len(queries) == len(expected_relationship_types)
    assert (
        tuple(relationship_type for relationship_type, _ in queries) == expected_relationship_types
    )

    for relationship_type, query in queries:
        assert relationship_type in query
        assert query.strip()
        assert not query.lstrip().casefold().startswith("union")
        assert "| project relationshipType" in query


def test_resource_graph_command_supports_pagination(
    collector_module: ModuleType,
) -> None:
    """Resource Graph commands must use bounded pages and continuation tokens."""
    query = "Resources | project id"

    first_page_command = collector_module.build_resource_graph_command(
        SUBSCRIPTION_ID,
        query,
        page_size=1000,
    )
    next_page_command = collector_module.build_resource_graph_command(
        SUBSCRIPTION_ID,
        query,
        page_size=1000,
        skip_token="opaque-continuation-token",
    )

    assert first_page_command == [
        "az",
        "graph",
        "query",
        "--subscriptions",
        SUBSCRIPTION_ID,
        "--graph-query",
        query,
        "--first",
        "1000",
        "--output",
        "json",
        "--only-show-errors",
    ]
    assert next_page_command == [
        "az",
        "graph",
        "query",
        "--subscriptions",
        SUBSCRIPTION_ID,
        "--graph-query",
        query,
        "--first",
        "1000",
        "--skip-token",
        "opaque-continuation-token",
        "--output",
        "json",
        "--only-show-errors",
    ]


def test_resource_graph_pages_are_collected_completely(
    collector_module: ModuleType,
) -> None:
    """Every Resource Graph page is collected exactly once."""
    query = "Resources | project id"
    responses = [
        {
            "count": 2,
            "data": [
                {"id": "/subscriptions/example/resourceGroups/rg-a"},
                {"id": "/subscriptions/example/resourceGroups/rg-b"},
            ],
            "skipToken": "page-2-token",
            "totalRecords": 3,
        },
        {
            "count": 1,
            "data": [
                {"id": "/subscriptions/example/resourceGroups/rg-c"},
            ],
            "skipToken": None,
            "totalRecords": 3,
        },
    ]
    observed_commands: list[list[str]] = []

    def fake_runner(
        command: list[str],
        **kwargs: object,
    ) -> SimpleNamespace:
        observed_commands.append(command)

        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(responses.pop(0)),
            stderr="",
        )

    records = collector_module.execute_paged_resource_graph_query(
        SUBSCRIPTION_ID,
        query,
        page_size=1000,
        runner=fake_runner,
    )

    assert records == [
        {"id": "/subscriptions/example/resourceGroups/rg-a"},
        {"id": "/subscriptions/example/resourceGroups/rg-b"},
        {"id": "/subscriptions/example/resourceGroups/rg-c"},
    ]
    assert observed_commands == [
        collector_module.build_resource_graph_command(
            SUBSCRIPTION_ID,
            query,
            page_size=1000,
        ),
        collector_module.build_resource_graph_command(
            SUBSCRIPTION_ID,
            query,
            page_size=1000,
            skip_token="page-2-token",
        ),
    ]
    assert responses == []


def test_resource_graph_pagination_rejects_inconsistent_total_records(
    collector_module: ModuleType,
) -> None:
    """Total-record metadata must remain stable across pages."""
    responses = [
        {
            "count": 2,
            "data": [
                {"id": "resource-a"},
                {"id": "resource-b"},
            ],
            "skipToken": "page-2",
            "totalRecords": 3,
        },
        {
            "count": 1,
            "data": [
                {"id": "resource-c"},
            ],
            "skipToken": None,
            "totalRecords": 4,
        },
    ]

    def fake_runner(
        command: list[str],
        **kwargs: object,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(responses.pop(0)),
            stderr="",
        )

    with pytest.raises(
        RuntimeError,
        match="total record count changed",
    ):
        collector_module.execute_paged_resource_graph_query(
            SUBSCRIPTION_ID,
            "Resources | project id",
            runner=fake_runner,
        )

    assert responses == []


def test_resource_graph_pagination_rejects_truncated_terminal_page(
    collector_module: ModuleType,
) -> None:
    """Missing continuation metadata must not silently truncate evidence."""
    responses = [
        {
            "count": 2,
            "data": [
                {"id": "resource-a"},
                {"id": "resource-b"},
            ],
            "skipToken": None,
            "totalRecords": 3,
        }
    ]

    def fake_runner(
        command: list[str],
        **kwargs: object,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(responses.pop(0)),
            stderr="",
        )

    with pytest.raises(
        RuntimeError,
        match="returned 2 of 3 records",
    ):
        collector_module.execute_paged_resource_graph_query(
            SUBSCRIPTION_ID,
            "Resources | project id",
            runner=fake_runner,
        )

    assert responses == []


def test_resource_graph_pagination_rejects_repeated_skip_token(
    collector_module: ModuleType,
) -> None:
    """A repeated continuation token must stop a pagination loop."""
    responses = [
        {
            "count": 1,
            "data": [{"id": "resource-a"}],
            "skipToken": "repeated-token",
            "totalRecords": 3,
        },
        {
            "count": 1,
            "data": [{"id": "resource-b"}],
            "skipToken": "repeated-token",
            "totalRecords": 3,
        },
    ]

    def fake_runner(
        command: list[str],
        **kwargs: object,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(responses.pop(0)),
            stderr="",
        )

    with pytest.raises(
        RuntimeError,
        match="repeated a pagination skip token",
    ):
        collector_module.execute_paged_resource_graph_query(
            SUBSCRIPTION_ID,
            "Resources | project id",
            runner=fake_runner,
        )

    assert responses == []


def test_resource_graph_command_normalizes_multiline_kql_for_windows(
    collector_module: ModuleType,
) -> None:
    """Multiline KQL must survive execution through the Windows az.cmd wrapper."""
    multiline_query = """Resources
| where false
| project id"""

    command = collector_module.build_resource_graph_command(
        SUBSCRIPTION_ID,
        multiline_query,
    )

    query_index = command.index("--graph-query") + 1
    command_query = command[query_index]

    assert command_query == "Resources | where false | project id"
    assert "\n" not in command_query
    assert "\r" not in command_query


def test_run_does_not_publish_partial_inventory_after_query_failure(
    collector_module: ModuleType,
    tmp_path: Path,
) -> None:
    """A failed topology query must not publish partial inventory evidence."""
    project_root = tmp_path / "project"
    (project_root / ".specify").mkdir(parents=True)
    output_path = (project_root / ".specify" / "discovery" / "azure-inventory.json").resolve()

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
            stdout=json.dumps(
                {
                    "data": [],
                    "totalRecords": 0,
                }
            ),
            stderr="",
        ),
        SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "data": [],
                    "totalRecords": 0,
                }
            ),
            stderr="",
        ),
        SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="simulated topology failure",
        ),
    ]
    observed_commands: list[list[str]] = []

    def fake_runner(
        command: list[str],
        **kwargs: object,
    ) -> SimpleNamespace:
        observed_commands.append(command)

        if not responses:
            raise AssertionError("Collection continued after the failing topology query.")

        return responses.pop(0)

    with pytest.raises(
        RuntimeError,
        match="simulated topology failure",
    ):
        collector_module.run(
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
                15,
                17,
                30,
                tzinfo=timezone.utc,
            ),
            runner=fake_runner,
        )

    assert len(observed_commands) == 4
    assert responses == []
    assert not output_path.exists()

    discovery_directory = output_path.parent

    if discovery_directory.exists():
        assert list(discovery_directory.glob(f".{output_path.name}.*.tmp")) == []


def test_run_preserves_existing_inventory_after_query_failure(
    collector_module: ModuleType,
    tmp_path: Path,
) -> None:
    """A failed overwrite attempt must preserve existing evidence exactly."""
    project_root = tmp_path / "project"
    discovery_directory = project_root / ".specify" / "discovery"
    discovery_directory.mkdir(parents=True)

    output_path = (discovery_directory / "azure-inventory.json").resolve()
    original_content = b'{"existing":true}\n'
    output_path.write_bytes(original_content)

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
            stdout=json.dumps(
                {
                    "data": [],
                    "totalRecords": 0,
                }
            ),
            stderr="",
        ),
        SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "data": [],
                    "totalRecords": 0,
                }
            ),
            stderr="",
        ),
        SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="simulated topology failure",
        ),
    ]
    observed_commands: list[list[str]] = []

    def fake_runner(
        command: list[str],
        **kwargs: object,
    ) -> SimpleNamespace:
        observed_commands.append(command)

        if not responses:
            raise AssertionError("Collection continued after the failing topology query.")

        return responses.pop(0)

    with pytest.raises(
        RuntimeError,
        match="simulated topology failure",
    ):
        collector_module.run(
            [
                "--subscription",
                SUBSCRIPTION_ID,
                "--tenant",
                TENANT_ID,
                "--approve-read-only",
                "--overwrite",
            ],
            project_root=project_root,
            collected_at=datetime(
                2026,
                9,
                15,
                17,
                30,
                tzinfo=timezone.utc,
            ),
            runner=fake_runner,
        )

    assert len(observed_commands) == 4
    assert responses == []
    assert output_path.read_bytes() == original_content
    assert list(discovery_directory.glob(f".{output_path.name}.*.tmp")) == []
