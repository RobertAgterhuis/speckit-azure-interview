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
        "LICENSE",
        "CHANGELOG.md",
        "requirements-dev.txt",
        "commands/azure-interview.md",
        "templates/azure-context-template.md",
        "templates/azure-context.schema.json",
        "scripts/python/validate_context.py",
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

    assert len(commands) == 1

    for command in commands:
        match = COMMAND_NAME_PATTERN.fullmatch(command["name"])

        assert match is not None, f"Invalid command name: {command['name']}"
        assert match.group(1) == extension_id
        assert match.group(2)
        assert command["description"]

        command_path = REPOSITORY_ROOT / command["file"]
        assert command_path.is_file(), f"Command file does not exist: {command['file']}"


def test_command_contains_valid_frontmatter(
    manifest: dict[str, Any],
) -> None:
    """Command Markdown must contain valid YAML frontmatter."""
    command = manifest["provides"]["commands"][0]
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

    assert len(templates) == 2

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

    assert len(scripts) == 2

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
        "speckit-azure-interview/archive/refs/tags/v0.1.1.zip" in quick_start_content
    )
