from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.plantlab.api import PlantLabAuthError, PlantLabConnectionError
from custom_components.plantlab.const import CONF_API_KEY, CONF_HOST, DEFAULT_HOST, DOMAIN

from .conftest import MOCK_API_KEY


async def test_config_flow_valid_key(hass: HomeAssistant):
    with (
        patch("custom_components.plantlab.config_flow.PlantLabApiClient") as mock_cls,
        patch(
            "custom_components.plantlab.async_setup_entry",
            return_value=True,
        ),
    ):
        mock_cls.return_value.async_validate = AsyncMock(return_value=True)

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_HOST: DEFAULT_HOST},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "PlantLab"
    assert result["data"][CONF_API_KEY] == MOCK_API_KEY

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_config_flow_invalid_key(hass: HomeAssistant):
    with patch("custom_components.plantlab.config_flow.PlantLabApiClient") as mock_cls:
        mock_cls.return_value.async_validate = AsyncMock(side_effect=PlantLabAuthError("Invalid API key"))

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: "bad_key", CONF_HOST: DEFAULT_HOST},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"]["base"] == "invalid_auth"


async def test_config_flow_cannot_connect(hass: HomeAssistant):
    with patch("custom_components.plantlab.config_flow.PlantLabApiClient") as mock_cls:
        mock_cls.return_value.async_validate = AsyncMock(side_effect=PlantLabConnectionError("Connection refused"))

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_HOST: "https://bad.host"},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"]["base"] == "cannot_connect"


async def test_config_flow_duplicate(hass: HomeAssistant):
    with patch("custom_components.plantlab.config_flow.PlantLabApiClient") as mock_cls:
        mock_cls.return_value.async_validate = AsyncMock(return_value=True)

        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_HOST: DEFAULT_HOST},
        )

        result2 = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
        result2 = await hass.config_entries.flow.async_configure(
            result2["flow_id"],
            {CONF_API_KEY: MOCK_API_KEY, CONF_HOST: DEFAULT_HOST},
        )
        assert result2["type"] is FlowResultType.ABORT
        assert result2["reason"] == "already_configured"
