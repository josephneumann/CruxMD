"""Task-specific extractors for FHIR Task resources.

Pure functions that extract fields from FHIR Task JSON for the
task_projections table.
"""

import json
import logging
from datetime import date
from typing import Any

from app.projections.constants import (
    EXT_CONTEXT_CONFIG,
    EXT_IS_DEFERRED,
    EXT_PRIORITY_SCORE,
    EXT_SESSION_ID,
    EXT_TASK_PROVENANCE,
    SYSTEM_TASK_CATEGORY,
    SYSTEM_TASK_TYPE,
)
from app.projections.registry import FieldExtractor, ProjectionConfig, ProjectionRegistry
from app.projections.status import get_cruxmd_status

logger = logging.getLogger(__name__)


def _get_extension_value(data: dict, url_suffix: str, value_key: str = "valueString") -> Any:
    """Get extension value by URL suffix.

    Args:
        data: FHIR resource data.
        url_suffix: End of extension URL (e.g., "priority-score").
        value_key: Key for the value (e.g., "valueInteger", "valueString").

    Returns:
        Extension value or None if not found.
    """
    for ext in data.get("extension", []):
        if ext.get("url", "").endswith(f"/{url_suffix}"):
            return ext.get(value_key)
    return None


def _get_coding_value(data: dict, system_url: str) -> str | None:
    """Get code from coding array by system URL.

    Args:
        data: FHIR resource data.
        system_url: System URL to match.

    Returns:
        Code value or None if not found.
    """
    for coding in data.get("code", {}).get("coding", []):
        if coding.get("system") == system_url:
            return coding.get("code")
    return None


def extract_status(data: dict) -> str:
    """Extract status from FHIR Task, converting to CruxMD status.

    Args:
        data: FHIR Task JSON.

    Returns:
        CruxMD status value.
    """
    fhir_status = data.get("status", "requested")
    is_deferred = _get_extension_value(data, EXT_IS_DEFERRED, "valueBoolean") or False
    return get_cruxmd_status(fhir_status, is_deferred)


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

    Args:
        data: FHIR Task JSON.

    Returns:
        Category value or None.
    """
    return _get_coding_value(data, SYSTEM_TASK_CATEGORY)


def extract_task_type(data: dict) -> str | None:
    """Extract CruxMD task type from FHIR Task.code.

    Args:
        data: FHIR Task JSON.

    Returns:
        Task type value or None.
    """
    return _get_coding_value(data, SYSTEM_TASK_TYPE)


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
    if notes:
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
    return _get_extension_value(data, EXT_PRIORITY_SCORE, "valueInteger")


def extract_provenance(data: dict) -> dict[str, Any] | None:
    """Extract AI provenance from CruxMD extension.

    Args:
        data: FHIR Task JSON.

    Returns:
        Provenance dict or None.
    """
    value_str = _get_extension_value(data, EXT_TASK_PROVENANCE, "valueString")
    if value_str:
        try:
            return json.loads(value_str)
        except json.JSONDecodeError:
            logger.warning("Failed to parse provenance JSON: %s", value_str[:100])
            return None
    return None


def extract_context_config(data: dict) -> dict[str, Any] | None:
    """Extract context config from CruxMD extension.

    Args:
        data: FHIR Task JSON.

    Returns:
        Context config dict or None.
    """
    value_str = _get_extension_value(data, EXT_CONTEXT_CONFIG, "valueString")
    if value_str:
        try:
            return json.loads(value_str)
        except json.JSONDecodeError:
            logger.warning("Failed to parse context_config JSON: %s", value_str[:100])
            return None
    return None


def extract_session_id(data: dict) -> str | None:
    """Extract session ID from CruxMD extension.

    Args:
        data: FHIR Task JSON.

    Returns:
        Session ID string or None.
    """
    return _get_extension_value(data, EXT_SESSION_ID, "valueString")


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
    from app.projections.serializers.task import TaskFhirSerializer

    config = ProjectionConfig(
        resource_type="Task",
        table_name="task_projections",
        model_class=TaskProjection,
        serializer_class=TaskFhirSerializer,
        extractors=[
            FieldExtractor("status", extract_status),
            FieldExtractor("priority", extract_priority),
            FieldExtractor("category", extract_category),
            FieldExtractor("task_type", extract_task_type),
            FieldExtractor("title", extract_title),
            FieldExtractor("description", extract_description),
            FieldExtractor("due_on", extract_due_on),
            FieldExtractor("priority_score", extract_priority_score),
            FieldExtractor("provenance", extract_provenance),
            FieldExtractor("context_config", extract_context_config),
            FieldExtractor("session_id", extract_session_id),
            FieldExtractor("focus_resource_id", extract_focus_resource_id),
        ],
    )
    ProjectionRegistry.register(config)
