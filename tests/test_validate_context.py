"""Tests for the Azure interview JSON validation utility."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from jsonschema.exceptions import SchemaError

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = REPOSITORY_ROOT / "scripts" / "python" / "validate_context.py"
SCHEMA_PATH = REPOSITORY_ROOT / "templates" / "azure-context.schema.json"
VALID_CONTEXT_PATH = REPOSITORY_ROOT / "tests" / "fixtures" / "valid-context.json"


def load_validator_module() -> ModuleType:
    """Load the validator script as a testable Python module."""
    specification = importlib.util.spec_from_file_location(
        "validate_context",
        VALIDATOR_PATH,
    )

    if specification is None or specification.loader is None:
        raise RuntimeError(f"Unable to load validator: {VALIDATOR_PATH}")

    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def validator_module() -> ModuleType:
    """Return the loaded validator module."""
    return load_validator_module()


@pytest.fixture()
def schema() -> dict[str, Any]:
    """Return the interview JSON Schema."""
    with SCHEMA_PATH.open("r", encoding="utf-8") as stream:
        return json.load(stream)


@pytest.fixture()
def valid_context() -> dict[str, Any]:
    """Return a fresh copy of the valid context fixture."""
    with VALID_CONTEXT_PATH.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def test_valid_fixture_passes_validation(
    validator_module: ModuleType,
    schema: dict[str, Any],
    valid_context: dict[str, Any],
) -> None:
    """A complete representative context must pass validation."""
    errors = validator_module.validate_context(valid_context, schema)

    assert errors == []


def test_missing_required_property_fails_validation(
    validator_module: ModuleType,
    schema: dict[str, Any],
    valid_context: dict[str, Any],
) -> None:
    """A missing top-level required property must fail validation."""
    invalid_context = copy.deepcopy(valid_context)
    del invalid_context["network"]

    errors = validator_module.validate_context(invalid_context, schema)

    assert any("'network' is a required property" in error for error in errors)


def test_unknown_top_level_property_fails_validation(
    validator_module: ModuleType,
    schema: dict[str, Any],
    valid_context: dict[str, Any],
) -> None:
    """Unexpected top-level data must not silently enter the contract."""
    invalid_context = copy.deepcopy(valid_context)
    invalid_context["uncontrolledProperty"] = "unexpected"

    errors = validator_module.validate_context(invalid_context, schema)

    assert any("Additional properties are not allowed" in error for error in errors)


def test_invalid_lifecycle_enum_fails_validation(
    validator_module: ModuleType,
    schema: dict[str, Any],
    valid_context: dict[str, Any],
) -> None:
    """Lifecycle values outside the controlled vocabulary must fail."""
    invalid_context = copy.deepcopy(valid_context)
    invalid_context["workload"]["lifecycle"] = "partly-existing"

    errors = validator_module.validate_context(invalid_context, schema)

    assert any("$.workload.lifecycle" in error and "is not one of" in error for error in errors)


def test_ready_context_rejects_blocking_questions(
    validator_module: ModuleType,
    schema: dict[str, Any],
    valid_context: dict[str, Any],
) -> None:
    """A context cannot be ready while blocking questions remain."""
    invalid_context = copy.deepcopy(valid_context)
    invalid_context["readiness"]["blockingQuestionsRemaining"] = 1

    errors = validator_module.validate_context(invalid_context, schema)

    assert any(
        "$.readiness.blockingQuestionsRemaining" in error and "0 was expected" in error
        for error in errors
    )


def test_ready_context_rejects_unvalidated_critical_assumptions(
    validator_module: ModuleType,
    schema: dict[str, Any],
    valid_context: dict[str, Any],
) -> None:
    """A context cannot be ready with critical assumptions outstanding."""
    invalid_context = copy.deepcopy(valid_context)
    invalid_context["readiness"]["unvalidatedCriticalAssumptions"] = 1

    errors = validator_module.validate_context(invalid_context, schema)

    assert any(
        "$.readiness.unvalidatedCriticalAssumptions" in error and "0 was expected" in error
        for error in errors
    )


def test_duplicate_prohibited_changes_fail_validation(
    validator_module: ModuleType,
    schema: dict[str, Any],
    valid_context: dict[str, Any],
) -> None:
    """Duplicate prohibited changes must not be accepted."""
    invalid_context = copy.deepcopy(valid_context)
    first_change = invalid_context["prohibitedChanges"][0]
    invalid_context["prohibitedChanges"].append(first_change)

    errors = validator_module.validate_context(invalid_context, schema)

    assert any(
        "$.prohibitedChanges" in error and "non-unique elements" in error for error in errors
    )


def test_invalid_tracking_identifier_fails_validation(
    validator_module: ModuleType,
    schema: dict[str, Any],
    valid_context: dict[str, Any],
) -> None:
    """Tracked-item identifiers must follow the defined pattern."""
    invalid_context = copy.deepcopy(valid_context)
    invalid_context["decisions"][0]["id"] = "D-1"

    errors = validator_module.validate_context(invalid_context, schema)

    assert any("$.decisions[0].id" in error and "does not match" in error for error in errors)


def test_schema_error_is_raised_for_invalid_schema(
    validator_module: ModuleType,
    valid_context: dict[str, Any],
) -> None:
    """An invalid schema must raise SchemaError."""
    invalid_schema = {"type": "unsupported-type"}

    with pytest.raises(SchemaError):
        validator_module.validate_context(
            valid_context,
            invalid_schema,
        )


def test_blocking_question_count_must_match_open_questions(
    validator_module: ModuleType,
    schema: dict[str, Any],
    valid_context: dict[str, Any],
) -> None:
    """The recorded blocking-question count must match the question collection."""
    invalid_context = copy.deepcopy(valid_context)
    invalid_context["openQuestions"].append(
        {
            "id": "OQ-001",
            "question": "Which production subscription must host the workload?",
            "owner": "Workload Owner",
            "blocking": True,
            "status": "open",
        }
    )

    errors = validator_module.validate_context(invalid_context, schema)

    assert any(
        "$.readiness.blockingQuestionsRemaining" in error and "calculated value 1" in error
        for error in errors
    )


def test_unvalidated_assumption_count_must_match_assumptions(
    validator_module: ModuleType,
    schema: dict[str, Any],
    valid_context: dict[str, Any],
) -> None:
    """The recorded assumption count must match validation-required assumptions."""
    invalid_context = copy.deepcopy(valid_context)
    invalid_context["assumptions"].append(
        {
            "id": "ASM-001",
            "statement": "The platform team will provide the required peering.",
            "validationRequired": True,
            "owner": "Platform Team",
            "status": "unvalidated",
        }
    )

    errors = validator_module.validate_context(invalid_context, schema)

    assert any(
        "$.readiness.unvalidatedCriticalAssumptions" in error and "calculated value 1" in error
        for error in errors
    )


def test_ready_context_requires_complete_interview(
    validator_module: ModuleType,
    schema: dict[str, Any],
    valid_context: dict[str, Any],
) -> None:
    """A ready context must have a completed interview."""
    invalid_context = copy.deepcopy(valid_context)
    invalid_context["interview"]["status"] = "in-progress"

    errors = validator_module.validate_context(invalid_context, schema)

    assert any("$.interview.status" in error and "must be 'complete'" in error for error in errors)


def test_ready_context_rejects_blocking_dependency(
    validator_module: ModuleType,
    schema: dict[str, Any],
    valid_context: dict[str, Any],
) -> None:
    """A ready context must not contain an unresolved blocking dependency."""
    invalid_context = copy.deepcopy(valid_context)
    invalid_context["dependencies"][0]["blocking"] = True
    invalid_context["dependencies"][0]["status"] = "in-progress"

    errors = validator_module.validate_context(invalid_context, schema)

    assert any(
        "$.dependencies[0]" in error
        and "DEP-001" in error
        and "must be resolved or accepted" in error
        for error in errors
    )


def test_ready_context_rejects_reused_resource_without_identifier(
    validator_module: ModuleType,
    schema: dict[str, Any],
    valid_context: dict[str, Any],
) -> None:
    """A reused resource must have a confirmed Azure resource identifier."""
    invalid_context = copy.deepcopy(valid_context)
    invalid_context["existingResources"][0]["resourceId"] = None

    errors = validator_module.validate_context(invalid_context, schema)

    assert any(
        "$.existingResources[0].resourceId" in error and "marked for reuse" in error
        for error in errors
    )


def test_updated_timestamp_must_not_precede_created_timestamp(
    validator_module: ModuleType,
    schema: dict[str, Any],
    valid_context: dict[str, Any],
) -> None:
    """The interview update timestamp cannot precede its creation timestamp."""
    invalid_context = copy.deepcopy(valid_context)
    invalid_context["interview"]["updatedAt"] = "2026-09-13T07:59:59Z"

    errors = validator_module.validate_context(invalid_context, schema)

    assert any(
        "$.interview.updatedAt" in error and "$.interview.createdAt" in error for error in errors
    )


def test_duplicate_dependency_identifier_fails_semantic_validation(
    validator_module: ModuleType,
    schema: dict[str, Any],
    valid_context: dict[str, Any],
) -> None:
    """Different dependency records must not reuse the same identifier."""
    invalid_context = copy.deepcopy(valid_context)
    duplicate_dependency = copy.deepcopy(invalid_context["dependencies"][0])
    duplicate_dependency["description"] = (
        "A separate dependency that incorrectly reuses an existing identifier."
    )
    invalid_context["dependencies"].append(duplicate_dependency)

    errors = validator_module.validate_context(invalid_context, schema)

    assert any(
        "$.dependencies[1].id" in error and "duplicates $.dependencies[0].id" in error
        for error in errors
    )
