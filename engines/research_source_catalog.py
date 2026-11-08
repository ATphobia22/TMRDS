"""Reviewed integration priorities; listings never imply an operational connection."""
from __future__ import annotations

import json
from importlib.resources import files


def research_source_catalog() -> dict:
    return json.loads(files("engines").joinpath("research_source_catalog.json").read_text())
