"""Projection registry and configuration.

The projection system maps FHIR resource types to projection tables,
extracting specific fields for indexed queries while keeping the canonical
FHIR JSON as the source of truth.
"""

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class FieldExtractor:
    """Maps a FHIR field to a projection column.

    Args:
        target_column: Name of the column in the projection table.
        extractor: Function that extracts the value from FHIR JSON.
    """

    target_column: str
    extractor: Callable[[dict], Any]


@dataclass
class ProjectionConfig:
    """Configuration for a resource type's projection.

    Defines how to extract fields from FHIR JSON into a projection table.
    """

    resource_type: str
    table_name: str
    model_class: type
    serializer_class: type
    extractors: list[FieldExtractor] = field(default_factory=list)

    def extract(self, fhir_data: dict) -> dict:
        """Extract all projection fields from FHIR data.

        Args:
            fhir_data: Raw FHIR resource JSON.

        Returns:
            Dictionary mapping column names to extracted values.
        """
        return {e.target_column: e.extractor(fhir_data) for e in self.extractors}


# Module-level storage (not class-level to avoid shared mutable state)
_registry_configs: dict[str, ProjectionConfig] = {}


class ProjectionRegistry:
    """Registry of projection configurations by resource type.

    Maintains a mapping of FHIR resource types to their projection
    configurations, enabling automatic projection sync when resources
    are saved.
    """

    @classmethod
    def register(cls, config: ProjectionConfig) -> None:
        """Register a projection configuration.

        Args:
            config: The projection configuration to register.
        """
        _registry_configs[config.resource_type] = config

    @classmethod
    def get(cls, resource_type: str) -> ProjectionConfig | None:
        """Get projection configuration for a resource type.

        Args:
            resource_type: FHIR resource type (e.g., 'Task').

        Returns:
            ProjectionConfig if registered, None otherwise.
        """
        return _registry_configs.get(resource_type)

    @classmethod
    def has_projection(cls, resource_type: str) -> bool:
        """Check if a resource type has a registered projection.

        Args:
            resource_type: FHIR resource type.

        Returns:
            True if projection is registered.
        """
        return resource_type in _registry_configs

    @classmethod
    def all_configs(cls) -> dict[str, ProjectionConfig]:
        """Get all registered projection configurations.

        Returns:
            Dictionary mapping resource types to configs.
        """
        return _registry_configs.copy()

    @classmethod
    def _clear_for_testing(cls) -> None:
        """Clear all registered configurations. Internal use in tests only."""
        _registry_configs.clear()
