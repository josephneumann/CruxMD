"""FHIR serializers.

Serializers convert application data to FHIR JSON format.
"""

from app.projections.serializers.task import TaskFhirSerializer

__all__ = ["TaskFhirSerializer"]
