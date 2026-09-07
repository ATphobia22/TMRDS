"""Conservative conflict detection for biomedical evidence assertions."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from engines.biomedical_evidence_models import ConflictGroup, ConflictState, ConflictType, EvidenceAssertion


class EvidenceConflictEngine:
    """Detects comparable disagreement without deciding which scientific claim is true."""

    def detect(self, assertions: list[EvidenceAssertion]) -> list[ConflictGroup]:
        groups: list[ConflictGroup] = []
        for index, left in enumerate(assertions):
            for right in assertions[index + 1 :]:
                conflict = self.compare_assertions(left, right)
                if conflict is not None:
                    groups.append(conflict)
        return groups

    def compare_assertions(
        self, left: EvidenceAssertion, right: EvidenceAssertion
    ) -> ConflictGroup | None:
        if left.subject_entity_id != right.subject_entity_id:
            return None
        if left.predicate != right.predicate or left.object_entity_id != right.object_entity_id:
            return None
        if left.population_context and right.population_context and left.population_context != right.population_context:
            return None

        conflict_type: ConflictType | None = None
        if left.effect_direction and right.effect_direction:
            positive = {"positive", "increase", "benefit", "favors", "up"}
            negative = {"negative", "decrease", "harm", "against", "down"}
            l = left.effect_direction.casefold()
            r = right.effect_direction.casefold()
            if (l in positive and r in negative) or (l in negative and r in positive):
                conflict_type = ConflictType.OPPOSITE_EFFECT
        elif {left.evidence_grade.casefold(), right.evidence_grade.casefold()} <= {"positive", "null"} and left.evidence_grade != right.evidence_grade:
            conflict_type = ConflictType.POSITIVE_VS_NULL

        if conflict_type is None:
            return None
        material = "|".join(sorted((left.assertion_id, right.assertion_id)))
        group_id = "conflict:" + hashlib.sha256(material.encode()).hexdigest()[:32]
        return ConflictGroup(
            conflict_group_id=group_id,
            conflict_type=conflict_type,
            assertion_ids=[left.assertion_id, right.assertion_id],
            affected_entity_ids=[left.subject_entity_id, left.object_entity_id],
            detected_at=datetime.now(timezone.utc),
            comparison_basis="same subject/predicate/object with comparable population context and incompatible effect direction or grade",
            state=ConflictState.HUMAN_REVIEW_REQUIRED,
        )
