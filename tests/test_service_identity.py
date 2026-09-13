from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from engines.service_identity import ServiceTokenValidator


def _key_material(kid: str = "test-key") -> tuple[rsa.RSAPrivateKey, dict[str, object]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key())
    import json

    jwk = json.loads(public_jwk)
    jwk.update({"kid": kid, "use": "sig", "alg": "RS256"})
    return private_key, jwk


def _token(private_key: rsa.RSAPrivateKey, kid: str = "test-key", **overrides: object) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "iss": "https://issuer.example",
        "aud": "tmrds-api",
        "sub": "service-a",
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=5)).timestamp()),
        "scope": "fhir.read evidence.read",
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": kid})


def test_valid_service_token_is_accepted() -> None:
    private_key, jwk = _key_material()
    validator = ServiceTokenValidator.from_jwks([jwk], issuer="https://issuer.example", audience="tmrds-api")
    claims = validator.validate(_token(private_key), required_scopes={"fhir.read"})
    assert claims.subject == "service-a"
    assert "fhir.read" in claims.scopes


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "https://evil.example"},
        {"aud": "other-api"},
        {"exp": int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp())},
        {"scope": "evidence.read"},
    ],
)
def test_invalid_claims_are_rejected(overrides: dict[str, object]) -> None:
    private_key, jwk = _key_material()
    validator = ServiceTokenValidator.from_jwks([jwk], issuer="https://issuer.example", audience="tmrds-api")
    with pytest.raises(ValueError):
        validator.validate(_token(private_key, **overrides), required_scopes={"fhir.read"})


def test_unknown_key_is_rejected() -> None:
    private_key, _ = _key_material("test-key")
    _, other_jwk = _key_material("other-key")
    validator = ServiceTokenValidator.from_jwks([other_jwk], issuer="https://issuer.example", audience="tmrds-api")
    with pytest.raises(ValueError, match="unknown key"):
        validator.validate(_token(private_key, kid="test-key"))
