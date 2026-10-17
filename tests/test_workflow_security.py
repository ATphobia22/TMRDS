from __future__ import annotations

from pathlib import Path

from scripts.check_workflow_security import scan_workflow_text, scan_workflows


def test_pinned_action_and_local_action_are_accepted() -> None:
    sha = "a" * 40
    workflow = (
        "name: safe\n"
        "permissions:\n"
        "  contents: read\n"
        "jobs:\n"
        "  test:\n"
        "    steps:\n"
        f"      - uses: actions/checkout@{sha} # release pin\n"
        "      - uses: ./.github/actions/local\n"
    )
    assert scan_workflow_text(workflow) == []


def test_mutable_action_tag_is_rejected_with_line_number() -> None:
    workflow = "name: unsafe\npermissions:\n  contents: read\njobs:\n  test:\n    steps:\n      - uses: actions/checkout@v4\n"
    findings = scan_workflow_text(workflow, ".github/workflows/ci.yml")
    assert any(f.line == 7 and "full 40-character commit SHA" in f.message for f in findings)


def test_workflow_must_declare_top_level_permissions() -> None:
    findings = scan_workflow_text("name: missing permissions\njobs:\n  test: {}\n")
    assert any("least-privilege top-level permissions" in f.message for f in findings)


def test_repository_workflows_use_immutable_action_refs() -> None:
    root = Path(__file__).resolve().parents[1]
    assert scan_workflows(root) == []
