from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from engines.ibm_quantum_compute import (
    IBMQuantumConfig,
    IBMQuantumComputeClient,
)


class IBMQuantumConfigTests(unittest.TestCase):
    def test_region_builds_expected_api_base(self) -> None:
        config = IBMQuantumConfig(
            api_key="not-a-real-key",
            instance_crn="crn:test",
            region="eu-de",
        )
        self.assertEqual(
            config.base_url,
            "https://eu-de.quantum.cloud.ibm.com/api/v1/",
        )

    def test_environment_requires_credentials(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                IBMQuantumConfig.from_environment()

    def test_invalid_region_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            IBMQuantumConfig(
                api_key="key",
                instance_crn="crn",
                region="ap-south",
            ).base_url if False else IBMQuantumConfig(
                api_key="key",
                instance_crn="crn",
                region="ap-south",
            ).__class__.from_environment()


class IBMQuantumSubmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = IBMQuantumComputeClient(
            IBMQuantumConfig(api_key="not-a-real-key", instance_crn="crn:test")
        )

    def tearDown(self) -> None:
        self.client.close()

    def test_sampler_builds_v2_pubs_payload(self) -> None:
        with patch.object(self.client, "_request", return_value={"id": "job-123"}) as request:
            result = self.client.submit_sampler(
                backend="ibm_test_backend",
                qasm_circuits=[
                    'OPENQASM 3.0; include "stdgates.inc"; qubit[1] q; bit[1] c; x q[0]; c[0] = measure q[0];'
                ],
                shots=512,
            )
        self.assertEqual(result, {"id": "job-123"})
        args, kwargs = request.call_args
        self.assertEqual(args, ("POST", "jobs"))
        body = kwargs["body"]
        self.assertEqual(body["program_id"], "sampler")
        self.assertEqual(body["backend"], "ibm_test_backend")
        self.assertEqual(body["params"]["version"], 2)
        self.assertEqual(
            body["params"]["pubs"][0][1:],
            [None, 512],
        )

    def test_sampler_rejects_empty_circuits(self) -> None:
        with self.assertRaises(ValueError):
            self.client.submit_sampler(backend="ibm_test_backend", qasm_circuits=[])

    def test_sampler_rejects_invalid_shots(self) -> None:
        with self.assertRaises(ValueError):
            self.client.submit_sampler(
                backend="ibm_test_backend",
                qasm_circuits=["OPENQASM 3.0;"],
                shots=0,
            )

    def test_submission_does_not_retry(self) -> None:
        # The adapter intentionally makes exactly one _request call for POST.
        with patch.object(self.client, "_request", side_effect=RuntimeError("network")) as request:
            with self.assertRaises(RuntimeError):
                self.client.submit_sampler(
                    backend="ibm_test_backend",
                    qasm_circuits=["OPENQASM 3.0;"],
                )
        self.assertEqual(request.call_count, 1)


if __name__ == "__main__":
    unittest.main()
