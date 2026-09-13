"""Fail-closed deployment security configuration for TMRDS."""
from __future__ import annotations

import os
from dataclasses import dataclass


_PRODUCTION_VALUES = {"production", "prod"}


@dataclass(frozen=True, slots=True)
class SecurityConfiguration:
    """Deployment-managed secrets and security-critical endpoints."""

    environment: str
    database_url: str
    hmac_secret: str
    neo4j_uri: str | None
    neo4j_user: str | None
    neo4j_password: str | None

    @classmethod
    def from_environment(cls) -> "SecurityConfiguration":
        environment = os.getenv("TMRDS_ENV", "development").strip().casefold()
        database_url = os.getenv("TMRDS_DATABASE_URL", "").strip()
        hmac_secret = os.getenv("TMRDS_HMAC_SECRET", "")
        if not database_url:
            raise RuntimeError("TMRDS_DATABASE_URL is required; no built-in database credential is permitted")
        if len(hmac_secret) < 32:
            raise ValueError("TMRDS_HMAC_SECRET must contain at least 32 characters")
        if environment in _PRODUCTION_VALUES:
            for name in ("TMRDS_NEO4J_URI", "TMRDS_NEO4J_USER", "TMRDS_NEO4J_PASSWORD"):
                if not os.getenv(name, "").strip():
                    raise RuntimeError(f"{name} is required in production")
        return cls(
            environment=environment,
            database_url=database_url,
            hmac_secret=hmac_secret,
            neo4j_uri=os.getenv("TMRDS_NEO4J_URI"),
            neo4j_user=os.getenv("TMRDS_NEO4J_USER"),
            neo4j_password=os.getenv("TMRDS_NEO4J_PASSWORD"),
        )
