"""Live integration tests for public biomedical research sources.

These tests intentionally use real upstream services. They are not mocks and require
outbound HTTPS access. Run with: pytest -q tests/test_live_research_pipelines.py
"""
from __future__ import annotations

import pytest

from engines.cdc_data_pipeline import CDCDataPipeline
from engines.clinical_trials_pipeline import ClinicalTrialsPipeline
from engines.europe_pmc_pipeline import EuropePMCPipeline
from engines.nlm_research_pipeline import NLMResearchPipeline
from engines.openfda_pipeline import OpenFDAPipeline
from engines.openneuro_pipeline import OpenNeuroPipeline
from engines.pubmed_literature_bridge import PubMedLiteratureBridge


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_cdc_live() -> None:
    data = await CDCDataPipeline().fetch_indicators(limit=1)
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_openneuro_live() -> None:
    data = await OpenNeuroPipeline().search_datasets("MRI", limit=1)
    assert isinstance(data, dict)
    assert "data" in data or "errors" not in data


@pytest.mark.asyncio
async def test_clinical_trials_live() -> None:
    data = await ClinicalTrialsPipeline().search("ALS", page_size=1)
    assert isinstance(data, dict)
    assert "studies" in data


@pytest.mark.asyncio
async def test_openfda_live() -> None:
    data = await OpenFDAPipeline().drug_labels("aspirin", limit=1)
    assert isinstance(data, dict)
    assert "results" in data or "error" in data


@pytest.mark.asyncio
async def test_nlm_live() -> None:
    data = await NLMResearchPipeline().search_conditions("diabetes", limit=1)
    assert data is not None


@pytest.mark.asyncio
async def test_europe_pmc_live() -> None:
    data = await EuropePMCPipeline().search("diabetes", page_size=1)
    assert isinstance(data, dict)
    assert "resultList" in data


def test_pubmed_live() -> None:
    result = PubMedLiteratureBridge().search("amyotrophic lateral sclerosis", max_results=1)
    assert result["status"] == "OK"
    assert isinstance(result["pmids"], list)
