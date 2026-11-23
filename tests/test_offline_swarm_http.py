"""Actual 127.0.0.1 smoke tests: no internet, patient routes or cloud."""
from __future__ import annotations
import http.client
import json
import threading
import unittest

from scripts.run_offline_swarm import build_server


class SwarmHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = build_server(host="127.0.0.1", port=0)
        cls.port = cls.server.server_address[1]
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=4)

    def call(self, method, path, payload=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=4)
        opts = {"Host": "127.0.0.1:" + str(self.port)}
        opts.update(headers or {})
        body = None if payload is None else json.dumps(payload).encode()
        if body is not None:
            opts.setdefault("Content-Type", "application/json")
            opts.setdefault("X-TMRDS-Local-Only", "synthetic-demo")
        conn.request(method, path, body=body, headers=opts)
        response = conn.getresponse()
        content = response.read()
        result = response.status, dict(response.getheaders()), content
        conn.close()
        return result

    def test_health_and_offline_workspace_static_assets(self):
        code, headers, body = self.call("GET", "/api/local/health")
        data = json.loads(body)
        self.assertEqual(code, 200)
        self.assertFalse(data["external_sources_verified"])
        self.assertEqual(data["mode"], "loopback_only")
        self.assertIn("no-store", headers["Cache-Control"])
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        for path in ("/", "/labs.html", "/imaging.html", "/genomics.html",
                     "/evidence.html", "/quantum.html", "/knowledge.html",
                     "/supervisor.html", "/drug_discovery.html",
                     "/swarm.js", "/swarm.css"):
            code, head, data = self.call("GET", path)
            self.assertEqual(code, 200, path)
            self.assertGreater(len(data), 20)
            self.assertEqual(head["Access-Control-Allow-Origin"] if
                             "Access-Control-Allow-Origin" in head else None, None)

    def test_real_local_synthetic_workflow_returns_all_node_receipts(self):
        code, headers, content = self.call(
            "POST", "/api/local/run", {"scenario": "synthetic_all"},
            {"Origin": f"http://127.0.0.1:{self.port}"})
        self.assertEqual(code, 200)
        data = json.loads(content)
        self.assertFalse(data["network_access_used"])
        self.assertFalse(data["patient_data_accepted"])
        self.assertEqual(data["nodes"]["labs"]["record_count"], 2)
        self.assertEqual(data["nodes"]["genomics"]["record_count"], 1)
        self.assertEqual(data["nodes"]["supervisor"]["status"], "human_review_required")
        self.assertEqual(len(data["events"]), 8)
        self.assertEqual(len(data["receipt_sha256"]), 64)

    def test_only_verified_public_metadata_pack_is_searchable_via_local_citation_post(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from engines.offline_evidence_pack import build_pack, save_pack
        from test_offline_evidence_pack import source
        packet = build_pack(source(), query="CFTR", retrieved_at="2026-11-23T08:00:00+00:00")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "citations.json"
            save_pack(path, packet)
            with patch("engines.offline_specialist_swarm.LOCAL_EVIDENCE_PACK_PATH", path):
                code, head, body = self.call(
                    "POST", "/api/local/evidence-search", {"term": "CFTR"},
                    {"Origin": f"http://127.0.0.1:{self.port}",
                     "X-TMRDS-Local-Only": "public-citation-query"},
                )
                self.assertEqual(code, 200)
                data = json.loads(body)
                self.assertEqual(data["schema_version"], "1.0")
                self.assertEqual(data["match_count"], 1)
                self.assertFalse(data["search_executed_online"])
                self.assertNotIn("patient_id", body.decode())
                code, _, _ = self.call(
                    "POST", "/api/local/evidence-search", {"term": "person@example.org"},
                    {"X-TMRDS-Local-Only": "public-citation-query"},
                )
                self.assertEqual(code, 422)
                code, _, _ = self.call(
                    "POST", "/api/local/evidence-search", {"term": "CFTR"},
                    {"X-TMRDS-Local-Only": "synthetic-demo"},
                )
                self.assertEqual(code, 415)
        code, _, body = self.call(
            "POST", "/api/local/evidence-search", {"term": "CFTR"},
            {"X-TMRDS-Local-Only": "public-citation-query"},
        )
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["status"], "offline_source_not_installed")

    def test_reject_cross_origin_patient_body_and_invalid_routes(self):
        cases = [
            ("POST", "/api/local/run", {"scenario": "synthetic_all"},
             {"Origin": "https://example.org"}, 403),
            ("POST", "/api/local/run", {"scenario": "synthetic_all", "patient_id": "secret"},
             {}, 422),
            ("POST", "/api/local/run", {"scenario": "synthetic_all"},
             {"X-TMRDS-Local-Only": "something-else"}, 415),
            ("GET", "/api/local/ingest", None, {}, 404),
            ("GET", "/../../etc/passwd", None, {}, 404),
            ("GET", "/api/local/run?scenario=synthetic_all", None, {}, 404),
            ("GET", "/api/local/health", None, {"Host": "another-host:9000"}, 403),
        ]
        for method, path, payload, headers, want in cases:
            with self.subTest(path=path, headers=headers):
                code, _head, _body = self.call(method, path, payload, headers)
                self.assertEqual(code, want)


if __name__ == "__main__":
    unittest.main()
