"""Loopback-only offline TMRDS HTML specialist swarm.

Start: python -m scripts.run_offline_swarm --port 8765
The server only accepts a fixed synthetic scenario enum, not patient uploads.
No external API, cloud, telemetry, data persistence, cookies or diagnosis.
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from engines.offline_specialist_swarm import capability_manifest, run_offline_case, validate_scenario

ASSETS = Path(__file__).resolve().parents[1] / "offline" / "swarm"


class OfflineSwarmHandler(BaseHTTPRequestHandler):
    ALLOWED_GET_PATHS = frozenset({
        "/", "/index.html", "/labs.html", "/imaging.html",
        "/genomics.html", "/evidence.html", "/drug_discovery.html",
        "/quantum.html", "/knowledge.html", "/supervisor.html",
        "/swarm.js", "/swarm.css", "/api/local/health",
        "/api/local/capabilities",
    })
    ALLOWED_POST_PATHS = frozenset({"/api/local/run"})
    MAX_REQUEST_BYTES = 256
    server_version = "TMRDSOfflineSwarm/1"
    sys_version = ""

    def log_message(self, fmt, *args):
        # The local service never records raw URL or request bodies.
        return

    def _valid_host(self):
        port = self.server.server_address[1]
        return self.headers.get("Host") == f"127.0.0.1:{port}"

    def _reply(self, code, payload, mime="application/json; charset=utf-8"):
        if isinstance(payload, dict):
            payload = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'self'; style-src 'self'; "
                         "connect-src 'self'; base-uri 'none'; form-action 'none'; "
                         "frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if not self._valid_host():
            return self._reply(403, {"error": "invalid_local_host"})
        split = urlsplit(self.path)
        if split.query or split.fragment or split.path not in self.ALLOWED_GET_PATHS:
            return self._reply(404, {"error": "route_not_found"})
        if split.path == "/api/local/health":
            return self._reply(200, {
                "status": "ready", "mode": "loopback_only",
                "offline": True, "external_sources_verified": False,
                "clinical_inference_enabled": False,
            })
        if split.path == "/api/local/capabilities":
            return self._reply(200, capability_manifest())
        name = "index.html" if split.path == "/" else split.path[1:]
        data = (ASSETS / name).read_bytes()
        mime = ("application/javascript; charset=utf-8" if name.endswith(".js") else
                "text/css; charset=utf-8" if name.endswith(".css") else
                "text/html; charset=utf-8")
        return self._reply(200, data, mime)

    def do_POST(self):
        if not self._valid_host():
            return self._reply(403, {"error": "invalid_local_host"})
        if urlsplit(self.path).path not in self.ALLOWED_POST_PATHS or "?" in self.path:
            return self._reply(404, {"error": "route_not_found"})
        expected_origin = f"http://127.0.0.1:{self.server.server_address[1]}"
        if self.headers.get("Origin") not in (None, expected_origin):
            return self._reply(403, {"error": "cross_origin_disallowed"})
        if (self.headers.get("Content-Type") != "application/json" or
                self.headers.get("X-TMRDS-Local-Only") != "synthetic-demo"):
            return self._reply(415, {"error": "json_local_demo_contract_required"})
        size = self.headers.get("Content-Length", "")
        if not size.isascii() or not size.isdecimal() or not 1 <= int(size) <= self.MAX_REQUEST_BYTES:
            return self._reply(413, {"error": "request_body_rejected"})
        try:
            data = json.loads(self.rfile.read(int(size)))
            if not isinstance(data, dict) or set(data) != {"scenario"}:
                raise ValueError("fixed scenario only")
            scenario = validate_scenario(data["scenario"])
        except (ValueError, UnicodeError):
            return self._reply(422, {"error": "only_built_in_synthetic_scenario_allowed"})
        return self._reply(200, run_offline_case(scenario))


def build_server(*, host="127.0.0.1", port=8765):
    if host != "127.0.0.1":
        raise ValueError("Offline TMRDS must bind only to IPv4 loopback")
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("Port must be a valid integer")
    return ThreadingHTTPServer((host, port), OfflineSwarmHandler)


def main():
    parser = argparse.ArgumentParser(description="Launch isolated synthetic TMRDS HTML specialist swarm.")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = build_server(port=args.port)
    addr = f"http://127.0.0.1:{server.server_address[1]}/"
    print("Local TMRDS synthetic-only specialist workstation: " + addr, flush=True)
    print("No patient file ingestion, clinical AI, licensed weights or Internet required.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
