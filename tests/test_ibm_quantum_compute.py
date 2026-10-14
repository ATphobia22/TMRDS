import unittest
from unittest.mock import patch
from engines.ibm_quantum_compute import IBMQuantumConfig, IBMQuantumComputeClient

class IBMQuantumTests(unittest.TestCase):
    def test_region(self):
        config = IBMQuantumConfig(api_key="key", instance_crn="crn:test", region="eu-de")
        self.assertEqual(config.base_url, "https://eu-de.quantum.cloud.ibm.com/api/v1/")

    def test_invalid_region(self):
        with self.assertRaises(ValueError):
            IBMQuantumConfig(api_key="key", instance_crn="crn:test", region="invalid")

    def test_sampler_payload(self):
        client = IBMQuantumComputeClient(IBMQuantumConfig(api_key="key", instance_crn="crn:test"))
        try:
            with patch.object(client, "_request", return_value={"id": "job-123"}) as request:
                result = client.submit_sampler(backend="backend", qasm_circuits=["OPENQASM 3.0;"], shots=512)
            self.assertEqual(result, {"id": "job-123"})
            self.assertEqual(request.call_args.kwargs["body"]["params"]["pubs"][0][1:], [None, 512])
        finally:
            client.close()

if __name__ == "__main__":
    unittest.main()
