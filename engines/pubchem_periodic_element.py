"""Official PubChem periodic table metadata, one element per bounded request.

Not drug discovery efficacy, toxicity, reaction prediction or a clinical
interpretation. Original reported fields are left as strings where units or
uncertainty vary by property or isotope.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

import httpx

PUBCHEM_PERIODIC_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/periodictable/JSON"
_MAX_BODY = 262_144
_ELEMENT = re.compile(r"^[A-Z][a-z]?$")
_FIELDS = (
    "AtomicNumber", "Symbol", "Name", "AtomicWeight", "ElectronConfiguration",
    "Electronegativity", "OxidationStates", "StandardState", "GroupBlock",
)


def extract_original_element(payload: dict[str, Any], symbol: str) -> dict[str, Any]:
    if not isinstance(payload, dict) or not isinstance(payload.get("Table"), dict):
        raise ValueError("Invalid PubChem table response")
    table = payload["Table"]
    columns = (table.get("Columns") or {}).get("Column")
    rows = table.get("Row")
    if not isinstance(columns, list) or not isinstance(rows, list) or not rows:
        raise ValueError("Missing PubChem columns or rows")
    if len(set(columns)) != len(columns) or not set(_FIELDS) <= set(columns):
        raise ValueError("PubChem required columns missing or duplicated")
    idx = {name: columns.index(name) for name in _FIELDS}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("Cell"), list):
            raise ValueError("PubChem table row invalid")
        cells = row["Cell"]
        if len(cells) != len(columns) or any(not isinstance(value, str) for value in cells):
            raise ValueError("PubChem cell lengths invalid")
        if cells[idx["Symbol"]] != symbol:
            continue
        atomic = cells[idx["AtomicNumber"]]
        if not atomic.isdecimal() or not (1 <= int(atomic) <= 118):
            raise ValueError("Invalid atomic number")
        return {
            "atomic_number": int(atomic),
            "symbol": symbol,
            "name": cells[idx["Name"]][:64],
            "atomic_weight_source_text": cells[idx["AtomicWeight"]][:80] or None,
            "electron_configuration_reported": cells[idx["ElectronConfiguration"]][:250] or None,
            "electronegativity_source_text": cells[idx["Electronegativity"]][:50] or None,
            "oxidation_states_reported": cells[idx["OxidationStates"]][:150] or None,
            "standard_state_reported": cells[idx["StandardState"]][:50] or None,
            "group_block_reported": cells[idx["GroupBlock"]][:60] or None,
            "source_table_rows": len(rows),
            "complete_table_cardinality_observed": len(rows) == 118,
            "units_and_isotope_variability": "Review original PubChem property definitions and isotopic context",
        }
    return {}


async def lookup_pubchem_element(
    symbol: str, *, transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    if not isinstance(symbol, str) or not _ELEMENT.fullmatch(symbol):
        raise ValueError("Element symbol must be capitalized (H, Fe, Og); no arbitrary URL or chemical recipe")
    when = datetime.now(timezone.utc).isoformat()
    base = {
        "source": "NCBI PubChem",
        "source_endpoint": PUBCHEM_PERIODIC_URL,
        "retrieved_at": when, "query_symbol": symbol,
        "drug_efficacy_inferred": False, "toxicity_inferred": False,
        "patent_freedom_to_operate": "NOT_DETERMINED",
        "clinical_promotion_allowed": False,
    }
    try:
        async with httpx.AsyncClient(transport=transport, timeout=12, follow_redirects=False) as client:
            async with client.stream(
                "GET", PUBCHEM_PERIODIC_URL, headers={"Accept": "application/json"}
            ) as response:
                if response.status_code != 200:
                    raise ValueError("PubChem unavailable")
                if int(response.headers.get("content-length") or 0) > _MAX_BODY:
                    raise ValueError("PubChem table too large")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > _MAX_BODY:
                        raise ValueError("PubChem table too large")
                payload = json.loads(body)
        record = extract_original_element(payload, symbol)
        return {
            **base, "status": "element_metadata" if record else "element_not_found",
            "element": record or None,
            "interpretation": "original_source_atomic_reference_only",
            "source_warning": "Not a chemical synthesis, toxicity or drug treatment recommendation.",
        }
    except (ValueError, httpx.HTTPError, json.JSONDecodeError, OverflowError):
        return {
            **base, "status": "source_unavailable", "element": None,
            "source_warning": "Original source unavailable/invalid; no element value invented.",
        }
