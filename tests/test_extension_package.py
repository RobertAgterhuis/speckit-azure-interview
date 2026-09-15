"""Structural tests for the Spec Kit Azure Interview extension package."""

from __future__ import annotations

import json
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
        "docs/AZURE-DESIGN-REVIEW.md",
        "LICENSE",
        "CHANGELOG.md",
        "requirements-dev.txt",
        "commands/azure-interview.md",
        "commands/azure-inventory.md",
        "commands/azure-design.md",
        "commands/azure-design-review.md",
        "templates/azure-context-template.md",
        "templates/azure-context.schema.json",
        "templates/azure-inventory.schema.json",
        "templates/azure-design.schema.json",
        "templates/azure-design-review.schema.json",
        "scripts/python/validate_context.py",
        "scripts/python/collect_azure_inventory.py",
        "scripts/python/generate_azure_design.py",
        "scripts/python/review_azure_design.py",
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

    assert len(commands) == 4

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

    assert len(templates) == 5

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
        "Ask the first business-purpose question by itself.",
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

    assert len(scripts) == 5

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
        "speckit-azure-interview/archive/refs/tags/v0.8.0.zip" in quick_start_content
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
        "Treat modification permission as a protected decision.",
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
            "docs/AZURE-DESIGN-REVIEW.md",
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
            "docs/AZURE-DESIGN-REVIEW.md",
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


def test_design_review_command_enforces_explicit_human_decision() -> None:
    """Design review must preserve explicit and traceable human control."""
    command_path = REPOSITORY_ROOT / "commands" / "azure-design-review.md"
    content = command_path.read_text(encoding="utf-8")

    required_statements = [
        "review_azure_design.py",
        "azure-design-review.schema.json",
        ".specify/design/azure-design-review.json",
        ".specify/design/azure-design-review.md",
        "--decision",
        "approved",
        "rejected",
        "explicit human approval",
        "SHA-256",
        "--overwrite",
        "does not prove deployed Azure state",
        "does not perform Azure write operations",
    ]

    for statement in required_statements:
        assert statement in content


def test_documentation_describes_explicit_design_review() -> None:
    """Documentation must explain approval evidence and control boundaries."""
    documentation_requirements = {
        "README.md": [
            "Azure Intended Design Review",
            "speckit.azure-interview.design-review",
            "azure-design-review.json",
            "docs/AZURE-DESIGN-REVIEW.md",
        ],
        "QUICK-START.md": [
            "Record the Intended Design Decision",
            "speckit.azure-interview.design-review",
            "approved",
            "rejected",
            "implementationAuthorized",
        ],
        "docs/ARCHITECTURE.md": [
            "Design Review Evidence",
            "azure-design-review.json",
            "SHA-256",
            "transaction",
        ],
        "docs/AZURE-DESIGN.md": [
            "speckit.azure-interview.design-review",
            "azure-design-review.json",
            "implementationAuthorized",
        ],
        "docs/AZURE-DESIGN-REVIEW.md": [
            "Azure Intended Design Review",
            "review_azure_design.py",
            "azure-design-review.schema.json",
            "azure-design-review.json",
            "azure-design-review.md",
            "SHA-256",
            "approved",
            "rejected",
            "implementationAuthorized",
            "--overwrite",
            "Troubleshooting",
        ],
        "docs/TESTING.md": [
            "Azure Design-Review Tests",
            "test_review_azure_design.py",
            "design digest",
            "transactional publication",
        ],
        "docs/CODEX.md": [
            "Review the Intended Azure Design",
            "speckit-azure-interview-design-review",
            "implementationAuthorized",
        ],
        "docs/COPILOT.md": [
            "Review the Intended Azure Design",
            "speckit-azure-interview-design-review",
            "implementationAuthorized",
        ],
        "site-docs/content/docs/workflow.md": [
            "Design Review Decision",
            "speckit.azure-interview.design-review",
            "implementationAuthorized",
        ],
        "site-docs/content/docs/commands/design-review.md": [
            "Intended Design Review",
            "speckit.azure-interview.design-review",
            "approved",
            "rejected",
        ],
        "site-docs/content/docs/artifacts/design-review.md": [
            "Design Review Evidence",
            "azure-design-review.json",
            "SHA-256",
            "implementationAuthorized",
        ],
    }

    for relative_path, required_statements in documentation_requirements.items():
        content = (REPOSITORY_ROOT / relative_path).read_text(
            encoding="utf-8",
        )

        for statement in required_statements:
            assert statement in content, f"{relative_path} is missing: {statement}"


def test_interview_command_uses_adaptive_question_batches() -> None:
    """The interview must collect related independent answers efficiently."""
    command_path = REPOSITORY_ROOT / "commands" / "azure-interview.md"
    content = command_path.read_text(encoding="utf-8")

    required_contracts = [
        "Ask the first business-purpose question by itself.",
        ("Ask two to four closely related, independent questions as a numbered batch."),
        "Never include more than four primary questions in one response.",
        ("Keep dependent questions separate when an earlier answer can change the later question."),
        ("Accept partial batch answers and continue only with the unanswered relevant questions."),
        ("Treat `unknown`, `TBD`, `not applicable`, and `use existing` as valid explicit answers."),
    ]

    for contract in required_contracts:
        assert contract in content


def test_interview_command_generalizes_scoped_answers() -> None:
    """Explicit scope-wide answers must prevent repetitive questions."""
    command_path = REPOSITORY_ROOT / "commands" / "azure-interview.md"
    content = command_path.read_text(encoding="utf-8")

    required_contracts = [
        ("Apply an explicitly scoped answer to every applicable resource or topic."),
        (
            "Do not ask the same ownership, reuse, or immutability "
            "question again for resources covered by that scope."
        ),
        ("Record the scope rule and preserve any explicitly stated exceptions."),
        ("Ask for clarification instead of generalizing when the scope is ambiguous."),
    ]

    for contract in required_contracts:
        assert contract in content


def test_interview_command_protects_sensitive_decisions() -> None:
    """High-impact decisions must remain isolated from ordinary batches."""
    command_path = REPOSITORY_ROOT / "commands" / "azure-interview.md"
    content = command_path.read_text(encoding="utf-8")

    required_contracts = [
        (
            "Ask approval, consent, security, destructive-action, and "
            "overwrite questions individually."
        ),
        ("Never infer approval or authorization from a batch answer or a scope-wide answer."),
    ]

    for contract in required_contracts:
        assert contract in content


def test_interview_command_requires_validated_handoff_artifacts() -> None:
    """Completion requires synchronized and validated Markdown and JSON."""
    command_path = REPOSITORY_ROOT / "commands" / "azure-interview.md"
    content = command_path.read_text(encoding="utf-8")

    required_contracts = [
        (
            "Generate both `azure-context.md` and `azure-context.json` "
            "before declaring the interview complete."
        ),
        ("Validate `azure-context.json` before setting `readyForSpecification` to `true`."),
        (
            "Do not recommend specification or design generation while "
            "a blocking question remains or JSON validation fails."
        ),
        ("Publish Markdown and JSON from the same confirmed interview state."),
    ]

    for contract in required_contracts:
        assert contract in content


def test_interview_command_removes_obsolete_single_question_contract() -> None:
    """The former unconditional single-question rule must be removed."""
    command_path = REPOSITORY_ROOT / "commands" / "azure-interview.md"
    content = command_path.read_text(encoding="utf-8")

    obsolete_contracts = [
        "Ask exactly one primary question per response.",
        ("Never combine independent decisions in one question, questionnaire, form, or"),
        ("End every response with exactly one next question or one explicit request"),
    ]

    for contract in obsolete_contracts:
        assert contract not in content


def test_interview_command_defines_deterministic_batch_planning() -> None:
    """Question batches must be selected through explicit ordered rules."""
    command_path = REPOSITORY_ROOT / "commands" / "azure-interview.md"
    content = command_path.read_text(encoding="utf-8")

    required_contracts = [
        "## Batch Planning Algorithm",
        "Build the candidate-question set from the earliest incomplete phase.",
        ("Remove questions answered by confirmed facts, scope rules, or applicable evidence."),
        ("Remove questions made irrelevant by earlier answers and record why they were skipped."),
        ("Select only questions that can be answered independently in the current state."),
        ("Select questions from one topic cluster only and preserve their documented order."),
        ("Stop adding questions when the batch contains four questions."),
        (
            "After processing the answers, recompute the candidate set "
            "instead of using a precomputed questionnaire."
        ),
    ]

    for contract in required_contracts:
        assert contract in content


def test_interview_command_defines_question_clusters() -> None:
    """The command must provide bounded clusters for related questions."""
    command_path = REPOSITORY_ROOT / "commands" / "azure-interview.md"
    content = command_path.read_text(encoding="utf-8")

    required_clusters = [
        "### Workload foundation cluster",
        "### Azure estate and placement cluster",
        "### Existing-resource boundaries cluster",
        "### Network and private-connectivity cluster",
        "### Governance and operations cluster",
    ]

    for cluster in required_clusters:
        assert cluster in content


def test_interview_command_defines_batch_response_protocol() -> None:
    """Users must be able to answer batches clearly and partially."""
    command_path = REPOSITORY_ROOT / "commands" / "azure-interview.md"
    content = command_path.read_text(encoding="utf-8")

    required_contracts = [
        "## Batch Response Protocol",
        "Give every question a stable question ID.",
        "Number questions from 1 through the batch size.",
        (
            "Tell the user that answers may be provided by number "
            "and that unanswered numbers remain open."
        ),
        ("Map each supplied answer to its question ID before updating interview state."),
        (
            "Do not reinterpret one answer as applying to another "
            "question unless the user explicitly scopes it."
        ),
        ("Acknowledge the accepted answers once, then ask only the next relevant batch."),
    ]

    for contract in required_contracts:
        assert contract in content


def test_interview_command_prevents_batching_across_boundaries() -> None:
    """Question grouping must not cross phase or decision boundaries."""
    command_path = REPOSITORY_ROOT / "commands" / "azure-interview.md"
    content = command_path.read_text(encoding="utf-8")

    required_contracts = [
        ("Do not combine questions from different interview phases in one batch."),
        ("Do not include a phase-confirmation request in a question batch."),
        ("Do not include a protected decision in an ordinary question batch."),
        ("Do not batch a question with its possible follow-up question."),
    ]

    for contract in required_contracts:
        assert contract in content


def test_interview_command_defines_ordered_completion_transaction() -> None:
    """The final context artifacts must be published in a safe order."""
    command_path = REPOSITORY_ROOT / "commands" / "azure-interview.md"
    content = command_path.read_text(encoding="utf-8")

    required_contracts = [
        "## Completion Transaction",
        ("Build one canonical final context state only after the user confirms the final summary."),
        ("Render candidate Markdown and JSON from that same canonical state."),
        ("Write both candidates to temporary files in their destination directory."),
        ("Validate the candidate JSON against the packaged schema and semantic validator."),
        ("Publish both final artifacts only after candidate validation succeeds."),
        (
            "Validate the persisted JSON again after publication "
            "before providing handoff instructions."
        ),
    ]

    for contract in required_contracts:
        assert contract in content


def test_interview_command_keeps_failed_completion_in_progress() -> None:
    """A failed completion transaction must never produce false readiness."""
    command_path = REPOSITORY_ROOT / "commands" / "azure-interview.md"
    content = command_path.read_text(encoding="utf-8")

    required_contracts = [
        ("If candidate rendering or validation fails, do not publish either candidate."),
        ("Keep the interview status `In Progress` or `Blocked` and keep readiness set to `No`."),
        (
            "Do not leave `azure-context.md` claiming completion "
            "when `azure-context.json` is absent or invalid."
        ),
        ("Never ask a downstream command to construct or repair the interview context."),
    ]

    for contract in required_contracts:
        assert contract in content


def test_interview_command_verifies_synchronized_final_state() -> None:
    """Published artifacts must describe one identical readiness state."""
    command_path = REPOSITORY_ROOT / "commands" / "azure-interview.md"
    content = command_path.read_text(encoding="utf-8")

    required_contracts = [
        ("Confirm that persisted Markdown and JSON both report a complete interview."),
        ("Confirm that persisted Markdown and JSON both report readiness for specification."),
        ("Confirm that the persisted blocking-question and critical-assumption counts are zero."),
        (
            "Provide specification and design handoff instructions "
            "only after all post-publication checks succeed."
        ),
    ]

    for contract in required_contracts:
        assert contract in content


def test_interview_phase_one_switches_to_batches_after_business_purpose() -> None:
    """Phase 1 must isolate purpose and then batch independent details."""
    command_path = REPOSITORY_ROOT / "commands" / "azure-interview.md"
    content = command_path.read_text(encoding="utf-8")

    required_contracts = [
        ("Ask only the business-purpose question while the purpose is missing or vague."),
        (
            "After the business purpose is confirmed, use the Workload "
            "foundation cluster for independent Phase 1 questions."
        ),
        (
            "Do not treat the documented Phase 1 order as a requirement "
            "to ask every item in a separate response."
        ),
    ]

    for contract in required_contracts:
        assert contract in content


def test_existing_resource_phase_uses_safe_scope_defaults() -> None:
    """Brownfield discovery must avoid repetitive resource-by-resource prompts."""
    command_path = REPOSITORY_ROOT / "commands" / "azure-interview.md"
    content = command_path.read_text(encoding="utf-8")

    required_contracts = [
        (
            "Ask for scope-wide ownership, reuse, and immutability "
            "rules before asking resource-specific questions."
        ),
        (
            "Apply the safe default that an existing resource remains "
            "unmodified unless the user explicitly authorizes an exception."
        ),
        ("Ask only about resources or fields not covered by a confirmed scope rule."),
        ("Handle each requested modification exception as an isolated protected decision."),
    ]

    for contract in required_contracts:
        assert contract in content


def test_inventory_reconciliation_supports_bulk_confirmation() -> None:
    """Inventory evidence must support explicit scoped confirmation."""
    command_path = REPOSITORY_ROOT / "commands" / "azure-interview.md"
    content = command_path.read_text(encoding="utf-8")

    required_contracts = [
        (
            "Allow the user to confirm one proposed interpretation "
            "for an explicitly listed group of inventory resources."
        ),
        (
            "Record one scope rule plus resource-specific exceptions "
            "instead of duplicating identical answers."
        ),
        ("Do not treat grouped confirmation as permission to modify any existing resource."),
    ]

    for contract in required_contracts:
        assert contract in content


def test_review_phase_delegates_to_completion_transaction() -> None:
    """Phase 13 must use the single authoritative completion workflow."""
    command_path = REPOSITORY_ROOT / "commands" / "azure-interview.md"
    content = command_path.read_text(encoding="utf-8")

    required_contracts = [
        (
            "After summary confirmation, execute the Completion "
            "Transaction; do not implement a separate Phase 13 "
            "publication flow."
        ),
        ("Keep the blocking-question set synchronized with the recomputed candidate-question set."),
    ]

    for contract in required_contracts:
        assert contract in content


def test_release_documentation_describes_adaptive_interview_batches() -> None:
    """Public documentation must describe the smarter interview behavior."""
    required_statements = {
        "README.md": [
            "Ask the first business-purpose question by itself",
            "numbered batches of two to four related independent questions",
        ],
        "CONTRIBUTING.md": [
            "first business-purpose question is isolated",
            "no more than four related questions",
        ],
        "docs/CODEX.md": [
            "opening business-purpose question first",
            "numbered batch of two to four related questions",
            "unanswered numbers remain open",
        ],
        "docs/COPILOT.md": [
            "isolating the first business-purpose question",
            "adaptive numbered batches",
            "unanswered numbers remain open",
        ],
        "docs/TESTING.md": [
            "business-purpose question separately",
            "numbered batches of two to four related questions",
        ],
        "site-docs/content/docs/commands/interview.md": [
            "Ask the first business-purpose question by itself",
            "two to four closely related",
            "Accept partial batch answers",
        ],
    }

    obsolete_statements = [
        "Ask exactly one primary question per response",
        "Answer one question at a time",
        "Answer one primary question at a time",
        "Asks only one primary question per response",
        "Confirm exactly one primary question is asked",
    ]

    for relative_path, statements in required_statements.items():
        content = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")

        for statement in statements:
            assert statement in content

        for statement in obsolete_statements:
            assert statement not in content


def test_quick_start_and_site_explain_adaptive_batch_answers() -> None:
    """Operator documentation must show how adaptive batches are answered."""
    required_statements = {
        "QUICK-START.md": [
            "### Answer Adaptive Question Batches",
            "Existing-resource boundaries",
            "A partial response is valid:",
            "The Platform Team owns all Azure resources.",
            "remains a protected decision",
        ],
        "site-docs/content/docs/workflow.md": [
            "## Adaptive interview batches",
            "two to four closely",
            "related, independent questions",
            "recomputes the next applicable questions",
            "isolated protected decisions",
            "passes schema and semantic validation",
        ],
        "site-docs/content/docs/commands/interview.md": [
            "## Batch Planning Algorithm",
            "## Question Clusters",
            "## Batch Response Protocol",
            "## Completion Transaction",
        ],
    }

    for relative_path, statements in required_statements.items():
        content = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")

        for statement in statements:
            assert " ".join(statement.split()) in " ".join(content.split())

    site_interview = (REPOSITORY_ROOT / "site-docs/content/docs/commands/interview.md").read_text(
        encoding="utf-8"
    )

    assert "End every response with exactly one next question" not in site_interview
    assert "Ask exactly one primary question per response" not in site_interview


def test_release_documentation_describes_brownfield_topology_discovery() -> None:
    """Public guidance must explain topology evidence and its safety boundaries."""
    documentation_requirements = {
        "README.md": [
            "Brownfield Topology Discovery",
            "six controlled relationship types",
            "external subscriptions are referenced but never queried",
        ],
        "QUICK-START.md": [
            "Review Brownfield Topology Evidence",
            "relationshipCount",
            "targetScope",
            "unconfirmed",
        ],
        "docs/AZURE-INVENTORY.md": [
            "Brownfield topology relationships",
            "vnet-contains-subnet",
            "vnet-peered-with-vnet",
            "subnet-associated-with-nsg",
            "subnet-associated-with-route-table",
            "private-endpoint-placed-in-subnet",
            "private-dns-zone-linked-to-vnet",
            "in-scope",
            "external-subscription",
            "unresolved",
            "topologyQueries",
        ],
        "commands/azure-inventory.md": [
            "Topology Evidence",
            "Report the topology relationship count",
            "external-subscription",
            "never query a referenced external subscription",
        ],
        "site-docs/content/docs/artifacts/inventory-evidence.md": [
            "## Topology evidence",
            "relationshipType",
            "sourceResourceId",
            "targetResourceId",
            "targetScope",
            "topologyQueries",
        ],
        "site-docs/content/docs/commands/inventory.md": [
            "Topology Evidence",
            "Report the topology relationship count",
            "external-subscription",
            "never query a referenced external subscription",
        ],
        "docs/TESTING.md": [
            "Windows-safe single-line KQL arguments",
            "seven separate Resource Graph query flows",
            "pagination integrity",
            "partial inventory evidence",
        ],
    }

    for relative_path, required_statements in documentation_requirements.items():
        content = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
        normalized_content = " ".join(content.split()).casefold()

        for statement in required_statements:
            normalized_statement = " ".join(statement.split()).casefold()

            assert normalized_statement in normalized_content, (
                f"{relative_path} is missing: {statement}"
            )


def test_brownfield_topology_release_is_version_0_8_0(
    manifest: dict[str, Any],
) -> None:
    """Brownfield topology discovery must ship as the v0.8.0 minor release."""
    expected_version = "0.8.0"
    expected_tag = "v0.8.0"

    assert manifest["extension"]["version"] == expected_version

    package = json.loads((REPOSITORY_ROOT / "package.json").read_text(encoding="utf-8"))
    package_lock = json.loads((REPOSITORY_ROOT / "package-lock.json").read_text(encoding="utf-8"))

    assert package["version"] == expected_version
    assert package_lock["version"] == expected_version
    assert package_lock["packages"][""]["version"] == expected_version

    release_facing_files = [
        "README.md",
        "QUICK-START.md",
        "docs/CODEX.md",
        "docs/COPILOT.md",
        "docs/TESTING.md",
        "site-docs/content/docs/getting-started.md",
    ]

    for relative_path in release_facing_files:
        content = (REPOSITORY_ROOT / relative_path).read_text(encoding="utf-8")
        assert expected_tag in content, f"{relative_path} does not reference {expected_tag}"

    changelog = (REPOSITORY_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    required_changelog_statements = [
        "## [0.8.0] - 2026-09-15",
        "Brownfield topology discovery",
        "six controlled topology relationship types",
        "Windows-safe KQL normalization",
        "seven separate Resource Graph query flows",
        "pagination integrity",
        "external subscriptions are referenced but never queried",
        (
            "[Unreleased]: "
            "https://github.com/RobertAgterhuis/"
            "speckit-azure-interview/compare/v0.8.0...HEAD"
        ),
        (
            "[0.8.0]: "
            "https://github.com/RobertAgterhuis/"
            "speckit-azure-interview/compare/v0.7.0...v0.8.0"
        ),
    ]

    normalized_changelog = " ".join(changelog.split()).casefold()

    for statement in required_changelog_statements:
        normalized_statement = " ".join(statement.split()).casefold()

        assert normalized_statement in normalized_changelog, f"CHANGELOG.md is missing: {statement}"
