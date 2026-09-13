"""HIPAA Security Rule technical controls for TMRDS (45 CFR 164.312).

Credentials and integrity secrets are deployment-managed. No built-in password,
PIN, or deterministic secret is permitted.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class HIPAASecurityControls:
    """Session, audit, and integrity controls for ePHI-touching surfaces."""

    _SCRYPT_N = 2**14
    _SCRYPT_R = 8
    _SCRYPT_P = 1
    _SCRYPT_DKLEN = 32
    _SCRYPT_SALT_BYTES = 16
    _PBKDF2_MIN_ITERATIONS = 600_000

    def __init__(self, audit_path: Optional[str] = None, session_timeout_min: int = 15, hmac_secret: Optional[str] = None) -> None:
        self.audit_path = Path(audit_path or os.environ.get("TMRDS_AUDIT_LOG", "data/audit/access.jsonl"))
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_timeout_sec = max(60, int(session_timeout_min) * 60)
        self._hmac_secret = self._load_hmac_secret(hmac_secret)
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._users: Dict[str, Dict[str, Any]] = {}
        self._load_configured_users()

    @staticmethod
    def _load_hmac_secret(explicit_secret: Optional[str]) -> bytes:
        secret = explicit_secret or os.environ.get("TMRDS_HMAC_SECRET")
        if not secret:
            if os.environ.get("TMRDS_ENV", "development").casefold() in {"production", "prod"}:
                raise RuntimeError("TMRDS_HMAC_SECRET is required in production")
            secret = secrets.token_hex(32)
        if len(secret) < 32:
            raise ValueError("TMRDS_HMAC_SECRET must contain at least 32 characters")
        return secret.encode("utf-8")

    def _load_configured_users(self) -> None:
        users = (
            ("clinician", "physician", "Attending Clinician", os.environ.get("TMRDS_CLINICIAN_PASSWORD")),
            ("emergency", "emergency_access", "Emergency Access", os.environ.get("TMRDS_EMERGENCY_PIN")),
        )
        for user_id, role, display_name, password in users:
            if password:
                self._users[user_id] = {
                    "user_id": user_id,
                    "role": role,
                    "display_name": display_name,
                    "password_hash": self._hash_password(password),
                }

    @classmethod
    def _hash_password(cls, password: str) -> str:
        if not isinstance(password, str) or len(password) < 12:
            raise ValueError("password must contain at least 12 characters")
        salt = secrets.token_bytes(cls._SCRYPT_SALT_BYTES)
        digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=cls._SCRYPT_N, r=cls._SCRYPT_R, p=cls._SCRYPT_P, dklen=cls._SCRYPT_DKLEN)
        return f"scrypt${cls._SCRYPT_N}${cls._SCRYPT_R}${cls._SCRYPT_P}${salt.hex()}${digest.hex()}"

    @classmethod
    def _verify_password(cls, password: str, encoded: str) -> bool:
        try:
            parts = encoded.split("$")
            if parts[0] == "scrypt" and len(parts) == 6:
                _, n, r, p, salt_hex, digest_hex = parts
                expected = bytes.fromhex(digest_hex)
                actual = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p), dklen=len(expected))
                return hmac.compare_digest(actual, expected)
            if parts[0] == "pbkdf2_sha256" and len(parts) == 4:
                _, iterations_text, salt_hex, digest_hex = parts
                iterations = int(iterations_text)
                if iterations < cls._PBKDF2_MIN_ITERATIONS:
                    return False
                digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), iterations)
                return hmac.compare_digest(digest.hex(), digest_hex)
            return False
        except (TypeError, ValueError):
            return False

    def authenticate(self, user_id: str, password: str) -> Dict[str, Any]:
        user = self._users.get(user_id)
        if not user or not self._verify_password(password, user["password_hash"]):
            self.audit("AUTH_FAILURE", user_id=user_id, detail="invalid credentials")
            return {"ok": False, "error": "authentication_failed"}
        token = secrets.token_urlsafe(32)
        now = time.time()
        self._sessions[token] = {"user_id": user["user_id"], "role": user["role"], "display_name": user["display_name"], "issued_at": now, "last_seen": now, "emergency": user["role"] == "emergency_access"}
        self.audit("AUTH_SUCCESS", user_id=user["user_id"], detail=f"role={user['role']}")
        return {"ok": True, "token": token, "user_id": user["user_id"], "role": user["role"], "display_name": user["display_name"], "session_timeout_sec": self.session_timeout_sec, "emergency_access": user["role"] == "emergency_access"}

    def validate_session(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        if not token or token not in self._sessions:
            return None
        sess = self._sessions[token]
        if time.time() - sess["last_seen"] > self.session_timeout_sec:
            self.audit("SESSION_TIMEOUT", user_id=sess["user_id"])
            del self._sessions[token]
            return None
        sess["last_seen"] = time.time()
        return dict(sess)

    def logout(self, token: Optional[str]) -> None:
        if token and token in self._sessions:
            uid = self._sessions[token]["user_id"]
            del self._sessions[token]
            self.audit("LOGOUT", user_id=uid)

    def audit(self, action: str, user_id: str = "system", detail: str = "", resource: str = "") -> None:
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "action": action, "user_id": user_id, "resource": resource, "detail": detail}
        with self.audit_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, separators=(",", ":")) + "\n")

    def integrity_seal(self, payload: Dict[str, Any]) -> str:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hmac.new(self._hmac_secret, body, hashlib.sha256).hexdigest()

    def verify_seal(self, payload: Dict[str, Any], seal: str) -> bool:
        return hmac.compare_digest(self.integrity_seal(payload), seal)

    def recent_audit(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.audit_path.exists():
            return []
        lines = self.audit_path.read_text(encoding="utf-8").strip().splitlines()
        out = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def status(self) -> Dict[str, Any]:
        return {
            "node": "HIPAASecurityControls",
            "cfr": "45 CFR 164.312",
            "controls": ["unique_user_identification", "emergency_access_procedure", "automatic_logoff", "audit_controls", "integrity_hmac", "person_entity_authentication", "memory_hard_password_kdf"],
            "encryption_note": "Encryption at rest/transit is addressable; enforce TLS termination and disk encryption in deployment environment.",
            "active_sessions": len(self._sessions),
            "configured_users": sorted(self._users),
            "status": "READY",
        }
