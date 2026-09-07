"""
HIPAA Security Rule technical controls for TMRDS (45 CFR 164.312).

Implements engineering controls aligned to:
  - Access control (unique user id, emergency access, automatic logoff, encryption)
  - Audit controls
  - Integrity
  - Person or entity authentication
  - Transmission security

This module supports covered-entity / BA technical practices. It does not
constitute a complete HIPAA compliance program (policies, BAAs, workforce
training, and physical safeguards remain organizational responsibilities).
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

    def __init__(
        self,
        audit_path: Optional[str] = None,
        session_timeout_min: int = 15,
        hmac_secret: Optional[str] = None,
    ) -> None:
        self.audit_path = Path(
            audit_path or os.environ.get("TMRDS_AUDIT_LOG", "data/audit/access.jsonl")
        )
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_timeout_sec = max(60, int(session_timeout_min) * 60)
        self._hmac_secret = (
            hmac_secret or os.environ.get("TMRDS_HMAC_SECRET") or secrets.token_hex(32)
        ).encode()
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._users: Dict[str, Dict[str, Any]] = {
            "clinician": {
                "user_id": "clinician",
                "role": "physician",
                "display_name": "Attending Clinician",
                "password_hash": self._hash_password("change-me-on-deploy"),
            },
            "emergency": {
                "user_id": "emergency",
                "role": "emergency_access",
                "display_name": "Emergency Access",
                "password_hash": self._hash_password(
                    os.environ.get("TMRDS_EMERGENCY_PIN", "911-break-glass")
                ),
            },
        }

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate(self, user_id: str, password: str) -> Dict[str, Any]:
        user = self._users.get(user_id)
        if not user or user["password_hash"] != self._hash_password(password):
            self.audit("AUTH_FAILURE", user_id=user_id, detail="invalid credentials")
            return {"ok": False, "error": "authentication_failed"}
        token = secrets.token_urlsafe(32)
        self._sessions[token] = {
            "user_id": user["user_id"],
            "role": user["role"],
            "display_name": user["display_name"],
            "issued_at": time.time(),
            "last_seen": time.time(),
            "emergency": user["role"] == "emergency_access",
        }
        self.audit("AUTH_SUCCESS", user_id=user["user_id"], detail=f"role={user['role']}")
        return {
            "ok": True,
            "token": token,
            "user_id": user["user_id"],
            "role": user["role"],
            "display_name": user["display_name"],
            "session_timeout_sec": self.session_timeout_sec,
            "emergency_access": user["role"] == "emergency_access",
        }

    def validate_session(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        if not token or token not in self._sessions:
            return None
        sess = self._sessions[token]
        now = time.time()
        if now - sess["last_seen"] > self.session_timeout_sec:
            self.audit("SESSION_TIMEOUT", user_id=sess["user_id"])
            del self._sessions[token]
            return None
        sess["last_seen"] = now
        return dict(sess)

    def logout(self, token: Optional[str]) -> None:
        if token and token in self._sessions:
            uid = self._sessions[token]["user_id"]
            del self._sessions[token]
            self.audit("LOGOUT", user_id=uid)

    def audit(self, action: str, user_id: str = "system", detail: str = "", resource: str = "") -> None:
        rec = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "action": action,
            "user_id": user_id,
            "resource": resource,
            "detail": detail,
        }
        with self.audit_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, separators=(",", ":")) + "\n")

    def integrity_seal(self, payload: Dict[str, Any]) -> str:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hmac.new(self._hmac_secret, body, hashlib.sha256).hexdigest()

    def verify_seal(self, payload: Dict[str, Any], seal: str) -> bool:
        expected = self.integrity_seal(payload)
        return hmac.compare_digest(expected, seal)

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
            "controls": [
                "unique_user_identification",
                "emergency_access_procedure",
                "automatic_logoff",
                "audit_controls",
                "integrity_hmac",
                "person_entity_authentication",
            ],
            "encryption_note": (
                "Encryption at rest/transit is addressable; enforce TLS termination "
                "and disk encryption in deployment environment."
            ),
            "active_sessions": len(self._sessions),
            "status": "READY",
        }
