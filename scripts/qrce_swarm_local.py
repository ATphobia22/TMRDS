"""Loopback-only offline research nodes speaking bounded JSON-RPC 2.0 over HTTP.

No WebSockets, remote agents, patient uploads, arbitrary file paths, subprocess
execution or networking. This reference swarm uses *actual* locally installed
research readers and deterministic synthetic fixtures, not diagnoses.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import sys
from typing import Any
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engines.offline_workstation_adapters import (
    OfflineWorkstationError, capability_report, molecule_descriptors,
)
from engines.cube_grover_research import simulate_grover_research_plan
from engines.qrce_research_formats import inspect_synthetic_fixture

UI = Path(__file__).resolve().parents[1] / "deploy" / "offline" / "swarm"
MAX_MESSAGE = 4096
_METHODS = frozenset({
    "swarm.capabilities", "swarm.run", "lab.synthetic_demo",
    "imaging.synthetic_demo", "molecular.descriptors",
    "quantum.grover", "evidence.offline_status", "governance.review",
})
_PAGES = {
    "/": "index.html", "/index.html": "index.html", "/lab.html": "lab.html",
    "/imaging.html": "imaging.html", "/molecular.html": "molecular.html",
    "/quantum.html": "quantum.html", "/evidence.html": "evidence.html",
    "/review.html": "review.html", "/swarm.js": "swarm.js",
    "/swarm.css": "swarm.css",
}
_SCENARIOS = {
    "disease": (("disease_phenotype", "target_pathway", "trials_labels"), 4),
    "chemistry": (("target_pathway", "structure", "molecule"), 4),
    "complete": (("disease_phenotype", "target_pathway", "structure", "molecule",
                  "trials_labels", "population_equity"), 6),
}
_LAB_FIXTURE = b"code,value,unit\n718-7,13.4,g/dL\n777-3,40,10*9/L\n"


def _imaging_demo() -> dict[str, Any]:
    """Use actual pydicom+NumPy library to decode a tiny in-memory MR image."""
    from engines.offline_workstation_adapters import _require
    _require("dicom")
    import numpy as np
    from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
    from pydicom.uid import MRImageStorage, ExplicitVRLittleEndian, generate_uid
    from pydicom import dcmread
    meta = FileMetaDataset()
    meta.MediaStorageSOPClassUID = MRImageStorage
    meta.MediaStorageSOPInstanceUID = generate_uid()
    meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds = FileDataset(None, {}, file_meta=meta, preamble=b"\x00" * 128)
    ds.SOPClassUID = MRImageStorage
    ds.SOPInstanceUID = meta.MediaStorageSOPInstanceUID
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.Modality = "MR"
    ds.Rows, ds.Columns = 4, 4
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated, ds.BitsStored = 16, 12
    ds.HighBit, ds.PixelRepresentation = 11, 0
    ds.PixelData = np.arange(16, dtype="<u2").tobytes()
    buffer = io.BytesIO()
    ds.save_as(buffer, enforce_file_format=True)
    buffer.seek(0)
    decoded = np.asarray(dcmread(buffer).pixel_array)
    return {
        "source": "generated_in_memory_synthetic_mr", "reader": "pydicom",
        "rows": int(decoded.shape[0]), "columns": int(decoded.shape[1]),
        "pixels": int(decoded.size), "min": int(decoded.min()),
        "max": int(decoded.max()), "diagnostic_interpretation": False,
        "clinical_accuracy_verified": False, "patient_records_used": False,
    }


def _lab_demo() -> dict[str, Any]:
    out = inspect_synthetic_fixture(
        suffix=".csv", data=_LAB_FIXTURE, explicitly_synthetic=True)
    out["source"] = "hardcoded_synthetic_fixture"
    return out


def _molecular_demo(smiles: str = "CCO") -> dict[str, Any]:
    value = molecule_descriptors(smiles)
    value["source"] = "local_rdkit_calculation"
    return value


def _quantum_demo(scenario: str = "disease") -> dict[str, Any]:
    if scenario not in _SCENARIOS:
        raise OfflineWorkstationError("Unknown bounded research-plan scenario")
    required, max_planes = _SCENARIOS[scenario]
    return simulate_grover_research_plan(required=required, max_planes=max_planes)


def _knowledge_status() -> dict[str, Any]:
    return {
        "source": "offline_knowledge_pack_registry",
        "status": "not_installed", "wiki_med_content_included": False,
        "pubmed_fulltext_included": False, "licensed_snapshots_available": False,
        "external_readers": [
            {"name": "Kiwix and WikiMed ZIM", "state": "external_install_required",
             "official_url": "https://kiwix.org/"},
        ],
        "warning": "Internet-disconnected worldwide research search is not possible without a licensed local corpus.",
    }


def _review_status() -> dict[str, Any]:
    return {
        "human_authority_final": True,
        "clinical_decision": "not_performed",
        "diagnosis": "not_generated",
        "treatment_recommendation": "not_generated",
        "scientific_validation": "not_established",
        "clinician_review": "required",
        "research_only": True,
        "note": "Swarm mathematical and synthetic checks do not establish clinical validity.",
    }


def _swarm_run() -> dict[str, Any]:
    """Independent, bounded tools run concurrently; no prompt-based 'agents' or PHI."""
    tasks = {
        "lab": _lab_demo,
        "imaging": _imaging_demo,
        "molecular": _molecular_demo,
        "quantum": _quantum_demo,
        "evidence": _knowledge_status,
    }
    results = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {name: pool.submit(func) for name, func in tasks.items()}
        for name, future in futures.items():
            try:
                results[name] = {"state": "completed", "result": future.result(timeout=8)}
            except Exception:
                results[name] = {
                    "state": "unavailable", "result": None,
                    "reason": "Local dependency or operation unavailable; no synthetic result invented",
                }
    canonical = json.dumps(
        {name: entry["state"] for name, entry in sorted(results.items())},
        sort_keys=True, separators=(",", ":")).encode()
    return {
        "schema": "tmrds.swarm.v1", "workflow": "parallel_synthetic_research_demo",
        "nodes": results,
        "completed": sum(v["state"] == "completed" for v in results.values()),
        "node_count": len(results),
        "receipt_sha256": hashlib.sha256(canonical).hexdigest(),
        "receipt_scope": "node_execution_states_not_original_data",
        "patient_data_ingested": False, "clinical_decision_generated": False,
        "clinical_validation_completed": False, "review": _review_status(),
    }


def dispatch(method: str, params: dict[str, Any]) -> dict[str, Any]:
    """Keep every accepted action narrowly typed and side-effect-free."""
    if method not in _METHODS or not isinstance(params, dict):
        raise OfflineWorkstationError("Unapproved method or parameter type")
    if method == "molecular.descriptors":
        if set(params) != {"smiles"}:
            raise OfflineWorkstationError("SMILES is the only accepted molecule field")
        return _molecular_demo(params["smiles"])
    if method == "quantum.grover":
        if set(params) != {"scenario"}:
            raise OfflineWorkstationError("Only preset quantum research scenarios accepted")
        return _quantum_demo(params["scenario"])
    if params:
        raise OfflineWorkstationError("This node accepts no raw input or patient data")
    if method == "swarm.capabilities":
        return capability_report()
    if method == "swarm.run":
        return _swarm_run()
    if method == "lab.synthetic_demo":
        return _lab_demo()
    if method == "imaging.synthetic_demo":
        return _imaging_demo()
    if method == "evidence.offline_status":
        return _knowledge_status()
    return _review_status()


def handle_rpc(message: Any) -> dict[str, Any]:
    """A deterministic subset of JSON-RPC 2.0; notifications are not enabled."""
    if not isinstance(message, dict) or set(message) != {"jsonrpc", "id", "method", "params"}:
        return {"jsonrpc": "2.0", "id": None,
                "error": {"code": -32600, "message": "Invalid request envelope"}}
    identifier = message["id"]
    if type(identifier) is not int or not 0 <= identifier <= 1_000_000:
        return {"jsonrpc": "2.0", "id": None,
                "error": {"code": -32600, "message": "Invalid request identifier"}}
    if message["jsonrpc"] != "2.0" or not isinstance(message["method"], str):
        return {"jsonrpc": "2.0", "id": identifier,
                "error": {"code": -32600, "message": "Invalid JSON-RPC protocol"}}
    try:
        return {"jsonrpc": "2.0", "id": identifier,
                "result": dispatch(message["method"], message["params"])}
    except OfflineWorkstationError:
        return {"jsonrpc": "2.0", "id": identifier,
                "error": {"code": -32602, "message": "Method or parameters not permitted"}}
    except Exception:
        return {"jsonrpc": "2.0", "id": identifier,
                "error": {"code": -32001, "message": "Local scientific adapter unavailable"}}


class Handler(BaseHTTPRequestHandler):
    server_version = "TMRDS-offline-research"
    sys_version = ""

    def log_message(self, format: str, *args: Any) -> None:
        # No request/response body, path, patient identifier or query logging.
        return

    def _valid_host(self) -> bool:
        hostname = self.headers.get("Host", "")
        expected = {f"127.0.0.1:{self.server.server_port}",
                    f"localhost:{self.server.server_port}"}
        return hostname in expected

    def _send(self, body: bytes, status: int, mime: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; style-src 'self'; script-src 'self'; "
                         "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if not self._valid_host():
            self._send(b"Host not allowed", 403, "text/plain; charset=utf-8")
            return
        page = _PAGES.get(urlsplit(self.path).path)
        if page is None or self.path != urlsplit(self.path).path:
            self._send(b"Not found", 404, "text/plain; charset=utf-8")
            return
        path = UI / page
        try:
            body = path.read_bytes()
        except OSError:
            self._send(b"Asset unavailable", 503, "text/plain; charset=utf-8")
            return
        mime = ("text/javascript" if page.endswith(".js") else
                "text/css" if page.endswith(".css") else "text/html") + "; charset=utf-8"
        self._send(body, 200, mime)

    def do_POST(self) -> None:
        if not self._valid_host() or self.path != "/rpc":
            self._send(b"Forbidden", 403, "text/plain; charset=utf-8")
            return
        allowed_origins = {f"http://127.0.0.1:{self.server.server_port}",
                           f"http://localhost:{self.server.server_port}"}
        if self.headers.get("Origin") not in allowed_origins:
            self._send(b"Same-origin browser only", 403, "text/plain; charset=utf-8")
            return
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            self._send(b"JSON only", 415, "text/plain; charset=utf-8")
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if not 0 < length <= MAX_MESSAGE:
                raise ValueError
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError
            packet = json.loads(raw)
        except (ValueError, OSError, json.JSONDecodeError):
            self._send(b"Invalid bounded JSON", 400, "text/plain; charset=utf-8")
            return
        response = json.dumps(handle_rpc(packet), separators=(",", ":"), sort_keys=True).encode()
        self._send(response, 200, "application/json; charset=utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Local-only synthetic research swarm; never upload clinical data")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("port out of range")
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    httpd.daemon_threads = True
    print(f"TMRDS offline research swarm: http://127.0.0.1:{httpd.server_port}/")
    try:
        httpd.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
