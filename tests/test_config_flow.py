"""Test Armadarr config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.armadarr.config_flow import ArmadarrFlowHandler
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

    with (
        patch(
            "custom_components.armadarr.config_flow.ArmadarrFlowHandler._test_connection",
            return_value=None,
        ),
        patch(
            "custom_components.armadarr.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
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


@pytest.mark.parametrize("verify_ssl", [True, False])
async def test_test_connection_passes_verify_ssl_to_session(
    hass: HomeAssistant, verify_ssl: bool
) -> None:
    """
    The verify_ssl choice must reach async_get_clientsession.

    pyarr only honours verify_ssl when it creates its own session; when a
    caller-supplied session is injected the flag is ignored. So the toggle only
    takes effect if we request the correctly-configured session from Home
    Assistant. Regression test for the "Verify SSL disabled but still get
    SSLCertVerificationError" report.
    """
    handler = ArmadarrFlowHandler()
    handler.hass = hass

    mock_client = MagicMock()
    mock_client.system.get_status = AsyncMock(return_value={})

    with (
        patch(
            "custom_components.armadarr.config_flow.async_get_clientsession"
        ) as mock_get_session,
        patch(
            "custom_components.armadarr.config_flow.AsyncRadarr",
            return_value=mock_client,
        ),
    ):
        await handler._test_connection(
            app_type="Radarr",
            url="https://home.lc/radarr",
            api_key="test-api-key",
            verify_ssl=verify_ssl,
        )

    mock_get_session.assert_called_once_with(hass, verify_ssl=verify_ssl)
