"""SMART on FHIR security primitives without storing client secrets."""
from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from hmac import compare_digest


@dataclass(frozen=True, slots=True)
class SmartConfiguration:
    """SMART discovery metadata safe for public exposure."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str

    def as_dict(self) -> dict[str, object]:
        return {
            "issuer": self.issuer,
            "authorization_endpoint": self.authorization_endpoint,
            "token_endpoint": self.token_endpoint,
            "jwks_uri": self.jwks_uri,
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "client_credentials"],
            "code_challenge_methods_supported": ["S256"],
            "scopes_supported": ["openid", "fhirUser", "launch", "patient/*.read", "user/*.read"],
            "token_endpoint_auth_methods_supported": ["private_key_jwt"],
            "capabilities": ["launch-ehr", "client-public", "client-confidential-symmetric", "sso-openid-connect"],
        }


def create_pkce_pair() -> tuple[str, str]:
    """Create RFC 7636 verifier/challenge using S256 only."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode("ascii")
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    return verifier, challenge


def validate_pkce(verifier: str, challenge: str) -> bool:
    """Constant-time validation of an S256 PKCE challenge."""
    if not verifier or not challenge:
        return False
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    return compare_digest(expected, challenge)
