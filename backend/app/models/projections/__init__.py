"""Projection models for FHIR resources.

Projection tables provide fast indexed queries over extracted FHIR fields
while keeping the canonical FHIR JSON as the source of truth.
"""

from app.models.projections.task import TaskProjection

__all__ = ["TaskProjection"]
