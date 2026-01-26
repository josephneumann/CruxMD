"""FHIR Task serializer.

Converts CruxMD task data to FHIR Task JSON format.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any


class TaskFhirSerializer:
    """Serializes CruxMD task data to FHIR Task resources.

    FHIR Task reference: https://www.hl7.org/fhir/task.html

    CruxMD extensions are stored under a custom extension URL to preserve
    application-specific data while maintaining FHIR compliance.
    """

    CRUXMD_EXTENSION_BASE = "https://cruxmd.com/fhir/extensions"

    # Map CruxMD category to FHIR Task.code coding
    CATEGORY_CODES = {
        "critical": {
            "system": "https://cruxmd.com/fhir/task-category",
            "code": "critical",
            "display": "Critical",
        },
        "routine": {
            "system": "https://cruxmd.com/fhir/task-category",
            "code": "routine",
            "display": "Routine",
        },
        "schedule": {
            "system": "https://cruxmd.com/fhir/task-category",
            "code": "schedule",
            "display": "Schedule",
        },
        "research": {
            "system": "https://cruxmd.com/fhir/task-category",
            "code": "research",
            "display": "Research",
        },
    }

    # Map CruxMD task type to FHIR coding
    TYPE_CODES = {
        "critical_lab_review": {
            "system": "https://cruxmd.com/fhir/task-type",
            "code": "critical_lab_review",
            "display": "Critical Lab Review",
        },
        "abnormal_result": {
            "system": "https://cruxmd.com/fhir/task-type",
            "code": "abnormal_result",
            "display": "Abnormal Result",
        },
        "hospitalization_alert": {
            "system": "https://cruxmd.com/fhir/task-type",
            "code": "hospitalization_alert",
            "display": "Hospitalization Alert",
        },
        "patient_message": {
            "system": "https://cruxmd.com/fhir/task-type",
            "code": "patient_message",
            "display": "Patient Message",
        },
        "external_result": {
            "system": "https://cruxmd.com/fhir/task-type",
            "code": "external_result",
            "display": "External Result",
        },
        "pre_visit_prep": {
            "system": "https://cruxmd.com/fhir/task-type",
            "code": "pre_visit_prep",
            "display": "Pre-Visit Prep",
        },
        "follow_up": {
            "system": "https://cruxmd.com/fhir/task-type",
            "code": "follow_up",
            "display": "Follow-Up",
        },
        "appointment": {
            "system": "https://cruxmd.com/fhir/task-type",
            "code": "appointment",
            "display": "Appointment",
        },
        "research_review": {
            "system": "https://cruxmd.com/fhir/task-type",
            "code": "research_review",
            "display": "Research Review",
        },
        "order_signature": {
            "system": "https://cruxmd.com/fhir/task-type",
            "code": "order_signature",
            "display": "Order Signature",
        },
        "custom": {
            "system": "https://cruxmd.com/fhir/task-type",
            "code": "custom",
            "display": "Custom",
        },
    }

    # Map CruxMD status to FHIR Task status
    STATUS_MAP = {
        "pending": "requested",
        "in_progress": "in-progress",
        "paused": "on-hold",
        "completed": "completed",
        "cancelled": "cancelled",
        "deferred": "on-hold",  # FHIR doesn't have deferred, use on-hold with extension
    }

    # Reverse map: FHIR status to CruxMD status
    STATUS_MAP_REVERSE = {
        "requested": "pending",
        "in-progress": "in_progress",
        "on-hold": "paused",  # Default mapping; deferred uses extension
        "completed": "completed",
        "cancelled": "cancelled",
        "draft": "pending",
        "received": "pending",
        "accepted": "in_progress",
        "rejected": "cancelled",
        "ready": "pending",
        "failed": "cancelled",
        "entered-in-error": "cancelled",
    }

    @classmethod
    def to_fhir(
        cls,
        task_data: Any,
        task_id: uuid.UUID | None = None,
    ) -> dict:
        """Convert CruxMD task data to FHIR Task JSON.

        Args:
            task_data: TaskCreate schema or dict with task fields.
            task_id: Optional UUID to use as the FHIR Task.id.

        Returns:
            FHIR Task resource as dict.
        """
        # Handle both Pydantic models and dicts
        if hasattr(task_data, "model_dump"):
            data = task_data.model_dump()
        else:
            data = dict(task_data)

        fhir_id = str(task_id) if task_id else str(uuid.uuid4())

        # Get status, handling enum values
        status_value = data.get("status", "pending")
        if hasattr(status_value, "value"):
            status_value = status_value.value
        fhir_status = cls.STATUS_MAP.get(status_value, "requested")

        # Get type and category, handling enum values
        task_type = data.get("type", "custom")
        if hasattr(task_type, "value"):
            task_type = task_type.value

        category = data.get("category", "routine")
        if hasattr(category, "value"):
            category = category.value

        priority = data.get("priority", "routine")
        if hasattr(priority, "value"):
            priority = priority.value

        # Build base FHIR Task
        fhir_task: dict[str, Any] = {
            "resourceType": "Task",
            "id": fhir_id,
            "status": fhir_status,
            "intent": "order",
            "priority": priority,
            "description": data.get("title", ""),
            "authoredOn": datetime.now(timezone.utc).isoformat(),
        }

        # Add code (task type)
        type_code = cls.TYPE_CODES.get(task_type, cls.TYPE_CODES["custom"])
        fhir_task["code"] = {
            "coding": [
                type_code,
                cls.CATEGORY_CODES.get(category, cls.CATEGORY_CODES["routine"]),
            ]
        }

        # Add patient reference
        patient_id = data.get("patient_id")
        if patient_id:
            fhir_task["for"] = {"reference": f"Patient/{patient_id}"}

        # Add focus resource reference
        focus_resource_id = data.get("focus_resource_id")
        if focus_resource_id:
            fhir_task["focus"] = {"reference": f"Resource/{focus_resource_id}"}

        # Add due date as restriction period
        due_on = data.get("due_on")
        if due_on:
            due_str = due_on.isoformat() if hasattr(due_on, "isoformat") else str(due_on)
            fhir_task["restriction"] = {"period": {"end": due_str}}

        # Add description as note if provided
        description = data.get("description")
        if description:
            fhir_task["note"] = [{"text": description}]

        # Build extensions
        extensions = []

        # Priority score extension
        priority_score = data.get("priority_score")
        if priority_score is not None:
            extensions.append({
                "url": f"{cls.CRUXMD_EXTENSION_BASE}/priority-score",
                "valueInteger": priority_score,
            })

        # Provenance extension
        provenance = data.get("provenance")
        if provenance:
            prov_value = provenance
            if hasattr(provenance, "model_dump"):
                prov_value = provenance.model_dump()
            extensions.append({
                "url": f"{cls.CRUXMD_EXTENSION_BASE}/task-provenance",
                "valueString": json.dumps(prov_value),
            })

        # Context config extension
        context_config = data.get("context_config")
        if context_config:
            config_value = context_config
            if hasattr(context_config, "model_dump"):
                config_value = context_config.model_dump()
            extensions.append({
                "url": f"{cls.CRUXMD_EXTENSION_BASE}/task-context-config",
                "valueString": json.dumps(config_value),
            })

        # Session ID extension
        session_id = data.get("session_id")
        if session_id:
            extensions.append({
                "url": f"{cls.CRUXMD_EXTENSION_BASE}/session-id",
                "valueString": str(session_id),
            })

        # Deferred flag extension (for distinguishing deferred from paused)
        if status_value == "deferred":
            extensions.append({
                "url": f"{cls.CRUXMD_EXTENSION_BASE}/is-deferred",
                "valueBoolean": True,
            })

        if extensions:
            fhir_task["extension"] = extensions

        return fhir_task

    @classmethod
    def get_fhir_status(cls, cruxmd_status: str) -> str:
        """Convert CruxMD status to FHIR status.

        Args:
            cruxmd_status: CruxMD status value.

        Returns:
            FHIR Task status value.
        """
        return cls.STATUS_MAP.get(cruxmd_status, "requested")

    @classmethod
    def get_cruxmd_status(cls, fhir_status: str, is_deferred: bool = False) -> str:
        """Convert FHIR status to CruxMD status.

        Args:
            fhir_status: FHIR Task status value.
            is_deferred: Whether the deferred extension is set.

        Returns:
            CruxMD status value.
        """
        if fhir_status == "on-hold" and is_deferred:
            return "deferred"
        return cls.STATUS_MAP_REVERSE.get(fhir_status, "pending")
