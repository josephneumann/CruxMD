"""FHIR field extractors.

Extractors are pure functions that pull specific fields from FHIR JSON
for projection tables.
"""

from app.projections.extractors.task import register_task_projection

__all__ = ["register_task_projection"]
