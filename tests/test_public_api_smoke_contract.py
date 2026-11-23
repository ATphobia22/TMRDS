"""Offline contract tests for the public HTTPS service smoke monitor."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.check_deployed_research_api import (
    BASE_URL, assess_payloads, fetch_json, run_smoke,
)


def sample():
    return {
        "/health/ready": {"status": "ready", "external_sources_verified": False},
        "/backend-config.json": {"api_mode": "same-origin"},
        "/api/v1/research/medical-projects?category=genomics": {
            "count": 19, "clinical_promotion_allowed": False,
            "all_platforms_installed": False, "license_approvals_completed": False,
        },
        "/api/v1/research/file-format-capabilities": {
            "mode": "local_synthetic_only",
            "patient_data_ingestion_enabled": False,
            "public_patient_upload_enabled": False,
        },
        "/api/v1/research/alphafold3-status": {
            "status": "not_configured",
            "model_parameters_bundled": False, "inference_submitted": False,
        },
    }


class SmokeContracts(unittest.TestCase):
    def test_exact_nonclinical_contract(self):
        result = assess_payloads(sample())
        self.assertEqual(result["status"], "research_service_ready")
        self.assertEqual(result["genomics_reference_count"], 19)
        self.assertTrue(result["source_health_not_verified"])
        self.assertFalse(result["alphafold3_inference_enabled"])

    def test_reject_false_patient_and_model_claims(self):
        for key, bad_value in [
            ("/health/ready", {"status": "ready", "external_sources_verified": True}),
            ("/backend-config.json", {"api_mode": "disabled"}),
            ("/api/v1/research/file-format-capabilities",
             {"mode": "public", "patient_data_ingestion_enabled": True,
              "public_patient_upload_enabled": True}),
            ("/api/v1/research/alphafold3-status",
             {"status": "ready", "model_parameters_bundled": True, "inference_submitted": True}),
        ]:
            with self.subTest(key=key):
                data = sample()
                data[key] = bad_value
                with self.assertRaises(ValueError):
                    assess_payloads(data)

    def test_missing_sources_or_catalog_regression_are_fatal(self):
        with self.assertRaises(KeyError):
            assess_payloads({})
        data = sample()
        data["/api/v1/research/medical-projects?category=genomics"]["count"] = 0
        with self.assertRaises(ValueError):
            assess_payloads(data)

    def test_receipt_scoped_hash_and_fixed_host_from_mock_data(self):
        with patch("scripts.check_deployed_research_api.fetch_json",
                   side_effect=lambda path: sample()[path]) as getter:
            result = run_smoke()
        self.assertEqual(result["source_url"], BASE_URL)
        self.assertEqual(getter.call_count, 5)
        self.assertEqual(len(result["sha256"]), 64)
        self.assertEqual(result["sha256_scope"],
                         "receipt_fields_before_hash_not_raw_remote_responses")

    def test_fixed_path_restrictions(self):
        for invalid in ("https://malicious.example/", "//fake", "/../secrets", "/x#frag", "/api/@me"):
            with self.subTest(path=invalid):
                with self.assertRaises(ValueError):
                    fetch_json(invalid)


if __name__ == "__main__":
    unittest.main()
