"""Offline evidence pack contracts: original IDs, rights, integrity, no-cloud searching."""
from __future__ import annotations
import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from engines.offline_evidence_pack import (
    EvidencePackError, build_pack, load_pack, save_pack, search_pack,
)


def source():
    return {
        "schema_version": "1.0", "query": "CFTR",
        "status": "records_retrieved",
        "source_status": {
            "pubmed": {"state": "responding", "records_returned": 1},
            "chembl": {"state": "source_unavailable", "records_returned": 0},
        },
        "source_licensing": {
            "pubmed": {"metadata_display_allowed": True, "bulk_redistribution_allowed": False},
            "chembl": {"metadata_display_allowed": True, "bulk_redistribution_allowed": False},
        },
        "groups": [{
            "source_records": [{
                "source": "pubmed", "stable_id": "pubmed:38718835",
                "title": "CFTR protein research and cystic fibrosis",
                "pmid": "38718835", "doi": "10.1000/example",
                "published": "2024", "source_url": "https://pubmed.ncbi.nlm.nih.gov/38718835/",
                "abstract": "full text SHALL NOT be stored",
                "patient_id": "SHALL NOT LEAK",
            }]
        }],
    }


class OfflineEvidencePackTests(unittest.TestCase):
    def test_build_search_and_save_are_deterministic_metadata_only(self):
        payload = source()
        a = build_pack(payload, query="CFTR", retrieved_at="2026-11-23T08:00:00+00:00")
        b = build_pack(payload, query="CFTR", retrieved_at="2026-11-23T08:00:00+00:00")
        self.assertEqual(a, b)
        self.assertEqual(a["record_count"], 1)
        self.assertEqual(len(a["pack_sha256"]), 64)
        self.assertFalse(a["clinical_promotion_allowed"])
        self.assertFalse(a["full_text_included"])
        self.assertFalse(a["patient_data_included"])
        self.assertEqual(a["source_status"]["chembl"], "source_unavailable")
        blob = json.dumps(a)
        self.assertNotIn("SHALL NOT", blob)
        self.assertNotIn("patient_id", blob)
        self.assertNotIn("abstract", blob)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "evidence-pack.json"
            save_pack(path, a)
            restored = load_pack(path)
            self.assertEqual(restored["pack_sha256"], a["pack_sha256"])
            found = search_pack(restored, "CFTR", as_of="2026-12-01")
            self.assertEqual(found["match_count"], 1)
            self.assertEqual(found["matches"][0]["pmid"], "38718835")
            self.assertFalse(found["search_executed_online"])
            self.assertTrue(found["coverage_partial"])
            self.assertEqual(search_pack(restored, "nonexistent", as_of="2026-12-01")["match_count"], 0)
            with self.assertRaises(EvidencePackError):
                save_pack(path, a)

    def test_reject_unlicensed_missing_provenance_or_personal_query(self):
        for mutation in [
            lambda x: x["source_licensing"]["pubmed"].update(metadata_display_allowed=False),
            lambda x: x["source_licensing"]["pubmed"].update(bulk_redistribution_allowed=True),
            lambda x: x["groups"][0]["source_records"][0].update(stable_id="wrong-source:000"),
            lambda x: x["groups"][0]["source_records"][0].update(source="not-reviewed"),
            lambda x: x.update(query="not-the-requested-term"),
        ]:
            data = source()
            mutation(data)
            with self.subTest(data=data), self.assertRaises(EvidencePackError):
                build_pack(data, query="CFTR", retrieved_at="2026-11-23T08:00:00+00:00")
        for personal in ("patient@example.com", "123-45-6789", "Patient/123"):
            with self.assertRaises(EvidencePackError):
                build_pack(source(), query=personal, retrieved_at="2026-11-23T08:00:00+00:00")

    def test_reject_tampering_symlinks_stale_invalid_dates_and_private_record_fields(self):
        pack = build_pack(source(), query="CFTR", retrieved_at="2026-11-23T08:00:00+00:00")
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "pack.json"
            save_pack(p, pack)
            stale = search_pack(load_pack(p), "CFTR", as_of="2027-05-01")
            self.assertEqual(stale["freshness"], "stale")
            self.assertFalse(stale["current_source_freshness_verified"])
            tampered = copy.deepcopy(pack)
            tampered["records"][0]["title"] = "FORGED"
            p.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaises(EvidencePackError):
                load_pack(p)
            p.unlink()
            alias = Path(temp) / "alias.json"
            alias.symlink_to(Path(temp) / "other.json")
            with self.assertRaises(EvidencePackError):
                load_pack(alias)
        with self.assertRaises(EvidencePackError):
            build_pack(source(), query="CFTR", retrieved_at="not-a-date")


    def test_installed_pack_is_usable_by_offline_specialist_cube_without_network(self):
        from unittest.mock import patch
        from engines.offline_specialist_swarm import run_offline_case
        pack = build_pack(source(), query="CFTR", retrieved_at="2026-11-23T08:00:00+00:00")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "citations.json"
            save_pack(path, pack)
            with patch("engines.offline_specialist_swarm.LOCAL_EVIDENCE_PACK_PATH", path):
                result = run_offline_case("synthetic_all")
            evidence = result["nodes"]["evidence"]
            self.assertEqual(evidence["status"], "offline_metadata_pack_verified")
            self.assertEqual(evidence["indexed_publications"], 1)
            self.assertEqual(evidence["pack_sha256"], pack["pack_sha256"])
            self.assertFalse(evidence["clinical_guidance_inferred"])
            self.assertFalse(result["network_access_used"])
            self.assertEqual(result["input_class"], "built_in_synthetic_fixture_plus_verified_public_citation_metadata")
            self.assertEqual(
                next(event for event in result["events"] if event["node"] == "evidence")["data_class"],
                "public_citation_metadata",
            )


if __name__ == "__main__":
    unittest.main()
