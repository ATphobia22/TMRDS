#!/usr/bin/env python3
"""Static contract gate for TMRDS public research atlas (not an integration test)."""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"

class Inspection(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.local_assets: list[str] = []
        self.inline_scripts = 0
        self.csp = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if a.get("id"):
            if a["id"] in self.ids:
                raise ValueError("duplicate HTML id: " + a["id"])
            self.ids.add(a["id"])
        if tag == "script":
            if a.get("src"):
                self.local_assets.append(a["src"])
            else:
                self.inline_scripts += 1
        if tag == "link" and a.get("rel") == "stylesheet" and a.get("href"):
            self.local_assets.append(a["href"])
        if tag == "meta" and a.get("http-equiv", "").lower() == "content-security-policy":
            self.csp = a.get("content", "")

def main() -> None:
    html = (PUBLIC / "index.html").read_text(encoding="utf-8")
    js = (PUBLIC / "site.js").read_text(encoding="utf-8")
    css = (PUBLIC / "site.css").read_text(encoding="utf-8")
    inspector = Inspection()
    inspector.feed(html)
    required = {"searchForm", "query", "searchBtn", "literature", "trials",
                "literatureStatus", "trialStatus", "fetchMeta", "litCount", "trialCount"}
    assert required <= inspector.ids, sorted(required - inspector.ids)
    assert inspector.inline_scripts == 0, "inline script prohibited"
    assert inspector.csp and "default-src 'none'" in inspector.csp
    assert "connect-src 'self' https://www.ebi.ac.uk https://clinicaltrials.gov;" in inspector.csp
    assert inspector.local_assets == ["./site.css", "./site.js"], inspector.local_assets
    import json
    backend_config = json.loads((PUBLIC / "backend-config.json").read_text())
    assert backend_config["api_mode"] == "disabled", "public Pages must never claim deployed backend"
    assert {"rubiksCube", "cubeMoveBtn", "cubeActivity", "backendState", "pathwayRecords", "pathwayFootnote"} <= inspector.ids
    for token in ("turnCubeLayer", "rotateVector", "startCubeSearch", "stopCubeSearch", "backendConfiguration", "loadGovernedPathway"):
        assert token in js, token
    assert "@keyframes cube-idle" in css and "@keyframes cube-working" in css
    assert "prefers-reduced-motion" in css
    assert {"medicalCategory", "medicalList", "medicalCount", "medicalRegistryStatus",
            "pubmedBackendState", "pubmedBackendRecords", "structureForm",
            "uniprotAccession", "structureBackendState", "structureBackendRecords"} <= inspector.ids
    medical_catalog = json.loads((PUBLIC / "medical-projects.json").read_text())
    assert medical_catalog["all_platforms_installed"] is False
    assert medical_catalog["license_approvals_completed"] is False
    assert len(medical_catalog["projects"]) >= 40
    assert len({p["id"] for p in medical_catalog["projects"]}) == len(medical_catalog["projects"])
    assert medical_catalog["schema_version"] == "1.0"
    for project in medical_catalog["projects"]:
        assert project["source_url"].startswith("https://")
        assert project["integration_state"] != "clinical_live"
    for token in ("loadMedicalProjectCatalog", "loadBackendPubMed", "structureForm",
                  "api/v1/research/pubmed-citations", "api/v1/research/alphafold-db/",
                  "NOT AlphaFold 3 inference"):
        assert token in js, token
    assert ".medical-grid" in css and ".extension-grid" in css
    assert len(css) > 1000
    for asset in inspector.local_assets:
        assert (PUBLIC / asset.removeprefix("./")).is_file(), asset
    assert "credentials: \"omit\"" in js
    assert "cache: \"no-store\"" in js
    assert "AbortController()" in js
    assert "crypto.subtle.digest" in js
    assert "Promise.allSettled" in js
    assert "textContent" in js, "source strings must not be injected as HTML"
    assert "innerHTML" not in js, "do not render upstream HTML"
    for host in ("https://www.ebi.ac.uk/europepmc/webservices/rest/search",
                 "https://clinicaltrials.gov/api/v2/studies"):
        assert host in js, host
    assert not re.search(r"fetch\(\s*['\"]http:", js)
    print("Public site static contract valid: CSP, bounded source hosts, provenance, no HTML injection")

if __name__ == "__main__":
    main()