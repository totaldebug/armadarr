"""Test Armadarr config flow."""

from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.armadarr.const import (
    CONF_API_KEY,
    CONF_APP_TYPE,
    CONF_UPCOMING_DAYS,
    CONF_URL,
    CONF_VERIFY_SSL,
    CONF_WANTED_COUNT,
    DOMAIN,
)


async def test_flow_user_media_app(hass: HomeAssistant) -> None:
    """Test user initialized flow for a media app (two steps)."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.armadarr.config_flow.ArmadarrFlowHandler._test_connection",
        return_value=None,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_APP_TYPE: "Sonarr",
                CONF_URL: "http://localhost:8989",
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "options"

    with patch(
        "custom_components.armadarr.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_UPCOMING_DAYS: 14,
                CONF_WANTED_COUNT: 20,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Sonarr (http://localhost:8989)"
    assert result["data"] == {
        CONF_APP_TYPE: "Sonarr",
        CONF_URL: "http://localhost:8989",
        CONF_API_KEY: "test-api-key",
        CONF_VERIFY_SSL: True,
        CONF_UPCOMING_DAYS: 14,
        CONF_WANTED_COUNT: 20,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_flow_user_non_media_app(hass: HomeAssistant) -> None:
    """Test user initialized flow for a non-media app (one step)."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.armadarr.config_flow.ArmadarrFlowHandler._test_connection",
        return_value=None,
    ), patch(
        "custom_components.armadarr.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_APP_TYPE: "Prowlarr",
                CONF_URL: "http://localhost:9696",
                CONF_API_KEY: "test-api-key",
                CONF_VERIFY_SSL: True,
            },
        )
        await hass.async_block_till_done()

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Prowlarr (http://localhost:9696)"
    assert result["data"] == {
        CONF_APP_TYPE: "Prowlarr",
        CONF_URL: "http://localhost:9696",
        CONF_API_KEY: "test-api-key",
        CONF_VERIFY_SSL: True,
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test options flow."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Sonarr",
        data={
            CONF_APP_TYPE: "Sonarr",
            CONF_URL: "http://localhost:8989",
            CONF_API_KEY: "test-api-key",
        },
        entry_id="test",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_UPCOMING_DAYS: 7,
            CONF_WANTED_COUNT: 10,
        },
    )

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_UPCOMING_DAYS: 7,
        CONF_WANTED_COUNT: 10,
    }
    assert entry.options == {
        CONF_UPCOMING_DAYS: 7,
        CONF_WANTED_COUNT: 10,
    }


async def test_options_flow_prowlarr(hass: HomeAssistant) -> None:
    """Test options flow for Prowlarr (no options)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Prowlarr",
        data={
            CONF_APP_TYPE: "Prowlarr",
            CONF_URL: "http://localhost:9696",
            CONF_API_KEY: "test-api-key",
        },
        entry_id="test_prowlarr",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    # Should create entry immediately as there are no options
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"] == {}
