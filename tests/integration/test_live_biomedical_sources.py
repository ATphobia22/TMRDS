"""Live-source integration tests. These tests intentionally do not mock upstream services."""
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
    result = await CDCDataPipeline().fetch_indicators(1)
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_openneuro_live() -> None:
    result = await OpenNeuroPipeline().search_datasets("MRI", 1)
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_clinical_trials_live() -> None:
    result = await ClinicalTrialsPipeline().search("cancer", 1)
    assert isinstance(result, dict)
    assert "studies" in result


@pytest.mark.asyncio
async def test_openfda_live() -> None:
    result = await OpenFDAPipeline().drug_labels("aspirin", 1)
    assert isinstance(result, dict)
    assert "results" in result


@pytest.mark.asyncio
async def test_nlm_live() -> None:
    result = await NLMResearchPipeline().search_conditions("diabetes", 1)
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_europe_pmc_live() -> None:
    result = await EuropePMCPipeline().search("cancer", 1)
    assert isinstance(result, dict)
    assert "resultList" in result


def test_pubmed_live() -> None:
    result = PubMedLiteratureBridge().search("cancer", 1)
    assert result.get("status") != "ERROR"
