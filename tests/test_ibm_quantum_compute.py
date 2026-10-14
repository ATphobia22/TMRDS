import unittest
from unittest.mock import patch

from engines.ibm_quantum_compute import IBMQuantumConfig, IBMQuantumComputeClient


class IBMQuantumTests(unittest.TestCase):
    def setUp(self):
        self.client = IBMQuantumComputeClient(
            IBMQuantumConfig(api_key="key", instance_crn="crn:test")
        )

    def tearDown(self):
        self.client.close()

    def test_region(self):
        config = IBMQuantumConfig(api_key="key", instance_crn="crn:test", region="eu-de")
        self.assertEqual(config.base_url, "https://eu-de.quantum.cloud.ibm.com/api/v1/")

    def test_invalid_region(self):
        with self.assertRaises(ValueError):
            IBMQuantumConfig(api_key="key", instance_crn="crn:test", region="invalid")

    def test_sampler_payload(self):
        with patch.object(self.client, "_request", return_value={"id": "job-123"}) as request:
            result = self.client.submit_sampler(
                backend="backend", qasm_circuits=["OPENQASM 3.0;"], shots=512
            )
        self.assertEqual(result, {"id": "job-123"})
        self.assertEqual(
            request.call_args.kwargs["body"]["params"]["pubs"][0][1:],
            [None, 512],
        )

    def test_sampler_rejects_more_than_eight_tags(self):
        with self.assertRaisesRegex(ValueError, "at most 8"):
            self.client.submit_sampler(
                backend="backend",
                qasm_circuits=["OPENQASM 3.0;"],
                tags=[f"tag-{index}" for index in range(9)],
            )

    def test_sampler_rejects_tag_longer_than_api_limit(self):
        with self.assertRaisesRegex(ValueError, "86 characters"):
            self.client.submit_sampler(
                backend="backend",
                qasm_circuits=["OPENQASM 3.0;"],
                tags=["x" * 87],
            )

    def test_instance_details_uses_documented_endpoint(self):
        with patch.object(self.client, "_request", return_value={"plan_id": "test"}) as request:
            result = self.client.get_instance_details()
        self.assertEqual(result, {"plan_id": "test"})
        request.assert_called_once_with("GET", "instance")


if __name__ == "__main__":
    unittest.main()
