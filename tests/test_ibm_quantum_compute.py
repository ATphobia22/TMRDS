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


    def test_invalid_shots_rejected_before_request(self):
        for shots in (0, -1, 10_000_001, True, 1.5):
            with self.subTest(shots=shots), self.assertRaises(ValueError):
                self.client.submit_sampler(
                    backend="backend", qasm_circuits=["OPENQASM 3.0;"], shots=shots
                )

    def test_empty_circuits_rejected_before_request(self):
        for circuits in ([], [""], ["  "], [None]):
            with self.subTest(circuits=circuits), self.assertRaises(ValueError):
                self.client.submit_sampler(backend="backend", qasm_circuits=circuits)

    def test_unsafe_api_paths_are_rejected(self):
        for path in ("/jobs", "../jobs", "jobs/../instance", "jobs/."):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.client._request("GET", path)

    def test_job_id_is_validated(self):
        for method in (self.client.get_job, self.client.get_job_results):
            for job_id in ("", "a/b", "x" * 257):
                with self.subTest(method=method.__name__, job_id=job_id), self.assertRaises(ValueError):
                    method(job_id)

    def test_environment_timeout_must_be_numeric(self):
        with patch.dict("os.environ", {
            "IBM_QUANTUM_API_KEY": "key",
            "IBM_QUANTUM_INSTANCE_CRN": "crn:test",
            "IBM_QUANTUM_TIMEOUT_SECONDS": "not-a-number",
        }, clear=True):
            with self.assertRaisesRegex(ValueError, "must be numeric"):
                IBMQuantumConfig.from_environment()

    def test_sampler_submission_does_not_retry_post(self):
        from unittest.mock import Mock
        import requests
        from engines.ibm_quantum_compute import IBMQuantumError

        response = Mock()
        response.status_code = 503
        response.close = Mock()
        self.client._get_token = Mock(return_value="test-token")
        self.client._session.request = Mock(return_value=response)
        with self.assertRaisesRegex(IBMQuantumError, "HTTP 503"):
            self.client.submit_sampler(backend="backend", qasm_circuits=["OPENQASM 3.0;"])
        self.client._session.request.assert_called_once()
        self.assertEqual(self.client._session.request.call_args.args[0], "POST")

    def test_read_only_get_refreshes_token_once_after_401(self):
        from unittest.mock import Mock
        self.client._get_token = Mock(side_effect=["expired-token", "fresh-token"])
        first = Mock(status_code=401)
        first.close = Mock()
        second = Mock(status_code=200)
        second.json.return_value = {"backends": []}
        second.close = Mock()
        self.client._session.request = Mock(return_value=first)
        self.client._session.get = Mock(return_value=second)
        result = self.client.list_backends()
        self.assertEqual(result, {"backends": []})
        self.client._session.get.assert_called_once()
        self.assertEqual(self.client._session.get.call_args.kwargs["headers"]["Authorization"], "Bearer fresh-token")



    def test_request_uses_cloud_compute_api_contract_headers(self):
        from unittest.mock import Mock

        self.client._get_token = Mock(return_value="test-token")
        response = Mock(status_code=200)
        response.json.return_value = {"ok": True}
        response.close = Mock()
        self.client._session.request = Mock(return_value=response)

        self.assertEqual(self.client.get_instance_details(), {"ok": True})
        args, kwargs = self.client._session.request.call_args
        self.assertEqual(args[:2], ("GET", "https://quantum.cloud.ibm.com/api/v1/instance"))
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-token")
        self.assertEqual(kwargs["headers"]["Service-CRN"], "crn:test")
        self.assertEqual(kwargs["headers"]["IBM-API-Version"], "2026-04-15")
        self.assertFalse(kwargs["allow_redirects"])

if __name__ == "__main__":
    unittest.main()
