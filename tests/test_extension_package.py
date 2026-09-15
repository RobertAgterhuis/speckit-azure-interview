"""Structural tests for the Spec Kit Azure Interview extension package."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pytest
import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPOSITORY_ROOT / "extension.yml"

EXTENSION_ID_PATTERN = re.compile(r"^[a-z0-9-]+$")
COMMAND_NAME_PATTERN = re.compile(r"^speckit\.([a-z0-9-]+)\.([a-z0-9-]+)$")
ARTIFACT_NAME_PATTERN = re.compile(r"^[a-z0-9-]+$")
SEMANTIC_VERSION_PATTERN = re.compile(
    r"^(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)\."
    r"(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z.-]+)?"
    r"(?:\+[0-9A-Za-z.-]+)?$"
)


@pytest.fixture(scope="module")
def manifest() -> dict[str, Any]:
    """Load the extension manifest."""
    with MANIFEST_PATH.open("r", encoding="utf-8") as stream:
        document = yaml.safe_load(stream)

    assert isinstance(document, dict)
    return document


def is_absolute_web_url(value: str) -> bool:
    """Return whether a value is an absolute HTTP or HTTPS URL."""
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def test_required_repository_files_exist() -> None:
    """The extension package must contain its required root files."""
    required_files = [
        "extension.yml",
        "README.md",
        "QUICK-START.md",
        "docs/CODEX.md",
        "docs/COPILOT.md",
        "docs/AZURE-INVENTORY.md",
        "docs/AZURE-DESIGN.md",
        "LICENSE",
        "CHANGELOG.md",
        "requirements-dev.txt",
        "commands/azure-interview.md",
        "commands/azure-inventory.md",
        "commands/azure-design.md",
        "templates/azure-context-template.md",
        "templates/azure-context.schema.json",
        "templates/azure-inventory.schema.json",
        "templates/azure-design.schema.json",
        "scripts/python/validate_context.py",
        "scripts/python/collect_azure_inventory.py",
        "scripts/python/generate_azure_design.py",
        "requirements-runtime.txt",
        ".extensionignore",
        "scripts/powershell/Install-HermesSkillAdapter.ps1",
    ]

    missing_files = [
        relative_path
        for relative_path in required_files
        if not (REPOSITORY_ROOT / relative_path).is_file()
    ]

    assert missing_files == [], f"Required package files are missing: {missing_files}"


def test_manifest_has_supported_schema_version(
    manifest: dict[str, Any],
) -> None:
    """The manifest must use the supported extension schema version."""
    assert manifest["schema_version"] == "1.0"


def test_extension_metadata_is_valid(
    manifest: dict[str, Any],
) -> None:
    """Extension metadata must follow Spec Kit conventions."""
    extension = manifest["extension"]

    assert extension["id"] == "azure-interview"
    assert EXTENSION_ID_PATTERN.fullmatch(extension["id"])
    assert extension["name"] == "Spec Kit Azure Interview"
    assert SEMANTIC_VERSION_PATTERN.fullmatch(extension["version"])
    assert 1 <= len(extension["description"]) < 200
    assert extension["author"] == "Robert Agterhuis"
    assert extension["license"] == "MIT"
    assert is_absolute_web_url(extension["repository"])
    assert is_absolute_web_url(extension["homepage"])
    assert "<YOUR-GITHUB-USERNAME>" not in extension["repository"]
    assert "<YOUR-GITHUB-USERNAME>" not in extension["homepage"]


def test_speckit_requirement_is_declared(
    manifest: dict[str, Any],
) -> None:
    """The manifest must declare a Spec Kit compatibility range."""
    requirement = manifest["requires"]["speckit_version"]

    assert isinstance(requirement, str)
    assert requirement.startswith(">=")
    assert " " not in requirement


def test_command_is_namespaced_and_exists(
    manifest: dict[str, Any],
) -> None:
    """Every command must use the extension namespace and exist."""
    extension_id = manifest["extension"]["id"]
    commands = manifest["provides"]["commands"]

    assert len(commands) == 3

    for command in commands:
        match = COMMAND_NAME_PATTERN.fullmatch(command["name"])

        assert match is not None, f"Invalid command name: {command['name']}"
        assert match.group(1) == extension_id
        assert match.group(2)
        assert command["description"]

        command_path = REPOSITORY_ROOT / command["file"]
        assert command_path.is_file(), f"Command file does not exist: {command['file']}"


def test_commands_contain_valid_frontmatter(
    manifest: dict[str, Any],
) -> None:
    """Command Markdown files must contain valid YAML frontmatter."""
    commands = manifest["provides"]["commands"]

    for command in commands:
        command_path = REPOSITORY_ROOT / command["file"]
        content = command_path.read_text(encoding="utf-8")

        assert content.startswith("---\n")

        parts = content.split("---", maxsplit=2)
        assert len(parts) == 3

        frontmatter = yaml.safe_load(parts[1])
        assert isinstance(frontmatter, dict)
        assert frontmatter.get("description")
        assert "$ARGUMENTS" in content


def test_declared_templates_are_valid_and_exist(
    manifest: dict[str, Any],
) -> None:
    """Every declared template must have a valid name and file."""
    templates = manifest["provides"]["templates"]
    template_names: set[str] = set()

    assert len(templates) == 4

    for template in templates:
        name = template["name"]

        assert ARTIFACT_NAME_PATTERN.fullmatch(name)
        assert name not in template_names
        assert template["description"]

        template_path = REPOSITORY_ROOT / template["file"]
        assert template_path.is_file(), f"Template file does not exist: {template['file']}"

        template_names.add(name)


def test_tags_are_valid(
    manifest: dict[str, Any],
) -> None:
    """The manifest must contain two to five unique lowercase tags."""
    tags = manifest["tags"]

    assert 2 <= len(tags) <= 5
    assert len(tags) == len(set(tags))

    for tag in tags:
        assert EXTENSION_ID_PATTERN.fullmatch(tag)


def test_manifest_contains_no_unresolved_placeholders(
    manifest: dict[str, Any],
) -> None:
    """Published manifest values must not contain template placeholders."""
    serialized_manifest = MANIFEST_PATH.read_text(encoding="utf-8")

    unresolved_patterns = ["<YOUR-", "YOUR_GITHUB", "TODO", "TBD"]

    for pattern in unresolved_patterns:
        assert pattern not in serialized_manifest, (
            f"Unresolved placeholder found in extension.yml: {pattern}"
        )


def test_runtime_requirements_are_minimal() -> None:
    """Runtime requirements must not include development-only tools."""
    runtime_requirements = (REPOSITORY_ROOT / "requirements-runtime.txt").read_text(
        encoding="utf-8"
    )

    assert "jsonschema" in runtime_requirements
    assert "pytest" not in runtime_requirements
    assert "pyyaml" not in runtime_requirements.lower()


def test_development_requirements_include_runtime_requirements() -> None:
    """Development dependencies must include the runtime dependency set."""
    development_requirements = (REPOSITORY_ROOT / "requirements-dev.txt").read_text(
        encoding="utf-8"
    )

    assert "-r requirements-runtime.txt" in development_requirements
    assert "pytest" in development_requirements
    assert "PyYAML" in development_requirements


def test_extensionignore_excludes_development_artifacts() -> None:
    """Development and repository artifacts must not enter installations."""
    extension_ignore = (REPOSITORY_ROOT / ".extensionignore").read_text(encoding="utf-8")

    required_patterns = [
        ".git/",
        ".venv/",
        ".pytest_cache/",
        ".github/",
        "tests/",
        "requirements-dev.txt",
        ".specify/",
        ".yamllint.yml",
        "pyproject.toml",
        "CONTRIBUTING.md",
        "SECURITY.md",
    ]

    for pattern in required_patterns:
        assert pattern in extension_ignore, f"Missing required .extensionignore pattern: {pattern}"


def test_command_enforces_business_first_interview_order() -> None:
    """The command must establish business purpose before architecture."""
    command_content = (REPOSITORY_ROOT / "commands" / "azure-interview.md").read_text(
        encoding="utf-8"
    )

    required_statements = [
        "Ask exactly one primary question per response.",
        "Establish the specific business capability or problem.",
        "Do not ask about criticality, topology, AVM strategy",
        "Create `azure-context.json` only when",
        "The JSON artifact exists and passes schema validation.",
        "the first interview question must",
    ]

    for statement in required_statements:
        assert statement in command_content, f"Required interview safeguard is missing: {statement}"


def test_inventory_command_enforces_read_only_human_control() -> None:
    """Inventory discovery must remain scoped, read-only, and unconfirmed."""
    command_path = REPOSITORY_ROOT / "commands" / "azure-inventory.md"
    command_content = command_path.read_text(encoding="utf-8")

    required_statements = [
        "explicit approval",
        "tenant and subscription",
        "--approve-read-only",
        ".specify/discovery/azure-inventory.json",
        "unconfirmed",
        "must not be merged automatically",
        "Do not retrieve secrets, keys, certificates, or access tokens.",
    ]

    for statement in required_statements:
        assert statement in command_content


def test_declared_scripts_are_valid_and_exist(
    manifest: dict[str, Any],
) -> None:
    """Every declared script must have valid metadata and exist."""
    scripts = manifest["provides"]["scripts"]
    script_names: set[str] = set()
    allowed_runtimes = {
        "bash",
        "powershell",
        "python",
    }

    assert len(scripts) == 4

    for script in scripts:
        name = script["name"]
        runtimes = script["runtimes"]

        assert ARTIFACT_NAME_PATTERN.fullmatch(name)
        assert name not in script_names
        assert script["description"]
        assert isinstance(runtimes, list)
        assert runtimes
        assert set(runtimes).issubset(allowed_runtimes)

        script_path = REPOSITORY_ROOT / script["file"]
        assert script_path.is_file(), f"Script file does not exist: {script['file']}"

        script_names.add(name)


def test_quick_start_documents_required_workflow_order() -> None:
    """Quick Start must place Azure discovery before specification."""
    quick_start_path = REPOSITORY_ROOT / "QUICK-START.md"
    quick_start_content = quick_start_path.read_text(encoding="utf-8")

    ordered_sections = [
        "## 8. Establish the Constitution",
        "## 9. Run the Azure Architecture Interview",
        "## 10. Verify Interview Readiness",
        "## 11. Create the Specification",
        "## 12. Clarify the Specification",
        "## 13. Create the Implementation Plan",
        "## 14. Generate a Quality Checklist",
        "## 15. Generate Tasks",
        "## 16. Analyze Consistency",
        "## 17. Implement",
        "## 18. Converge",
    ]

    section_positions = [quick_start_content.index(section) for section in ordered_sections]

    assert section_positions == sorted(section_positions)


def test_quick_start_uses_versioned_public_archive() -> None:
    """Quick Start must document the tested public installation syntax."""
    quick_start_path = REPOSITORY_ROOT / "QUICK-START.md"
    quick_start_content = quick_start_path.read_text(encoding="utf-8")

    assert "specify extension add azure-interview" in quick_start_content
    assert (
        "--from "
        "https://github.com/RobertAgterhuis/"
        "speckit-azure-interview/archive/refs/tags/v0.5.0.zip" in quick_start_content
    )


def test_codex_documentation_describes_generated_skill() -> None:
    """Codex documentation must describe the tested Spec Kit integration."""
    codex_documentation_path = REPOSITORY_ROOT / "docs" / "CODEX.md"
    codex_documentation = codex_documentation_path.read_text(encoding="utf-8")

    required_statements = [
        "specify init --here --integration codex --script ps",
        ".agents/skills/speckit-azure-interview-run/SKILL.md",
        "$speckit-azure-interview-run",
        "What specific business capability or problem must this workload address?",
        ".specify/discovery/azure-context.md",
        ".specify/discovery/azure-context.json",
    ]

    for statement in required_statements:
        assert statement in codex_documentation


def test_release_versions_are_consistent(
    manifest: dict[str, Any],
) -> None:
    """Release-facing files must reference the current extension version."""
    expected_version = manifest["extension"]["version"]
    expected_tag = f"v{expected_version}"

    release_facing_files = [
        REPOSITORY_ROOT / "README.md",
        REPOSITORY_ROOT / "QUICK-START.md",
        REPOSITORY_ROOT / "docs" / "CODEX.md",
        REPOSITORY_ROOT / "docs" / "TESTING.md",
        REPOSITORY_ROOT / "docs" / "COPILOT.md",
    ]

    for file_path in release_facing_files:
        content = file_path.read_text(encoding="utf-8")
        assert expected_tag in content, (
            f"{file_path.relative_to(REPOSITORY_ROOT)} does not reference "
            f"the current release tag {expected_tag}"
        )


def test_copilot_documentation_describes_preview_support() -> None:
    """Copilot documentation must distinguish structural and behavioral support."""
    copilot_documentation_path = REPOSITORY_ROOT / "docs" / "COPILOT.md"
    copilot_documentation = copilot_documentation_path.read_text(encoding="utf-8")

    required_statements = [
        "specify init --here --integration copilot --script ps",
        ".github/skills/speckit-azure-interview-run/SKILL.md",
        "/speckit-azure-interview-run",
        "Preview — structurally verified; behavioral testing requested",
        "What specific business capability or problem must this workload address?",
        "Community Testing Requested",
    ]

    for statement in required_statements:
        assert statement in copilot_documentation


def test_quick_start_identifies_copilot_as_preview() -> None:
    """Quick Start must not present Copilot as behaviorally verified."""
    quick_start_path = REPOSITORY_ROOT / "QUICK-START.md"
    quick_start_content = quick_start_path.read_text(encoding="utf-8")

    assert "--integration copilot" in quick_start_content
    assert ".github/skills/speckit-azure-interview-run/SKILL.md" in quick_start_content
    assert "Preview — structurally verified; behavioral testing requested" in quick_start_content


def test_interview_reconciles_unconfirmed_inventory_evidence() -> None:
    """The interview must reconcile inventory without auto-confirming it."""
    command_content = (REPOSITORY_ROOT / "commands" / "azure-interview.md").read_text(
        encoding="utf-8"
    )

    required_statements = [
        ".specify/discovery/azure-inventory.json",
        "Treat every inventory record as `unconfirmed`",
        "Never copy inventory evidence automatically",
        "Confirm lifecycle intent",
        "Confirm modification permission",
        "source `azure`",
    ]

    for statement in required_statements:
        assert statement in command_content


def test_inventory_documentation_covers_safe_operation() -> None:
    """Inventory documentation must cover setup, safety, and reconciliation."""
    documentation = (REPOSITORY_ROOT / "docs" / "AZURE-INVENTORY.md").read_text(encoding="utf-8")

    required_statements = [
        "Azure CLI",
        "Azure Resource Graph",
        "Reader",
        "--approve-read-only",
        "--overwrite",
        ".specify/discovery/azure-inventory.json",
        "evidenceStatus",
        "unconfirmed",
        "Windows",
        "must not be committed",
        "Troubleshooting",
    ]

    for statement in required_statements:
        assert statement in documentation


def test_release_documentation_describes_inventory_workflow() -> None:
    """Release-facing guidance must expose optional inventory discovery."""
    documentation_requirements = {
        "README.md": [
            "Azure Inventory Discovery",
            "speckit.azure-interview.inventory",
            "docs/AZURE-INVENTORY.md",
            "docs/AZURE-DESIGN.md",
            "unconfirmed",
        ],
        "QUICK-START.md": [
            "Optional Azure Inventory Discovery",
            "speckit.azure-interview.inventory",
            ".specify/discovery/azure-inventory.json",
            "--approve-read-only",
        ],
        "docs/ARCHITECTURE.md": [
            "azure-inventory.json",
            "Azure Resource Graph",
            "unconfirmed",
            "metadata allowlist",
        ],
        "docs/TESTING.md": [
            "Azure inventory",
            "68 passed",
            "metadata allowlist",
            "live smoke test",
        ],
    }

    for relative_path, required_statements in documentation_requirements.items():
        content = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")

        for statement in required_statements:
            assert statement in content, f"{relative_path} is missing: {statement}"


def test_design_command_enforces_reviewable_intended_state() -> None:
    """Design generation remains reviewable, intended, and non-deploying."""
    command_path = REPOSITORY_ROOT / "commands" / "azure-design.md"
    command_content = command_path.read_text(encoding="utf-8")

    required_statements = [
        ".specify/discovery/azure-context.json",
        ".specify/design/azure-design-model.json",
        ".specify/design/azure-design-overview.md",
        ".specify/design/azure-design-overview.svg",
        ".specify/design/azure-design-overview.drawio",
        "designStatus: intended",
        "reviewStatus: unreviewed",
        "generate_azure_design.py",
        "--overwrite",
        "explicit human approval",
        "exactly one next review or confirmation question",
    ]

    for statement in required_statements:
        assert statement in command_content

    prohibited_claims = [
        "designStatus: deployed",
        "reviewStatus: approved",
        "automatically approve",
        "start deployment automatically",
    ]

    for statement in prohibited_claims:
        assert statement not in command_content


def test_release_documentation_describes_intended_design_workflow() -> None:
    """Release guidance must expose intended-design generation and review."""
    documentation_requirements = {
        "README.md": [
            "Azure Intended Design",
            "speckit.azure-interview.design",
            "docs/AZURE-DESIGN.md",
            "reviewStatus: unreviewed",
        ],
        "QUICK-START.md": [
            "Generate and Review the Intended Design",
            "speckit.azure-interview.design",
            "azure-design-overview.drawio",
            "--overwrite",
        ],
        "docs/ARCHITECTURE.md": [
            "Intended-Design Evidence Layer",
            "azure-design-model.json",
            "explicit human approval",
            "As-built verification",
        ],
        "docs/TESTING.md": [
            "Azure Intended-Design Tests",
            "test_generate_azure_design.py",
            "Mermaid",
            "Draw.io",
        ],
        "docs/CODEX.md": [
            "Generate the Intended Azure Design",
            "speckit.azure-interview.design",
            "intended",
            "unreviewed",
        ],
        "docs/COPILOT.md": [
            "Generate the Intended Azure Design",
            "speckit-azure-interview-design",
            "designStatus: intended",
            "reviewStatus: unreviewed",
        ],
        "docs/AZURE-DESIGN.md": [
            "Azure Intended Design",
            "azure-design-model.json",
            "azure-design-overview.svg",
            "azure-design-overview.drawio",
            "Future As-Built Verification",
        ],
    }

    for relative_path, required_statements in documentation_requirements.items():
        content = (REPOSITORY_ROOT / relative_path).read_text(
            encoding="utf-8",
        )

        for statement in required_statements:
            assert statement in content, f"{relative_path} is missing: {statement}"


def test_quick_start_places_inventory_and_design_in_workflow_order() -> None:
    """Inventory and design review must appear in the documented lifecycle."""
    quick_start = (REPOSITORY_ROOT / "QUICK-START.md").read_text(
        encoding="utf-8",
    )
    diagram_marker = "The complete workflow is:\n\n```text\n"
    diagram_start = quick_start.index(diagram_marker) + len(diagram_marker)
    diagram_end = quick_start.index("\n```", diagram_start)
    workflow = quick_start[diagram_start:diagram_end]

    ordered_stages = [
        "Constitution",
        "Azure Inventory Discovery (optional)",
        "Azure Interview",
        "Intended Design Review",
        "Specify",
        "Clarify (optional)",
        "Plan",
        "Checklist (optional)",
        "Tasks",
        "Analyze (recommended)",
        "Implement",
        "Converge until complete",
    ]

    positions = [workflow.index(stage) for stage in ordered_stages]

    assert positions == sorted(positions)
    assert "speckit.azure-interview.inventory" in quick_start
    assert "speckit.azure-interview.design" in quick_start
    assert "unconfirmed" in quick_start
    assert "unreviewed" in quick_start
    normalized_quick_start = " ".join(quick_start.split())
    assert "explicit human approval" in normalized_quick_start
