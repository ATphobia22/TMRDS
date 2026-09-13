from __future__ import annotations

from scripts.security_scan import scan_text


def test_scanner_detects_private_key_and_common_tokens() -> None:
    private_key_marker = "-----BEGIN " + "PRIVATE KEY-----"
    token = "sk-" + "test-secret-material-1234567890"
    findings = scan_text(private_key_marker + "\n" + token + "\n")
    assert any(f.pattern_name == "private_key" for f in findings)
    assert any(f.pattern_name == "api_token" for f in findings)


def test_scanner_allows_documented_secret_placeholders() -> None:
    findings = scan_text("export TMRDS_HMAC_SECRET='<strong-random-secret>'\nexport NEO4J_PASSWORD='<strong-password>'\n")
    assert findings == []
