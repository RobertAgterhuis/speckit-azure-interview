"""Tests for the Azure intended-design review contract."""

from __future__ import annotations

import importlib.util
import json
import xml.etree.ElementTree as ET
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REVIEW_SCHEMA_PATH = REPOSITORY_ROOT / "templates" / "azure-design-review.schema.json"


def load_review_schema() -> dict[str, Any]:
    """Load the review schema or skip dependent tests during the red phase."""
    if not REVIEW_SCHEMA_PATH.is_file():
        pytest.skip("Review schema has not been implemented yet.")

    return json.loads(REVIEW_SCHEMA_PATH.read_text(encoding="utf-8"))


def build_valid_review(
    *,
    review_status: str = "approved",
    findings: list[str] | None = None,
    implementation_authorized: bool | None = None,
) -> dict[str, Any]:
    """Build one valid review artifact for schema tests."""
    if findings is None:
        findings = []

    if implementation_authorized is None:
        implementation_authorized = review_status == "approved"

    return {
        "schemaVersion": "1.0",
        "reviewStatus": review_status,
        "designModel": ".specify/design/azure-design-model.json",
        "designDigest": {
            "algorithm": "sha256",
            "value": "a" * 64,
        },
        "reviewedBy": "Robert Agterhuis",
        "reviewedAt": "2026-09-15T08:00:00Z",
        "comment": "Reviewed with the workload and platform owners.",
        "findings": findings,
        "implementationAuthorized": implementation_authorized,
    }


def validate_review(review: dict[str, Any]) -> None:
    """Validate one review artifact against the review schema."""
    validator = Draft202012Validator(load_review_schema())
    validator.validate(review)


def test_review_schema_exists() -> None:
    """The packaged extension must provide a review JSON Schema."""
    assert REVIEW_SCHEMA_PATH.is_file()


def test_review_schema_is_valid_draft_2020_12() -> None:
    """The review contract itself must be a valid JSON Schema."""
    Draft202012Validator.check_schema(load_review_schema())


def test_review_schema_accepts_approved_review() -> None:
    """An approved design authorizes implementation."""
    validate_review(build_valid_review())


def test_review_schema_accepts_rejected_review_with_findings() -> None:
    """A rejected design records at least one actionable finding."""
    validate_review(
        build_valid_review(
            review_status="rejected",
            findings=["Confirm the production subnet prefix."],
        )
    )


def test_review_schema_rejects_unknown_decision() -> None:
    """Only approved and rejected are terminal review decisions."""
    review = build_valid_review()
    review["reviewStatus"] = "conditionally-approved"

    with pytest.raises(ValidationError):
        validate_review(review)


@pytest.mark.parametrize(
    "digest",
    [
        "a" * 63,
        "a" * 65,
        "A" * 64,
        "not-a-sha256-digest",
    ],
)
def test_review_schema_rejects_invalid_design_digest(
    digest: str,
) -> None:
    """The reviewed design digest must be canonical lowercase SHA-256."""
    review = build_valid_review()
    review["designDigest"]["value"] = digest

    with pytest.raises(ValidationError):
        validate_review(review)


def test_review_schema_requires_findings_for_rejection() -> None:
    """A rejected review without a finding is not actionable."""
    review = build_valid_review(
        review_status="rejected",
        findings=[],
    )

    with pytest.raises(ValidationError):
        validate_review(review)


def test_review_schema_requires_authorization_for_approval() -> None:
    """Approved reviews must authorize implementation."""
    review = build_valid_review(
        review_status="approved",
        implementation_authorized=False,
    )

    with pytest.raises(ValidationError):
        validate_review(review)


def test_review_schema_forbids_authorization_after_rejection() -> None:
    """Rejected reviews must never authorize implementation."""
    review = build_valid_review(
        review_status="rejected",
        findings=["Private endpoint ownership is unresolved."],
        implementation_authorized=True,
    )

    with pytest.raises(ValidationError):
        validate_review(review)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("reviewedBy", ""),
        ("reviewedBy", "   "),
        ("reviewedAt", "2026-09-15"),
        ("reviewedAt", "2026-09-15T08:00:00"),
        ("designModel", "C:/outside-project/design.json"),
    ],
)
def test_review_schema_rejects_invalid_required_values(
    field: str,
    value: str,
) -> None:
    """Identity, timestamp, and design path values remain constrained."""
    review = build_valid_review()
    review[field] = value

    with pytest.raises(ValidationError):
        validate_review(review)


def test_review_schema_rejects_undeclared_properties() -> None:
    """Unreviewed metadata cannot silently enter the approval record."""
    review = build_valid_review()
    review["deployed"] = True

    with pytest.raises(ValidationError):
        validate_review(review)


REVIEW_MODULE_PATH = REPOSITORY_ROOT / "scripts" / "python" / "review_azure_design.py"
DESIGN_GENERATOR_PATH = REPOSITORY_ROOT / "scripts" / "python" / "generate_azure_design.py"
VALID_CONTEXT_PATH = REPOSITORY_ROOT / "tests" / "fixtures" / "valid-context.json"


def load_python_module(
    module_name: str,
    module_path: Path,
) -> ModuleType:
    """Load one repository Python module directly from its path."""
    specification = importlib.util.spec_from_file_location(
        module_name,
        module_path,
    )

    if specification is None or specification.loader is None:
        raise AssertionError(f"Could not load Python module: {module_path}")

    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


@pytest.fixture
def review_module() -> ModuleType:
    """Load the review implementation or skip during the red phase."""
    if not REVIEW_MODULE_PATH.is_file():
        pytest.skip("Review implementation has not been created yet.")

    return load_python_module(
        "review_azure_design",
        REVIEW_MODULE_PATH,
    )


@pytest.fixture
def unreviewed_design() -> dict[str, Any]:
    """Build a representative valid unreviewed intended design."""
    generator_module = load_python_module(
        "generate_azure_design_for_review_tests",
        DESIGN_GENERATOR_PATH,
    )
    context = json.loads(VALID_CONTEXT_PATH.read_text(encoding="utf-8"))

    return generator_module.build_design_model(
        context,
        generated_at=datetime(
            2026,
            9,
            15,
            8,
            0,
            0,
            tzinfo=timezone.utc,
        ),
    )


def test_review_module_exists() -> None:
    """The extension must provide the intended-design review implementation."""
    assert REVIEW_MODULE_PATH.is_file()


def test_approve_unreviewed_design(
    review_module: ModuleType,
    unreviewed_design: dict[str, Any],
) -> None:
    """An explicit approval creates an authorized review record."""
    reviewed_design, review = review_module.review_design_model(
        unreviewed_design,
        design_model=".specify/design/azure-design-model.json",
        decision="approved",
        reviewer="Robert Agterhuis",
        reviewed_at=datetime(
            2026,
            9,
            15,
            8,
            30,
            0,
            tzinfo=timezone.utc,
        ),
        comment="Reviewed with the platform and workload owners.",
    )

    assert reviewed_design["designStatus"] == "intended"
    assert reviewed_design["reviewStatus"] == "approved"
    assert review["reviewStatus"] == "approved"
    assert review["reviewedBy"] == "Robert Agterhuis"
    assert review["reviewedAt"] == "2026-09-15T08:30:00Z"
    assert review["findings"] == []
    assert review["implementationAuthorized"] is True
    assert review_module.verify_design_digest(
        reviewed_design,
        review,
    )


def test_reject_unreviewed_design(
    review_module: ModuleType,
    unreviewed_design: dict[str, Any],
) -> None:
    """A rejection is non-authorizing and records actionable findings."""
    findings = [
        "Confirm the production subnet prefix.",
        "Confirm private endpoint ownership.",
    ]

    reviewed_design, review = review_module.review_design_model(
        unreviewed_design,
        design_model=".specify/design/azure-design-model.json",
        decision="rejected",
        reviewer="Architecture Review Board",
        reviewed_at=datetime(
            2026,
            9,
            15,
            8,
            45,
            0,
            tzinfo=timezone.utc,
        ),
        findings=findings,
    )

    assert reviewed_design["reviewStatus"] == "rejected"
    assert review["reviewStatus"] == "rejected"
    assert review["findings"] == findings
    assert review["implementationAuthorized"] is False
    assert review_module.verify_design_digest(
        reviewed_design,
        review,
    )


def test_review_does_not_mutate_input_design(
    review_module: ModuleType,
    unreviewed_design: dict[str, Any],
) -> None:
    """Review construction leaves the caller's source object unchanged."""
    original_design = deepcopy(unreviewed_design)

    reviewed_design, _ = review_module.review_design_model(
        unreviewed_design,
        design_model=".specify/design/azure-design-model.json",
        decision="approved",
        reviewer="Robert Agterhuis",
        reviewed_at=datetime(
            2026,
            9,
            15,
            9,
            0,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert unreviewed_design == original_design
    assert reviewed_design is not unreviewed_design
    assert reviewed_design["reviewStatus"] == "approved"


@pytest.mark.parametrize(
    "existing_status",
    [
        "approved",
        "rejected",
    ],
)
def test_terminal_review_requires_overwrite(
    review_module: ModuleType,
    unreviewed_design: dict[str, Any],
    existing_status: str,
) -> None:
    """A terminal review decision cannot be silently replaced."""
    unreviewed_design["reviewStatus"] = existing_status

    with pytest.raises(
        ValueError,
        match="already been reviewed",
    ):
        review_module.review_design_model(
            unreviewed_design,
            design_model=".specify/design/azure-design-model.json",
            decision="approved",
            reviewer="Robert Agterhuis",
            reviewed_at=datetime(
                2026,
                9,
                15,
                9,
                15,
                0,
                tzinfo=timezone.utc,
            ),
        )


def test_terminal_review_can_be_explicitly_overwritten(
    review_module: ModuleType,
    unreviewed_design: dict[str, Any],
) -> None:
    """Explicit overwrite permits a replacement review decision."""
    unreviewed_design["reviewStatus"] = "rejected"

    reviewed_design, review = review_module.review_design_model(
        unreviewed_design,
        design_model=".specify/design/azure-design-model.json",
        decision="approved",
        reviewer="Robert Agterhuis",
        reviewed_at=datetime(
            2026,
            9,
            15,
            9,
            30,
            0,
            tzinfo=timezone.utc,
        ),
        overwrite=True,
    )

    assert reviewed_design["reviewStatus"] == "approved"
    assert review["implementationAuthorized"] is True


@pytest.mark.parametrize(
    ("decision", "findings", "message"),
    [
        ("pending", [], "decision"),
        ("approved", ["Unresolved issue"], "findings"),
        ("rejected", [], "finding"),
    ],
)
def test_review_rejects_invalid_decision_combinations(
    review_module: ModuleType,
    unreviewed_design: dict[str, Any],
    decision: str,
    findings: list[str],
    message: str,
) -> None:
    """Decision semantics prevent ambiguous authorization."""
    with pytest.raises(
        ValueError,
        match=message,
    ):
        review_module.review_design_model(
            unreviewed_design,
            design_model=".specify/design/azure-design-model.json",
            decision=decision,
            reviewer="Robert Agterhuis",
            reviewed_at=datetime(
                2026,
                9,
                15,
                9,
                45,
                0,
                tzinfo=timezone.utc,
            ),
            findings=findings,
        )


def test_review_rejects_naive_timestamp(
    review_module: ModuleType,
    unreviewed_design: dict[str, Any],
) -> None:
    """Review timestamps must carry explicit timezone information."""
    with pytest.raises(
        ValueError,
        match="timezone",
    ):
        review_module.review_design_model(
            unreviewed_design,
            design_model=".specify/design/azure-design-model.json",
            decision="approved",
            reviewer="Robert Agterhuis",
            reviewed_at=datetime(2026, 9, 15, 10, 0, 0),
        )


def test_digest_verification_detects_design_change(
    review_module: ModuleType,
    unreviewed_design: dict[str, Any],
) -> None:
    """Any design change invalidates the recorded review digest."""
    reviewed_design, review = review_module.review_design_model(
        unreviewed_design,
        design_model=".specify/design/azure-design-model.json",
        decision="approved",
        reviewer="Robert Agterhuis",
        reviewed_at=datetime(
            2026,
            9,
            15,
            10,
            15,
            0,
            tzinfo=timezone.utc,
        ),
    )
    modified_design = deepcopy(reviewed_design)
    modified_design["reviewStatus"] = "rejected"

    assert not review_module.verify_design_digest(
        modified_design,
        review,
    )


def test_parse_arguments_uses_canonical_review_paths(
    review_module: ModuleType,
) -> None:
    """The CLI defaults stay inside the project design directory."""
    arguments = review_module.parse_arguments(
        [
            "--decision",
            "approved",
            "--reviewer",
            "Robert Agterhuis",
        ]
    )

    assert arguments.design == Path(".specify/design/azure-design-model.json")
    assert arguments.review_output == Path(".specify/design/azure-design-review.json")
    assert arguments.review_overview_output == Path(".specify/design/azure-design-review.md")
    assert arguments.decision == "approved"
    assert arguments.reviewer == "Robert Agterhuis"
    assert arguments.finding == []
    assert arguments.comment is None
    assert arguments.overwrite is False


def test_parse_arguments_accepts_explicit_review_values(
    review_module: ModuleType,
) -> None:
    """Explicit review inputs are preserved by argument parsing."""
    arguments = review_module.parse_arguments(
        [
            "--design",
            ".specify/design/custom-design.json",
            "--review-output",
            ".specify/design/custom-review.json",
            "--review-overview-output",
            ".specify/design/custom-review.md",
            "--decision",
            "rejected",
            "--reviewer",
            "Architecture Review Board",
            "--finding",
            "Confirm the production subnet prefix.",
            "--finding",
            "Confirm private endpoint ownership.",
            "--comment",
            "Review completed with both owning teams.",
            "--overwrite",
        ]
    )

    assert arguments.design == Path(".specify/design/custom-design.json")
    assert arguments.review_output == Path(".specify/design/custom-review.json")
    assert arguments.review_overview_output == Path(".specify/design/custom-review.md")
    assert arguments.decision == "rejected"
    assert arguments.reviewer == "Architecture Review Board"
    assert arguments.finding == [
        "Confirm the production subnet prefix.",
        "Confirm private endpoint ownership.",
    ]
    assert arguments.comment == ("Review completed with both owning teams.")
    assert arguments.overwrite is True


@pytest.mark.parametrize(
    ("validator_name", "relative_path"),
    [
        (
            "validate_review_design_path",
            ".specify/design/azure-design-model.json",
        ),
        (
            "validate_review_output_path",
            ".specify/design/azure-design-review.json",
        ),
        (
            "validate_review_overview_path",
            ".specify/design/azure-design-review.md",
        ),
    ],
)
def test_review_paths_accept_project_design_directory(
    review_module: ModuleType,
    tmp_path: Path,
    validator_name: str,
    relative_path: str,
) -> None:
    """Every review artifact remains inside .specify/design."""
    design_directory = tmp_path / ".specify" / "design"
    design_directory.mkdir(parents=True)

    validator = getattr(
        review_module,
        validator_name,
    )
    validated_path = validator(
        Path(relative_path),
        project_root=tmp_path,
    )

    assert validated_path == (tmp_path / relative_path).resolve()


@pytest.mark.parametrize(
    ("validator_name", "outside_path"),
    [
        (
            "validate_review_design_path",
            "outside/design.json",
        ),
        (
            "validate_review_output_path",
            "outside/review.json",
        ),
        (
            "validate_review_overview_path",
            "outside/review.md",
        ),
    ],
)
def test_review_paths_reject_locations_outside_design_directory(
    review_module: ModuleType,
    tmp_path: Path,
    validator_name: str,
    outside_path: str,
) -> None:
    """Review inputs and outputs cannot escape .specify/design."""
    (tmp_path / ".specify" / "design").mkdir(parents=True)
    validator = getattr(
        review_module,
        validator_name,
    )

    with pytest.raises(
        ValueError,
        match=r"\.specify/design",
    ):
        validator(
            Path(outside_path),
            project_root=tmp_path,
        )


def test_render_review_markdown_documents_approval(
    review_module: ModuleType,
) -> None:
    """The human-readable artifact exposes the approval evidence."""
    review = build_valid_review(
        review_status="approved",
        findings=[],
        implementation_authorized=True,
    )

    document = review_module.render_review_markdown(review)

    assert document.startswith("# Azure Intended Design Review\n")
    assert "Review status: **approved**" in document
    assert "Implementation authorized: **Yes**" in document
    assert "Reviewed by: Robert Agterhuis" in document
    assert "Reviewed at: 2026-09-15T08:00:00Z" in document
    assert "Algorithm: `sha256`" in document
    assert f"Digest: `{'a' * 64}`" in document
    assert "No unresolved findings were recorded." in document
    assert document.endswith("\n")


def test_render_review_markdown_documents_rejection_findings(
    review_module: ModuleType,
) -> None:
    """Rejected review findings remain visible and actionable."""
    review = build_valid_review(
        review_status="rejected",
        findings=[
            "Confirm the production subnet prefix.",
            "Confirm private endpoint ownership.",
        ],
        implementation_authorized=False,
    )

    document = review_module.render_review_markdown(review)

    assert "Review status: **rejected**" in document
    assert "Implementation authorized: **No**" in document
    assert "- Confirm the production subnet prefix." in document
    assert "- Confirm private endpoint ownership." in document


def test_render_review_markdown_escapes_untrusted_content(
    review_module: ModuleType,
) -> None:
    """Reviewer-controlled Markdown content cannot inject raw HTML."""
    review = build_valid_review(
        review_status="rejected",
        findings=[
            'Unsafe <script>alert("finding")</script>',
        ],
        implementation_authorized=False,
    )
    review["reviewedBy"] = 'Reviewer <img src="x" onerror="alert(1)">'
    review["comment"] = 'Comment <iframe src="unsafe"></iframe>'

    document = review_module.render_review_markdown(review)

    assert "<script>" not in document
    assert "<img" not in document
    assert "<iframe" not in document
    assert "&lt;script&gt;" in document
    assert "&lt;img" in document
    assert "&lt;iframe" in document


def write_unreviewed_design(
    review_module: ModuleType,
    project_root: Path,
    design: dict[str, Any],
) -> Path:
    """Write one canonical unreviewed design into a test project."""
    design_directory = project_root / ".specify" / "design"
    design_directory.mkdir(parents=True)

    design_path = design_directory / "azure-design-model.json"
    design_path.write_bytes(review_module.serialize_design_model(design))
    return design_path


def test_run_publishes_synchronized_approval_artifacts(
    review_module: ModuleType,
    unreviewed_design: dict[str, Any],
    tmp_path: Path,
) -> None:
    """A successful approval publishes the complete artifact set."""
    design_path = write_unreviewed_design(
        review_module,
        tmp_path,
        unreviewed_design,
    )

    review_path = review_module.run(
        project_root=tmp_path,
        design_path=Path(".specify/design/azure-design-model.json"),
        review_path=Path(".specify/design/azure-design-review.json"),
        review_overview_path=Path(".specify/design/azure-design-review.md"),
        decision="approved",
        reviewer="Robert Agterhuis",
        reviewed_at=datetime(
            2026,
            9,
            15,
            11,
            0,
            0,
            tzinfo=timezone.utc,
        ),
        findings=[],
        comment="Reviewed with both owning teams.",
        overwrite=False,
        design_schema_path=(REPOSITORY_ROOT / "templates" / "azure-design.schema.json"),
        review_schema_path=REVIEW_SCHEMA_PATH,
    )

    design_directory = tmp_path / ".specify" / "design"
    expected_paths = {
        "design": design_path,
        "overview": (design_directory / "azure-design-overview.md"),
        "svg": (design_directory / "azure-design-overview.svg"),
        "drawio": (design_directory / "azure-design-overview.drawio"),
        "review": (design_directory / "azure-design-review.json"),
        "review_overview": (design_directory / "azure-design-review.md"),
    }

    assert review_path == expected_paths["review"].resolve()

    for artifact_path in expected_paths.values():
        assert artifact_path.is_file(), artifact_path

    reviewed_design = json.loads(expected_paths["design"].read_text(encoding="utf-8"))
    review = json.loads(expected_paths["review"].read_text(encoding="utf-8"))

    assert reviewed_design["designStatus"] == "intended"
    assert reviewed_design["reviewStatus"] == "approved"
    assert review["reviewStatus"] == "approved"
    assert review["implementationAuthorized"] is True
    assert review_module.verify_design_digest(
        reviewed_design,
        review,
    )

    review_validator = Draft202012Validator(load_review_schema())
    review_validator.validate(review)

    overview = expected_paths["overview"].read_text(encoding="utf-8")
    svg = expected_paths["svg"].read_text(encoding="utf-8")
    drawio = expected_paths["drawio"].read_text(encoding="utf-8")
    review_overview = expected_paths["review_overview"].read_text(encoding="utf-8")

    assert "Review status: **approved**" in overview
    assert "Review status: approved" in svg
    assert "Review status: approved" in drawio
    assert "Review status: **approved**" in review_overview

    ET.fromstring(svg)
    ET.fromstring(drawio)


def test_run_rejects_existing_review_before_changing_design(
    review_module: ModuleType,
    unreviewed_design: dict[str, Any],
    tmp_path: Path,
) -> None:
    """Existing review output blocks every publication side effect."""
    design_path = write_unreviewed_design(
        review_module,
        tmp_path,
        unreviewed_design,
    )
    design_before = design_path.read_bytes()

    design_directory = tmp_path / ".specify" / "design"
    review_path = design_directory / "azure-design-review.json"
    review_before = b'{"protected": true}\n'
    review_path.write_bytes(review_before)

    with pytest.raises(
        FileExistsError,
        match="overwrite",
    ):
        review_module.run(
            project_root=tmp_path,
            design_path=Path(".specify/design/azure-design-model.json"),
            review_path=Path(".specify/design/azure-design-review.json"),
            review_overview_path=Path(".specify/design/azure-design-review.md"),
            decision="approved",
            reviewer="Robert Agterhuis",
            reviewed_at=datetime(
                2026,
                9,
                15,
                11,
                15,
                0,
                tzinfo=timezone.utc,
            ),
            findings=[],
            comment=None,
            overwrite=False,
            design_schema_path=(REPOSITORY_ROOT / "templates" / "azure-design.schema.json"),
            review_schema_path=REVIEW_SCHEMA_PATH,
        )

    assert design_path.read_bytes() == design_before
    assert review_path.read_bytes() == review_before
    assert not (design_directory / "azure-design-review.md").exists()
    assert not (design_directory / "azure-design-overview.md").exists()
    assert not (design_directory / "azure-design-overview.svg").exists()
    assert not (design_directory / "azure-design-overview.drawio").exists()


def test_main_records_approved_design_review(
    review_module: ModuleType,
    unreviewed_design: dict[str, Any],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI entry point must publish an explicit approved review."""
    write_unreviewed_design(
        review_module,
        tmp_path,
        unreviewed_design,
    )
    reviewed_at = datetime(
        2026,
        9,
        15,
        12,
        0,
        0,
        tzinfo=timezone.utc,
    )

    exit_code = review_module.main(
        [
            "--decision",
            "approved",
            "--reviewer",
            "Robert Agterhuis",
            "--comment",
            "Architecture approved for implementation.",
        ],
        project_root=tmp_path,
        reviewed_at=reviewed_at,
        design_schema_path=(REPOSITORY_ROOT / "templates" / "azure-design.schema.json"),
        review_schema_path=REVIEW_SCHEMA_PATH,
    )

    assert exit_code == 0

    review_path = tmp_path / ".specify" / "design" / "azure-design-review.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))

    assert review["reviewStatus"] == "approved"
    assert review["implementationAuthorized"] is True
    assert review["reviewedAt"] == "2026-09-15T12:00:00Z"

    captured = capsys.readouterr()

    assert "Azure intended design review written successfully:" in captured.out
    assert "Review status: approved" in captured.out
    assert "Implementation authorized: Yes" in captured.out
    assert captured.err == ""


def test_main_reports_controlled_review_error(
    review_module: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI entry point must report failures without a traceback."""
    (tmp_path / ".specify").mkdir()

    exit_code = review_module.main(
        [
            "--decision",
            "approved",
            "--reviewer",
            "Robert Agterhuis",
        ],
        project_root=tmp_path,
        reviewed_at=datetime(
            2026,
            9,
            15,
            12,
            0,
            0,
            tzinfo=timezone.utc,
        ),
        design_schema_path=(REPOSITORY_ROOT / "templates" / "azure-design.schema.json"),
        review_schema_path=REVIEW_SCHEMA_PATH,
    )

    assert exit_code == 1

    captured = capsys.readouterr()

    assert captured.out == ""
    assert "Azure design review failed:" in captured.err
    assert "azure-design-model.json" in captured.err


def test_review_script_has_executable_entry_point() -> None:
    """Direct Python execution must invoke the review CLI."""
    source = REVIEW_MODULE_PATH.read_text(encoding="utf-8")

    assert 'if __name__ == "__main__":' in source
    assert "raise SystemExit(main())" in source
