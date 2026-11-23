"""Offline mathematical and no-PHI contract tests of the six-plane Grover simulator."""
from __future__ import annotations
import unittest

from engines.cube_grover_research import PLANES, simulate_grover_research_plan


class CubeGroverTests(unittest.TestCase):
    def test_actual_oracle_and_diffuser_amplify_valid_coverage_plans(self):
        data = simulate_grover_research_plan()
        self.assertEqual(data["oracle"]["size"], 64)
        self.assertEqual(data["oracle"]["marked_states"], 4)
        self.assertGreater(data["simulated_probability_of_valid_plan"], 0.9)
        self.assertEqual(data["uniform_random_baseline_probability"], 0.0625)
        self.assertLess(data["normalization_error"], 1e-10)
        for plan in data["example_marked_plans"]:
            self.assertEqual(len(plan["bitstring"]), 6)
            self.assertIn("disease_phenotype", plan["planes"])
            self.assertIn("trials_labels", plan["planes"])
            self.assertIn("target_pathway", plan["planes"])
            self.assertLessEqual(len(plan["planes"]), 4)

    def test_deterministic_digest_and_no_claimed_speedup(self):
        a = simulate_grover_research_plan()
        self.assertEqual(a, simulate_grover_research_plan())
        self.assertEqual(len(a["oracle_sha256"]), 64)
        self.assertIsNone(a["measured_speedup"])
        self.assertFalse(a["simulated_quantum_advantage_claimed"])

    def test_unique_marked_six_plane_state(self):
        data = simulate_grover_research_plan(required=PLANES, max_planes=6)
        self.assertEqual(data["oracle"]["marked_states"], 1)
        self.assertGreater(data["simulated_probability_of_valid_plan"], 0.9)
        self.assertEqual(data["example_marked_plans"][0]["bitstring"], "111111")

    def test_reject_malformed_constraints(self):
        invalid = [
            {"required": ()}, {"required": ("disease_phenotype", "disease_phenotype")},
            {"required": ("not_a_source",)}, {"required": ["disease_phenotype"]},
            {"required": PLANES, "max_planes": 5}, {"max_planes": 7},
            {"max_planes": True},
        ]
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(ValueError):
                simulate_grover_research_plan(**values)

    def test_no_patient_biology_or_hardware_inference(self):
        data = simulate_grover_research_plan()
        self.assertTrue(data["governance"]["human_authority_final"])
        self.assertFalse(data["governance"]["clinical_promotion_allowed"])
        self.assertFalse(data["governance"]["cure_claim"])
        self.assertFalse(data["execution"]["quantum_hardware_used"])
        self.assertFalse(data["execution"]["source_data_queried"])
        self.assertFalse(data["execution"]["patient_data_ingested"])
        self.assertFalse(data["execution"]["sparse_blossom_used"])

    def test_public_get_endpoint_and_write_denial(self):
        from fastapi.testclient import TestClient
        from api.public_gateway import app
        with TestClient(app) as client:
            good = client.get("/api/v1/research/cube-search")
            self.assertEqual(good.status_code, 200)
            self.assertEqual(good.json()["algorithm"], "grover_phase_oracle_and_diffusion")
            invalid = [
                {"required": "patient_data"},
                {"required": "disease_phenotype,disease_phenotype"},
                {"required": "structure,not_a_plane"},
                {"required": "disease_phenotype,target_pathway", "max_planes": "1"},
            ]
            for params in invalid:
                with self.subTest(params=params):
                    self.assertEqual(client.get("/api/v1/research/cube-search", params=params).status_code, 422)
            self.assertEqual(client.post("/api/v1/research/cube-search").status_code, 405)
