"""SSRF-resistant outbound HTTP policy for TMRDS upstream connectors."""
from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urlparse

import httpx


class OutboundRequestPolicy:
    """Validate outbound URLs before a connector opens a network connection."""

    def __init__(self, allowed_private_hosts: set[str] | None = None, resolve_host: Callable[[str], list[ipaddress.IPv4Address | ipaddress.IPv6Address]] | None = None) -> None:
        self.allowed_private_hosts = {host.casefold().rstrip(".") for host in (allowed_private_hosts or set())}
        self._resolve_host = resolve_host or self._resolve

    @staticmethod
    def _resolve(host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        results = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        return list({ipaddress.ip_address(result[4][0]) for result in results})

    def validate_url(self, url: str, allow_private: bool = False) -> str:
        parsed = urlparse(url)
        host = (parsed.hostname or "").casefold().rstrip(".")
        if parsed.scheme != "https":
            raise ValueError("outbound protected requests require HTTPS")
        if not host:
            raise ValueError("outbound URL requires a hostname")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("outbound URL must not contain credentials")
        if parsed.fragment:
            raise ValueError("outbound URL must not contain a fragment")
        if host not in self.allowed_private_hosts:
            try:
                addresses = self._resolve_host(host)
            except (OSError, socket.gaierror) as exc:
                raise ValueError("outbound hostname could not be resolved") from exc
            if any(address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_multicast for address in addresses):
                if not allow_private:
                    raise ValueError("outbound hostname resolves to a private/reserved address")
        return url


class SecureHTTPClient:
    """Bounded-timeout HTTP client with redirects disabled by default."""

    def __init__(self, policy: OutboundRequestPolicy | None = None) -> None:
        self.policy = policy or OutboundRequestPolicy()
        self.timeout = httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0)

    def client(self, *, allow_private: bool = False) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=self.timeout, follow_redirects=False)

    def validate(self, url: str, *, allow_private: bool = False) -> str:
        return self.policy.validate_url(url, allow_private=allow_private)
