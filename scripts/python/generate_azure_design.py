#!/usr/bin/env python3
"""Generate reviewable intended-state Azure architecture designs."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

EXIT_SUCCESS = 0
EXIT_EXECUTION_ERROR = 2


def parse_arguments(
    arguments: list[str] | None = None,
) -> argparse.Namespace:
    """Parse intended-design generator command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate a reviewable intended-state Azure architecture "
            "design from a completed Azure interview context."
        )
    )
    parser.add_argument(
        "--context",
        type=Path,
        default=Path(".specify/discovery/azure-context.json"),
        help=(
            "Validated Azure interview context. Defaults to .specify/discovery/azure-context.json."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".specify/design/azure-design-model.json"),
        help=("Design model output. Defaults to .specify/design/azure-design-model.json."),
    )
    parser.add_argument(
        "--overview-output",
        type=Path,
        default=Path(".specify/design/azure-design-overview.md"),
        help=(
            "Human-reviewable overview output. Defaults to "
            ".specify/design/azure-design-overview.md."
        ),
    )
    parser.add_argument(
        "--svg-output",
        type=Path,
        default=Path(".specify/design/azure-design-overview.svg"),
        help=(
            "Standalone SVG diagram output. Defaults to .specify/design/azure-design-overview.svg."
        ),
    )
    parser.add_argument(
        "--drawio-output",
        type=Path,
        default=Path(".specify/design/azure-design-overview.drawio"),
        help=(
            "Editable Draw.io diagram output. Defaults to "
            ".specify/design/azure-design-overview.drawio."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=("Explicitly replace an existing intended-design model."),
    )

    return parser.parse_args(arguments)


def require_mapping(
    document: dict[str, Any],
    property_name: str,
) -> dict[str, Any]:
    """Return a required object property or reject malformed input."""
    value = document.get(property_name)

    if not isinstance(value, dict):
        raise ValueError(f"Design source must contain an object named '{property_name}'.")

    return value


def validate_design_source(context: dict[str, Any]) -> None:
    """Require a completed and specification-ready interview context."""
    if not isinstance(context, dict):
        raise ValueError("Design source must be a JSON object.")

    interview = require_mapping(context, "interview")
    readiness = require_mapping(context, "readiness")

    if interview.get("status") != "complete":
        raise ValueError("Interview status must be complete.")

    if readiness.get("readyForSpecification") is not True:
        raise ValueError("Context is not ready for specification.")

    readiness_requirements = [
        (
            "blockingQuestionsRemaining",
            "Blocking questions remain.",
        ),
        (
            "unvalidatedCriticalAssumptions",
            "Critical assumptions remain unvalidated.",
        ),
        (
            "missingResourceIdentifiers",
            "Required resource identifiers are missing.",
        ),
        (
            "conflictingRequirements",
            "Conflicting requirements remain.",
        ),
    ]

    for property_name, error_message in readiness_requirements:
        value = readiness.get(property_name)

        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"Readiness property '{property_name}' must be an integer.")

        if value != 0:
            raise ValueError(error_message)


def resource_name_from_id(resource_id: object) -> str | None:
    """Extract the final resource name from an Azure resource ID."""
    if not isinstance(resource_id, str):
        return None

    normalized_resource_id = resource_id.rstrip("/")

    if not normalized_resource_id:
        return None

    return normalized_resource_id.rsplit("/", maxsplit=1)[-1]


def build_network_nodes(
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build intended and existing network architecture nodes."""
    workload = require_mapping(context, "workload")
    network = require_mapping(context, "network")
    private_connectivity = require_mapping(
        context,
        "privateConnectivity",
    )

    workload_name = workload.get("name")
    workload_owner = workload.get("technicalOwner")
    hub_owner = network.get("hubOwner")
    hub_resource_id = network.get("hubResourceId")
    firewall_resource_id = network.get("firewallResourceId")
    dns_resolver_resource_id = private_connectivity.get("privateDnsResolverResourceId")

    nodes: list[dict[str, Any]] = [
        {
            "id": "network:hub",
            "category": "network",
            "resourceType": "Microsoft.Network/virtualNetworks",
            "name": resource_name_from_id(hub_resource_id),
            "state": "existing",
            "owner": hub_owner,
            "modifiable": False,
            "resourceId": hub_resource_id,
            "properties": {},
        },
        {
            "id": "network:spoke",
            "category": "network",
            "resourceType": "Microsoft.Network/virtualNetworks",
            "name": f"{workload_name} spoke",
            "state": "planned",
            "owner": workload_owner,
            "modifiable": True,
            "resourceId": network.get("spokeResourceId"),
            "properties": {
                "addressSpaces": deepcopy(network.get("addressSpaces", [])),
                "topology": network.get("topology"),
            },
        },
    ]

    subnets = network.get("subnets", [])

    if not isinstance(subnets, list):
        raise ValueError("Network property 'subnets' must be an array.")

    for subnet in subnets:
        if not isinstance(subnet, dict):
            raise ValueError("Every subnet must be an object.")

        subnet_name = subnet.get("name")

        if not isinstance(subnet_name, str) or not subnet_name:
            raise ValueError("Every subnet must have a name.")

        nodes.append(
            {
                "id": f"network:subnet:{subnet_name.lower()}",
                "category": "network",
                "resourceType": ("Microsoft.Network/virtualNetworks/subnets"),
                "name": subnet_name,
                "state": "planned",
                "owner": workload_owner,
                "modifiable": True,
                "resourceId": None,
                "properties": {
                    "prefix": subnet.get("prefix"),
                    "purpose": subnet.get("purpose"),
                },
            }
        )

    nodes.extend(
        [
            {
                "id": "network:firewall",
                "category": "network",
                "resourceType": "Microsoft.Network/azureFirewalls",
                "name": resource_name_from_id(firewall_resource_id),
                "state": "existing",
                "owner": hub_owner,
                "modifiable": False,
                "resourceId": firewall_resource_id,
                "properties": {},
            },
            {
                "id": "network:private-dns-resolver",
                "category": "network",
                "resourceType": "Microsoft.Network/dnsResolvers",
                "name": resource_name_from_id(dns_resolver_resource_id),
                "state": "existing",
                "owner": private_connectivity.get("vnetLinkOwner"),
                "modifiable": False,
                "resourceId": dns_resolver_resource_id,
                "properties": {},
            },
        ]
    )

    return nodes


def build_declared_resource_nodes(
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Convert declared create and reuse resources into design nodes."""
    existing_resources = context.get("existingResources", [])

    if not isinstance(existing_resources, list):
        raise ValueError("Context property 'existingResources' must be an array.")

    nodes: list[dict[str, Any]] = []

    for resource in existing_resources:
        if not isinstance(resource, dict):
            raise ValueError("Every existingResources entry must be an object.")

        resource_type = resource.get("resourceType")
        resource_name = resource.get("resourceName")
        intent = resource.get("intent")

        if not isinstance(resource_type, str) or not resource_type:
            raise ValueError("Every declared resource must have a resourceType.")

        if not isinstance(resource_name, str) or not resource_name:
            raise ValueError("Every declared resource must have a resourceName.")

        nodes.append(
            {
                "id": (f"resource:{resource_type.lower()}:{resource_name.lower()}"),
                "category": "resource",
                "resourceType": resource_type,
                "name": resource_name,
                "state": ("existing" if intent == "reuse" else "planned"),
                "owner": resource.get("owner"),
                "modifiable": resource.get("modifiable"),
                "resourceId": resource.get("resourceId"),
                "properties": {
                    "intent": intent,
                    "requiredIntegrations": deepcopy(
                        resource.get(
                            "requiredIntegrations",
                            [],
                        )
                    ),
                },
            }
        )

    return nodes


def build_architecture_nodes(
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build architecture nodes in deterministic display order."""
    return [
        *build_network_nodes(context),
        *build_declared_resource_nodes(context),
    ]


def build_architecture_relationships(
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build deterministic relationships between architecture nodes."""
    workload = require_mapping(context, "workload")
    network = require_mapping(context, "network")
    private_connectivity = require_mapping(
        context,
        "privateConnectivity",
    )

    workload_owner = workload.get("technicalOwner")
    hub_owner = network.get("hubOwner")
    relationships: list[dict[str, Any]] = []

    if network.get("hubResourceId"):
        relationships.append(
            {
                "id": "relationship:hub-spoke-peering",
                "type": "peered-with",
                "source": "network:spoke",
                "target": "network:hub",
                "label": "Hub-to-spoke peering",
                "state": "planned",
                "owner": network.get("peeringOwner"),
            }
        )

    subnets = network.get("subnets", [])

    if not isinstance(subnets, list):
        raise ValueError("Network property 'subnets' must be an array.")

    for subnet in subnets:
        if not isinstance(subnet, dict):
            raise ValueError("Every subnet must be an object.")

        subnet_name = subnet.get("name")

        if not isinstance(subnet_name, str) or not subnet_name:
            raise ValueError("Every subnet must have a name.")

        relationships.append(
            {
                "id": (f"relationship:spoke-subnet:{subnet_name.lower()}"),
                "type": "contains",
                "source": "network:spoke",
                "target": (f"network:subnet:{subnet_name.lower()}"),
                "label": "Contains subnet",
                "state": "planned",
                "owner": workload_owner,
            }
        )

    if network.get("firewallResourceId"):
        relationships.append(
            {
                "id": "relationship:spoke-egress-firewall",
                "type": "egress-through",
                "source": "network:spoke",
                "target": "network:firewall",
                "label": "Central egress",
                "state": "existing",
                "owner": hub_owner,
            }
        )

    if private_connectivity.get("privateDnsResolverResourceId"):
        relationships.append(
            {
                "id": ("relationship:spoke-private-dns-resolver"),
                "type": "dns-resolution-through",
                "source": "network:spoke",
                "target": "network:private-dns-resolver",
                "label": "Private DNS resolution",
                "state": "existing",
                "owner": private_connectivity.get("vnetLinkOwner"),
            }
        )

    existing_resources = context.get(
        "existingResources",
        [],
    )

    if not isinstance(existing_resources, list):
        raise ValueError("Context property 'existingResources' must be an array.")

    private_endpoint_subnet_id: str | None = None

    for subnet in subnets:
        subnet_name = subnet.get("name")
        subnet_purpose = subnet.get("purpose")

        searchable_subnet_text = " ".join(
            [
                str(subnet_name or ""),
                str(subnet_purpose or ""),
            ]
        ).casefold()

        if "private endpoint" in searchable_subnet_text:
            private_endpoint_subnet_id = f"network:subnet:{str(subnet_name).lower()}"
            break

    workspace_node_id: str | None = None

    for resource in existing_resources:
        if not isinstance(resource, dict):
            raise ValueError("Every existingResources entry must be an object.")

        resource_type = resource.get("resourceType")
        resource_name = resource.get("resourceName")

        if (
            isinstance(resource_type, str)
            and isinstance(resource_name, str)
            and resource_type.casefold() == "microsoft.operationalinsights/workspaces"
        ):
            workspace_node_id = f"resource:{resource_type.lower()}:{resource_name.lower()}"
            break

    for resource in existing_resources:
        if not isinstance(resource, dict):
            continue

        resource_type = resource.get("resourceType")
        resource_name = resource.get("resourceName")
        resource_owner = resource.get("owner")
        integrations = resource.get(
            "requiredIntegrations",
            [],
        )

        if (
            not isinstance(resource_type, str)
            or not isinstance(resource_name, str)
            or not isinstance(integrations, list)
        ):
            continue

        resource_node_id = f"resource:{resource_type.lower()}:{resource_name.lower()}"
        relationship_prefix = f"relationship:{resource_node_id}"
        normalized_integrations = {str(integration).casefold() for integration in integrations}

        if "private endpoint" in normalized_integrations and private_endpoint_subnet_id is not None:
            relationships.append(
                {
                    "id": (f"{relationship_prefix}:private-endpoint"),
                    "type": "private-endpoint-through",
                    "source": resource_node_id,
                    "target": private_endpoint_subnet_id,
                    "label": "Private endpoint",
                    "state": "planned",
                    "owner": resource_owner,
                }
            )

        if (
            "diagnostic settings" in normalized_integrations
            and workspace_node_id is not None
            and resource_node_id != workspace_node_id
        ):
            relationships.append(
                {
                    "id": (f"{relationship_prefix}:diagnostics"),
                    "type": "diagnostics-to",
                    "source": resource_node_id,
                    "target": workspace_node_id,
                    "label": "Diagnostic settings",
                    "state": "planned",
                    "owner": resource_owner,
                }
            )

    return relationships


def validate_design_model(
    design: dict[str, Any],
    schema: dict[str, Any],
) -> None:
    """Validate design structure, identifiers, and relationships."""
    validator = Draft202012Validator(schema)
    schema_errors = sorted(
        validator.iter_errors(design),
        key=lambda error: "/".join(str(part) for part in error.absolute_path),
    )

    if schema_errors:
        messages = "; ".join(error.message for error in schema_errors)
        raise ValueError(f"Design schema validation failed: {messages}")

    architecture = require_mapping(
        design,
        "architecture",
    )
    nodes = architecture["nodes"]
    relationships = architecture["relationships"]

    node_ids: set[str] = set()

    for node in nodes:
        node_id = node["id"]

        if node_id in node_ids:
            raise ValueError(f"Duplicate architecture node ID: {node_id}")

        node_ids.add(node_id)

    relationship_ids: set[str] = set()

    for relationship in relationships:
        relationship_id = relationship["id"]

        if relationship_id in relationship_ids:
            raise ValueError(f"Duplicate architecture relationship ID: {relationship_id}")

        relationship_ids.add(relationship_id)

        for endpoint_name in ("source", "target"):
            endpoint_id = relationship[endpoint_name]

            if endpoint_id not in node_ids:
                raise ValueError(
                    f"Relationship '{relationship_id}' "
                    f"{endpoint_name} references unknown node: "
                    f"{endpoint_id}"
                )


def validate_design_context_path(
    context_path: Path,
    *,
    project_root: Path,
) -> Path:
    """Require a JSON context inside the Spec Kit discovery directory."""
    resolved_project_root = project_root.resolve()
    specify_directory = resolved_project_root / ".specify"

    if not specify_directory.is_dir():
        raise ValueError(f"Current directory is not a Spec Kit project: {resolved_project_root}")

    if context_path.is_absolute():
        resolved_context_path = context_path.resolve()
    else:
        resolved_context_path = (resolved_project_root / context_path).resolve()

    discovery_directory = (specify_directory / "discovery").resolve()

    if not resolved_context_path.is_relative_to(discovery_directory):
        raise ValueError("Design context must remain inside .specify/discovery.")

    if resolved_context_path.suffix.lower() != ".json":
        raise ValueError("Design context input must be a JSON file.")

    if not resolved_context_path.is_file():
        raise FileNotFoundError(f"Design context does not exist: {resolved_context_path}")

    return resolved_context_path


def load_json_document(
    document_path: Path,
) -> dict[str, Any]:
    """Load a JSON object from disk with controlled errors."""
    try:
        with document_path.open(
            "r",
            encoding="utf-8",
        ) as stream:
            document = json.load(stream)
    except json.JSONDecodeError as exception:
        raise ValueError(f"Invalid JSON document: {document_path}") from exception
    except OSError as exception:
        raise ValueError(f"Unable to read JSON document: {document_path}") from exception

    if not isinstance(document, dict):
        raise ValueError(f"JSON document must contain a JSON object: {document_path}")

    return document


def validate_design_output_path(
    output_path: Path,
    *,
    project_root: Path,
) -> Path:
    """Require a JSON output inside a Spec Kit design directory."""
    resolved_project_root = project_root.resolve()
    specify_directory = resolved_project_root / ".specify"

    if not specify_directory.is_dir():
        raise ValueError(f"Current directory is not a Spec Kit project: {resolved_project_root}")

    if output_path.is_absolute():
        resolved_output_path = output_path.resolve()
    else:
        resolved_output_path = (resolved_project_root / output_path).resolve()

    design_directory = (specify_directory / "design").resolve()

    if not resolved_output_path.is_relative_to(design_directory):
        raise ValueError("Design output must remain inside .specify/design.")

    if resolved_output_path.suffix.lower() != ".json":
        raise ValueError("Design model output must be a JSON file.")

    return resolved_output_path


def validate_design_overview_path(
    overview_path: Path,
    *,
    project_root: Path,
) -> Path:
    """Require a Markdown overview inside the design directory."""
    resolved_project_root = project_root.resolve()
    specify_directory = resolved_project_root / ".specify"

    if not specify_directory.is_dir():
        raise ValueError(f"Current directory is not a Spec Kit project: {resolved_project_root}")

    if overview_path.is_absolute():
        resolved_overview_path = overview_path.resolve()
    else:
        resolved_overview_path = (resolved_project_root / overview_path).resolve()

    design_directory = (specify_directory / "design").resolve()

    if not resolved_overview_path.is_relative_to(design_directory):
        raise ValueError("Design overview must remain inside .specify/design.")

    if resolved_overview_path.suffix.lower() != ".md":
        raise ValueError("Design overview output must be a Markdown file.")

    return resolved_overview_path


def validate_design_svg_path(
    svg_path: Path,
    *,
    project_root: Path,
) -> Path:
    """Require an SVG artifact inside the design directory."""
    resolved_project_root = project_root.resolve()
    specify_directory = resolved_project_root / ".specify"

    if not specify_directory.is_dir():
        raise ValueError(f"Current directory is not a Spec Kit project: {resolved_project_root}")

    if svg_path.is_absolute():
        resolved_svg_path = svg_path.resolve()
    else:
        resolved_svg_path = (resolved_project_root / svg_path).resolve()

    design_directory = (specify_directory / "design").resolve()

    if not resolved_svg_path.is_relative_to(design_directory):
        raise ValueError("Design SVG must remain inside .specify/design.")

    if resolved_svg_path.suffix.lower() != ".svg":
        raise ValueError("Design SVG output must be an SVG file.")

    return resolved_svg_path


def validate_design_drawio_path(
    drawio_path: Path,
    *,
    project_root: Path,
) -> Path:
    """Require a Draw.io artifact inside the design directory."""
    resolved_project_root = project_root.resolve()
    specify_directory = resolved_project_root / ".specify"

    if not specify_directory.is_dir():
        raise ValueError(f"Current directory is not a Spec Kit project: {resolved_project_root}")

    if drawio_path.is_absolute():
        resolved_drawio_path = drawio_path.resolve()
    else:
        resolved_drawio_path = (resolved_project_root / drawio_path).resolve()

    design_directory = (specify_directory / "design").resolve()

    if not resolved_drawio_path.is_relative_to(design_directory):
        raise ValueError("Draw.io output must remain inside .specify/design.")

    if resolved_drawio_path.suffix.lower() != ".drawio":
        raise ValueError("Editable design output must be a Draw.io file.")

    return resolved_drawio_path


def write_design_model(
    design: dict[str, Any],
    output_path: Path,
    *,
    overwrite: bool,
) -> None:
    """Atomically write a design model without implicit overwrite."""
    resolved_output_path = output_path.resolve()

    if resolved_output_path.exists() and not overwrite:
        raise FileExistsError(f"Design output already exists: {resolved_output_path}")

    resolved_output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{resolved_output_path.name}.",
            suffix=".tmp",
            dir=resolved_output_path.parent,
            delete=False,
        ) as temporary_file:
            json.dump(
                design,
                temporary_file,
                indent=2,
                ensure_ascii=False,
            )
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
            temporary_path = Path(temporary_file.name)

        os.replace(
            temporary_path,
            resolved_output_path,
        )
        temporary_path = None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def build_design_model(
    context: dict[str, Any],
    *,
    generated_at: datetime,
) -> dict[str, Any]:
    """Build an unreviewed intended-state model from confirmed discovery."""
    validate_design_source(context)

    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        raise ValueError("Generation timestamp must be timezone-aware.")

    interview = require_mapping(context, "interview")
    workload = require_mapping(context, "workload")
    azure_estate = require_mapping(context, "azureEstate")

    normalized_generated_at = (
        generated_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    )

    architecture_nodes = build_architecture_nodes(context)
    architecture_relationships = build_architecture_relationships(context)

    return {
        "schemaVersion": "1.0",
        "designStatus": "intended",
        "reviewStatus": "unreviewed",
        "generatedAt": normalized_generated_at,
        "source": {
            "type": "azure-interview-context",
            "schemaVersion": context.get("schemaVersion"),
            "interviewUpdatedAt": interview.get("updatedAt"),
            "confirmedBy": interview.get("confirmedBy"),
        },
        "workload": {
            "name": workload.get("name"),
            "purpose": workload.get("purpose"),
            "lifecycle": workload.get("lifecycle"),
            "criticality": workload.get("criticality"),
            "environments": deepcopy(workload.get("environments", [])),
        },
        "azureScope": {
            "tenantId": azure_estate.get("tenantId"),
            "managementGroupId": azure_estate.get("managementGroupId"),
            "subscriptions": deepcopy(azure_estate.get("subscriptions", [])),
            "regions": deepcopy(azure_estate.get("regions", [])),
        },
        "architecture": {
            "nodes": architecture_nodes,
            "relationships": architecture_relationships,
        },
    }


def escape_mermaid_label(value: object) -> str:
    """Escape untrusted text for use inside a Mermaid label."""
    if value is None:
        return "Unnamed resource"

    normalized_value = " ".join(str(value).splitlines())

    return escape(
        normalized_value,
        quote=True,
    )


def render_mermaid_diagram(
    design: dict[str, Any],
) -> str:
    """Render a deterministic Mermaid overview diagram."""
    architecture = require_mapping(
        design,
        "architecture",
    )
    nodes = architecture["nodes"]
    relationships = architecture["relationships"]

    node_aliases: dict[str, str] = {}
    existing_aliases: list[str] = []
    planned_aliases: list[str] = []
    lines = ["flowchart TB"]

    for index, node in enumerate(nodes):
        node_id = node["id"]
        alias = f"n{index}"
        node_aliases[node_id] = alias

        name = escape_mermaid_label(node.get("name"))
        resource_type = escape_mermaid_label(node.get("resourceType"))
        state = node.get("state")
        state_label = escape_mermaid_label(str(state).capitalize())

        lines.append(f'    {alias}["{name}<br/>{resource_type}<br/>{state_label}"]')

        if state == "existing":
            existing_aliases.append(alias)
        elif state == "planned":
            planned_aliases.append(alias)

    for relationship in relationships:
        source_alias = node_aliases[relationship["source"]]
        target_alias = node_aliases[relationship["target"]]
        label = escape_mermaid_label(relationship.get("label"))

        lines.append(f'    {source_alias} -->|"{label}"| {target_alias}')

    lines.extend(
        [
            ("    classDef existing fill:#E8F3FF,stroke:#0078D4,color:#102A43"),
            (
                "    classDef planned "
                "fill:#FFF4CE,stroke:#C19C00,"
                "color:#3B2F00,stroke-dasharray: 5 3"
            ),
        ]
    )

    if existing_aliases:
        lines.append(f"    class {','.join(existing_aliases)} existing")

    if planned_aliases:
        lines.append(f"    class {','.join(planned_aliases)} planned")

    return "\n".join(lines) + "\n"


def normalize_markdown_text(value: object) -> str:
    """Normalize untrusted text so it cannot create new Markdown lines."""
    if value is None:
        return "Unknown"

    return " ".join(str(value).splitlines())


def render_drawio_diagram(
    design: dict[str, Any],
) -> str:
    """Render an editable uncompressed Draw.io architecture diagram."""
    architecture = require_mapping(
        design,
        "architecture",
    )
    nodes = architecture["nodes"]
    relationships = architecture["relationships"]

    preferred_positions: dict[str, tuple[int, int]] = {
        "network:hub": (60, 180),
        "network:spoke": (430, 180),
        "network:subnet:snet-application": (390, 440),
        ("network:subnet:snet-private-endpoints"): (720, 440),
        "network:firewall": (60, 440),
        "network:private-dns-resolver": (60, 680),
        ("resource:microsoft.operationalinsights/workspaces:log-hub-we-prd"): (1060, 440),
        ("resource:microsoft.keyvault/vaults:kv-example-we-prd"): (1060, 180),
    }

    node_positions: dict[str, tuple[int, int]] = {}
    node_cell_ids: dict[str, str] = {}
    fallback_index = 0

    for index, node in enumerate(nodes):
        node_id = str(node["id"])
        node_cell_ids[node_id] = f"node-{index}"

        preferred_position = preferred_positions.get(node_id)

        if preferred_position is not None:
            node_positions[node_id] = preferred_position
            continue

        fallback_column = fallback_index % 4
        fallback_row = fallback_index // 4
        node_positions[node_id] = (
            60 + fallback_column * 330,
            180 + fallback_row * 300,
        )
        fallback_index += 1

    lines = [
        ('<mxfile host="app.diagrams.net" agent="Spec Kit Azure Interview" version="1.0">'),
        ('  <diagram id="azure-intended-design" name="Azure Intended Design">'),
        (
            '    <mxGraphModel dx="1400" dy="900" '
            'grid="1" gridSize="10" guides="1" '
            'tooltips="1" connect="1" arrows="1" '
            'fold="1" page="1" pageScale="1" '
            'pageWidth="1400" pageHeight="900" '
            'math="0" shadow="0">'
        ),
        "      <root>",
        '        <mxCell id="0" />',
        '        <mxCell id="1" parent="0" />',
    ]

    for index, node in enumerate(nodes):
        node_id = str(node["id"])
        node_state = str(node.get("state"))
        x_position, y_position = node_positions[node_id]

        if node_state == "existing":
            fill_color = "#E8F3FF"
            stroke_color = "#0078D4"
            font_color = "#102A43"
            dashed = "0"
            state_label = "Existing"
        else:
            fill_color = "#FFF4CE"
            stroke_color = "#C19C00"
            font_color = "#3B2F00"
            dashed = "1"
            state_label = "Planned"

        name = normalize_markdown_text(node.get("name"))
        resource_type = normalize_markdown_text(node.get("resourceType"))
        owner = normalize_markdown_text(node.get("owner"))

        safe_name = escape(
            name,
            quote=True,
        )
        safe_resource_type = escape(
            resource_type,
            quote=True,
        )
        safe_owner = escape(
            owner,
            quote=True,
        )

        html_value = (
            f"<b>{safe_name}</b><br>"
            f"{safe_resource_type}<br>"
            f"Owner: {safe_owner}<br>"
            f"<b>{state_label}</b>"
        )
        cell_value = escape(
            html_value,
            quote=True,
        )
        escaped_node_id = escape(
            node_id,
            quote=True,
        )

        style = (
            "rounded=1;"
            "whiteSpace=wrap;"
            "html=1;"
            "align=left;"
            "verticalAlign=middle;"
            "spacingTop=12;"
            "spacingLeft=12;"
            "fontFamily=Segoe UI;"
            "fontSize=13;"
            f"fontColor={font_color};"
            f"fillColor={fill_color};"
            f"strokeColor={stroke_color};"
            "strokeWidth=3;"
            f"dashed={dashed};"
        )

        lines.extend(
            [
                (
                    f'        <mxCell id="node-{index}" '
                    f'value="{cell_value}" '
                    f'style="{style}" vertex="1" '
                    'parent="1" '
                    f'data-node-id="{escaped_node_id}" '
                    f'data-state="{node_state}">'
                ),
                (
                    f'          <mxGeometry x="{x_position}" '
                    f'y="{y_position}" width="280" '
                    'height="130" as="geometry" />'
                ),
                "        </mxCell>",
            ]
        )

    relationship_label_offsets = {
        "relationship:hub-spoke-peering": (0, -50),
        "relationship:spoke-subnet:snet-application": (-45, -18),
        "relationship:spoke-subnet:snet-private-endpoints": (55, -18),
        "relationship:spoke-egress-firewall": (-65, 105),
        "relationship:spoke-private-dns-resolver": (-70, 25),
        ("relationship:resource:microsoft.keyvault/vaults:kv-example-we-prd:private-endpoint"): (
            0,
            -30,
        ),
        ("relationship:resource:microsoft.keyvault/vaults:kv-example-we-prd:diagnostics"): (65, 0),
    }

    for index, relationship in enumerate(relationships):
        relationship_id = str(relationship["id"])
        source_id = str(relationship["source"])
        target_id = str(relationship["target"])
        relationship_label = escape(
            normalize_markdown_text(relationship.get("label")),
            quote=True,
        )
        escaped_relationship_id = escape(
            relationship_id,
            quote=True,
        )

        source_cell_id = node_cell_ids[source_id]
        target_cell_id = node_cell_ids[target_id]
        label_offset_x, label_offset_y = relationship_label_offsets.get(
            relationship_id,
            (0, -20),
        )

        relationship_style = (
            "edgeStyle=orthogonalEdgeStyle;"
            "rounded=1;"
            "orthogonalLoop=1;"
            "jettySize=auto;"
            "html=0;"
            "endArrow=block;"
            "endFill=1;"
            "strokeColor=#5B6573;"
            "strokeWidth=2;"
            "fontFamily=Segoe UI;"
            "fontSize=12;"
            "labelBackgroundColor=#FFFFFF;"
        )

        lines.extend(
            [
                (
                    f'        <mxCell id="edge-{index}" '
                    f'value="{relationship_label}" '
                    f'style="{relationship_style}" edge="1" '
                    'parent="1" '
                    f'source="{source_cell_id}" '
                    f'target="{target_cell_id}" '
                    f'data-relationship-id="'
                    f'{escaped_relationship_id}">'
                ),
                '          <mxGeometry relative="1" as="geometry">',
                (f'            <mxPoint x="{label_offset_x}" y="{label_offset_y}" as="offset" />'),
                "          </mxGeometry>",
                "        </mxCell>",
            ]
        )

    lines.extend(
        [
            "      </root>",
            "    </mxGraphModel>",
            "  </diagram>",
            "</mxfile>",
        ]
    )

    return "\n".join(lines) + "\n"


def render_svg_diagram(
    design: dict[str, Any],
) -> str:
    """Render a topology-aware standalone SVG architecture diagram."""
    workload = require_mapping(design, "workload")
    architecture = require_mapping(design, "architecture")
    nodes = architecture["nodes"]
    relationships = architecture["relationships"]

    workload_name = normalize_markdown_text(workload.get("name"))
    escaped_workload_name = escape(
        workload_name,
        quote=True,
    )

    node_width = 280
    node_height = 130

    preferred_positions: dict[str, tuple[int, int]] = {
        "network:hub": (60, 180),
        "network:spoke": (430, 180),
        "network:subnet:snet-application": (390, 440),
        ("network:subnet:snet-private-endpoints"): (720, 440),
        "network:firewall": (60, 440),
        "network:private-dns-resolver": (60, 680),
        ("resource:microsoft.operationalinsights/workspaces:log-hub-we-prd"): (1060, 440),
        ("resource:microsoft.keyvault/vaults:kv-example-we-prd"): (1060, 180),
    }

    preferred_routes: dict[str, str] = {
        "relationship:hub-spoke-peering": ("M 430 245 L 340 245"),
        ("relationship:spoke-subnet:snet-application"): ("M 570 310 L 570 375 L 530 375 L 530 440"),
        ("relationship:spoke-subnet:snet-private-endpoints"): (
            "M 570 310 L 570 375 L 860 375 L 860 440"
        ),
        "relationship:spoke-egress-firewall": ("M 430 245 L 380 245 L 380 505 L 340 505"),
        ("relationship:spoke-private-dns-resolver"): ("M 430 245 L 365 245 L 365 745 L 340 745"),
        ("relationship:resource:microsoft.keyvault/vaults:kv-example-we-prd:private-endpoint"): (
            "M 1060 245 L 1000 245 L 1000 375 L 860 375 L 860 440"
        ),
        ("relationship:resource:microsoft.keyvault/vaults:kv-example-we-prd:diagnostics"): (
            "M 1200 310 L 1200 440"
        ),
    }

    preferred_label_positions: dict[str, tuple[int, int]] = {
        "relationship:hub-spoke-peering": (385, 155),
        ("relationship:spoke-subnet:snet-application"): (500, 355),
        ("relationship:spoke-subnet:snet-private-endpoints"): (735, 355),
        "relationship:spoke-egress-firewall": (355, 385),
        ("relationship:spoke-private-dns-resolver"): (330, 620),
        ("relationship:resource:microsoft.keyvault/vaults:kv-example-we-prd:private-endpoint"): (
            930,
            355,
        ),
        ("relationship:resource:microsoft.keyvault/vaults:kv-example-we-prd:diagnostics"): (
            1210,
            385,
        ),
    }

    node_positions: dict[str, tuple[int, int]] = {}
    fallback_index = 0

    for node in nodes:
        node_id = str(node["id"])
        preferred_position = preferred_positions.get(node_id)

        if preferred_position is not None:
            node_positions[node_id] = preferred_position
            continue

        fallback_column = fallback_index % 4
        fallback_row = fallback_index // 4
        node_positions[node_id] = (
            60 + fallback_column * 330,
            180 + fallback_row * 300,
        )
        fallback_index += 1

    lines = [
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 1400 900" role="img" '
            f'aria-label="Azure intended architecture for '
            f'{escaped_workload_name}">'
        ),
        "  <defs>",
        (
            '    <marker id="arrow" markerWidth="10" '
            'markerHeight="10" refX="9" refY="3" '
            'orient="auto" markerUnits="strokeWidth">'
        ),
        ('      <path d="M0,0 L0,6 L9,3 z" fill="#5B6573" />'),
        "    </marker>",
        "  </defs>",
        ('  <rect x="0" y="0" width="1400" height="900" fill="#FFFFFF" />'),
        (
            '  <text x="60" y="65" '
            'font-family="Segoe UI, Arial, sans-serif" '
            'font-size="30" font-weight="600" '
            f'fill="#102A43">Azure Intended Design — '
            f"{escaped_workload_name}</text>"
        ),
        (
            '  <text x="60" y="102" '
            'font-family="Segoe UI, Arial, sans-serif" '
            'font-size="17" fill="#52606D">'
            "Blue = existing and reused | "
            "Yellow = planned and pending implementation"
            "</text>"
        ),
        '  <g id="relationships">',
    ]

    for relationship in relationships:
        relationship_id = str(relationship["id"])
        source_id = str(relationship["source"])
        target_id = str(relationship["target"])

        route = preferred_routes.get(relationship_id)

        source_x, source_y = node_positions[source_id]
        target_x, target_y = node_positions[target_id]

        if route is None:
            source_center_x = source_x + node_width // 2
            source_center_y = source_y + node_height // 2
            target_center_x = target_x + node_width // 2
            target_center_y = target_y + node_height // 2
            route = f"M {source_center_x} {source_center_y} L {target_center_x} {target_center_y}"

        label_position = preferred_label_positions.get(relationship_id)

        if label_position is None:
            label_x = (source_x + target_x + node_width) // 2
            label_y = (source_y + target_y + node_height) // 2 - 8
        else:
            label_x, label_y = label_position

        escaped_relationship_id = escape(
            relationship_id,
            quote=True,
        )
        relationship_label = escape_mermaid_label(relationship.get("label"))

        lines.extend(
            [
                (
                    f'    <path data-relationship-id="'
                    f'{escaped_relationship_id}" '
                    f'd="{route}" fill="none" '
                    'stroke="#5B6573" stroke-width="2" '
                    'stroke-linejoin="round" '
                    'marker-end="url(#arrow)" />'
                ),
                (
                    f'    <text data-relationship-label-id="'
                    f'{escaped_relationship_id}" '
                    f'x="{label_x}" y="{label_y}" '
                    'text-anchor="middle" '
                    'font-family="Segoe UI, Arial, sans-serif" '
                    'font-size="13" fill="#323F4B" '
                    'paint-order="stroke" stroke="#FFFFFF" '
                    'stroke-width="5" '
                    f'stroke-linejoin="round">'
                    f"{relationship_label}</text>"
                ),
            ]
        )

    lines.extend(
        [
            "  </g>",
            '  <g id="nodes">',
        ]
    )

    for node in nodes:
        node_id = str(node["id"])
        x_position, y_position = node_positions[node_id]
        node_state = node.get("state")

        if node_state == "existing":
            fill_color = "#E8F3FF"
            stroke_color = "#0078D4"
            state_label = "Existing"
        else:
            fill_color = "#FFF4CE"
            stroke_color = "#C19C00"
            state_label = "Planned"

        escaped_node_id = escape(
            node_id,
            quote=True,
        )
        escaped_name = escape_mermaid_label(node.get("name"))
        escaped_resource_type = escape_mermaid_label(node.get("resourceType"))
        escaped_owner = escape_mermaid_label(node.get("owner"))

        lines.extend(
            [
                (
                    f'    <g data-node-id="{escaped_node_id}" '
                    f'transform="translate('
                    f'{x_position} {y_position})">'
                ),
                (
                    f'      <rect width="{node_width}" '
                    f'height="{node_height}" rx="12" '
                    f'fill="{fill_color}" '
                    f'stroke="{stroke_color}" '
                    'stroke-width="3" />'
                ),
                (
                    '      <text x="18" y="31" '
                    'font-family="Segoe UI, Arial, sans-serif" '
                    'font-size="17" font-weight="600" '
                    f'fill="#102A43">{escaped_name}</text>'
                ),
                (
                    '      <text x="18" y="59" '
                    'font-family="Segoe UI, Arial, sans-serif" '
                    'font-size="12" '
                    f'fill="#52606D">{escaped_resource_type}</text>'
                ),
                (
                    '      <text x="18" y="89" '
                    'font-family="Segoe UI, Arial, sans-serif" '
                    'font-size="13" fill="#323F4B">'
                    f"Owner: {escaped_owner}</text>"
                ),
                (
                    '      <text x="18" y="113" '
                    'font-family="Segoe UI, Arial, sans-serif" '
                    'font-size="13" font-weight="600" '
                    f'fill="{stroke_color}">'
                    f"{state_label}</text>"
                ),
                "    </g>",
            ]
        )

    lines.extend(
        [
            "  </g>",
            (
                '  <text x="60" y="850" '
                'font-family="Segoe UI, Arial, sans-serif" '
                'font-size="14" fill="#52606D">'
                "Review status: unreviewed — "
                "not evidence of deployed Azure state"
                "</text>"
            ),
            "</svg>",
        ]
    )

    return "\n".join(lines) + "\n"


def render_design_markdown(
    design: dict[str, Any],
    diagram: str,
) -> str:
    """Render a human-reviewable intended-design document."""
    workload = require_mapping(
        design,
        "workload",
    )
    source = require_mapping(
        design,
        "source",
    )

    workload_name = normalize_markdown_text(workload.get("name"))
    review_status = normalize_markdown_text(design.get("reviewStatus"))
    confirmed_by = normalize_markdown_text(source.get("confirmedBy"))
    interview_updated_at = normalize_markdown_text(source.get("interviewUpdatedAt"))
    generated_at = normalize_markdown_text(design.get("generatedAt"))

    normalized_diagram = diagram.rstrip("\n")

    return (
        f"# Azure Intended Design — {workload_name}\n"
        "\n"
        f"> Review status: **{review_status}**\n"
        "\n"
        "This document represents intended architecture derived from "
        "confirmed Azure interview information. "
        "It does not prove deployed Azure state.\n"
        "\n"
        "## Architecture overview\n"
        "\n"
        "```mermaid\n"
        f"{normalized_diagram}\n"
        "```\n"
        "\n"
        "## Interpretation\n"
        "\n"
        "- Blue resources already exist and are expected to be reused.\n"
        "- Yellow resources are planned and require implementation.\n"
        "- Connections describe intended dependencies and traffic paths.\n"
        "- Existing resources remain subject to their recorded ownership "
        "and modification boundaries.\n"
        "\n"
        "## Review checklist\n"
        "\n"
        "- Confirm that every planned resource is required.\n"
        "- Confirm that existing resources are correctly identified.\n"
        "- Confirm ownership and modification boundaries.\n"
        "- Confirm network address spaces and subnet prefixes.\n"
        "- Confirm hub peering, central egress, and private DNS paths.\n"
        "- Record approval or rejection before implementation begins.\n"
        "\n"
        "## Source provenance\n"
        "\n"
        f"- Confirmed by: {confirmed_by}\n"
        f"- Interview updated at: {interview_updated_at}\n"
        f"- Design generated at: {generated_at}\n"
        "- Source type: azure-interview-context\n"
    )


def write_text_artifact(
    content: str,
    output_path: Path,
    *,
    overwrite: bool,
) -> None:
    """Atomically write a text artifact without implicit overwrite."""
    resolved_output_path = output_path.resolve()

    if resolved_output_path.exists() and not overwrite:
        raise FileExistsError(f"Text artifact already exists: {resolved_output_path}")

    resolved_output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{resolved_output_path.name}.",
            suffix=".tmp",
            dir=resolved_output_path.parent,
            delete=False,
        ) as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
            temporary_path = Path(temporary_file.name)

        os.replace(
            temporary_path,
            resolved_output_path,
        )
        temporary_path = None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def run(
    *,
    project_root: Path,
    context_path: Path,
    output_path: Path,
    overwrite: bool,
    generated_at: datetime,
    schema_path: Path,
    overview_path: Path | None = None,
    svg_path: Path | None = None,
    drawio_path: Path | None = None,
) -> Path:
    """Generate, validate, and write intended-design artifacts."""
    resolved_overview_input = (
        overview_path
        if overview_path is not None
        else Path(".specify/design/azure-design-overview.md")
    )
    resolved_svg_input = (
        svg_path if svg_path is not None else Path(".specify/design/azure-design-overview.svg")
    )
    resolved_drawio_input = (
        drawio_path
        if drawio_path is not None
        else Path(".specify/design/azure-design-overview.drawio")
    )

    validated_context_path = validate_design_context_path(
        context_path,
        project_root=project_root,
    )
    validated_output_path = validate_design_output_path(
        output_path,
        project_root=project_root,
    )
    validated_overview_path = validate_design_overview_path(
        resolved_overview_input,
        project_root=project_root,
    )
    validated_svg_path = validate_design_svg_path(
        resolved_svg_input,
        project_root=project_root,
    )
    validated_drawio_path = validate_design_drawio_path(
        resolved_drawio_input,
        project_root=project_root,
    )

    protected_outputs = [
        validated_output_path,
        validated_overview_path,
        validated_svg_path,
        validated_drawio_path,
    ]

    if not overwrite:
        for protected_output in protected_outputs:
            if protected_output.exists():
                raise FileExistsError(f"Design artifact already exists: {protected_output}")

    context = load_json_document(validated_context_path)
    schema = load_json_document(schema_path.resolve())

    design = build_design_model(
        context,
        generated_at=generated_at,
    )
    validate_design_model(
        design,
        schema,
    )

    mermaid_diagram = render_mermaid_diagram(design)
    overview = render_design_markdown(
        design,
        mermaid_diagram,
    )
    svg = render_svg_diagram(design)
    drawio = render_drawio_diagram(design)

    write_design_model(
        design,
        validated_output_path,
        overwrite=overwrite,
    )
    write_text_artifact(
        overview,
        validated_overview_path,
        overwrite=overwrite,
    )
    write_text_artifact(
        svg,
        validated_svg_path,
        overwrite=overwrite,
    )
    write_text_artifact(
        drawio,
        validated_drawio_path,
        overwrite=overwrite,
    )

    return validated_output_path


def main(
    arguments: list[str] | None = None,
    *,
    project_root: Path | None = None,
    generated_at: datetime | None = None,
    schema_path: Path | None = None,
) -> int:
    """Run the intended-design generator command-line workflow."""
    parsed_arguments = parse_arguments(arguments)

    resolved_project_root = (
        project_root.resolve() if project_root is not None else Path.cwd().resolve()
    )
    resolved_generated_at = generated_at if generated_at is not None else datetime.now(timezone.utc)
    resolved_schema_path = (
        schema_path.resolve()
        if schema_path is not None
        else (Path(__file__).resolve().parents[2] / "templates" / "azure-design.schema.json")
    )

    try:
        written_path = run(
            project_root=resolved_project_root,
            context_path=parsed_arguments.context,
            output_path=parsed_arguments.output,
            overview_path=parsed_arguments.overview_output,
            svg_path=parsed_arguments.svg_output,
            drawio_path=parsed_arguments.drawio_output,
            overwrite=parsed_arguments.overwrite,
            generated_at=resolved_generated_at,
            schema_path=resolved_schema_path,
        )
    except (OSError, ValueError) as exception:
        print(
            f"Azure design generation failed: {exception}",
            file=sys.stderr,
        )
        return EXIT_EXECUTION_ERROR

    print(f"Azure intended design written successfully: {written_path}")
    print(
        "Review status: unreviewed. Review and approve the "
        "intended architecture before implementation."
    )

    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
