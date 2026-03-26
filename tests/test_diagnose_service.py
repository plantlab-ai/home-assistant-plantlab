from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.plantlab.api import PlantLabAuthError, PlantLabRateLimitError
from custom_components.plantlab.const import DOMAIN, SERVICE_DIAGNOSE

from .conftest import DIAGNOSE_RESPONSE_UNHEALTHY


async def _setup_integration(hass, mock_config_entry, mock_api_client):
    with patch(
        "custom_components.plantlab.PlantLabApiClient",
        return_value=mock_api_client,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()


async def test_diagnose_with_image_path(hass: HomeAssistant, mock_config_entry, mock_api_client):
    await _setup_integration(hass, mock_config_entry, mock_api_client)

    with patch(
        "custom_components.plantlab._read_image_file",
        return_value=b"fake_image",
    ):
        result = await hass.services.async_call(
            DOMAIN,
            SERVICE_DIAGNOSE,
            {"image_path": "/config/test.jpg"},
            blocking=True,
            return_response=True,
        )

    assert result["success"] is True
    assert result["is_cannabis"] is True
    mock_api_client.async_diagnose.assert_called_once_with(b"fake_image")


async def test_diagnose_with_camera_entity(hass: HomeAssistant, mock_config_entry, mock_api_client):
    await _setup_integration(hass, mock_config_entry, mock_api_client)

    with patch(
        "custom_components.plantlab._get_image_from_camera",
        new_callable=AsyncMock,
        return_value=b"camera_image",
    ):
        result = await hass.services.async_call(
            DOMAIN,
            SERVICE_DIAGNOSE,
            {"entity_id": "camera.grow_tent"},
            blocking=True,
            return_response=True,
        )

    assert result["success"] is True
    mock_api_client.async_diagnose.assert_called_once_with(b"camera_image")


async def test_diagnose_missing_input(hass: HomeAssistant, mock_config_entry, mock_api_client):
    await _setup_integration(hass, mock_config_entry, mock_api_client)

    with pytest.raises(ServiceValidationError, match="Must provide"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DIAGNOSE,
            {},
            blocking=True,
            return_response=True,
        )


async def test_diagnose_auth_error(hass: HomeAssistant, mock_config_entry, mock_api_client):
    mock_api_client.async_diagnose = AsyncMock(side_effect=PlantLabAuthError("Invalid API key"))
    await _setup_integration(hass, mock_config_entry, mock_api_client)

    with (
        patch(
            "custom_components.plantlab._read_image_file",
            return_value=b"fake_image",
        ),
        pytest.raises(HomeAssistantError, match="Authentication failed"),
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DIAGNOSE,
            {"image_path": "/config/test.jpg"},
            blocking=True,
            return_response=True,
        )


async def test_diagnose_rate_limit(hass: HomeAssistant, mock_config_entry, mock_api_client):
    mock_api_client.async_diagnose = AsyncMock(
        side_effect=PlantLabRateLimitError("Rate limit exceeded - free tier allows 3 diagnoses/day")
    )
    await _setup_integration(hass, mock_config_entry, mock_api_client)

    with (
        patch(
            "custom_components.plantlab._read_image_file",
            return_value=b"fake_image",
        ),
        pytest.raises(HomeAssistantError, match="Rate limit"),
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DIAGNOSE,
            {"image_path": "/config/test.jpg"},
            blocking=True,
            return_response=True,
        )


async def test_diagnose_updates_sensors(hass: HomeAssistant, mock_config_entry, mock_api_client):
    mock_api_client.async_diagnose = AsyncMock(return_value=DIAGNOSE_RESPONSE_UNHEALTHY)
    await _setup_integration(hass, mock_config_entry, mock_api_client)

    with patch(
        "custom_components.plantlab._read_image_file",
        return_value=b"fake_image",
    ):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_DIAGNOSE,
            {"image_path": "/config/test.jpg"},
            blocking=True,
            return_response=True,
        )
    await hass.async_block_till_done()

    health = hass.states.get("sensor.plantlab_health")
    assert health.state == "unhealthy"

    problem = hass.states.get("binary_sensor.plantlab_problem")
    assert problem.state == "on"
