"""Task-specific extractors for FHIR Task resources.

Pure functions that extract fields from FHIR Task JSON for the
task_projections table.
"""

import json
from datetime import date
from typing import Any

from app.projections.registry import FieldExtractor, ProjectionConfig, ProjectionRegistry
from app.projections.serializers.task import TaskFhirSerializer


def extract_status(data: dict) -> str:
    """Extract status from FHIR Task, converting to CruxMD status.

    Args:
        data: FHIR Task JSON.

    Returns:
        CruxMD status value.
    """
    fhir_status = data.get("status", "requested")

    # Check for deferred extension
    is_deferred = False
    for ext in data.get("extension", []):
        if ext.get("url", "").endswith("/is-deferred"):
            is_deferred = ext.get("valueBoolean", False)
            break

    return TaskFhirSerializer.get_cruxmd_status(fhir_status, is_deferred)


def extract_priority(data: dict) -> str:
    """Extract priority from FHIR Task.

    Args:
        data: FHIR Task JSON.

    Returns:
        Priority value (routine, urgent, asap, stat).
    """
    return data.get("priority", "routine")


def extract_category(data: dict) -> str | None:
    """Extract CruxMD category from FHIR Task.code.

    Looks for the category coding in Task.code.coding array.

    Args:
        data: FHIR Task JSON.

    Returns:
        Category value or None.
    """
    codings = data.get("code", {}).get("coding", [])
    for coding in codings:
        if coding.get("system") == "https://cruxmd.com/fhir/task-category":
            return coding.get("code")
    return None


def extract_type(data: dict) -> str | None:
    """Extract CruxMD task type from FHIR Task.code.

    Looks for the type coding in Task.code.coding array.

    Args:
        data: FHIR Task JSON.

    Returns:
        Task type value or None.
    """
    codings = data.get("code", {}).get("coding", [])
    for coding in codings:
        if coding.get("system") == "https://cruxmd.com/fhir/task-type":
            return coding.get("code")
    return None


def extract_title(data: dict) -> str:
    """Extract title from FHIR Task.description.

    Args:
        data: FHIR Task JSON.

    Returns:
        Task title/description.
    """
    return data.get("description", "")


def extract_description(data: dict) -> str | None:
    """Extract detailed description from FHIR Task.note.

    Args:
        data: FHIR Task JSON.

    Returns:
        Description text or None.
    """
    notes = data.get("note", [])
    if notes and len(notes) > 0:
        return notes[0].get("text")
    return None


def extract_due_on(data: dict) -> date | None:
    """Extract due date from FHIR Task.restriction.period.end.

    Args:
        data: FHIR Task JSON.

    Returns:
        Due date or None.
    """
    period = data.get("restriction", {}).get("period", {})
    end_str = period.get("end")
    if end_str:
        try:
            # Handle both date and datetime strings
            if "T" in end_str:
                return date.fromisoformat(end_str.split("T")[0])
            return date.fromisoformat(end_str)
        except ValueError:
            return None
    return None


def extract_priority_score(data: dict) -> int | None:
    """Extract priority score from CruxMD extension.

    Args:
        data: FHIR Task JSON.

    Returns:
        Priority score (0-100) or None.
    """
    for ext in data.get("extension", []):
        if ext.get("url", "").endswith("/priority-score"):
            return ext.get("valueInteger")
    return None


def extract_provenance(data: dict) -> dict[str, Any] | None:
    """Extract AI provenance from CruxMD extension.

    Args:
        data: FHIR Task JSON.

    Returns:
        Provenance dict or None.
    """
    for ext in data.get("extension", []):
        if ext.get("url", "").endswith("/task-provenance"):
            value_str = ext.get("valueString")
            if value_str:
                try:
                    return json.loads(value_str)
                except json.JSONDecodeError:
                    return None
    return None


def extract_context_config(data: dict) -> dict[str, Any] | None:
    """Extract context config from CruxMD extension.

    Args:
        data: FHIR Task JSON.

    Returns:
        Context config dict or None.
    """
    for ext in data.get("extension", []):
        if ext.get("url", "").endswith("/task-context-config"):
            value_str = ext.get("valueString")
            if value_str:
                try:
                    return json.loads(value_str)
                except json.JSONDecodeError:
                    return None
    return None


def extract_session_id(data: dict) -> str | None:
    """Extract session ID from CruxMD extension.

    Args:
        data: FHIR Task JSON.

    Returns:
        Session ID string or None.
    """
    for ext in data.get("extension", []):
        if ext.get("url", "").endswith("/session-id"):
            return ext.get("valueString")
    return None


def extract_focus_resource_id(data: dict) -> str | None:
    """Extract focus resource ID from FHIR Task.focus.

    Args:
        data: FHIR Task JSON.

    Returns:
        Focus resource ID string or None.
    """
    focus = data.get("focus", {})
    ref = focus.get("reference", "")
    if ref and "/" in ref:
        return ref.split("/")[-1]
    return None


def register_task_projection() -> None:
    """Register the Task projection configuration with the registry.

    This should be called at application startup to enable automatic
    projection sync for Task resources.
    """
    # Import here to avoid circular imports
    from app.models.projections.task import TaskProjection

    config = ProjectionConfig(
        resource_type="Task",
        table_name="task_projections",
        model_class=TaskProjection,
        serializer_class=TaskFhirSerializer,
        extractors=[
            FieldExtractor("status", extract_status),
            FieldExtractor("priority", extract_priority),
            FieldExtractor("category", extract_category),
            FieldExtractor("task_type", extract_type),
            FieldExtractor("title", extract_title),
            FieldExtractor("due_on", extract_due_on),
            FieldExtractor("priority_score", extract_priority_score),
            FieldExtractor("provenance", extract_provenance),
            FieldExtractor("context_config", extract_context_config),
            FieldExtractor("session_id", extract_session_id),
            FieldExtractor("focus_resource_id", extract_focus_resource_id),
        ],
    )
    ProjectionRegistry.register(config)
