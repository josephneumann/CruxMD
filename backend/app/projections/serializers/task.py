"""FHIR Task serializer.

Converts CruxMD task data to FHIR Task JSON format.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.projections.constants import (
    EXT_CONTEXT_CONFIG,
    EXT_IS_DEFERRED,
    EXT_PRIORITY_SCORE,
    EXT_SESSION_ID,
    EXT_TASK_PROVENANCE,
    SYSTEM_TASK_CATEGORY,
    SYSTEM_TASK_TYPE,
    extension_url,
)
from app.projections.status import get_fhir_status


def _unwrap_enum(value: Any) -> Any:
    """Extract .value from enum if present, otherwise return as-is."""
    return value.value if hasattr(value, "value") else value


class TaskFhirSerializer:
    """Serializes CruxMD task data to FHIR Task resources.

    FHIR Task reference: https://www.hl7.org/fhir/task.html
    """

    @classmethod
    def to_fhir(cls, task_data: Any, task_id: uuid.UUID | None = None) -> dict:
        """Convert CruxMD task data to FHIR Task JSON."""
        data = task_data.model_dump() if hasattr(task_data, "model_dump") else dict(task_data)
        fhir_id = str(task_id) if task_id else str(uuid.uuid4())

        status_value = _unwrap_enum(data.get("status", "pending"))
        task_type = _unwrap_enum(data.get("type", "custom"))
        category = _unwrap_enum(data.get("category", "routine"))
        priority = _unwrap_enum(data.get("priority", "routine"))

        fhir_task: dict[str, Any] = {
            "resourceType": "Task",
            "id": fhir_id,
            "status": get_fhir_status(status_value),
            "intent": "order",
            "priority": priority,
            "description": data.get("title", ""),
            "authoredOn": datetime.now(timezone.utc).isoformat(),
            "code": {
                "coding": [
                    {
                        "system": SYSTEM_TASK_TYPE,
                        "code": task_type,
                        "display": task_type.replace("_", " ").title(),
                    },
                    {
                        "system": SYSTEM_TASK_CATEGORY,
                        "code": category,
                        "display": category.replace("_", " ").title(),
                    },
                ]
            },
        }

        # Optional references
        if patient_id := data.get("patient_id"):
            fhir_task["for"] = {"reference": f"Patient/{patient_id}"}

        if focus_resource_id := data.get("focus_resource_id"):
            fhir_task["focus"] = {"reference": f"Resource/{focus_resource_id}"}

        if due_on := data.get("due_on"):
            due_str = due_on.isoformat() if hasattr(due_on, "isoformat") else str(due_on)
            fhir_task["restriction"] = {"period": {"end": due_str}}

        if description := data.get("description"):
            fhir_task["note"] = [{"text": description}]

        # Build extensions
        extensions = []

        if (priority_score := data.get("priority_score")) is not None:
            extensions.append({
                "url": extension_url(EXT_PRIORITY_SCORE),
                "valueInteger": priority_score,
            })

        if provenance := data.get("provenance"):
            prov_value = provenance.model_dump() if hasattr(provenance, "model_dump") else provenance
            extensions.append({
                "url": extension_url(EXT_TASK_PROVENANCE),
                "valueString": json.dumps(prov_value),
            })

        if context_config := data.get("context_config"):
            config_value = context_config.model_dump() if hasattr(context_config, "model_dump") else context_config
            extensions.append({
                "url": extension_url(EXT_CONTEXT_CONFIG),
                "valueString": json.dumps(config_value),
            })

        if session_id := data.get("session_id"):
            extensions.append({
                "url": extension_url(EXT_SESSION_ID),
                "valueString": str(session_id),
            })

        if status_value == "deferred":
            extensions.append({
                "url": extension_url(EXT_IS_DEFERRED),
                "valueBoolean": True,
            })

        if extensions:
            fhir_task["extension"] = extensions

        return fhir_task

    @classmethod
    def update_fhir_data(cls, fhir_data: dict, updates: dict) -> dict:
        """Apply updates to existing FHIR data."""
        data = fhir_data.copy()

        for field, value in updates.items():
            if field == "status":
                cls._set_status(data, value)
            elif field == "priority" and value:
                data["priority"] = _unwrap_enum(value)
            elif field == "title" and value:
                data["description"] = value
            elif field == "description":
                cls._set_note(data, value)
            elif field == "due_on":
                cls._set_due_date(data, value)
            elif field == "priority_score":
                cls._set_extension_value(data, EXT_PRIORITY_SCORE, "valueInteger", value)
            elif field == "session_id":
                cls._set_extension_value(data, EXT_SESSION_ID, "valueString", str(value) if value else None)
            elif field == "provenance":
                cls._set_extension_json(data, EXT_TASK_PROVENANCE, value)
            elif field == "context_config":
                cls._set_extension_json(data, EXT_CONTEXT_CONFIG, value)

        return data

    @classmethod
    def _set_status(cls, data: dict, status: Any) -> None:
        """Set status with deferred extension handling."""
        if status is None:
            return
        status = _unwrap_enum(status)
        data["status"] = get_fhir_status(status)

        if status == "deferred":
            cls._set_extension_value(data, EXT_IS_DEFERRED, "valueBoolean", True)
        else:
            cls._remove_extension(data, EXT_IS_DEFERRED)

    @classmethod
    def _set_note(cls, data: dict, text: str | None) -> None:
        """Set or remove note."""
        if text:
            data["note"] = [{"text": text}]
        else:
            data.pop("note", None)

    @classmethod
    def _set_due_date(cls, data: dict, due_on: Any) -> None:
        """Set or remove due date."""
        if due_on:
            due_str = due_on.isoformat() if hasattr(due_on, "isoformat") else str(due_on)
            data["restriction"] = {"period": {"end": due_str}}
        else:
            data.pop("restriction", None)

    @classmethod
    def _set_extension_value(cls, data: dict, suffix: str, value_key: str, value: Any) -> None:
        """Set or update an extension value."""
        url = extension_url(suffix)
        if value is None:
            cls._remove_extension(data, suffix)
            return

        if "extension" not in data:
            data["extension"] = []

        for ext in data["extension"]:
            if ext.get("url") == url:
                ext[value_key] = value
                return

        data["extension"].append({"url": url, value_key: value})

    @classmethod
    def _set_extension_json(cls, data: dict, suffix: str, value: Any) -> None:
        """Set extension with JSON-encoded value."""
        if value is None:
            cls._remove_extension(data, suffix)
            return
        if hasattr(value, "model_dump"):
            value = value.model_dump()
        cls._set_extension_value(data, suffix, "valueString", json.dumps(value))

    @classmethod
    def _remove_extension(cls, data: dict, suffix: str) -> None:
        """Remove an extension by URL suffix."""
        if "extension" not in data:
            return
        url = extension_url(suffix)
        data["extension"] = [e for e in data["extension"] if e.get("url") != url]
        if not data["extension"]:
            del data["extension"]
