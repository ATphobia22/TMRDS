"""Tamper-evident local evidence ledger contracts; synthetic metadata only."""
from __future__ import annotations

import json

import pytest

from engines.evidence_ledger import EvidenceLedger, LedgerIntegrityError
from engines.qrce_research_orchestrator import QRCEResearchOrchestrator


def test_append_creates_canonical_hash_chain_and_recent_is_bounded(tmp_path) -> None:
    ledger = EvidenceLedger(str(tmp_path / "ledger.jsonl"))

    first = ledger.append({"record_type": "research_run", "payload": {"count": 1}})
    second = ledger.append({"record_type": "research_run", "payload": {"count": 2}})

    assert first["schema_version"] == 2
    assert first["previous_hash"] == "0" * 64
    assert second["previous_hash"] == first["content_hash"]
    assert ledger.recent(1) == [second]
    report = ledger.verify()
    assert report["valid"] is True
    assert report["entry_count"] == 2
    assert report["chain_status"] == "VERIFIED"


def test_verify_detects_record_tampering(tmp_path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = EvidenceLedger(str(path))
    ledger.append({"record_type": "research_run", "payload": {"count": 1}})

    entry = json.loads(path.read_text(encoding="utf-8"))
    entry["payload"]["count"] = 99
    path.write_text(json.dumps(entry, separators=(",", ":")) + "\n", encoding="utf-8")

    with pytest.raises(LedgerIntegrityError, match="hash mismatch"):
        ledger.verify()


def test_append_fails_closed_when_existing_ledger_is_corrupt(tmp_path) -> None:
    path = tmp_path / "ledger.jsonl"
    ledger = EvidenceLedger(str(path))
    ledger.append({"record_type": "research_run", "payload": {"count": 1}})
    original = path.read_bytes()
    path.write_bytes(original.replace(b'"count":1', b'"count":2'))

    corrupted = path.read_bytes()
    with pytest.raises(LedgerIntegrityError):
        ledger.append({"record_type": "research_run", "payload": {"count": 3}})
    assert path.read_bytes() == corrupted


def test_legacy_v1_records_are_verified_and_anchor_new_v2_chain(tmp_path) -> None:
    path = tmp_path / "ledger.jsonl"
    legacy = {
        "ts": "2026-01-01T00:00:00Z",
        "record_type": "legacy",
        "payload": {"count": 1},
    }
    legacy["content_hash"] = EvidenceLedger(str(path)).content_hash(legacy)
    path.write_text(json.dumps(legacy, separators=(",", ":")) + "\n", encoding="utf-8")

    ledger = EvidenceLedger(str(path))
    report = ledger.verify()
    assert report["valid"] is True
    assert report["legacy_entry_count"] == 1
    assert report["chain_status"] == "PARTIAL_LEGACY_PREFIX"

    current = ledger.append({"record_type": "new", "payload": {"count": 2}})
    assert current["previous_hash"] == legacy["content_hash"]
    report = ledger.verify()
    assert report["entry_count"] == 2
    assert report["legacy_entry_count"] == 1
    assert report["chain_entry_count"] == 1
    assert report["chain_status"] == "PARTIAL_LEGACY_PREFIX"


def test_ledger_rejects_truncated_or_malformed_tail(tmp_path) -> None:
    path = tmp_path / "ledger.jsonl"
    path.write_bytes(b'{"record_type":"incomplete"')
    ledger = EvidenceLedger(str(path))

    with pytest.raises(LedgerIntegrityError):
        ledger.verify()


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_recent_rejects_invalid_limits(tmp_path, limit) -> None:
    ledger = EvidenceLedger(str(tmp_path / "ledger.jsonl"))
    with pytest.raises(ValueError):
        ledger.recent(limit)


def test_append_rejects_reserved_hash_fields_and_non_finite_numbers(tmp_path) -> None:
    ledger = EvidenceLedger(str(tmp_path / "ledger.jsonl"))

    with pytest.raises(ValueError, match="reserved"):
        ledger.append({"record_type": "forged", "content_hash": "0" * 64})
    with pytest.raises(ValueError, match="JSON"):
        ledger.append({"record_type": "invalid", "payload": {"value": float("nan")}})
    assert ledger.verify()["entry_count"] == 0


def test_status_reports_integrity_failure_instead_of_ready(tmp_path) -> None:
    path = tmp_path / "ledger.jsonl"
    path.write_text("not-json\n", encoding="utf-8")

    status = EvidenceLedger(str(path)).status()
    assert status["status"] == "INTEGRITY_ERROR"
    assert status["integrity_valid"] is False


class _NoNetworkPubMed:
    def search_treatments(self, *_args, **_kwargs):
        return {"count": 0, "pmids": [], "articles": [], "status": "empty"}


class _LocalGraph:
    def upsert_node(self, node_id, _label, _kind, _properties):
        return {"id": node_id}

    def graph_of_thoughts_stub(self, _seed):
        return {"seed_count": 0}


def test_qrce_orchestrator_appends_safe_metadata_without_patient_context(tmp_path) -> None:
    patient_ref = "local-patient-reference-should-not-be-persisted"
    problem = "synthetic-only research context"
    ledger = EvidenceLedger(str(tmp_path / "qrce-ledger.jsonl"))
    orchestrator = QRCEResearchOrchestrator(
        pubmed=_NoNetworkPubMed(),
        kragen=_LocalGraph(),
        ledger=ledger,
    )

    result = orchestrator.run(patient_ref=patient_ref, disease_or_problem=problem)

    assert result["status"] == "ORCHESTRATION_COMPLETE"
    entry = ledger.recent(1)[0]
    serialized = json.dumps(entry, sort_keys=True)
    assert entry["record_type"] == "qrce_research_search"
    assert patient_ref not in serialized
    assert problem not in serialized
    assert result["packet_hash"] not in serialized
    assert ledger.verify()["valid"] is True


def test_verify_rejects_non_finite_json_constants(tmp_path) -> None:
    path = tmp_path / "ledger.jsonl"
    path.write_text(
        '{"schema_version":2,"previous_hash":"' + "0" * 64
        + '","payload":{"value":NaN},"content_hash":"' + "0" * 64 + '"}\\n',
        encoding="utf-8",
    )

    with pytest.raises(LedgerIntegrityError, match="JSON is invalid"):
        EvidenceLedger(str(path)).verify()
