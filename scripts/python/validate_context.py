#!/usr/bin/env python3
"""Validate a Spec Kit Azure Interview context."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

EXIT_SUCCESS = 0
EXIT_VALIDATION_FAILED = 1
EXIT_EXECUTION_ERROR = 2


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    script_path = Path(__file__).resolve()
    repository_root = script_path.parents[2]

    parser = argparse.ArgumentParser(
        description=(
            "Validate an Azure interview context against its JSON Schema "
            "and semantic readiness rules."
        )
    )
    parser.add_argument(
        "context",
        type=Path,
        help="Path to azure-context.json.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=repository_root / "templates" / "azure-context.schema.json",
        help="Path to the JSON Schema. Defaults to templates/azure-context.schema.json.",
    )
    return parser.parse_args()


def load_json(path: Path, label: str) -> dict[str, Any]:
    """Load a JSON object from disk."""
    if not path.is_file():
        raise FileNotFoundError(f"{label} file does not exist: {path}")

    try:
        with path.open("r", encoding="utf-8") as stream:
            document = json.load(stream)
    except json.JSONDecodeError as exception:
        raise ValueError(
            f"{label} is not valid JSON at line {exception.lineno}, "
            f"column {exception.colno}: {exception.msg}"
        ) from exception

    if not isinstance(document, dict):
        raise ValueError(f"{label} root must be a JSON object: {path}")

    return document


def format_json_path(path: Any) -> str:
    """Format a jsonschema error path for readable output."""
    segments = list(path)

    if not segments:
        return "$"

    result = "$"
    for segment in segments:
        if isinstance(segment, int):
            result += f"[{segment}]"
        else:
            result += f".{segment}"

    return result


def parse_iso_datetime(value: str) -> datetime:
    """Parse an ISO 8601 date-time accepted by the JSON Schema."""
    normalized_value = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized_value)


def find_duplicate_identifiers(
    items: list[dict[str, Any]],
    collection_name: str,
) -> list[str]:
    """Return semantic errors for duplicate identifiers in a collection."""
    errors: list[str] = []
    seen_identifiers: dict[str, int] = {}

    for index, item in enumerate(items):
        identifier = item["id"]

        if identifier in seen_identifiers:
            first_index = seen_identifiers[identifier]
            errors.append(
                f"$.{collection_name}[{index}].id: identifier '{identifier}' "
                f"duplicates $.{collection_name}[{first_index}].id"
            )
        else:
            seen_identifiers[identifier] = index

    return errors


def validate_semantics(context: dict[str, Any]) -> list[str]:
    """Validate cross-field consistency and readiness semantics."""
    errors: list[str] = []

    interview = context["interview"]
    readiness = context["readiness"]
    open_questions = context["openQuestions"]
    assumptions = context["assumptions"]
    dependencies = context["dependencies"]
    existing_resources = context["existingResources"]

    created_at = parse_iso_datetime(interview["createdAt"])
    updated_at = parse_iso_datetime(interview["updatedAt"])

    if updated_at < created_at:
        errors.append(
            "$.interview.updatedAt: must be greater than or equal to $.interview.createdAt"
        )

    calculated_blocking_questions = sum(
        1 for question in open_questions if question["blocking"] and question["status"] == "open"
    )

    recorded_blocking_questions = readiness["blockingQuestionsRemaining"]

    if recorded_blocking_questions != calculated_blocking_questions:
        errors.append(
            "$.readiness.blockingQuestionsRemaining: "
            f"recorded value {recorded_blocking_questions} does not match "
            f"the calculated value {calculated_blocking_questions}"
        )

    calculated_unvalidated_assumptions = sum(
        1
        for assumption in assumptions
        if assumption["validationRequired"] and assumption["status"] == "unvalidated"
    )

    recorded_unvalidated_assumptions = readiness["unvalidatedCriticalAssumptions"]

    if recorded_unvalidated_assumptions != calculated_unvalidated_assumptions:
        errors.append(
            "$.readiness.unvalidatedCriticalAssumptions: "
            f"recorded value {recorded_unvalidated_assumptions} does not match "
            f"the calculated value {calculated_unvalidated_assumptions}"
        )

    errors.extend(find_duplicate_identifiers(dependencies, "dependencies"))
    errors.extend(find_duplicate_identifiers(context["decisions"], "decisions"))
    errors.extend(find_duplicate_identifiers(assumptions, "assumptions"))
    errors.extend(find_duplicate_identifiers(open_questions, "openQuestions"))

    if readiness["readyForSpecification"]:
        if interview["status"] != "complete":
            errors.append(
                "$.interview.status: must be 'complete' when "
                "$.readiness.readyForSpecification is true"
            )

        blocking_dependencies = [
            (index, dependency)
            for index, dependency in enumerate(dependencies)
            if dependency["blocking"] and dependency["status"] in {"open", "in-progress"}
        ]

        for index, dependency in blocking_dependencies:
            errors.append(
                f"$.dependencies[{index}]: blocking dependency "
                f"'{dependency['id']}' must be resolved or accepted before "
                "the context is ready for specification"
            )

        unresolved_reused_resources = [
            (index, resource)
            for index, resource in enumerate(existing_resources)
            if resource["intent"] == "reuse" and resource["resourceId"] is None
        ]

        for index, resource in unresolved_reused_resources:
            errors.append(
                f"$.existingResources[{index}].resourceId: resource "
                f"'{resource['resourceName']}' is marked for reuse but has no "
                "confirmed resource identifier"
            )

    return errors


def validate_context(
    context: dict[str, Any],
    schema: dict[str, Any],
) -> list[str]:
    """Return sorted schema and semantic validation errors."""
    Draft202012Validator.check_schema(schema)

    validator = Draft202012Validator(
        schema=schema,
        format_checker=FormatChecker(),
    )

    schema_errors = sorted(
        validator.iter_errors(context),
        key=lambda error: (
            list(error.absolute_path),
            error.message,
        ),
    )

    formatted_schema_errors = [
        f"{format_json_path(error.absolute_path)}: {error.message}" for error in schema_errors
    ]

    if formatted_schema_errors:
        return formatted_schema_errors

    return sorted(validate_semantics(context))


def main() -> int:
    """Run validation and return a stable process exit code."""
    arguments = parse_arguments()
    context_path = arguments.context.resolve()
    schema_path = arguments.schema.resolve()

    try:
        schema = load_json(schema_path, "Schema")
        context = load_json(context_path, "Context")
        errors = validate_context(context, schema)
    except (FileNotFoundError, OSError, ValueError) as exception:
        print(f"ERROR: {exception}", file=sys.stderr)
        return EXIT_EXECUTION_ERROR
    except SchemaError as exception:
        print(
            f"ERROR: The JSON Schema is invalid: {exception.message}",
            file=sys.stderr,
        )
        return EXIT_EXECUTION_ERROR

    if errors:
        print(
            f"INVALID: {context_path} contains {len(errors)} validation error(s).",
            file=sys.stderr,
        )

        for index, error in enumerate(errors, start=1):
            print(f"{index}. {error}", file=sys.stderr)

        return EXIT_VALIDATION_FAILED

    print(f"VALID: {context_path}")
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
