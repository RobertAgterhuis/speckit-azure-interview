#!/usr/bin/env python3
"""Review and authorize an exact Azure intended-design model."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import importlib.util
import json
import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from copy import deepcopy
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from types import ModuleType
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

CANONICAL_DESIGN_MODEL = ".specify/design/azure-design-model.json"
TERMINAL_REVIEW_STATUSES = frozenset(
    {
        "approved",
        "rejected",
    }
)
SUPPORTED_DECISIONS = TERMINAL_REVIEW_STATUSES


def serialize_design_model(
    design: dict[str, Any],
) -> bytes:
    """Serialize a design deterministically as UTF-8 JSON."""
    serialized = json.dumps(
        design,
        ensure_ascii=False,
        indent=2,
    )
    return f"{serialized}\n".encode()


def calculate_design_digest(
    design: dict[str, Any],
) -> str:
    """Calculate the canonical lowercase SHA-256 design digest."""
    return hashlib.sha256(
        serialize_design_model(design),
    ).hexdigest()


def normalize_required_text(
    value: object,
    *,
    field_name: str,
    maximum_length: int,
) -> str:
    """Normalize and validate one required human-entered value."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field_name} must not be empty.")

    if len(normalized) > maximum_length:
        raise ValueError(f"{field_name} must contain at most {maximum_length} characters.")

    return normalized


def normalize_optional_comment(
    comment: object | None,
) -> str | None:
    """Normalize an optional reviewer comment."""
    if comment is None:
        return None

    return normalize_required_text(
        comment,
        field_name="comment",
        maximum_length=4000,
    )


def normalize_findings(
    findings: Sequence[str] | None,
) -> list[str]:
    """Normalize, constrain, and deduplicate review findings."""
    if findings is None:
        return []

    if isinstance(findings, str):
        raise ValueError("findings must be a sequence of strings.")

    if len(findings) > 100:
        raise ValueError("findings must contain at most 100 entries.")

    normalized_findings: list[str] = []

    for index, finding in enumerate(findings):
        normalized_finding = normalize_required_text(
            finding,
            field_name=f"finding at index {index}",
            maximum_length=2000,
        )

        if normalized_finding in normalized_findings:
            raise ValueError("findings must not contain duplicate entries.")

        normalized_findings.append(normalized_finding)

    return normalized_findings


def format_utc_timestamp(
    value: datetime,
) -> str:
    """Return a second-precision UTC timestamp with a canonical Z suffix."""
    if not isinstance(value, datetime):
        raise ValueError("reviewed_at must be a datetime.")

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("reviewed_at must include timezone information.")

    normalized = value.astimezone(timezone.utc).replace(
        microsecond=0,
    )
    return normalized.isoformat().replace("+00:00", "Z")


def validate_review_request(
    design: dict[str, Any],
    *,
    design_model: str,
    decision: str,
    reviewer: object,
    reviewed_at: datetime,
    findings: Sequence[str] | None,
    comment: object | None,
    overwrite: bool,
) -> tuple[str, str, str, list[str], str | None]:
    """Validate and normalize an intended-design review request."""
    if not isinstance(design, dict):
        raise ValueError("design must be a JSON object.")

    if design.get("designStatus") != "intended":
        raise ValueError("designStatus must be intended.")

    current_review_status = design.get("reviewStatus")

    if current_review_status not in {
        "unreviewed",
        *TERMINAL_REVIEW_STATUSES,
    }:
        raise ValueError("The design has an unsupported reviewStatus.")

    if current_review_status in TERMINAL_REVIEW_STATUSES and not overwrite:
        raise ValueError("The design has already been reviewed.")

    if decision not in SUPPORTED_DECISIONS:
        raise ValueError("The review decision must be approved or rejected.")

    if design_model != CANONICAL_DESIGN_MODEL:
        raise ValueError("design_model must reference the canonical project design model.")

    normalized_reviewer = normalize_required_text(
        reviewer,
        field_name="reviewer",
        maximum_length=256,
    )
    format_utc_timestamp(reviewed_at)
    normalized_findings = normalize_findings(findings)
    normalized_comment = normalize_optional_comment(comment)

    if decision == "approved" and normalized_findings:
        raise ValueError("Approved reviews cannot contain unresolved findings.")

    if decision == "rejected" and not normalized_findings:
        raise ValueError("A rejected decision requires at least one finding.")

    return (
        design_model,
        decision,
        normalized_reviewer,
        normalized_findings,
        normalized_comment,
    )


def review_design_model(
    design: dict[str, Any],
    *,
    design_model: str,
    decision: str,
    reviewer: object,
    reviewed_at: datetime,
    findings: Sequence[str] | None = None,
    comment: object | None = None,
    overwrite: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Apply an explicit human decision to a copied intended design."""
    (
        normalized_design_model,
        normalized_decision,
        normalized_reviewer,
        normalized_findings,
        normalized_comment,
    ) = validate_review_request(
        design,
        design_model=design_model,
        decision=decision,
        reviewer=reviewer,
        reviewed_at=reviewed_at,
        findings=findings,
        comment=comment,
        overwrite=overwrite,
    )

    reviewed_design = deepcopy(design)
    reviewed_design["reviewStatus"] = normalized_decision

    review: dict[str, Any] = {
        "schemaVersion": "1.0",
        "reviewStatus": normalized_decision,
        "designModel": normalized_design_model,
        "designDigest": {
            "algorithm": "sha256",
            "value": calculate_design_digest(reviewed_design),
        },
        "reviewedBy": normalized_reviewer,
        "reviewedAt": format_utc_timestamp(reviewed_at),
        "findings": normalized_findings,
        "implementationAuthorized": normalized_decision == "approved",
    }

    if normalized_comment is not None:
        review["comment"] = normalized_comment

    return reviewed_design, review


def verify_design_digest(
    design: dict[str, Any],
    review: dict[str, Any],
) -> bool:
    """Return whether a review still matches the exact design model."""
    digest = review.get("designDigest")

    if not isinstance(digest, dict):
        return False

    if digest.get("algorithm") != "sha256":
        return False

    recorded_value = digest.get("value")

    if not isinstance(recorded_value, str):
        return False

    calculated_value = calculate_design_digest(design)

    return hmac.compare_digest(
        calculated_value,
        recorded_value,
    )


def parse_arguments(
    arguments: list[str] | None = None,
) -> argparse.Namespace:
    """Parse intended-design review command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Record an explicit human approval or rejection of an "
            "intended-state Azure architecture design."
        ),
    )
    parser.add_argument(
        "--design",
        type=Path,
        default=Path(
            ".specify/design/azure-design-model.json",
        ),
        help=(
            "Intended-design model to review. Defaults to .specify/design/azure-design-model.json."
        ),
    )
    parser.add_argument(
        "--review-output",
        type=Path,
        default=Path(
            ".specify/design/azure-design-review.json",
        ),
        help=(
            "Machine-readable review output. Defaults to .specify/design/azure-design-review.json."
        ),
    )
    parser.add_argument(
        "--review-overview-output",
        type=Path,
        default=Path(
            ".specify/design/azure-design-review.md",
        ),
        help=("Human-readable review output. Defaults to .specify/design/azure-design-review.md."),
    )
    parser.add_argument(
        "--decision",
        required=True,
        choices=sorted(SUPPORTED_DECISIONS),
        help="Explicit human review decision.",
    )
    parser.add_argument(
        "--reviewer",
        required=True,
        help="Identity of the human reviewer.",
    )
    parser.add_argument(
        "--finding",
        action="append",
        default=[],
        help=("Actionable rejection finding. Repeat this argument for multiple findings."),
    )
    parser.add_argument(
        "--comment",
        help="Optional human review comment.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Explicitly replace an existing terminal review.",
    )
    return parser.parse_args(arguments)


def resolve_project_design_path(
    artifact_path: Path,
    *,
    project_root: Path,
    expected_suffix: str,
    artifact_name: str,
) -> Path:
    """Resolve and constrain one artifact to the project design directory."""
    resolved_project_root = project_root.resolve()
    specify_directory = resolved_project_root / ".specify"

    if not specify_directory.is_dir():
        raise ValueError("The project root must contain a .specify directory.")

    design_directory = (specify_directory / "design").resolve()

    if artifact_path.is_absolute():
        resolved_artifact_path = artifact_path.resolve()
    else:
        resolved_artifact_path = (resolved_project_root / artifact_path).resolve()

    if not resolved_artifact_path.is_relative_to(design_directory):
        raise ValueError(f"{artifact_name} must remain inside .specify/design.")

    if resolved_artifact_path.suffix.lower() != expected_suffix:
        raise ValueError(f"{artifact_name} must use the {expected_suffix} extension.")

    return resolved_artifact_path


def validate_review_design_path(
    design_path: Path,
    *,
    project_root: Path,
) -> Path:
    """Validate the intended-design model input path."""
    return resolve_project_design_path(
        design_path,
        project_root=project_root,
        expected_suffix=".json",
        artifact_name="Design model path",
    )


def validate_review_output_path(
    review_path: Path,
    *,
    project_root: Path,
) -> Path:
    """Validate the machine-readable review output path."""
    return resolve_project_design_path(
        review_path,
        project_root=project_root,
        expected_suffix=".json",
        artifact_name="Review output path",
    )


def validate_review_overview_path(
    review_overview_path: Path,
    *,
    project_root: Path,
) -> Path:
    """Validate the human-readable review output path."""
    return resolve_project_design_path(
        review_overview_path,
        project_root=project_root,
        expected_suffix=".md",
        artifact_name="Review overview path",
    )


def escape_markdown_text(
    value: object,
) -> str:
    """Escape untrusted text for safe inline Markdown rendering."""
    normalized = " ".join(str(value).splitlines()).strip()
    escaped_html = escape(
        normalized,
        quote=False,
    )

    markdown_characters = (
        "\\",
        "`",
        "*",
        "_",
        "{",
        "}",
        "[",
        "]",
        "<",
        ">",
        "#",
        "|",
    )

    for character in markdown_characters:
        escaped_html = escaped_html.replace(
            character,
            f"\\{character}",
        )

    return escaped_html


def render_review_markdown(
    review: dict[str, Any],
) -> str:
    """Render a human-readable intended-design review record."""
    review_status = escape_markdown_text(review.get("reviewStatus", ""))
    reviewer = escape_markdown_text(review.get("reviewedBy", ""))
    reviewed_at = escape_markdown_text(review.get("reviewedAt", ""))
    design_model = escape_markdown_text(review.get("designModel", ""))

    implementation_authorized = "Yes" if review.get("implementationAuthorized") is True else "No"

    design_digest = review.get("designDigest", {})

    if isinstance(design_digest, dict):
        digest_algorithm = escape_markdown_text(design_digest.get("algorithm", ""))
        digest_value = escape_markdown_text(design_digest.get("value", ""))
    else:
        digest_algorithm = ""
        digest_value = ""

    lines = [
        "# Azure Intended Design Review",
        "",
        (
            "This document records an explicit human review of one exact "
            "intended-state Azure architecture design."
        ),
        "",
        "## Decision",
        "",
        f"Review status: **{review_status}**",
        "",
        (f"Implementation authorized: **{implementation_authorized}**"),
        "",
        f"Reviewed by: {reviewer}",
        "",
        f"Reviewed at: {reviewed_at}",
        "",
    ]

    comment = review.get("comment")

    if comment is not None:
        lines.extend(
            [
                "## Reviewer comment",
                "",
                escape_markdown_text(comment),
                "",
            ]
        )

    lines.extend(
        [
            "## Findings",
            "",
        ]
    )

    findings = review.get("findings", [])

    if isinstance(findings, list) and findings:
        for finding in findings:
            lines.append(f"- {escape_markdown_text(finding)}")
    else:
        lines.append("No unresolved findings were recorded.")

    lines.extend(
        [
            "",
            "## Reviewed design integrity",
            "",
            f"Design model: `{design_model}`",
            "",
            f"Algorithm: `{digest_algorithm}`",
            "",
            f"Digest: `{digest_value}`",
            "",
            ("Any later change to the design model invalidates this recorded review digest."),
            "",
            "## Scope boundary",
            "",
            (
                "This review concerns intended architecture only. It does "
                "not claim or prove that the design has been deployed to "
                "Azure."
            ),
            "",
        ]
    )

    return "\n".join(lines)


def load_json_document(
    document_path: Path,
) -> dict[str, Any]:
    """Load one UTF-8 JSON object from disk."""
    try:
        document = json.loads(document_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Required JSON document was not found: {document_path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON document: {document_path}: {error}") from error

    if not isinstance(document, dict):
        raise ValueError(f"JSON document must contain an object: {document_path}")

    return document


def serialize_json_document(
    document: dict[str, Any],
) -> bytes:
    """Serialize one generic JSON artifact deterministically."""
    serialized = json.dumps(
        document,
        ensure_ascii=False,
        indent=2,
    )
    return f"{serialized}\n".encode()


def load_design_generator() -> ModuleType:
    """Load the sibling intended-design generator module."""
    generator_path = Path(__file__).resolve().parent / "generate_azure_design.py"
    specification = importlib.util.spec_from_file_location(
        "generate_azure_design_for_review",
        generator_path,
    )

    if specification is None or specification.loader is None:
        raise RuntimeError(f"Could not load design generator: {generator_path}")

    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def stage_artifact(
    target_path: Path,
    content: bytes,
) -> Path:
    """Write and synchronize one temporary artifact beside its target."""
    target_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target_path.parent,
            prefix=f".{target_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_file.write(content)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
            temporary_path = Path(temporary_file.name)

        return temporary_path
    except Exception:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

        raise


def restore_artifact(
    target_path: Path,
    original_content: bytes | None,
) -> None:
    """Restore one target after an interrupted multi-file publication."""
    if original_content is None:
        if target_path.exists():
            target_path.unlink()
        return

    restoration_path = stage_artifact(
        target_path,
        original_content,
    )

    try:
        os.replace(
            restoration_path,
            target_path,
        )
    finally:
        if restoration_path.exists():
            restoration_path.unlink()


def publish_artifacts_transactionally(
    artifacts: dict[Path, bytes],
) -> None:
    """Publish a staged artifact set and roll back on replacement failure."""
    if not artifacts:
        raise ValueError("At least one artifact is required.")

    resolved_targets = [target.resolve() for target in artifacts]

    if len(resolved_targets) != len(set(resolved_targets)):
        raise ValueError("Artifact target paths must be unique.")

    originals = {target: (target.read_bytes() if target.exists() else None) for target in artifacts}
    staged: dict[Path, Path] = {}
    replaced: list[Path] = []

    try:
        for target, content in artifacts.items():
            staged[target] = stage_artifact(
                target,
                content,
            )

        for target, temporary_path in staged.items():
            os.replace(
                temporary_path,
                target,
            )
            replaced.append(target)

    except Exception as publication_error:
        rollback_errors: list[str] = []

        for target in reversed(replaced):
            try:
                restore_artifact(
                    target,
                    originals[target],
                )
            except Exception as rollback_error:
                rollback_errors.append(f"{target}: {rollback_error}")

        if rollback_errors:
            joined_errors = "; ".join(rollback_errors)
            raise RuntimeError(
                f"Artifact publication failed and rollback was incomplete: {joined_errors}"
            ) from publication_error

        raise

    finally:
        for temporary_path in staged.values():
            if temporary_path.exists():
                temporary_path.unlink()


def validate_xml_artifact(
    content: str,
    *,
    artifact_name: str,
) -> None:
    """Require generated SVG or Draw.io content to be valid XML."""
    try:
        ET.fromstring(content)
    except ET.ParseError as error:
        raise ValueError(f"{artifact_name} is not valid XML: {error}") from error


def run(
    *,
    project_root: Path,
    design_path: Path,
    review_path: Path,
    review_overview_path: Path,
    decision: str,
    reviewer: object,
    reviewed_at: datetime,
    findings: Sequence[str] | None,
    comment: object | None,
    overwrite: bool,
    design_schema_path: Path,
    review_schema_path: Path,
) -> Path:
    """Review a design and publish a synchronized artifact transaction."""
    resolved_design_path = validate_review_design_path(
        design_path,
        project_root=project_root,
    )
    resolved_review_path = validate_review_output_path(
        review_path,
        project_root=project_root,
    )
    resolved_review_overview_path = validate_review_overview_path(
        review_overview_path,
        project_root=project_root,
    )

    design_directory = (project_root.resolve() / ".specify" / "design").resolve()
    overview_path = design_directory / "azure-design-overview.md"
    svg_path = design_directory / "azure-design-overview.svg"
    drawio_path = design_directory / "azure-design-overview.drawio"

    all_targets = [
        resolved_design_path,
        overview_path,
        svg_path,
        drawio_path,
        resolved_review_path,
        resolved_review_overview_path,
    ]

    if len(all_targets) != len(set(all_targets)):
        raise ValueError("Review artifact paths must be unique.")

    if not overwrite:
        protected_outputs = [
            resolved_review_path,
            resolved_review_overview_path,
        ]
        existing_outputs = [path for path in protected_outputs if path.exists()]

        if existing_outputs:
            existing_names = ", ".join(str(path) for path in existing_outputs)
            raise FileExistsError(
                f"Review output already exists. Use --overwrite to replace it: {existing_names}"
            )

    design = load_json_document(
        resolved_design_path,
    )
    design_schema = load_json_document(
        design_schema_path.resolve(),
    )
    review_schema = load_json_document(
        review_schema_path.resolve(),
    )

    generator = load_design_generator()
    generator.validate_design_model(
        design,
        design_schema,
    )

    reviewed_design, review = review_design_model(
        design,
        design_model=CANONICAL_DESIGN_MODEL,
        decision=decision,
        reviewer=reviewer,
        reviewed_at=reviewed_at,
        findings=findings,
        comment=comment,
        overwrite=overwrite,
    )

    generator.validate_design_model(
        reviewed_design,
        design_schema,
    )
    Draft202012Validator(
        review_schema,
    ).validate(review)

    if not verify_design_digest(
        reviewed_design,
        review,
    ):
        raise ValueError("Generated review digest does not match the design.")

    mermaid = generator.render_mermaid_diagram(
        reviewed_design,
    )
    overview = generator.render_design_markdown(
        reviewed_design,
        mermaid,
    )
    svg = generator.render_svg_diagram(
        reviewed_design,
    )
    drawio = generator.render_drawio_diagram(
        reviewed_design,
    )
    review_overview = render_review_markdown(
        review,
    )

    validate_xml_artifact(
        svg,
        artifact_name="SVG overview",
    )
    validate_xml_artifact(
        drawio,
        artifact_name="Draw.io overview",
    )

    artifacts = {
        resolved_design_path: serialize_design_model(reviewed_design),
        overview_path: overview.encode("utf-8"),
        svg_path: svg.encode("utf-8"),
        drawio_path: drawio.encode("utf-8"),
        resolved_review_path: serialize_json_document(review),
        resolved_review_overview_path: (review_overview.encode("utf-8")),
    }

    publish_artifacts_transactionally(
        artifacts,
    )

    return resolved_review_path


def main(
    arguments: list[str] | None = None,
    *,
    project_root: Path | None = None,
    reviewed_at: datetime | None = None,
    design_schema_path: Path | None = None,
    review_schema_path: Path | None = None,
) -> int:
    """Run the intended-design review command-line workflow."""
    parsed_arguments = parse_arguments(arguments)

    resolved_project_root = (
        project_root.resolve() if project_root is not None else Path.cwd().resolve()
    )
    resolved_reviewed_at = reviewed_at if reviewed_at is not None else datetime.now(timezone.utc)
    templates_directory = Path(__file__).resolve().parents[2] / "templates"
    resolved_design_schema_path = (
        design_schema_path.resolve()
        if design_schema_path is not None
        else templates_directory / "azure-design.schema.json"
    )
    resolved_review_schema_path = (
        review_schema_path.resolve()
        if review_schema_path is not None
        else templates_directory / "azure-design-review.schema.json"
    )

    try:
        written_path = run(
            project_root=resolved_project_root,
            design_path=parsed_arguments.design,
            review_path=parsed_arguments.review_output,
            review_overview_path=parsed_arguments.review_overview_output,
            decision=parsed_arguments.decision,
            reviewer=parsed_arguments.reviewer,
            reviewed_at=resolved_reviewed_at,
            findings=parsed_arguments.finding,
            comment=parsed_arguments.comment,
            overwrite=parsed_arguments.overwrite,
            design_schema_path=resolved_design_schema_path,
            review_schema_path=resolved_review_schema_path,
        )
    except (OSError, ValueError, ValidationError) as exception:
        print(
            f"Azure design review failed: {exception}",
            file=sys.stderr,
        )
        return 1

    implementation_authorized = "Yes" if parsed_arguments.decision == "approved" else "No"

    print(f"Azure intended design review written successfully: {written_path}")
    print(f"Review status: {parsed_arguments.decision}")
    print(f"Implementation authorized: {implementation_authorized}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
