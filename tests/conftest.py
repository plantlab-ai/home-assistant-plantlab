from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.plantlab.const import CONF_API_KEY, CONF_HOST, DOMAIN

MOCK_API_KEY = "pl_live_test123456789"
MOCK_HOST = "https://api.plantlab.ai"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
def _prevent_pycares_thread():
    with patch("pycares._ChannelShutdownManager.start"):
        yield


@pytest.fixture
def mock_config_entry(hass: HomeAssistant):
    entry = MockConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="PlantLab",
        data={CONF_API_KEY: MOCK_API_KEY, CONF_HOST: MOCK_HOST},
        source="user",
        unique_id=DOMAIN,
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_api_client():
    with patch("custom_components.plantlab.PlantLabApiClient", autospec=True) as mock_cls:
        client = mock_cls.return_value
        client.async_validate = AsyncMock(return_value=True)
        client.async_diagnose = AsyncMock(return_value=DIAGNOSE_RESPONSE_HEALTHY)
        yield client


@pytest.fixture
def mock_api_client_unhealthy(mock_api_client):
    mock_api_client.async_diagnose = AsyncMock(return_value=DIAGNOSE_RESPONSE_UNHEALTHY)
    return mock_api_client


@pytest.fixture
def mock_api_client_not_cannabis(mock_api_client):
    mock_api_client.async_diagnose = AsyncMock(return_value=DIAGNOSE_RESPONSE_NOT_CANNABIS)
    return mock_api_client


DIAGNOSE_RESPONSE_HEALTHY = {
    "schema_version": "1.0.0",
    "success": True,
    "is_cannabis": True,
    "cannabis_confidence": 0.98,
    "is_healthy": True,
    "health_confidence": 0.95,
    "growth_stage": "flowering",
    "growth_stage_confidence": 0.92,
    "conditions": [],
    "pests": [],
    "mulders_hypotheses": [],
    "diagnostic_confidence": 0.95,
    "safety_classification": "confident",
    "uncertainty_factors": [],
    "environmental_patterns": [],
    "progression_risks": [],
    "stage_times": {"stage1a": 45.2, "stage1b": 32.1, "stage1c": 18.5, "stage2": 67.3},
    "verification": {"status": "pending", "verification_id": "abc-123"},
}

DIAGNOSE_RESPONSE_UNHEALTHY = {
    "schema_version": "1.0.0",
    "success": True,
    "is_cannabis": True,
    "cannabis_confidence": 0.97,
    "is_healthy": False,
    "health_confidence": 0.87,
    "growth_stage": "vegetative",
    "growth_stage_confidence": 0.89,
    "conditions": [
        {
            "class_id": "nitrogen_deficiency",
            "confidence": 0.85,
            "display_name": "Nitrogen Deficiency",
        },
    ],
    "pests": [
        {
            "class_id": "spider_mites",
            "confidence": 0.72,
            "display_name": "Spider Mites",
        },
    ],
    "mulders_hypotheses": [
        {
            "excess": "potassium_excess",
            "explains": ["nitrogen_deficiency"],
            "evidence": 0.85,
            "evidence_count": 1,
        },
        {
            "excess": "calcium_excess",
            "explains": ["nitrogen_deficiency"],
            "evidence": 0.85,
            "evidence_count": 1,
        },
    ],
    "diagnostic_confidence": 0.82,
    "safety_classification": "confident",
    "uncertainty_factors": [],
    "environmental_patterns": [],
    "progression_risks": [],
    "stage_times": {"stage1a": 40.1, "stage1b": 28.3, "stage1c": 15.7, "stage2": 89.2},
    "verification": {"status": "pending", "verification_id": "def-456"},
}

DIAGNOSE_RESPONSE_NOT_CANNABIS = {
    "schema_version": "1.0.0",
    "success": True,
    "is_cannabis": False,
    "cannabis_confidence": 0.12,
    "conditions": [],
    "pests": [],
    "stage_times": {"stage1a": 38.5},
}
