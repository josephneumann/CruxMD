"""FHIR projection system.

Projections extract indexed fields from FHIR JSON into separate tables
for fast queries while keeping the canonical FHIR data as the source of truth.
"""

from app.projections.registry import FieldExtractor, ProjectionConfig, ProjectionRegistry

__all__ = [
    "FieldExtractor",
    "ProjectionConfig",
    "ProjectionRegistry",
]
