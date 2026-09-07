"""Deterministic biomedical identifier and label canonicalization."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timezone

from engines.biomedical_evidence_models import CanonicalEntity, EntityType

NORMALIZATION_VERSION = "1.0.0"


def canonicalize_label(label: str) -> str:
    if not isinstance(label, str) or not label.strip():
        raise ValueError("label must be a non-empty string")
    value = unicodedata.normalize("NFKC", label).strip()
    value = re.sub(r"\s+", " ", value)
    return value.casefold()


def normalize_identifier(namespace: str, identifier: str) -> str:
    namespace = namespace.strip().casefold()
    identifier = identifier.strip()
    if not namespace or not identifier:
        raise ValueError("identifier namespace and identifier are required")
    if any(ord(ch) < 32 for ch in identifier):
        raise ValueError("identifier contains control characters")
    return f"{namespace}:{identifier}"


def resolve_entity_key(
    entity_type: EntityType | str,
    identifiers: list[tuple[str, str]],
    normalized_label: str,
) -> str:
    entity_value = entity_type.value if isinstance(entity_type, EntityType) else str(entity_type)
    normalized = canonicalize_label(normalized_label)
    normalized_ids = sorted(normalize_identifier(ns, value) for ns, value in identifiers)
    if normalized_ids:
        identity = "|".join(normalized_ids)
    else:
        identity = f"label:{normalized}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]
    return f"tmrds:{entity_value.casefold()}:{digest}"


def canonicalize_record(
    entity_type: EntityType,
    label: str,
    identifiers: list[tuple[str, str]],
    synonyms: list[str] | None = None,
    properties: dict | None = None,
    source_ids: list[str] | None = None,
) -> CanonicalEntity:
    now = datetime.now(timezone.utc)
    normalized_label = canonicalize_label(label)
    identifier_map = {ns.strip().casefold(): value.strip() for ns, value in identifiers}
    return CanonicalEntity(
        entity_id=resolve_entity_key(entity_type, identifiers, normalized_label),
        entity_type=entity_type,
        label=label.strip(),
        normalized_label=normalized_label,
        identifiers=identifier_map,
        synonyms=[canonicalize_label(x) for x in (synonyms or []) if x.strip()],
        source_ids=source_ids or [],
        properties=properties or {},
        created_at=now,
        updated_at=now,
    )
