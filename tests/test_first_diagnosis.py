from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components import persistent_notification
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.plantlab.const import (
    CONF_CAMERA_ENTITY,
    CONF_DAILY_TIME,
    CONF_FIRST_RUN_NOTIFIED,
    DOMAIN,
    OPTIONS_URL,
)

from .conftest import DIAGNOSE_RESPONSE_UNHEALTHY

BUTTON_ID = "button.plantlab_diagnose"
CAMERA_OPTIONS = {CONF_CAMERA_ENTITY: "camera.grow_tent", CONF_DAILY_TIME: "08:30:00"}
CAMERA_IMAGE = "custom_components.plantlab._get_image_from_camera"


async def _setup(hass, entry, client):
    with patch("custom_components.plantlab.PlantLabApiClient", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()


def _notifications(hass):
    return persistent_notification._async_get_or_create_notifications(hass)


async def test_button_diagnoses_chosen_camera(hass: HomeAssistant, mock_config_entry, mock_api_client):
    mock_api_client.async_diagnose = AsyncMock(return_value=DIAGNOSE_RESPONSE_UNHEALTHY)
    hass.config_entries.async_update_entry(mock_config_entry, options=CAMERA_OPTIONS)
    await _setup(hass, mock_config_entry, mock_api_client)

    with patch(CAMERA_IMAGE, new_callable=AsyncMock, return_value=b"camera_image") as get_image:
        await hass.services.async_call("button", SERVICE_PRESS, {"entity_id": BUTTON_ID}, blocking=True)
    await hass.async_block_till_done()

    get_image.assert_awaited_once_with(hass, "camera.grow_tent")
    mock_api_client.async_diagnose.assert_called_once_with(b"camera_image", filename="snapshot.jpg")
    assert hass.states.get("sensor.plantlab_health").state == "unhealthy"


async def test_button_without_camera_raises(hass: HomeAssistant, mock_config_entry, mock_api_client):
    await _setup(hass, mock_config_entry, mock_api_client)

    with pytest.raises(ServiceValidationError, match="Choose a camera"):
        await hass.services.async_call("button", SERVICE_PRESS, {"entity_id": BUTTON_ID}, blocking=True)
    mock_api_client.async_diagnose.assert_not_called()


async def test_options_flow_saves_camera_and_time(hass: HomeAssistant, mock_config_entry, mock_api_client):
    await _setup(hass, mock_config_entry, mock_api_client)

    form = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert form["step_id"] == "init"

    with patch("custom_components.plantlab.PlantLabApiClient", return_value=mock_api_client):
        result = await hass.config_entries.options.async_configure(form["flow_id"], user_input=CAMERA_OPTIONS)
        await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    assert mock_config_entry.options == CAMERA_OPTIONS


async def test_options_flow_accepts_empty_input(hass: HomeAssistant, mock_config_entry, mock_api_client):
    await _setup(hass, mock_config_entry, mock_api_client)

    form = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    with patch("custom_components.plantlab.PlantLabApiClient", return_value=mock_api_client):
        result = await hass.config_entries.options.async_configure(form["flow_id"], user_input={})
        await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    assert mock_config_entry.options == {}


async def test_daily_diagnosis_runs_at_chosen_time(hass: HomeAssistant, mock_config_entry, mock_api_client, freezer):
    freezer.move_to(dt_util.now().replace(hour=8, minute=0, second=0, microsecond=0))
    hass.config_entries.async_update_entry(mock_config_entry, options=CAMERA_OPTIONS)
    await _setup(hass, mock_config_entry, mock_api_client)

    with patch(CAMERA_IMAGE, new_callable=AsyncMock, return_value=b"scheduled") as get_image:
        freezer.tick(timedelta(minutes=29))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        mock_api_client.async_diagnose.assert_not_called()

        freezer.tick(timedelta(minutes=1))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

    get_image.assert_awaited_once_with(hass, "camera.grow_tent")
    mock_api_client.async_diagnose.assert_called_once_with(b"scheduled", filename="snapshot.jpg")


async def test_daily_diagnosis_failure_is_logged_not_raised(
    hass: HomeAssistant, mock_config_entry, mock_api_client, freezer, caplog
):
    freezer.move_to(dt_util.now().replace(hour=8, minute=29, second=59, microsecond=0))
    hass.config_entries.async_update_entry(mock_config_entry, options=CAMERA_OPTIONS)
    await _setup(hass, mock_config_entry, mock_api_client)

    with patch(CAMERA_IMAGE, new_callable=AsyncMock, side_effect=HomeAssistantError("camera offline")):
        freezer.tick(timedelta(seconds=1))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

    assert "Daily PlantLab diagnosis failed: camera offline" in caplog.text


@pytest.mark.parametrize(
    "options",
    [{}, {CONF_CAMERA_ENTITY: "camera.grow_tent"}, {CONF_DAILY_TIME: "08:30:00"}],
)
async def test_daily_diagnosis_needs_camera_and_time(
    hass: HomeAssistant, mock_config_entry, mock_api_client, freezer, options
):
    freezer.move_to(dt_util.now().replace(hour=8, minute=29, second=59, microsecond=0))
    hass.config_entries.async_update_entry(mock_config_entry, options=options)
    await _setup(hass, mock_config_entry, mock_api_client)

    with patch(CAMERA_IMAGE, new_callable=AsyncMock, return_value=b"x"):
        freezer.tick(timedelta(seconds=1))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

    mock_api_client.async_diagnose.assert_not_called()


async def test_unload_cancels_daily_diagnosis(hass: HomeAssistant, mock_config_entry, mock_api_client, freezer):
    freezer.move_to(dt_util.now().replace(hour=8, minute=29, second=59, microsecond=0))
    hass.config_entries.async_update_entry(mock_config_entry, options=CAMERA_OPTIONS)
    await _setup(hass, mock_config_entry, mock_api_client)

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    with patch(CAMERA_IMAGE, new_callable=AsyncMock, return_value=b"x"):
        freezer.tick(timedelta(seconds=1))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

    mock_api_client.async_diagnose.assert_not_called()


async def test_first_run_notification_links_to_options_and_covers_no_camera(
    hass: HomeAssistant, mock_config_entry, mock_api_client
):
    await _setup(hass, mock_config_entry, mock_api_client)

    notification = _notifications(hass)[f"{DOMAIN}_first_diagnosis_{mock_config_entry.entry_id}"]
    assert OPTIONS_URL in notification["message"]
    assert "No camera?" in notification["message"]
    assert "image_path" in notification["message"]
    assert notification["title"] == "PlantLab: run your first diagnosis"
    assert mock_config_entry.data[CONF_FIRST_RUN_NOTIFIED] is True


async def test_first_run_notification_is_not_repeated_after_reload(
    hass: HomeAssistant, mock_config_entry, mock_api_client
):
    await _setup(hass, mock_config_entry, mock_api_client)
    persistent_notification.async_dismiss(hass, f"{DOMAIN}_first_diagnosis_{mock_config_entry.entry_id}")

    with patch("custom_components.plantlab.PlantLabApiClient", return_value=mock_api_client):
        assert await hass.config_entries.async_reload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert _notifications(hass) == {}


async def test_first_run_notification_dismissed_once_scheduled(hass: HomeAssistant, mock_config_entry, mock_api_client):
    await _setup(hass, mock_config_entry, mock_api_client)
    assert _notifications(hass)

    form = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    with patch("custom_components.plantlab.PlantLabApiClient", return_value=mock_api_client):
        await hass.config_entries.options.async_configure(form["flow_id"], user_input=CAMERA_OPTIONS)
        await hass.async_block_till_done()

    assert _notifications(hass) == {}
