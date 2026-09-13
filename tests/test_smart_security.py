from __future__ import annotations

from engines.smart_security import SmartConfiguration, create_pkce_pair, validate_pkce


def test_pkce_uses_s256_and_round_trips() -> None:
    verifier, challenge = create_pkce_pair()
    assert len(verifier) >= 43
    assert validate_pkce(verifier, challenge)
    assert not validate_pkce(verifier + "x", challenge)


def test_smart_configuration_contains_no_secret_material() -> None:
    config = SmartConfiguration(
        issuer="https://tmrds.example",
        authorization_endpoint="https://tmrds.example/oauth/authorize",
        token_endpoint="https://tmrds.example/oauth/token",
        jwks_uri="https://tmrds.example/.well-known/jwks.json",
    )
    data = config.as_dict()
    assert data["code_challenge_methods_supported"] == ["S256"]
    assert "client_secret" not in str(data).lower()
    assert data["grant_types_supported"] == ["authorization_code", "client_credentials"]
