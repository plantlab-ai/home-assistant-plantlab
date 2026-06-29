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


HISTORY_RESPONSE = {
    "items": [
        {
            "id": "hist-001",
            "request_id": "req-001",
            "class_id": "healthy",
            "confidence": 0.95,
            "is_cannabis": True,
            "is_healthy": True,
            "growth_stage": "flowering",
            "growth_stage_confidence": 0.92,
            "conditions": [],
            "pests": [],
            "engine_version": "1.0.94",
            "created_at": "2026-05-08T10:00:00+00:00",
        },
        {
            "id": "hist-002",
            "request_id": "req-002",
            "class_id": "nitrogen_deficiency",
            "confidence": 0.85,
            "is_cannabis": True,
            "is_healthy": False,
            "growth_stage": "vegetative",
            "growth_stage_confidence": 0.89,
            "conditions": [{"class_id": "nitrogen_deficiency", "confidence": 0.85}],
            "pests": [],
            "engine_version": "1.0.94",
            "created_at": "2026-05-08T09:00:00+00:00",
        },
        {
            "id": "hist-003",
            "request_id": "req-003",
            "class_id": "healthy",
            "confidence": 0.91,
            "is_cannabis": True,
            "is_healthy": True,
            "growth_stage": "seedling",
            "growth_stage_confidence": 0.88,
            "conditions": [],
            "pests": [],
            "engine_version": "1.0.94",
            "created_at": "2026-05-01T12:00:00+00:00",
        },
    ],
    "count": 3,
    "next_cursor": "",
}


@pytest.fixture
def mock_api_client():
    with patch("custom_components.plantlab.PlantLabApiClient", autospec=True) as mock_cls:
        client = mock_cls.return_value
        client.async_validate = AsyncMock(return_value=True)
        client.async_diagnose = AsyncMock(return_value=DIAGNOSE_RESPONSE_HEALTHY)
        client.async_get_history = AsyncMock(return_value=HISTORY_RESPONSE)
        yield client


@pytest.fixture
def mock_api_client_unhealthy(mock_api_client):
    mock_api_client.async_diagnose = AsyncMock(return_value=DIAGNOSE_RESPONSE_UNHEALTHY)
    return mock_api_client


@pytest.fixture
def mock_api_client_not_cannabis(mock_api_client):
    mock_api_client.async_diagnose = AsyncMock(return_value=DIAGNOSE_RESPONSE_NOT_CANNABIS)
    return mock_api_client


# Whole-image bbox for single-plant fixtures (schema 3.0.0).
_WHOLE_IMAGE_BBOX = {"x0": 0.0, "y0": 0.0, "x1": 1.0, "y1": 1.0, "normalized": True}

DIAGNOSE_RESPONSE_HEALTHY = {
    "schema_version": "3.0.0",
    "engine_version": {"api": "1.0.93", "models": "v3"},
    "success": True,
    "is_cannabis": True,
    "cannabis_confidence": 0.98,
    "results": [
        {
            "bbox": _WHOLE_IMAGE_BBOX,
            "is_healthy": True,
            "health_confidence": 0.95,
            "growth_stage": "flowering",
            "growth_stage_confidence": 0.92,
            "conditions": [],
            "pests": [],
            "mulders_hypotheses": [],
            "reliability_score": 0.95,
            "uncertainty_factors": [],
            "environmental_patterns": [],
            "progression_risks": [],
        },
    ],
    "stage_times": {"stage1a": 45.2, "stage1b": 32.1, "stage1c": 18.5, "stage2": 67.3},
    "verification": {"status": "pending", "verification_id": "abc-123"},
}

DIAGNOSE_RESPONSE_UNHEALTHY = {
    "schema_version": "3.0.0",
    "engine_version": {"api": "1.0.93", "models": "v3"},
    "success": True,
    "is_cannabis": True,
    "cannabis_confidence": 0.97,
    "results": [
        {
            "bbox": _WHOLE_IMAGE_BBOX,
            "is_healthy": False,
            "health_confidence": 0.87,
            "growth_stage": "vegetative",
            "growth_stage_confidence": 0.89,
            "conditions": [
                {
                    "class_id": "nitrogen_deficiency",
                    "display_name": "Nitrogen Deficiency",
                    "confidence": 0.85,
                },
            ],
            "pests": [
                {
                    "class_id": "spider_mites",
                    "display_name": "Spider Mites",
                    "confidence": 0.72,
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
            "reliability_score": 0.82,
            "uncertainty_factors": [],
            "environmental_patterns": [],
            "progression_risks": [],
        },
    ],
    "stage_times": {"stage1a": 40.1, "stage1b": 28.3, "stage1c": 15.7, "stage2": 89.2},
    "verification": {"status": "pending", "verification_id": "def-456"},
}

DIAGNOSE_RESPONSE_NOT_CANNABIS = {
    "schema_version": "3.0.0",
    "success": True,
    "is_cannabis": False,
    "cannabis_confidence": 0.12,
    "results": [],
    "stage_times": {"stage1a": 38.5},
}
