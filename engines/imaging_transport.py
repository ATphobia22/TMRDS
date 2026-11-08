"""Bounded requests bridge for optional imaging clients; no environment proxies."""
from __future__ import annotations
import time
from urllib.parse import urlsplit
import requests
from engines.secure_http import OutboundRequestPolicy


class ImagingSession(requests.Session):
    def __init__(self, base_url: str, *, local_sandbox: bool = False, methods=("GET",), max_bytes=10 * 1024 * 1024):
        super().__init__()
        local_urls = {"http://127.0.0.1:8042/dicom-web", "http://127.0.0.1:8000"}
        if local_sandbox and base_url not in local_urls:
            raise ValueError("sandbox requires an exact approved localhost service")
        if not local_sandbox:
            OutboundRequestPolicy().validate_url(base_url)
        self.base_url = base_url.rstrip("/")
        self.local_sandbox = local_sandbox
        self.methods = methods
        self.max_bytes = max_bytes
        self.trust_env = False

    def request(self, method, url, **kwargs):
        target, base = urlsplit(url), urlsplit(self.base_url)
        if method.upper() not in self.methods or (target.scheme, target.netloc) != (base.scheme, base.netloc):
            raise ValueError("imaging request outside configured method/origin")
        if not (target.path == base.path or target.path.startswith(base.path + "/")):
            raise ValueError("imaging request outside configured path")
        if any(x in target.path.lower() for x in ("..", "%2e", "%2f", "%5c")) or target.fragment or target.username:
            raise ValueError("invalid imaging URL")
        if not self.local_sandbox:
            OutboundRequestPolicy().validate_url(url)
        kwargs.update(timeout=(5, 10), allow_redirects=False, stream=True)
        started = time.monotonic()
        response = super().request(method, url, **kwargs)
        try:
            if 300 <= response.status_code < 400:
                raise ValueError("imaging redirects are disabled")
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_content(65536):
                data.extend(chunk)
                if len(data) > self.max_bytes or time.monotonic() - started > 30:
                    raise ValueError("imaging response exceeded byte/time budget")
            response._content = bytes(data)
            response._content_consumed = True
            return response
        finally:
            response.close()
