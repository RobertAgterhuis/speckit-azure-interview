"""Tests for Azure intended-design generation."""

from __future__ import annotations

import importlib.util
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType

import pytest
from jsonschema import Draft202012Validator

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

GENERATOR_PATH = REPOSITORY_ROOT / "scripts" / "python" / "generate_azure_design.py"

VALID_CONTEXT_PATH = REPOSITORY_ROOT / "tests" / "fixtures" / "valid-context.json"

DESIGN_SCHEMA_PATH = REPOSITORY_ROOT / "templates" / "azure-design.schema.json"


@pytest.fixture
def generator_module() -> ModuleType:
    """Load the design generator directly from its repository path."""
    specification = importlib.util.spec_from_file_location(
        "generate_azure_design",
        GENERATOR_PATH,
    )
    assert specification is not None
    assert specification.loader is not None

    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


@pytest.fixture
def valid_context() -> dict[str, object]:
    """Load a confirmed, specification-ready Azure interview context."""
    with VALID_CONTEXT_PATH.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def test_validate_design_source_accepts_ready_context(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Completed and ready interview context may produce a design."""
    generator_module.validate_design_source(valid_context)


@pytest.mark.parametrize(
    ("field_path", "replacement", "expected_message"),
    [
        (
            ("interview", "status"),
            "in-progress",
            "Interview status must be complete",
        ),
        (
            ("readiness", "readyForSpecification"),
            False,
            "Context is not ready for specification",
        ),
        (
            ("readiness", "blockingQuestionsRemaining"),
            1,
            "Blocking questions remain",
        ),
        (
            ("readiness", "unvalidatedCriticalAssumptions"),
            1,
            "Critical assumptions remain unvalidated",
        ),
        (
            ("readiness", "missingResourceIdentifiers"),
            1,
            "Required resource identifiers are missing",
        ),
        (
            ("readiness", "conflictingRequirements"),
            1,
            "Conflicting requirements remain",
        ),
    ],
)
def test_validate_design_source_rejects_unready_context(
    generator_module: ModuleType,
    valid_context: dict[str, object],
    field_path: tuple[str, str],
    replacement: object,
    expected_message: str,
) -> None:
    """An intended design cannot be generated from unresolved discovery."""
    section_name, field_name = field_path
    section = valid_context[section_name]
    assert isinstance(section, dict)
    section[field_name] = replacement

    with pytest.raises(ValueError, match=expected_message):
        generator_module.validate_design_source(valid_context)


def test_build_design_model_creates_unreviewed_intended_design(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """A generated design remains intended state pending human review."""
    generated_at = datetime(
        2026,
        9,
        14,
        14,
        30,
        tzinfo=timezone.utc,
    )

    design = generator_module.build_design_model(
        valid_context,
        generated_at=generated_at,
    )

    assert design["schemaVersion"] == "1.0"
    assert design["designStatus"] == "intended"
    assert design["reviewStatus"] == "unreviewed"
    assert design["generatedAt"] == "2026-09-14T14:30:00Z"


def test_build_design_model_records_source_provenance(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """The model identifies the confirmed interview context it represents."""
    design = generator_module.build_design_model(
        valid_context,
        generated_at=datetime(
            2026,
            9,
            14,
            14,
            30,
            tzinfo=timezone.utc,
        ),
    )

    assert design["source"] == {
        "type": "azure-interview-context",
        "schemaVersion": "1.0",
        "interviewUpdatedAt": "2026-09-13T09:00:00Z",
        "confirmedBy": "Workload Owner",
    }


def test_build_design_model_captures_workload_and_azure_scope(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """The intended design carries its workload and deployment boundary."""
    design = generator_module.build_design_model(
        valid_context,
        generated_at=datetime(
            2026,
            9,
            14,
            14,
            30,
            tzinfo=timezone.utc,
        ),
    )

    assert design["workload"] == {
        "name": "Example Workload",
        "purpose": "Provide a secure internal application platform.",
        "lifecycle": "brownfield",
        "criticality": "high",
        "environments": ["dev", "tst", "acc", "prd"],
    }
    assert design["azureScope"] == {
        "tenantId": "00000000-0000-0000-0000-000000000001",
        "managementGroupId": "mg-platform",
        "subscriptions": [
            {
                "environment": "prd",
                "subscriptionId": ("00000000-0000-0000-0000-000000000002"),
            }
        ],
        "regions": ["westeurope"],
    }


def test_build_design_model_copies_source_collections(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """The design must not retain mutable collections owned by its caller."""
    design = generator_module.build_design_model(
        valid_context,
        generated_at=datetime(
            2026,
            9,
            14,
            14,
            30,
            tzinfo=timezone.utc,
        ),
    )

    workload = valid_context["workload"]
    azure_estate = valid_context["azureEstate"]
    assert isinstance(workload, dict)
    assert isinstance(azure_estate, dict)

    environments = workload["environments"]
    regions = azure_estate["regions"]
    subscriptions = azure_estate["subscriptions"]
    assert isinstance(environments, list)
    assert isinstance(regions, list)
    assert isinstance(subscriptions, list)

    environments.append("temporary")
    regions.append("temporary")
    subscriptions.clear()

    assert design["workload"]["environments"] == [
        "dev",
        "tst",
        "acc",
        "prd",
    ]
    assert design["azureScope"]["regions"] == ["westeurope"]
    assert len(design["azureScope"]["subscriptions"]) == 1


def test_build_design_model_rejects_naive_generation_timestamp(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Generated design timestamps must be timezone-aware."""
    with pytest.raises(ValueError, match="timezone-aware"):
        generator_module.build_design_model(
            valid_context,
            generated_at=datetime(2026, 9, 14, 14, 30),
        )


def get_design_nodes(
    design: dict[str, object],
) -> list[dict[str, object]]:
    """Return architecture nodes from a generated design."""
    architecture = design["architecture"]
    assert isinstance(architecture, dict)

    nodes = architecture["nodes"]
    assert isinstance(nodes, list)

    return nodes


def get_design_node(
    design: dict[str, object],
    node_id: str,
) -> dict[str, object]:
    """Return one architecture node by its stable identifier."""
    for node in get_design_nodes(design):
        if node.get("id") == node_id:
            return node

    raise AssertionError(f"Design node was not found: {node_id}")


def test_build_design_model_creates_deterministic_network_nodes(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """The network design uses stable identifiers and source ordering."""
    design = generator_module.build_design_model(
        valid_context,
        generated_at=datetime(
            2026,
            9,
            14,
            14,
            30,
            tzinfo=timezone.utc,
        ),
    )

    node_ids = [node["id"] for node in get_design_nodes(design)]

    assert node_ids[:6] == [
        "network:hub",
        "network:spoke",
        "network:subnet:snet-application",
        "network:subnet:snet-private-endpoints",
        "network:firewall",
        "network:private-dns-resolver",
    ]


def test_build_design_model_distinguishes_existing_and_planned_network(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Existing platform services and planned workload resources stay distinct."""
    design = generator_module.build_design_model(
        valid_context,
        generated_at=datetime(
            2026,
            9,
            14,
            14,
            30,
            tzinfo=timezone.utc,
        ),
    )

    hub = get_design_node(design, "network:hub")
    spoke = get_design_node(design, "network:spoke")
    application_subnet = get_design_node(
        design,
        "network:subnet:snet-application",
    )
    firewall = get_design_node(design, "network:firewall")
    dns_resolver = get_design_node(
        design,
        "network:private-dns-resolver",
    )

    assert hub == {
        "id": "network:hub",
        "category": "network",
        "resourceType": "Microsoft.Network/virtualNetworks",
        "name": "vnet-hub-we-prd",
        "state": "existing",
        "owner": "Platform Team",
        "modifiable": False,
        "resourceId": (
            "/subscriptions/00000000-0000-0000-0000-000000000002"
            "/resourceGroups/rg-hub-we-prd"
            "/providers/Microsoft.Network/virtualNetworks"
            "/vnet-hub-we-prd"
        ),
        "properties": {},
    }

    assert spoke == {
        "id": "network:spoke",
        "category": "network",
        "resourceType": "Microsoft.Network/virtualNetworks",
        "name": "Example Workload spoke",
        "state": "planned",
        "owner": "Workload Team",
        "modifiable": True,
        "resourceId": None,
        "properties": {
            "addressSpaces": ["10.20.0.0/24"],
            "topology": "existing-hub-spoke",
        },
    }

    assert application_subnet["state"] == "planned"
    assert application_subnet["owner"] == "Workload Team"
    assert application_subnet["properties"] == {
        "prefix": "10.20.0.0/26",
        "purpose": "Application hosting",
    }

    assert firewall["state"] == "existing"
    assert firewall["owner"] == "Platform Team"
    assert firewall["modifiable"] is False

    assert dns_resolver["state"] == "existing"
    assert dns_resolver["owner"] == "Platform Team"
    assert dns_resolver["modifiable"] is False


def test_build_design_model_maps_declared_resources(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Declared create and reuse intentions become architecture nodes."""
    design = generator_module.build_design_model(
        valid_context,
        generated_at=datetime(
            2026,
            9,
            14,
            14,
            30,
            tzinfo=timezone.utc,
        ),
    )

    workspace = get_design_node(
        design,
        ("resource:microsoft.operationalinsights/workspaces:log-hub-we-prd"),
    )
    key_vault = get_design_node(
        design,
        "resource:microsoft.keyvault/vaults:kv-example-we-prd",
    )

    assert workspace == {
        "id": ("resource:microsoft.operationalinsights/workspaces:log-hub-we-prd"),
        "category": "resource",
        "resourceType": "Microsoft.OperationalInsights/workspaces",
        "name": "log-hub-we-prd",
        "state": "existing",
        "owner": "Platform Team",
        "modifiable": False,
        "resourceId": (
            "/subscriptions/00000000-0000-0000-0000-000000000002"
            "/resourceGroups/rg-monitoring-we-prd"
            "/providers/Microsoft.OperationalInsights/workspaces"
            "/log-hub-we-prd"
        ),
        "properties": {
            "intent": "reuse",
            "requiredIntegrations": ["Diagnostic settings"],
        },
    }

    assert key_vault == {
        "id": ("resource:microsoft.keyvault/vaults:kv-example-we-prd"),
        "category": "resource",
        "resourceType": "Microsoft.KeyVault/vaults",
        "name": "kv-example-we-prd",
        "state": "planned",
        "owner": "Workload Team",
        "modifiable": True,
        "resourceId": None,
        "properties": {
            "intent": "create",
            "requiredIntegrations": [
                "Private endpoint",
                "Private DNS",
                "Azure RBAC",
                "Diagnostic settings",
            ],
        },
    }


def test_build_design_model_copies_architecture_node_properties(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Architecture nodes must not share mutable source collections."""
    design = generator_module.build_design_model(
        valid_context,
        generated_at=datetime(
            2026,
            9,
            14,
            14,
            30,
            tzinfo=timezone.utc,
        ),
    )

    network = valid_context["network"]
    existing_resources = valid_context["existingResources"]
    assert isinstance(network, dict)
    assert isinstance(existing_resources, list)

    address_spaces = network["addressSpaces"]
    assert isinstance(address_spaces, list)
    address_spaces.clear()

    first_resource = existing_resources[0]
    assert isinstance(first_resource, dict)
    integrations = first_resource["requiredIntegrations"]
    assert isinstance(integrations, list)
    integrations.clear()

    spoke = get_design_node(design, "network:spoke")
    workspace = get_design_node(
        design,
        ("resource:microsoft.operationalinsights/workspaces:log-hub-we-prd"),
    )

    assert spoke["properties"]["addressSpaces"] == ["10.20.0.0/24"]
    assert workspace["properties"]["requiredIntegrations"] == ["Diagnostic settings"]


def get_design_relationships(
    design: dict[str, object],
) -> list[dict[str, object]]:
    """Return relationships from a generated design."""
    architecture = design["architecture"]
    assert isinstance(architecture, dict)

    relationships = architecture["relationships"]
    assert isinstance(relationships, list)

    return relationships


def get_design_relationship(
    design: dict[str, object],
    relationship_id: str,
) -> dict[str, object]:
    """Return one architecture relationship by stable identifier."""
    for relationship in get_design_relationships(design):
        if relationship.get("id") == relationship_id:
            return relationship

    raise AssertionError(f"Design relationship was not found: {relationship_id}")


def test_build_design_model_creates_deterministic_network_relationships(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Network relationships use stable identifiers and ordering."""
    design = generator_module.build_design_model(
        valid_context,
        generated_at=datetime(
            2026,
            9,
            14,
            14,
            30,
            tzinfo=timezone.utc,
        ),
    )

    relationship_ids = [relationship["id"] for relationship in get_design_relationships(design)]

    assert relationship_ids == [
        "relationship:hub-spoke-peering",
        "relationship:spoke-subnet:snet-application",
        ("relationship:spoke-subnet:snet-private-endpoints"),
        "relationship:spoke-egress-firewall",
        "relationship:spoke-private-dns-resolver",
        ("relationship:resource:microsoft.keyvault/vaults:kv-example-we-prd:private-endpoint"),
        ("relationship:resource:microsoft.keyvault/vaults:kv-example-we-prd:diagnostics"),
    ]


def test_build_design_model_maps_hub_and_spoke_relationships(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """The intended design records peering and subnet containment."""
    design = generator_module.build_design_model(
        valid_context,
        generated_at=datetime(
            2026,
            9,
            14,
            14,
            30,
            tzinfo=timezone.utc,
        ),
    )

    peering = get_design_relationship(
        design,
        "relationship:hub-spoke-peering",
    )
    application_subnet = get_design_relationship(
        design,
        "relationship:spoke-subnet:snet-application",
    )

    assert peering == {
        "id": "relationship:hub-spoke-peering",
        "type": "peered-with",
        "source": "network:spoke",
        "target": "network:hub",
        "label": "Hub-to-spoke peering",
        "state": "planned",
        "owner": "Platform Team",
    }

    assert application_subnet == {
        "id": "relationship:spoke-subnet:snet-application",
        "type": "contains",
        "source": "network:spoke",
        "target": "network:subnet:snet-application",
        "label": "Contains subnet",
        "state": "planned",
        "owner": "Workload Team",
    }


def test_build_design_model_maps_shared_network_services(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """The spoke records its shared egress and DNS dependencies."""
    design = generator_module.build_design_model(
        valid_context,
        generated_at=datetime(
            2026,
            9,
            14,
            14,
            30,
            tzinfo=timezone.utc,
        ),
    )

    firewall = get_design_relationship(
        design,
        "relationship:spoke-egress-firewall",
    )
    dns_resolver = get_design_relationship(
        design,
        "relationship:spoke-private-dns-resolver",
    )

    assert firewall == {
        "id": "relationship:spoke-egress-firewall",
        "type": "egress-through",
        "source": "network:spoke",
        "target": "network:firewall",
        "label": "Central egress",
        "state": "existing",
        "owner": "Platform Team",
    }

    assert dns_resolver == {
        "id": "relationship:spoke-private-dns-resolver",
        "type": "dns-resolution-through",
        "source": "network:spoke",
        "target": "network:private-dns-resolver",
        "label": "Private DNS resolution",
        "state": "existing",
        "owner": "Platform Team",
    }


def test_every_relationship_references_existing_nodes(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Every relationship endpoint must exist in the same design."""
    design = generator_module.build_design_model(
        valid_context,
        generated_at=datetime(
            2026,
            9,
            14,
            14,
            30,
            tzinfo=timezone.utc,
        ),
    )

    node_ids = {node["id"] for node in get_design_nodes(design)}

    for relationship in get_design_relationships(design):
        assert relationship["source"] in node_ids
        assert relationship["target"] in node_ids


def load_design_schema() -> dict[str, object]:
    """Load the intended-design JSON Schema."""
    with DESIGN_SCHEMA_PATH.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def build_valid_design(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> dict[str, object]:
    """Build a representative intended-design document."""
    return generator_module.build_design_model(
        valid_context,
        generated_at=datetime(
            2026,
            9,
            14,
            14,
            30,
            tzinfo=timezone.utc,
        ),
    )


def test_design_model_matches_schema(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """A representative intended design must satisfy its schema."""
    schema = load_design_schema()
    design = build_valid_design(
        generator_module,
        valid_context,
    )

    Draft202012Validator(schema).validate(design)


def test_design_schema_requires_intended_state(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """A design artifact cannot claim to represent deployed state."""
    schema = load_design_schema()
    design = build_valid_design(
        generator_module,
        valid_context,
    )
    design["designStatus"] = "deployed"

    errors = list(Draft202012Validator(schema).iter_errors(design))

    assert errors


def test_design_schema_controls_review_status(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Review status must use the controlled lifecycle vocabulary."""
    schema = load_design_schema()
    design = build_valid_design(
        generator_module,
        valid_context,
    )
    design["reviewStatus"] = "probably-approved"

    errors = list(Draft202012Validator(schema).iter_errors(design))

    assert errors


def test_design_schema_rejects_unknown_top_level_properties(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Unexpected properties cannot silently enter the design contract."""
    schema = load_design_schema()
    design = build_valid_design(
        generator_module,
        valid_context,
    )
    design["unexpected"] = True

    errors = list(Draft202012Validator(schema).iter_errors(design))

    assert errors


def clone_json_document(
    document: dict[str, object],
) -> dict[str, object]:
    """Create a JSON-compatible deep copy."""
    return json.loads(json.dumps(document))


def test_validate_design_model_accepts_valid_design(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """A structurally and semantically valid design is accepted."""
    design = build_valid_design(
        generator_module,
        valid_context,
    )

    generator_module.validate_design_model(
        design,
        load_design_schema(),
    )


def test_validate_design_model_rejects_duplicate_node_ids(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Stable architecture node identifiers must be unique."""
    design = clone_json_document(
        build_valid_design(
            generator_module,
            valid_context,
        )
    )
    architecture = design["architecture"]
    assert isinstance(architecture, dict)

    nodes = architecture["nodes"]
    assert isinstance(nodes, list)
    nodes.append(clone_json_document(nodes[0]))

    with pytest.raises(
        ValueError,
        match="Duplicate architecture node ID",
    ):
        generator_module.validate_design_model(
            design,
            load_design_schema(),
        )


def test_validate_design_model_rejects_duplicate_relationship_ids(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Stable relationship identifiers must be unique."""
    design = clone_json_document(
        build_valid_design(
            generator_module,
            valid_context,
        )
    )
    architecture = design["architecture"]
    assert isinstance(architecture, dict)

    relationships = architecture["relationships"]
    assert isinstance(relationships, list)
    relationships.append(clone_json_document(relationships[0]))

    with pytest.raises(
        ValueError,
        match="Duplicate architecture relationship ID",
    ):
        generator_module.validate_design_model(
            design,
            load_design_schema(),
        )


@pytest.mark.parametrize(
    "endpoint_name",
    [
        "source",
        "target",
    ],
)
def test_validate_design_model_rejects_missing_relationship_endpoint(
    generator_module: ModuleType,
    valid_context: dict[str, object],
    endpoint_name: str,
) -> None:
    """Every relationship endpoint must reference a defined node."""
    design = clone_json_document(
        build_valid_design(
            generator_module,
            valid_context,
        )
    )
    architecture = design["architecture"]
    assert isinstance(architecture, dict)

    relationships = architecture["relationships"]
    assert isinstance(relationships, list)

    first_relationship = relationships[0]
    assert isinstance(first_relationship, dict)
    first_relationship[endpoint_name] = "network:not-present"

    with pytest.raises(
        ValueError,
        match="references unknown node",
    ):
        generator_module.validate_design_model(
            design,
            load_design_schema(),
        )


def test_validate_design_model_rejects_schema_violation(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """A schema-invalid design cannot become a design artifact."""
    design = clone_json_document(
        build_valid_design(
            generator_module,
            valid_context,
        )
    )
    design["unexpected"] = True

    with pytest.raises(
        ValueError,
        match="Design schema validation failed",
    ):
        generator_module.validate_design_model(
            design,
            load_design_schema(),
        )


def test_validate_design_output_path_accepts_project_design_directory(
    generator_module: ModuleType,
    tmp_path: Path,
) -> None:
    """Design artifacts may be written inside the project design directory."""
    project_root = tmp_path / "consumer-project"
    output_path = project_root / ".specify" / "design" / "azure-design-model.json"
    (project_root / ".specify").mkdir(parents=True)

    validated_path = generator_module.validate_design_output_path(
        output_path,
        project_root=project_root,
    )

    assert validated_path == output_path.resolve()


def test_validate_design_output_path_rejects_non_speckit_project(
    generator_module: ModuleType,
    tmp_path: Path,
) -> None:
    """Design generation requires an initialized Spec Kit project."""
    project_root = tmp_path / "not-a-speckit-project"
    project_root.mkdir()

    with pytest.raises(
        ValueError,
        match="not a Spec Kit project",
    ):
        generator_module.validate_design_output_path(
            (project_root / ".specify" / "design" / "azure-design-model.json"),
            project_root=project_root,
        )


def test_validate_design_output_path_rejects_path_outside_design_directory(
    generator_module: ModuleType,
    tmp_path: Path,
) -> None:
    """Generated design data cannot escape its controlled directory."""
    project_root = tmp_path / "consumer-project"
    (project_root / ".specify").mkdir(parents=True)

    with pytest.raises(
        ValueError,
        match=r"\.specify/design",
    ):
        generator_module.validate_design_output_path(
            project_root / "azure-design-model.json",
            project_root=project_root,
        )


def test_write_design_model_creates_json_artifact(
    generator_module: ModuleType,
    valid_context: dict[str, object],
    tmp_path: Path,
) -> None:
    """A validated design model is written as readable JSON."""
    output_path = tmp_path / ".specify" / "design" / "azure-design-model.json"
    design = build_valid_design(
        generator_module,
        valid_context,
    )

    generator_module.write_design_model(
        design,
        output_path,
        overwrite=False,
    )

    written_design = json.loads(output_path.read_text(encoding="utf-8"))

    assert written_design == design
    assert output_path.read_text(encoding="utf-8").endswith("\n")


def test_write_design_model_rejects_existing_output(
    generator_module: ModuleType,
    valid_context: dict[str, object],
    tmp_path: Path,
) -> None:
    """Existing reviewed design evidence is not replaced implicitly."""
    output_path = tmp_path / ".specify" / "design" / "azure-design-model.json"
    output_path.parent.mkdir(parents=True)
    output_path.write_text(
        '{"preserve": true}\n',
        encoding="utf-8",
    )
    design = build_valid_design(
        generator_module,
        valid_context,
    )

    with pytest.raises(
        FileExistsError,
        match="already exists",
    ):
        generator_module.write_design_model(
            design,
            output_path,
            overwrite=False,
        )

    assert json.loads(output_path.read_text(encoding="utf-8")) == {"preserve": True}


def test_write_design_model_allows_explicit_overwrite(
    generator_module: ModuleType,
    valid_context: dict[str, object],
    tmp_path: Path,
) -> None:
    """An explicit overwrite replaces an existing design artifact."""
    output_path = tmp_path / ".specify" / "design" / "azure-design-model.json"
    output_path.parent.mkdir(parents=True)
    output_path.write_text(
        '{"old": true}\n',
        encoding="utf-8",
    )
    design = build_valid_design(
        generator_module,
        valid_context,
    )

    generator_module.write_design_model(
        design,
        output_path,
        overwrite=True,
    )

    assert json.loads(output_path.read_text(encoding="utf-8")) == design


def test_parse_arguments_uses_canonical_design_paths(
    generator_module: ModuleType,
) -> None:
    """The CLI uses the established discovery and design directories."""
    arguments = generator_module.parse_arguments([])

    assert arguments.context == Path(".specify/discovery/azure-context.json")
    assert arguments.output == Path(".specify/design/azure-design-model.json")
    assert arguments.overwrite is False


def test_parse_arguments_accepts_explicit_paths_and_overwrite(
    generator_module: ModuleType,
) -> None:
    """Operators may explicitly select input, output, and overwrite."""
    context_path = Path(".specify/discovery/approved-context.json")
    output_path = Path(".specify/design/approved-design.json")

    arguments = generator_module.parse_arguments(
        [
            "--context",
            str(context_path),
            "--output",
            str(output_path),
            "--overwrite",
        ]
    )

    assert arguments.context == context_path
    assert arguments.output == output_path
    assert arguments.overwrite is True


def test_validate_design_context_path_accepts_discovery_context(
    generator_module: ModuleType,
    tmp_path: Path,
) -> None:
    """Design input may come from the Spec Kit discovery directory."""
    project_root = tmp_path / "consumer-project"
    context_path = project_root / ".specify" / "discovery" / "azure-context.json"
    context_path.parent.mkdir(parents=True)
    context_path.write_text("{}\n", encoding="utf-8")

    validated_path = generator_module.validate_design_context_path(
        context_path,
        project_root=project_root,
    )

    assert validated_path == context_path.resolve()


def test_validate_design_context_path_rejects_non_speckit_project(
    generator_module: ModuleType,
    tmp_path: Path,
) -> None:
    """Context loading requires an initialized Spec Kit project."""
    project_root = tmp_path / "not-a-speckit-project"
    project_root.mkdir()

    with pytest.raises(
        ValueError,
        match="not a Spec Kit project",
    ):
        generator_module.validate_design_context_path(
            project_root / "azure-context.json",
            project_root=project_root,
        )


def test_validate_design_context_path_rejects_outside_discovery(
    generator_module: ModuleType,
    tmp_path: Path,
) -> None:
    """Context input cannot escape the controlled discovery directory."""
    project_root = tmp_path / "consumer-project"
    (project_root / ".specify").mkdir(parents=True)

    with pytest.raises(
        ValueError,
        match=r"\.specify/discovery",
    ):
        generator_module.validate_design_context_path(
            project_root / "azure-context.json",
            project_root=project_root,
        )


def test_load_json_document_reads_context_object(
    generator_module: ModuleType,
    valid_context: dict[str, object],
    tmp_path: Path,
) -> None:
    """A valid JSON object is loaded from disk."""
    context_path = tmp_path / "azure-context.json"
    context_path.write_text(
        json.dumps(valid_context),
        encoding="utf-8",
    )

    loaded_context = generator_module.load_json_document(context_path)

    assert loaded_context == valid_context


def test_load_json_document_rejects_invalid_json(
    generator_module: ModuleType,
    tmp_path: Path,
) -> None:
    """Malformed discovery input produces a controlled error."""
    context_path = tmp_path / "azure-context.json"
    context_path.write_text(
        "{not-valid-json",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Invalid JSON document",
    ):
        generator_module.load_json_document(context_path)


def test_load_json_document_rejects_non_object(
    generator_module: ModuleType,
    tmp_path: Path,
) -> None:
    """The Azure context root must be a JSON object."""
    context_path = tmp_path / "azure-context.json"
    context_path.write_text(
        "[]\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="must contain a JSON object",
    ):
        generator_module.load_json_document(context_path)


def test_run_generates_validated_design_artifact(
    generator_module: ModuleType,
    valid_context: dict[str, object],
    tmp_path: Path,
) -> None:
    """The complete workflow produces a validated intended design."""
    project_root = tmp_path / "consumer-project"
    context_path = project_root / ".specify" / "discovery" / "azure-context.json"
    output_path = project_root / ".specify" / "design" / "azure-design-model.json"
    context_path.parent.mkdir(parents=True)
    context_path.write_text(
        json.dumps(valid_context),
        encoding="utf-8",
    )

    written_path = generator_module.run(
        project_root=project_root,
        context_path=Path(".specify/discovery/azure-context.json"),
        output_path=Path(".specify/design/azure-design-model.json"),
        overwrite=False,
        generated_at=datetime(
            2026,
            9,
            14,
            14,
            30,
            tzinfo=timezone.utc,
        ),
        schema_path=DESIGN_SCHEMA_PATH,
    )

    assert written_path == output_path.resolve()
    assert output_path.is_file()

    design = json.loads(output_path.read_text(encoding="utf-8"))
    generator_module.validate_design_model(
        design,
        load_design_schema(),
    )
    assert design["designStatus"] == "intended"
    assert design["reviewStatus"] == "unreviewed"


def test_run_rejects_existing_output_before_reading_context(
    generator_module: ModuleType,
    tmp_path: Path,
) -> None:
    """Existing design output stops execution before context processing."""
    project_root = tmp_path / "consumer-project"
    context_path = project_root / ".specify" / "discovery" / "azure-context.json"
    output_path = project_root / ".specify" / "design" / "azure-design-model.json"
    context_path.parent.mkdir(parents=True)
    output_path.parent.mkdir(parents=True)

    context_path.write_text(
        "{invalid-json",
        encoding="utf-8",
    )
    output_path.write_text(
        '{"preserve": true}\n',
        encoding="utf-8",
    )

    with pytest.raises(
        FileExistsError,
        match="already exists",
    ):
        generator_module.run(
            project_root=project_root,
            context_path=Path(".specify/discovery/azure-context.json"),
            output_path=Path(".specify/design/azure-design-model.json"),
            overwrite=False,
            generated_at=datetime(
                2026,
                9,
                14,
                14,
                30,
                tzinfo=timezone.utc,
            ),
            schema_path=DESIGN_SCHEMA_PATH,
        )

    assert json.loads(output_path.read_text(encoding="utf-8")) == {"preserve": True}


def test_main_generates_unreviewed_intended_design(
    generator_module: ModuleType,
    valid_context: dict[str, object],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI reports the generated artifact and review requirement."""
    project_root = tmp_path / "consumer-project"
    context_path = project_root / ".specify" / "discovery" / "azure-context.json"
    context_path.parent.mkdir(parents=True)
    context_path.write_text(
        json.dumps(valid_context),
        encoding="utf-8",
    )

    exit_code = generator_module.main(
        [],
        project_root=project_root,
        generated_at=datetime(
            2026,
            9,
            14,
            14,
            30,
            tzinfo=timezone.utc,
        ),
        schema_path=DESIGN_SCHEMA_PATH,
    )

    captured = capsys.readouterr()
    output_path = project_root / ".specify" / "design" / "azure-design-model.json"

    assert exit_code == generator_module.EXIT_SUCCESS
    assert output_path.is_file()
    assert "Azure intended design written successfully" in captured.out
    assert str(output_path.resolve()) in captured.out
    assert "Review status: unreviewed" in captured.out
    assert captured.err == ""


def test_main_reports_controlled_generation_error(
    generator_module: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Expected operator errors produce a stable nonzero exit code."""
    project_root = tmp_path / "consumer-project"
    (project_root / ".specify").mkdir(parents=True)

    exit_code = generator_module.main(
        [],
        project_root=project_root,
        generated_at=datetime(
            2026,
            9,
            14,
            14,
            30,
            tzinfo=timezone.utc,
        ),
        schema_path=DESIGN_SCHEMA_PATH,
    )

    captured = capsys.readouterr()

    assert exit_code == generator_module.EXIT_EXECUTION_ERROR
    assert captured.out == ""
    assert "Azure design generation failed:" in captured.err
    assert "azure-context.json" in captured.err


def test_render_mermaid_diagram_contains_design_nodes_and_relationships(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """The overview diagram renders architecture nodes and connections."""
    design = build_valid_design(
        generator_module,
        valid_context,
    )

    diagram = generator_module.render_mermaid_diagram(design)

    assert diagram.startswith("flowchart TB\n")
    assert 'n0["vnet-hub-we-prd' in diagram
    assert 'n1["Example Workload spoke' in diagram
    assert 'n2["snet-application' in diagram
    assert 'n3["snet-private-endpoints' in diagram
    assert 'n4["afw-hub-we-prd' in diagram
    assert 'n5["pdnsr-hub-we-prd' in diagram
    assert 'n6["log-hub-we-prd' in diagram
    assert 'n7["kv-example-we-prd' in diagram

    assert 'n1 -->|"Hub-to-spoke peering"| n0' in diagram
    assert 'n1 -->|"Contains subnet"| n2' in diagram
    assert 'n1 -->|"Central egress"| n4' in diagram
    assert 'n1 -->|"Private DNS resolution"| n5' in diagram


def test_render_mermaid_diagram_distinguishes_resource_state(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Existing and planned resources receive distinct visual classes."""
    design = build_valid_design(
        generator_module,
        valid_context,
    )

    diagram = generator_module.render_mermaid_diagram(design)

    assert "class n0,n4,n5,n6 existing" in diagram
    assert "class n1,n2,n3,n7 planned" in diagram
    assert "classDef existing fill:#E8F3FF,stroke:#0078D4" in diagram
    assert "classDef planned fill:#FFF4CE,stroke:#C19C00" in diagram


def test_render_mermaid_diagram_is_deterministic(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Identical design input produces identical diagram source."""
    design = build_valid_design(
        generator_module,
        valid_context,
    )

    first_diagram = generator_module.render_mermaid_diagram(design)
    second_diagram = generator_module.render_mermaid_diagram(design)

    assert first_diagram == second_diagram


def test_render_mermaid_diagram_escapes_untrusted_labels(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """User-provided labels cannot break Mermaid node syntax."""
    workload = valid_context["workload"]
    assert isinstance(workload, dict)
    workload["name"] = 'Unsafe "name" <test>'

    design = build_valid_design(
        generator_module,
        valid_context,
    )
    diagram = generator_module.render_mermaid_diagram(design)

    assert "Unsafe &quot;name&quot; &lt;test&gt; spoke" in diagram
    assert 'Unsafe "name" <test> spoke' not in diagram


def test_render_design_markdown_creates_review_document(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """The Markdown artifact explains status, scope, and review duties."""
    design = build_valid_design(
        generator_module,
        valid_context,
    )
    diagram = generator_module.render_mermaid_diagram(design)

    document = generator_module.render_design_markdown(
        design,
        diagram,
    )

    assert document.startswith("# Azure Intended Design — Example Workload\n")
    assert "Review status: **unreviewed**" in document
    assert "This document represents intended architecture" in document
    assert "It does not prove deployed Azure state." in document
    assert "## Architecture overview" in document
    assert "```mermaid\nflowchart TB\n" in document
    assert "## Review checklist" in document
    assert "## Source provenance" in document
    assert "Workload Owner" in document
    assert "2026-09-13T09:00:00Z" in document
    assert document.endswith("\n")


def test_render_design_markdown_escapes_heading_text(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Untrusted workload names cannot inject Markdown headings."""
    workload = valid_context["workload"]
    assert isinstance(workload, dict)
    workload["name"] = "Example\n# Injected heading"

    design = build_valid_design(
        generator_module,
        valid_context,
    )
    diagram = generator_module.render_mermaid_diagram(design)

    document = generator_module.render_design_markdown(
        design,
        diagram,
    )

    assert "\n# Injected heading" not in document
    assert "Example # Injected heading" in document


def test_write_text_artifact_creates_markdown_file(
    generator_module: ModuleType,
    tmp_path: Path,
) -> None:
    """A generated Markdown document is written atomically."""
    output_path = tmp_path / ".specify" / "design" / "azure-design-overview.md"
    content = "# Intended design\n"

    generator_module.write_text_artifact(
        content,
        output_path,
        overwrite=False,
    )

    assert output_path.read_text(encoding="utf-8") == content


def test_write_text_artifact_rejects_existing_output(
    generator_module: ModuleType,
    tmp_path: Path,
) -> None:
    """An existing review document cannot be replaced implicitly."""
    output_path = tmp_path / ".specify" / "design" / "azure-design-overview.md"
    output_path.parent.mkdir(parents=True)
    output_path.write_text(
        "# Approved design\n",
        encoding="utf-8",
    )

    with pytest.raises(
        FileExistsError,
        match="already exists",
    ):
        generator_module.write_text_artifact(
            "# Replacement\n",
            output_path,
            overwrite=False,
        )

    assert output_path.read_text(encoding="utf-8") == "# Approved design\n"


def test_parse_arguments_uses_canonical_overview_path(
    generator_module: ModuleType,
) -> None:
    """The CLI exposes the canonical review-document path."""
    arguments = generator_module.parse_arguments([])

    assert arguments.overview_output == Path(".specify/design/azure-design-overview.md")


def test_run_generates_markdown_overview(
    generator_module: ModuleType,
    valid_context: dict[str, object],
    tmp_path: Path,
) -> None:
    """The workflow writes a human-reviewable architecture overview."""
    project_root = tmp_path / "consumer-project"
    context_path = project_root / ".specify" / "discovery" / "azure-context.json"
    overview_path = project_root / ".specify" / "design" / "azure-design-overview.md"
    context_path.parent.mkdir(parents=True)
    context_path.write_text(
        json.dumps(valid_context),
        encoding="utf-8",
    )

    generator_module.run(
        project_root=project_root,
        context_path=Path(".specify/discovery/azure-context.json"),
        output_path=Path(".specify/design/azure-design-model.json"),
        overview_path=Path(".specify/design/azure-design-overview.md"),
        overwrite=False,
        generated_at=datetime(
            2026,
            9,
            14,
            14,
            30,
            tzinfo=timezone.utc,
        ),
        schema_path=DESIGN_SCHEMA_PATH,
    )

    document = overview_path.read_text(encoding="utf-8")

    assert "# Azure Intended Design — Example Workload" in document
    assert "```mermaid\nflowchart TB\n" in document
    assert "Review status: **unreviewed**" in document


def test_run_rejects_existing_overview_before_writing_model(
    generator_module: ModuleType,
    valid_context: dict[str, object],
    tmp_path: Path,
) -> None:
    """Preflight protects all design artifacts before any are written."""
    project_root = tmp_path / "consumer-project"
    context_path = project_root / ".specify" / "discovery" / "azure-context.json"
    model_path = project_root / ".specify" / "design" / "azure-design-model.json"
    overview_path = project_root / ".specify" / "design" / "azure-design-overview.md"

    context_path.parent.mkdir(parents=True)
    overview_path.parent.mkdir(parents=True)
    context_path.write_text(
        json.dumps(valid_context),
        encoding="utf-8",
    )
    overview_path.write_text(
        "# Preserve reviewed design\n",
        encoding="utf-8",
    )

    with pytest.raises(
        FileExistsError,
        match="already exists",
    ):
        generator_module.run(
            project_root=project_root,
            context_path=Path(".specify/discovery/azure-context.json"),
            output_path=Path(".specify/design/azure-design-model.json"),
            overview_path=Path(".specify/design/azure-design-overview.md"),
            overwrite=False,
            generated_at=datetime(
                2026,
                9,
                14,
                14,
                30,
                tzinfo=timezone.utc,
            ),
            schema_path=DESIGN_SCHEMA_PATH,
        )

    assert not model_path.exists()
    assert overview_path.read_text(encoding="utf-8") == "# Preserve reviewed design\n"


def test_render_svg_diagram_produces_valid_svg(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """The generated architecture diagram is valid SVG XML."""
    design = build_valid_design(
        generator_module,
        valid_context,
    )

    svg = generator_module.render_svg_diagram(design)
    root = ET.fromstring(svg)

    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.attrib["viewBox"] == "0 0 1400 900"
    assert root.attrib["role"] == "img"
    assert root.attrib["aria-label"] == "Azure intended architecture for Example Workload"


def test_render_svg_diagram_contains_every_node_and_relationship(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """SVG elements remain traceable to model identifiers."""
    design = build_valid_design(
        generator_module,
        valid_context,
    )

    svg = generator_module.render_svg_diagram(design)
    root = ET.fromstring(svg)

    namespace = {
        "svg": "http://www.w3.org/2000/svg",
    }
    node_elements = root.findall(
        ".//svg:g[@data-node-id]",
        namespace,
    )
    relationship_elements = root.findall(
        ".//svg:path[@data-relationship-id]",
        namespace,
    )

    assert len(node_elements) == 8
    assert len(relationship_elements) == 7

    assert {element.attrib["data-node-id"] for element in node_elements} == {
        node["id"] for node in get_design_nodes(design)
    }

    assert {element.attrib["data-relationship-id"] for element in relationship_elements} == {
        relationship["id"] for relationship in get_design_relationships(design)
    }


def test_render_svg_diagram_distinguishes_resource_state(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """SVG uses different fills for existing and planned resources."""
    design = build_valid_design(
        generator_module,
        valid_context,
    )

    svg = generator_module.render_svg_diagram(design)

    assert 'fill="#E8F3FF"' in svg
    assert 'stroke="#0078D4"' in svg
    assert 'fill="#FFF4CE"' in svg
    assert 'stroke="#C19C00"' in svg


def test_render_svg_diagram_escapes_untrusted_xml_text(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """User-provided labels cannot inject SVG markup."""
    workload = valid_context["workload"]
    assert isinstance(workload, dict)
    workload["name"] = 'Unsafe <script>alert("x")</script>'

    design = build_valid_design(
        generator_module,
        valid_context,
    )
    svg = generator_module.render_svg_diagram(design)
    root = ET.fromstring(svg)

    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg
    assert root.attrib["aria-label"] == (
        'Azure intended architecture for Unsafe <script>alert("x")</script>'
    )


def test_parse_arguments_uses_canonical_svg_path(
    generator_module: ModuleType,
) -> None:
    """The CLI exposes the canonical standalone SVG path."""
    arguments = generator_module.parse_arguments([])

    assert arguments.svg_output == Path(".specify/design/azure-design-overview.svg")


def test_run_generates_standalone_svg(
    generator_module: ModuleType,
    valid_context: dict[str, object],
    tmp_path: Path,
) -> None:
    """The workflow writes a directly viewable SVG diagram."""
    project_root = tmp_path / "consumer-project"
    context_path = project_root / ".specify" / "discovery" / "azure-context.json"
    svg_path = project_root / ".specify" / "design" / "azure-design-overview.svg"
    context_path.parent.mkdir(parents=True)
    context_path.write_text(
        json.dumps(valid_context),
        encoding="utf-8",
    )

    generator_module.run(
        project_root=project_root,
        context_path=Path(".specify/discovery/azure-context.json"),
        output_path=Path(".specify/design/azure-design-model.json"),
        overview_path=Path(".specify/design/azure-design-overview.md"),
        svg_path=Path(".specify/design/azure-design-overview.svg"),
        overwrite=False,
        generated_at=datetime(
            2026,
            9,
            14,
            14,
            30,
            tzinfo=timezone.utc,
        ),
        schema_path=DESIGN_SCHEMA_PATH,
    )

    svg = svg_path.read_text(encoding="utf-8")
    root = ET.fromstring(svg)

    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.attrib["aria-label"] == "Azure intended architecture for Example Workload"


def test_run_rejects_existing_svg_before_writing_other_artifacts(
    generator_module: ModuleType,
    valid_context: dict[str, object],
    tmp_path: Path,
) -> None:
    """SVG preflight protects the complete artifact set."""
    project_root = tmp_path / "consumer-project"
    context_path = project_root / ".specify" / "discovery" / "azure-context.json"
    model_path = project_root / ".specify" / "design" / "azure-design-model.json"
    overview_path = project_root / ".specify" / "design" / "azure-design-overview.md"
    svg_path = project_root / ".specify" / "design" / "azure-design-overview.svg"

    context_path.parent.mkdir(parents=True)
    svg_path.parent.mkdir(parents=True)
    context_path.write_text(
        json.dumps(valid_context),
        encoding="utf-8",
    )
    svg_path.write_text(
        "<svg><!-- preserve --></svg>\n",
        encoding="utf-8",
    )

    with pytest.raises(
        FileExistsError,
        match="already exists",
    ):
        generator_module.run(
            project_root=project_root,
            context_path=Path(".specify/discovery/azure-context.json"),
            output_path=Path(".specify/design/azure-design-model.json"),
            overview_path=Path(".specify/design/azure-design-overview.md"),
            svg_path=Path(".specify/design/azure-design-overview.svg"),
            overwrite=False,
            generated_at=datetime(
                2026,
                9,
                14,
                14,
                30,
                tzinfo=timezone.utc,
            ),
            schema_path=DESIGN_SCHEMA_PATH,
        )

    assert not model_path.exists()
    assert not overview_path.exists()
    assert svg_path.read_text(encoding="utf-8") == "<svg><!-- preserve --></svg>\n"


def test_build_design_model_maps_key_vault_integrations(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Key Vault integrations connect to their intended targets."""
    design = build_valid_design(
        generator_module,
        valid_context,
    )

    private_endpoint = get_design_relationship(
        design,
        ("relationship:resource:microsoft.keyvault/vaults:kv-example-we-prd:private-endpoint"),
    )
    diagnostics = get_design_relationship(
        design,
        ("relationship:resource:microsoft.keyvault/vaults:kv-example-we-prd:diagnostics"),
    )

    assert private_endpoint == {
        "id": (
            "relationship:resource:microsoft.keyvault/vaults:kv-example-we-prd:private-endpoint"
        ),
        "type": "private-endpoint-through",
        "source": ("resource:microsoft.keyvault/vaults:kv-example-we-prd"),
        "target": ("network:subnet:snet-private-endpoints"),
        "label": "Private endpoint",
        "state": "planned",
        "owner": "Workload Team",
    }

    assert diagnostics == {
        "id": ("relationship:resource:microsoft.keyvault/vaults:kv-example-we-prd:diagnostics"),
        "type": "diagnostics-to",
        "source": ("resource:microsoft.keyvault/vaults:kv-example-we-prd"),
        "target": ("resource:microsoft.operationalinsights/workspaces:log-hub-we-prd"),
        "label": "Diagnostic settings",
        "state": "planned",
        "owner": "Workload Team",
    }


def test_render_svg_diagram_uses_topology_aware_positions(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Related Azure components receive intentional diagram positions."""
    design = build_valid_design(
        generator_module,
        valid_context,
    )
    root = ET.fromstring(generator_module.render_svg_diagram(design))
    namespace = {
        "svg": "http://www.w3.org/2000/svg",
    }

    positions = {
        element.attrib["data-node-id"]: element.attrib["transform"]
        for element in root.findall(
            ".//svg:g[@data-node-id]",
            namespace,
        )
    }

    assert positions == {
        "network:hub": "translate(60 180)",
        "network:spoke": "translate(430 180)",
        ("network:subnet:snet-application"): "translate(390 440)",
        ("network:subnet:snet-private-endpoints"): "translate(720 440)",
        "network:firewall": "translate(60 440)",
        ("network:private-dns-resolver"): "translate(60 680)",
        ("resource:microsoft.operationalinsights/workspaces:log-hub-we-prd"): "translate(1060 440)",
        ("resource:microsoft.keyvault/vaults:kv-example-we-prd"): "translate(1060 180)",
    }


def test_render_svg_diagram_uses_routed_relationship_paths(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Important relationships use routes that avoid resource cards."""
    design = build_valid_design(
        generator_module,
        valid_context,
    )
    root = ET.fromstring(generator_module.render_svg_diagram(design))
    namespace = {
        "svg": "http://www.w3.org/2000/svg",
    }

    paths = {
        element.attrib["data-relationship-id"]: element.attrib["d"]
        for element in root.findall(
            ".//svg:path[@data-relationship-id]",
            namespace,
        )
    }

    assert paths["relationship:hub-spoke-peering"] == ("M 430 245 L 340 245")
    assert paths["relationship:spoke-subnet:snet-application"] == (
        "M 570 310 L 570 375 L 530 375 L 530 440"
    )
    assert paths["relationship:spoke-subnet:snet-private-endpoints"] == (
        "M 570 310 L 570 375 L 860 375 L 860 440"
    )
    assert paths["relationship:spoke-egress-firewall"] == (
        "M 430 245 L 380 245 L 380 505 L 340 505"
    )
    assert paths["relationship:spoke-private-dns-resolver"] == (
        "M 430 245 L 365 245 L 365 745 L 340 745"
    )
    assert paths[
        ("relationship:resource:microsoft.keyvault/vaults:kv-example-we-prd:private-endpoint")
    ] == ("M 1060 245 L 1000 245 L 1000 375 L 860 375 L 860 440")
    assert paths[
        ("relationship:resource:microsoft.keyvault/vaults:kv-example-we-prd:diagnostics")
    ] == ("M 1200 310 L 1200 440")


def test_render_svg_places_peering_label_above_resource_cards(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """The long peering label must not overlap the hub or spoke."""
    design = build_valid_design(
        generator_module,
        valid_context,
    )
    root = ET.fromstring(generator_module.render_svg_diagram(design))
    namespace = {
        "svg": "http://www.w3.org/2000/svg",
    }

    label = root.find(
        (".//svg:text[@data-relationship-label-id='relationship:hub-spoke-peering']"),
        namespace,
    )

    assert label is not None
    assert label.attrib["x"] == "385"
    assert label.attrib["y"] == "155"
    assert label.text == "Hub-to-spoke peering"


def test_render_drawio_diagram_produces_valid_document(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """The editable diagram is a valid uncompressed Draw.io document."""
    design = build_valid_design(
        generator_module,
        valid_context,
    )

    drawio = generator_module.render_drawio_diagram(design)
    root = ET.fromstring(drawio)

    assert root.tag == "mxfile"
    assert root.attrib["host"] == "app.diagrams.net"

    diagram = root.find("diagram")
    assert diagram is not None
    assert diagram.attrib["name"] == "Azure Intended Design"

    graph_model = diagram.find("mxGraphModel")
    assert graph_model is not None


def test_render_drawio_diagram_contains_all_model_elements(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Draw.io cells remain traceable to model identifiers."""
    design = build_valid_design(
        generator_module,
        valid_context,
    )
    root = ET.fromstring(generator_module.render_drawio_diagram(design))

    node_cells = root.findall(".//mxCell[@data-node-id]")
    relationship_cells = root.findall(".//mxCell[@edge='1']")

    assert len(node_cells) == 8
    assert len(relationship_cells) == 7

    assert {cell.attrib["data-node-id"] for cell in node_cells} == {
        node["id"] for node in get_design_nodes(design)
    }

    assert {cell.attrib["data-relationship-id"] for cell in relationship_cells} == {
        relationship["id"] for relationship in get_design_relationships(design)
    }


def test_render_drawio_diagram_distinguishes_resource_state(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Editable nodes preserve existing and planned styling."""
    design = build_valid_design(
        generator_module,
        valid_context,
    )
    root = ET.fromstring(generator_module.render_drawio_diagram(design))

    node_cells = root.findall(".//mxCell[@data-node-id]")
    existing_cells = [cell for cell in node_cells if cell.attrib["data-state"] == "existing"]
    planned_cells = [cell for cell in node_cells if cell.attrib["data-state"] == "planned"]

    assert len(existing_cells) == 4
    assert len(planned_cells) == 4

    for cell in existing_cells:
        assert "fillColor=#E8F3FF" in cell.attrib["style"]
        assert "strokeColor=#0078D4" in cell.attrib["style"]

    for cell in planned_cells:
        assert "fillColor=#FFF4CE" in cell.attrib["style"]
        assert "strokeColor=#C19C00" in cell.attrib["style"]


def test_render_drawio_diagram_escapes_untrusted_xml_text(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """User content cannot inject Draw.io XML elements."""
    workload = valid_context["workload"]
    assert isinstance(workload, dict)
    workload["name"] = 'Unsafe <mxCell id="injected"/>'

    design = build_valid_design(
        generator_module,
        valid_context,
    )
    drawio = generator_module.render_drawio_diagram(design)
    root = ET.fromstring(drawio)

    assert drawio.count('id="injected"') == 0

    node_values = [cell.attrib["value"] for cell in root.findall(".//mxCell[@vertex='1']")]

    assert any(
        ("Unsafe &lt;mxCell id=&quot;injected&quot;/&gt; spoke") in value for value in node_values
    )


def test_parse_arguments_uses_canonical_drawio_path(
    generator_module: ModuleType,
) -> None:
    """The CLI exposes the canonical editable diagram path."""
    arguments = generator_module.parse_arguments([])

    assert arguments.drawio_output == Path(".specify/design/azure-design-overview.drawio")


def test_run_generates_editable_drawio_diagram(
    generator_module: ModuleType,
    valid_context: dict[str, object],
    tmp_path: Path,
) -> None:
    """The workflow writes an editable Draw.io architecture diagram."""
    project_root = tmp_path / "consumer-project"
    context_path = project_root / ".specify" / "discovery" / "azure-context.json"
    drawio_path = project_root / ".specify" / "design" / "azure-design-overview.drawio"
    context_path.parent.mkdir(parents=True)
    context_path.write_text(
        json.dumps(valid_context),
        encoding="utf-8",
    )

    generator_module.run(
        project_root=project_root,
        context_path=Path(".specify/discovery/azure-context.json"),
        output_path=Path(".specify/design/azure-design-model.json"),
        overview_path=Path(".specify/design/azure-design-overview.md"),
        svg_path=Path(".specify/design/azure-design-overview.svg"),
        drawio_path=Path(".specify/design/azure-design-overview.drawio"),
        overwrite=False,
        generated_at=datetime(
            2026,
            9,
            14,
            14,
            30,
            tzinfo=timezone.utc,
        ),
        schema_path=DESIGN_SCHEMA_PATH,
    )

    drawio = drawio_path.read_text(encoding="utf-8")
    root = ET.fromstring(drawio)

    assert root.tag == "mxfile"
    assert root.attrib["host"] == "app.diagrams.net"


def test_run_rejects_existing_drawio_before_writing_other_artifacts(
    generator_module: ModuleType,
    valid_context: dict[str, object],
    tmp_path: Path,
) -> None:
    """Draw.io preflight protects the complete artifact set."""
    project_root = tmp_path / "consumer-project"
    context_path = project_root / ".specify" / "discovery" / "azure-context.json"
    design_directory = project_root / ".specify" / "design"
    model_path = design_directory / "azure-design-model.json"
    overview_path = design_directory / "azure-design-overview.md"
    svg_path = design_directory / "azure-design-overview.svg"
    drawio_path = design_directory / "azure-design-overview.drawio"

    context_path.parent.mkdir(parents=True)
    drawio_path.parent.mkdir(parents=True)
    context_path.write_text(
        json.dumps(valid_context),
        encoding="utf-8",
    )
    drawio_path.write_text(
        "<mxfile><!-- preserve --></mxfile>\n",
        encoding="utf-8",
    )

    with pytest.raises(
        FileExistsError,
        match="already exists",
    ):
        generator_module.run(
            project_root=project_root,
            context_path=Path(".specify/discovery/azure-context.json"),
            output_path=Path(".specify/design/azure-design-model.json"),
            overview_path=Path(".specify/design/azure-design-overview.md"),
            svg_path=Path(".specify/design/azure-design-overview.svg"),
            drawio_path=Path(".specify/design/azure-design-overview.drawio"),
            overwrite=False,
            generated_at=datetime(
                2026,
                9,
                14,
                14,
                30,
                tzinfo=timezone.utc,
            ),
            schema_path=DESIGN_SCHEMA_PATH,
        )

    assert not model_path.exists()
    assert not overview_path.exists()
    assert not svg_path.exists()
    assert drawio_path.read_text(encoding="utf-8") == "<mxfile><!-- preserve --></mxfile>\n"


def test_render_drawio_diagram_uses_structured_html_labels(
    generator_module: ModuleType,
    valid_context: dict[str, object],
) -> None:
    """Editable resource cards separate their important metadata."""
    design = build_valid_design(
        generator_module,
        valid_context,
    )
    root = ET.fromstring(generator_module.render_drawio_diagram(design))

    node_cells = root.findall(".//mxCell[@data-node-id]")
    hub = next(cell for cell in node_cells if cell.attrib["data-node-id"] == "network:hub")

    assert hub.attrib["value"] == (
        "<b>vnet-hub-we-prd</b><br>"
        "Microsoft.Network/virtualNetworks<br>"
        "Owner: Platform Team<br>"
        "<b>Existing</b>"
    )
    assert "html=1" in hub.attrib["style"]
    assert "html=0" not in hub.attrib["style"]
