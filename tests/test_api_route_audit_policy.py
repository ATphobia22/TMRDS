from __future__ import annotations

from scripts.audit_api_routes import build_inventory, policy_findings


def test_current_api_route_inventory_has_no_duplicate_or_unguarded_write_routes() -> None:
    findings = policy_findings(build_inventory())
    assert findings == []


def test_route_policy_rejects_duplicate_method_path() -> None:
    findings = policy_findings({
        "duplicate_method_paths": [{"method": "POST", "path": "/mutate"}],
        "write_routes_without_declared_auth_dependency": [],
    })
    assert findings == ["duplicate route: POST /mutate"]


def test_route_policy_rejects_unguarded_write() -> None:
    findings = policy_findings({
        "duplicate_method_paths": [],
        "write_routes_without_declared_auth_dependency": [{"method": "DELETE", "path": "/resource"}],
    })
    assert findings == ["write route lacks recognized declared auth dependency: DELETE /resource"]
