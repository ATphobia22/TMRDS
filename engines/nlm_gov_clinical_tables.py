"""
NLM / .gov Clinical Data Bridges for TMRDS.

Verified public services (National Library of Medicine / NIH):
  - Clinical Table Search Service (ICD-10-CM, HPO, RxTerms, HCPCS, NPI, …)
    https://clinicaltables.nlm.nih.gov/
  - MedlinePlus Connect / Web Service
  - RxNorm API (rxnav.nlm.nih.gov)
  - PubMed E-utilities (PubMedLiteratureBridge)
  - ClinicalTrials.gov API v2

Official U.S. government terminology and patient-education endpoints — not scraped.
"""
from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from typing import Any, Dict

logger = logging.getLogger("TMRDS.NLMGov")

CLINICAL_TABLES = "https://clinicaltables.nlm.nih.gov/api"
MEDLINEPLUS_WS = "https://wsearch.nlm.nih.gov/ws/query"
RXNORM_API = "https://rxnav.nlm.nih.gov/REST"


class NLMGovClinicalTables:
    """Query NLM Clinical Tables and related .gov clinical APIs."""

    TABLES = {
        "icd10cm": "icd10cm",
        "hpo": "hpo",
        "rxterms": "rxterms",
        "hcpcs": "hcpcs",
        "conditions": "conditions",
        "npi_individuals": "npi_idv",
    }

    def _get(self, url: str, timeout: int = 20) -> Any:
        req = urllib.request.Request(url, headers={"User-Agent": "TMRDS-NLMGov/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode()
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return body
        except Exception as exc:  # noqa: BLE001
            logger.warning("NLM request failed: %s", exc)
            return {"error": str(exc), "url": url}

    def search_table(self, table: str, terms: str, max_list: int = 15) -> Dict[str, Any]:
        key = self.TABLES.get(table, table)
        q = urllib.parse.quote(terms)
        url = f"{CLINICAL_TABLES}/{key}/v3/search?terms={q}&maxList={max(1, min(max_list, 50))}"
        data = self._get(url)
        return {
            "table": key,
            "terms": terms,
            "raw": data,
            "source": "clinicaltables.nlm.nih.gov",
            "status": "ERROR" if isinstance(data, dict) and data.get("error") else "OK",
        }

    def medlineplus(self, term: str, retmax: int = 5) -> Dict[str, Any]:
        q = urllib.parse.quote(term)
        url = f"{MEDLINEPLUS_WS}?db=healthTopics&term={q}&retmax={retmax}"
        data = self._get(url)
        return {
            "term": term,
            "raw": data,
            "source": "MedlinePlus NLM Web Service",
            "status": "OK",
            "patient_education": True,
        }

    def rxnorm_approximate(self, drug_name: str) -> Dict[str, Any]:
        q = urllib.parse.quote(drug_name)
        url = f"{RXNORM_API}/approximateTerm.json?term={q}&maxEntries=10"
        data = self._get(url)
        return {
            "term": drug_name,
            "raw": data,
            "source": "RxNorm API (NLM)",
            "status": "ERROR" if isinstance(data, dict) and data.get("error") else "OK",
        }

    def status(self) -> Dict[str, Any]:
        return {
            "node": "NLMGovClinicalTables",
            "tables": list(self.TABLES.keys()),
            "endpoints": {
                "clinical_tables": CLINICAL_TABLES,
                "medlineplus": MEDLINEPLUS_WS,
                "rxnorm": RXNORM_API,
            },
            "authority": "U.S. National Library of Medicine / NIH",
            "status": "READY",
        }
