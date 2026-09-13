"""Zero-trust service identity validation for TMRDS machine-to-machine calls."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

import jwt
from jwt import InvalidTokenError


@dataclass(frozen=True, slots=True)
class ServiceTokenClaims:
    """Validated identity claims; raw bearer tokens are never retained."""

    subject: str
    issuer: str
    audience: str
    scopes: frozenset[str]
    key_id: str


class ServiceTokenValidator:
    """Validate asymmetric JWTs against an explicitly configured JWKS set."""

    def __init__(self, keys: dict[str, Any], issuer: str, audience: str) -> None:
        if not issuer or not audience:
            raise ValueError("issuer and audience are required")
        self._keys = dict(keys)
        self.issuer = issuer
        self.audience = audience

    @classmethod
    def from_jwks(cls, jwks: Iterable[dict[str, Any]], issuer: str, audience: str) -> "ServiceTokenValidator":
        keys: dict[str, Any] = {}
        for jwk in jwks:
            kid = str(jwk.get("kid", "")).strip()
            if not kid:
                raise ValueError("every service JWKS key requires kid")
            if jwk.get("use", "sig") != "sig":
                continue
            if jwk.get("alg", "RS256") not in {"RS256", "ES256"}:
                continue
            keys[kid] = jwt.algorithms.get_default_algorithms()[jwk["alg"]].from_jwk(json.dumps(jwk))
        return cls(keys, issuer, audience)

    def validate(self, token: str, required_scopes: set[str] | frozenset[str] = frozenset()) -> ServiceTokenClaims:
        if not token or token.count(".") != 2:
            raise ValueError("malformed service token")
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            kid = header.get("kid")
            if algorithm not in {"RS256", "ES256"} or not kid:
                raise ValueError("unsupported service token header")
            key = self._keys.get(str(kid))
            if key is None:
                raise ValueError("unknown key")
            payload = jwt.decode(
                token,
                key=key,
                algorithms=[str(algorithm)],
                issuer=self.issuer,
                audience=self.audience,
                options={"require": ["iss", "sub", "aud", "iat", "nbf", "exp"]},
            )
        except InvalidTokenError as exc:
            raise ValueError("invalid service token") from exc
        scopes = frozenset(str(payload.get("scope", "")).split())
        missing = set(required_scopes) - scopes
        if missing:
            raise ValueError(f"missing required scopes: {sorted(missing)}")
        audience = payload["aud"]
        if isinstance(audience, list):
            audience = audience[0] if audience else ""
        return ServiceTokenClaims(
            subject=str(payload["sub"]),
            issuer=str(payload["iss"]),
            audience=str(audience),
            scopes=scopes,
            key_id=str(kid),
        )
