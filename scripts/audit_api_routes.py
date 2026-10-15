#!/usr/bin/env python3
"""Emit a deterministic inventory of FastAPI routes and declared dependencies."""
from __future__ import annotations

import argparse
import inspect
import json
import sys
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.main import app

AUTH_DEPENDENCY_NAMES = {
    "require_service_identity",
    "require_user",
    "require_authenticated_user",
    "require_admin",
    "require_privileged_user",
}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _dependency_names(dependant: Any) -> set[str]:
    names: set[str] = set()
    for dependency in getattr(dependant, "dependencies", []):
        call = getattr(dependency, "call", None)
        if call is not None:
            names.add(getattr(call, "__name__", call.__class__.__name__))
        names.update(_dependency_names(dependency))
    return names


def build_inventory() -> dict[str, Any]:
    routes: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    duplicates: list[dict[str, str]] = []
    unguarded_writes: list[dict[str, str]] = []

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        endpoint = route.endpoint
        dependencies = sorted(_dependency_names(route.dependant))
        auth_guards = sorted(set(dependencies) & AUTH_DEPENDENCY_NAMES)
        auth_class = "declared-auth-dependency" if auth_guards else "no-declared-route-auth-dependency"
        source_file = inspect.getsourcefile(endpoint) or ""
        source_line = inspect.getsourcelines(endpoint)[1] if source_file else None

        for method in sorted(route.methods or set()):
            if method in {"HEAD", "OPTIONS"}:
                continue
            key = (method, route.path)
            if key in seen:
                duplicates.append({"method": method, "path": route.path})
            seen.add(key)
            entry = {
                "method": method,
                "path": route.path,
                "endpoint": f"{endpoint.__module__}.{endpoint.__name__}",
                "source_file": source_file,
                "source_line": source_line,
                "dependencies": dependencies,
                "auth_guards": auth_guards,
                "auth_classification": auth_class,
            }
            routes.append(entry)
            if method in WRITE_METHODS and not auth_guards:
                unguarded_writes.append({"method": method, "path": route.path})

    routes.sort(key=lambda item: (item["path"], item["method"]))
    return {
        "schema_version": 1,
        "application": app.title,
        "route_count": len(routes),
        "routes": routes,
        "duplicate_method_paths": duplicates,
        "write_routes_without_declared_auth_dependency": unguarded_writes,
        "interpretation": (
            "Static inventory of declared FastAPI dependencies only. It does not prove authorization correctness, "
            "database permissions, reverse-proxy policy, or runtime configuration."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write JSON to this path instead of stdout")
    args = parser.parse_args()
    inventory = build_inventory()
    rendered = json.dumps(inventory, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 1 if inventory["duplicate_method_paths"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
