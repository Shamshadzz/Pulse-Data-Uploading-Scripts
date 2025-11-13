from typing import Literal

# Duplicate handling policy per entity.
# Allowed values:
# - 'skip': skip rows that only violate unique constraints
# - 'error': treat duplicates as errors (default if not listed here)

DuplicatePolicy = Literal['skip', 'error']

_ENTITY_POLICIES = {
    # Transactional entities where duplicate SO_NUMBER may appear in Excel; prefer skipping
    'SERVICEORDERS': 'skip',
}


def get_duplicate_policy(entity: str) -> DuplicatePolicy:
    return _ENTITY_POLICIES.get(entity.upper(), 'error')
"""
Policy configuration for handling duplicates and validation behavior.

Defaults:
- Master data duplicates: already handled via dedup/skip-if-exists in transformer
- Transactional data duplicates (e.g., SERVICEORDERS): skip duplicate rows by default

This module can be extended later to read from config/policy.yaml.
"""
from typing import Dict


# Per-entity duplicate handling policy: 'skip' or 'error'
DUPLICATE_POLICY: Dict[str, str] = {
    # Master entities are already deduped and skip-if-exists
    'CLUSTERS': 'skip',
    'LOCATIONS': 'skip',
    'SPVS': 'skip',
    'PROJECTS': 'skip',
    'PACKAGES': 'skip',
    'PROJECTDEFINITIONS': 'skip',
    'VENDORS': 'skip',
    # Transactional entities
    'SERVICEORDERS': 'skip',  # default preference: skip conflicting rows
}


def get_duplicate_policy(entity: str) -> str:
    """Return duplicate handling policy for an entity: 'skip' or 'error'."""
    return DUPLICATE_POLICY.get(entity, 'skip')
