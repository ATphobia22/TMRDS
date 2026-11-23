"""Test-first: air-gapped TMRDS specialist HTML swarm, synthetic only."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

from engines.offline_specialist_swarm import (
    NODES, SCENARIOS, capability_manifest, run_offline_case, validate_scenario,
)
from scripts.run_offline_swarm import OfflineSwarmHandler, build_server

ROOT = Path(__file__).resolve().parents[1]


class OfflineSwarmTests(unittest.TestCase):
    def test_real_local_agent_chain_returns_source_scoped_actions_not_diagnoses(self):
        result = run_offline_case("synthetic_all")
        self.assertEqual(result["schema_version"], "1.0")
        self.assertEqual(result["input_class"], "built_in_synthetic_fixture_only")
        self.assertTrue(result["offline"])
        self.assertEqual(set(result["nodes"]), set(NODES))
        self.assertEqual(result["nodes"]["labs"]["status"], "synthetic_fixture_inspected")
        self.assertEqual(result["nodes"]["genomics"]["status"], "synthetic_fixture_inspected")
        self.assertEqual(result["nodes"]["quantum"]["status"], "simulated_research_plan")
        self.assertEqual(result["nodes"]["imaging"]["status"], "requires_approved_local_reader")
        self.assertEqual(result["nodes"]["drug_discovery"]["status"], "not_executed")
        self.assertEqual(result["nodes"]["knowledge"]["status"], "external_archive_not_bundled")
        self.assertEqual(result["nodes"]["supervisor"]["status"], "human_review_required")
        self.assertFalse(result["patient_data_accepted"])
        self.assertFalse(result["network_access_used"])
        self.assertFalse(result["clinical_inference_performed"])
        self.assertFalse(result["treatment_recommended"])
        self.assertEqual(len(result["receipt_sha256"]), 64)
        self.assertEqual(len(result["events"]), len(NODES))
        self.assertEqual(len({event["event_id"] for event in result["events"]}), len(NODES))
        for e in result["events"]:
            self.assertEqual(e["channel"], "tmrds.offline.node.v1")
            self.assertEqual(e["data_class"], "synthetic_nonidentifying")
            self.assertTrue(e["result_sha256"])
        self.assertNotIn("patient_ref", json.dumps(result))

    def test_network_and_heavy_clinical_modules_not_falsely_enabled(self):
        manifest = capability_manifest()
        self.assertEqual(manifest["mode"], "loopback_only")
        self.assertTrue(manifest["offline"])
        self.assertFalse(manifest["public_patient_upload_enabled"])
        self.assertFalse(manifest["openmi_2_conformance"])
        self.assertFalse(manifest["quantum_hardware_enabled"])
        self.assertFalse(manifest["clinical_model_weights_bundled"])
        for module in ("orthanc", "monai", "kiwix", "alphafold3", "openelis"):
            self.assertNotEqual(manifest["optional_integrations"][module], "installed_and_verified")
        self.assertTrue(manifest["human_authority_final"])

    def test_fixed_scenarios_and_no_personal_data_arguments(self):
        self.assertEqual(set(SCENARIOS), {"synthetic_all", "synthetic_lab", "synthetic_genomics"})
        for value in ("../secrets", "john@example.org", "", "patient-123", None, 7, "synthetic_all/../"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_scenario(value)
        with self.assertRaises(TypeError):
            run_offline_case("synthetic_all", patient_id="123")
        for scenario in SCENARIOS:
            result = run_offline_case(scenario)
            self.assertEqual(result["scenario"], scenario)

    def test_deterministic_receipt_and_simulated_quantum_math(self):
        first = run_offline_case("synthetic_all")
        second = run_offline_case("synthetic_all")
        self.assertEqual(first["receipt_sha256"], second["receipt_sha256"])
        self.assertEqual(first["nodes"]["quantum"]["algorithm"], "grover_phase_oracle_and_diffusion")
        self.assertFalse(first["nodes"]["quantum"]["quantum_hardware_used"])
        self.assertFalse(first["nodes"]["quantum"]["probability_is_clinical"])

    def test_local_server_rejects_non_loopback_bind_and_path_escape(self):
        with self.assertRaises(ValueError):
            build_server(host="0.0.0.0", port=0)
        with self.assertRaises(ValueError):
            build_server(host="localhost", port=0)
        for path in ("/../../etc/passwd", "/api/local/ingest", "/clinical/patient", "/api/local/ehr"):
            self.assertNotIn(path, OfflineSwarmHandler.ALLOWED_GET_PATHS)
        self.assertEqual(OfflineSwarmHandler.ALLOWED_POST_PATHS, {"/api/local/run", "/api/local/evidence-search"})

    def test_offline_html_swarm_has_real_specialist_pages_and_no_external_runtime_scripts(self):
        root = ROOT / "offline" / "swarm"
        pages = ["index", "labs", "imaging", "genomics", "evidence", "drug_discovery", "quantum", "knowledge", "supervisor"]
        for page in pages:
            text = (root / (page + ".html")).read_text(encoding="utf8")
            self.assertIn('src="swarm.js"', text)
            self.assertIn('href="swarm.css"', text)
            self.assertNotIn("https://", text)
            self.assertNotIn("http://", text)
            self.assertIn('data-node=', text)
        js = (root / "swarm.js").read_text(encoding="utf8")
        self.assertIn("/api/local/run", js)
        self.assertIn("/api/local/capabilities", js)
        self.assertNotIn("localStorage", js)
        self.assertNotIn("WebSocket(", js)
        self.assertNotIn("eval(", js)
        self.assertNotIn("fetch('https:", js)
        self.assertTrue((root / "contracts" / "openapi.yaml").exists())
        self.assertTrue((root / "contracts" / "event.schema.json").exists())


if __name__ == "__main__":
    unittest.main()
