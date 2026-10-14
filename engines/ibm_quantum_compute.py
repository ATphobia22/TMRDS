"""IBM Quantum Compute Service adapter for TMRDS.

This adapter is deliberately opt-in. It never falls back to simulated or
synthetic results when credentials, access, or hardware are unavailable.
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urljoin

import requests


class IBMQuantumError(RuntimeError):
    """Safe, non-secret-bearing IBM Quantum integration error."""


@dataclass(frozen=True, slots=True)
class IBMQuantumConfig:
    api_key: str
    instance_crn: str
    region: str = "us"
    api_version: str = "2026-04-15"
    timeout_seconds: float = 20.0

    @classmethod
    def from_environment(cls) -> "IBMQuantumConfig":
        api_key = os.getenv("IBM_QUANTUM_API_KEY", "").strip()
        instance_crn = os.getenv("IBM_QUANTUM_INSTANCE_CRN", "").strip()
        region = os.getenv("IBM_QUANTUM_REGION", "us").strip()
        api_version = os.getenv("IBM_QUANTUM_API_VERSION", "2026-04-15").strip()
        try:
            timeout = float(os.getenv("IBM_QUANTUM_TIMEOUT_SECONDS", "20"))
        except ValueError as exc:
            raise ValueError("IBM_QUANTUM_TIMEOUT_SECONDS must be numeric.") from exc
        if not api_key or not instance_crn:
            raise ValueError(
                "IBM_QUANTUM_API_KEY and IBM_QUANTUM_INSTANCE_CRN are required."
            )
        if region not in {"us", "eu-de"}:
            raise ValueError("IBM_QUANTUM_REGION must be 'us' or 'eu-de'.")
        if not api_version or len(api_version) > 32:
            raise ValueError("IBM_QUANTUM_API_VERSION is invalid.")
        if timeout <= 0 or timeout > 300:
            raise ValueError("Timeout must be greater than 0 and at most 300 seconds.")
        return cls(api_key, instance_crn, region, api_version, timeout)

    @property
    def base_url(self) -> str:
        host = "eu-de.quantum.cloud.ibm.com" if self.region == "eu-de" else "quantum.cloud.ibm.com"
        return f"https://{host}/api/v1/"


class IBMQuantumComputeClient:
    """Small synchronous REST client; callers own durable job orchestration."""

    IAM_URL = "https://iam.cloud.ibm.com/identity/token"

    def __init__(self, config: IBMQuantumConfig) -> None:
        self._config = config
        self._session = requests.Session()
        self._token_lock = threading.Lock()
        self._token: str | None = None
        self._token_deadline = 0.0

    @classmethod
    def from_environment(cls) -> "IBMQuantumComputeClient":
        return cls(IBMQuantumConfig.from_environment())

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "IBMQuantumComputeClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _get_token(self, *, force_refresh: bool = False) -> str:
        with self._token_lock:
            if not force_refresh and self._token and time.monotonic() < self._token_deadline:
                return self._token
            try:
                response = self._session.post(
                    self.IAM_URL,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    data={
                        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                        "apikey": self._config.api_key,
                    },
                    timeout=self._config.timeout_seconds,
                    allow_redirects=False,
                )
                response.raise_for_status()
                data = response.json()
            except (requests.RequestException, ValueError) as exc:
                raise IBMQuantumError("IBM IAM token acquisition failed.") from exc
            token = data.get("access_token") if isinstance(data, dict) else None
            expires_in = data.get("expires_in") if isinstance(data, dict) else None
            if (
                not isinstance(token, str)
                or not token
                or not isinstance(expires_in, (int, float))
                or isinstance(expires_in, bool)
                or expires_in <= 0
            ):
                raise IBMQuantumError("IBM IAM returned an invalid token response.")
            self._token = token
            self._token_deadline = time.monotonic() + max(
                0.0, float(expires_in) - min(60.0, float(expires_in) / 2)
            )
            return token

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str | int | bool] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        if path.startswith("/") or any(part in {".", ".."} for part in path.split("/")):
            raise ValueError("API path must be relative and safe.")
        url = urljoin(self._config.base_url, path)
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._get_token()}",
            "Service-CRN": self._config.instance_crn,
            "IBM-API-Version": self._config.api_version,
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        try:
            response = self._session.request(
                method.upper(),
                url,
                headers=headers,
                params=params,
                json=body,
                timeout=self._config.timeout_seconds,
                allow_redirects=False,
            )
            # Safe retry: only GET, and only once, after refreshing an expired token.
            if response.status_code == 401 and method.upper() == "GET":
                response.close()
                headers["Authorization"] = f"Bearer {self._get_token(force_refresh=True)}"
                response = self._session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=self._config.timeout_seconds,
                    allow_redirects=False,
                )
            if not 200 <= response.status_code < 300:
                raise IBMQuantumError(
                    f"IBM Quantum request failed with HTTP {response.status_code}."
                )
            try:
                payload = response.json()
            except ValueError as exc:
                raise IBMQuantumError("IBM Quantum returned invalid JSON.") from exc
            if not isinstance(payload, (dict, list)):
                raise IBMQuantumError("IBM Quantum returned an unexpected JSON type.")
            return payload
        except requests.RequestException as exc:
            raise IBMQuantumError("IBM Quantum transport request failed.") from exc

    def list_backends(self) -> dict[str, Any] | list[Any]:
        return self._request("GET", "backends")

    def get_backend_status(self, backend: str) -> dict[str, Any] | list[Any]:
        if not backend or len(backend) > 200:
            raise ValueError("Backend identifier is invalid.")
        return self._request("GET", f"backends/{quote(backend, safe='')}/status")

    def submit_sampler(
        self,
        *,
        backend: str,
        qasm_circuits: list[str],
        shots: int | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Submit OpenQASM 3 circuits; submission is never automatically retried."""
        if not backend or len(backend) > 200:
            raise ValueError("Backend identifier is invalid.")
        if not qasm_circuits or any(not isinstance(q, str) or not q.strip() for q in qasm_circuits):
            raise ValueError("At least one non-empty OpenQASM circuit is required.")
        if shots is not None and (isinstance(shots, bool) or shots < 1 or shots > 10_000_000):
            raise ValueError("shots must be an integer between 1 and 10000000.")
        params: dict[str, Any] = {
            "pubs": [[qasm] if shots is None else [qasm, None, shots] for qasm in qasm_circuits],
            "options": {},
            "version": 2,
        }
        body: dict[str, Any] = {
            "program_id": "sampler",
            "backend": backend,
            "params": params,
        }
        if tags:
            if len(tags) > 20 or any(not tag or len(tag) > 128 for tag in tags):
                raise ValueError("Tags must contain 1-20 non-empty strings of at most 128 characters.")
            body["tags"] = tags
        return self._request("POST", "jobs", body=body)

    def get_job(self, job_id: str) -> dict[str, Any] | list[Any]:
        if not job_id or len(job_id) > 256 or "/" in job_id:
            raise ValueError("Job identifier is invalid.")
        return self._request("GET", f"jobs/{quote(job_id, safe='')}")

    def get_job_results(self, job_id: str) -> dict[str, Any] | list[Any]:
        if not job_id or len(job_id) > 256 or "/" in job_id:
            raise ValueError("Job identifier is invalid.")
        return self._request("GET", f"jobs/{quote(job_id, safe='')}/results")

    def list_jobs(self, *, limit: int = 50, offset: int = 0, pending: bool | None = None) -> dict[str, Any] | list[Any]:
        if not 1 <= limit <= 200 or offset < 0:
            raise ValueError("limit must be 1-200 and offset must be non-negative.")
        params: dict[str, str | int | bool] = {"limit": limit, "offset": offset}
        if pending is not None:
            params["pending"] = pending
        return self._request("GET", "jobs", params=params)
