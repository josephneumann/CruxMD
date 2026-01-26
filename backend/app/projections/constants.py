"""Shared constants for FHIR projections.

Centralizes URLs and extension identifiers used across serializers and extractors.
"""

# Base URL for CruxMD FHIR extensions
CRUXMD_EXTENSION_BASE = "https://cruxmd.com/fhir/extensions"

# Extension URL suffixes
EXT_PRIORITY_SCORE = "priority-score"
EXT_IS_DEFERRED = "is-deferred"
EXT_TASK_PROVENANCE = "task-provenance"
EXT_CONTEXT_CONFIG = "task-context-config"
EXT_SESSION_ID = "session-id"

# Coding system URLs
SYSTEM_TASK_TYPE = "https://cruxmd.com/fhir/task-type"
SYSTEM_TASK_CATEGORY = "https://cruxmd.com/fhir/task-category"


def extension_url(suffix: str) -> str:
    """Build full extension URL from suffix."""
    return f"{CRUXMD_EXTENSION_BASE}/{suffix}"
