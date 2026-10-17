from __future__ import annotations

from scripts.security_scan import scan_text


def test_scanner_detects_private_key_and_common_tokens() -> None:
    private_key_marker = "-----BEGIN " + "PRIVATE KEY-----"
    token = "sk-" + "test-secret-material-1234567890"
    findings = scan_text(private_key_marker + "\n" + token + "\n")
    assert any(f.pattern_name == "private_key" for f in findings)
    assert any(f.pattern_name == "api_token" for f in findings)


def test_scanner_allows_documented_secret_placeholders() -> None:
    findings = scan_text(
        "export TMRDS_HMAC_SECRET='<strong-random-secret>'\n"
        "export NEO4J_PASSWORD='<strong-password>'\n"
        "TMRDS_DATABASE_URL=postgresql://tmrds:replace-with-local-only-password@tmrds-postgres:5432/tmrds # example.invalid\n"
    )
    assert findings == []


def test_placeholder_or_example_comment_does_not_hide_another_token_on_same_line() -> None:
    token = "ghp_" + "A" * 36
    findings = scan_text(f"TMRDS_HMAC_SECRET='<redacted>' # example.invalid {token}")
    assert any(f.pattern_name == "github_token" for f in findings)


def test_scanner_detects_fine_grained_github_gitlab_and_slack_tokens() -> None:
    samples = [
        ("github_fine_grained_token", "github_pat_" + "A" * 36),
        ("gitlab_token", "glpat-" + "A" * 30),
        ("slack_token", "xoxb-" + "A" * 20),
    ]
    for expected, token in samples:
        findings = scan_text("credential=" + token)
        assert any(f.pattern_name == expected for f in findings), expected


def test_scanner_ignores_only_the_matched_safe_placeholder() -> None:
    token = "xoxb-" + "A" * 20
    findings = scan_text(f"API_KEY='<set-in-deployment-secret>' # {token}")
    assert any(f.pattern_name == "slack_token" for f in findings)
