"""Local HTML swarm contracts: real TCP loopback, same-origin JSON-RPC,
rejection of raw patient input and deterministic synthetic model execution."""
from __future__ import annotations

import json
from pathlib import Path
import socket
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from engines.cube_grover_research import PLANES
from scripts.qrce_swarm_local import (
    Handler, ThreadingHTTPServer, _METHODS, _PAGES, dispatch,
    handle_rpc, _knowledge_status, UI,
)


def request(method, params=None, identity=1):
    return handle_rpc({"jsonrpc": "2.0", "id": identity,
                       "method": method, "params": params or {}})


def test_live_simulator_governance_and_precise_json_rpc_protocol():
    out = request("quantum.grover", {"scenario": "disease"})
    assert out["jsonrpc"] == "2.0" and out["id"] == 1
    assert out["result"]["oracle"]["size"] == 64
    assert out["result"]["governance"]["cure_claim"] is False
    assert out["result"]["execution"]["quantum_hardware_used"] is False
    for payload in [
        {"jsonrpc": "1.0", "id": 1, "method": "lab.synthetic_demo", "params": {}},
        {"jsonrpc": "2.0", "id": "patient-123", "method": "lab.synthetic_demo", "params": {}},
        {"jsonrpc": "2.0", "id": 1, "method": "lab.synthetic_demo"},
        [{"jsonrpc": "2.0", "id": 1, "method": "lab.synthetic_demo", "params": {}}],
    ]:
        assert "error" in handle_rpc(payload)


def test_no_arbitrary_patient_urls_files_or_agent_execution():
    blocked = [
        ("patient.diagnose", {"patient": {"id": "Patient/42"}}),
        ("lab.synthetic_demo", {"patient_name": "Sensitive"}),
        ("swarm.run", {"records": ["private"]}),
        ("governance.review", {"approve_drug": True}),
        ("imaging.synthetic_demo", {"path": "/patient/files"}),
        ("evidence.offline_status", {"url": "https://example.com"}),
        ("quantum.grover", {"scenario": "unapproved"}),
        ("molecular.descriptors", {"smiles": "CCO", "patient_id": "42"}),
        ("fhir.upload", {}),
    ]
    for method, params in blocked:
        assert "error" in request(method, params), method
    assert "patient.diagnose" not in _METHODS


def test_synthetic_lab_and_offline_knowledge_are_explicit():
    lab = request("lab.synthetic_demo")["result"]
    assert lab["status"] == "synthetic_fixture_inspected"
    assert lab["record_count"] == 2
    assert lab["declared_synthetic"] is True
    assert lab["clinical_promotion_allowed"] is False
    knowledge = request("evidence.offline_status")["result"]
    assert knowledge["status"] == "not_installed"
    assert knowledge["wiki_med_content_included"] is False


def test_actual_local_rdkit_and_dicom_are_used_only_when_pinned(monkeypatch):
    # Minimal core CI does not have these optional packages; no fake successes.
    import scripts.qrce_swarm_local as swarm
    def unavailable():
        raise ValueError("optional package absent")
    monkeypatch.setattr(swarm, "_imaging_demo", unavailable)
    result = swarm._swarm_run()
    assert result["nodes"]["imaging"]["state"] == "unavailable"
    assert result["nodes"]["imaging"]["result"] is None
    assert result["clinical_decision_generated"] is False
    assert result["review"]["clinician_review"] == "required"
    assert len(result["receipt_sha256"]) == 64


def test_all_seven_html_nodes_and_no_external_network_assets():
    for page in _PAGES.values():
        assert (UI / page).is_file(), page
        text = (UI / page).read_text(encoding="utf-8")
        if page.endswith(".html"):
            assert 'src="swarm.js"' in text
            assert 'href="swarm.css"' in text
            assert "no patient" in text.lower() or "patient" in text.lower()
            assert "http://" not in text and "https://" not in text
        elif page == "swarm.js":
            assert 'fetch("/rpc"' in text
            assert 'credentials:"omit"' in text
            assert 'mode:"same-origin"' in text
            assert "eval(" not in text
    assert len(set(_PAGES.values())) == 9


def test_loopback_http_jsonrpc_host_origin_and_content_type():
    host = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    host.daemon_threads = True
    thread = Thread(target=host.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{host.server_port}"
    def fetch(path, *, method="GET", body=None, origin=None, host_header=None, content_type=None):
        headers = {}
        if origin:
            headers["Origin"] = origin
        if host_header:
            headers["Host"] = host_header
        if content_type:
            headers["Content-Type"] = content_type
        request_obj = Request(base + path, method=method, data=body, headers=headers)
        try:
            with urlopen(request_obj, timeout=3) as response:
                return response.status, dict(response.headers), response.read()
        except HTTPError as exc:
            return exc.code, dict(exc.headers), exc.read()
    try:
        status, headers, data = fetch("/lab.html")
        assert status == 200 and b'data-node="lab"' in data
        assert headers["Content-Security-Policy"].startswith("default-src 'none'")
        assert headers["Cache-Control"] == "no-store"
        packet = json.dumps({"jsonrpc":"2.0", "id":3, "method":"lab.synthetic_demo", "params":{}}).encode()
        status, _, data = fetch("/rpc", method="POST", body=packet,
                                origin=base, content_type="application/json")
        assert status == 200
        assert json.loads(data)["result"]["record_count"] == 2
        assert fetch("/rpc", method="POST", body=packet,
                     origin="https://malicious.invalid", content_type="application/json")[0] == 403
        assert fetch("/rpc", method="POST", body=packet, content_type="application/json")[0] == 403
        assert fetch("/rpc", method="POST", body=packet, origin=base,
                     content_type="text/plain")[0] == 415
        assert fetch("/rpc", method="POST", body=b"x"*4100, origin=base,
                     content_type="application/json")[0] == 400
        assert fetch("/etc/passwd")[0] == 404
        assert fetch("/lab.html", host_header="example.com")[0] == 403
    finally:
        host.shutdown()
        host.server_close()
        thread.join(timeout=3)
