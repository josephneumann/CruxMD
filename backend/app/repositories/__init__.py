"""Repository layer for data access.

Repositories encapsulate database operations and provide a clean interface
for CRUD operations on domain objects.
"""

from app.repositories.fhir import FhirRepository
from app.repositories.task import TaskRepository

__all__ = ["FhirRepository", "TaskRepository"]
