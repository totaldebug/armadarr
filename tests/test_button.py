"""
Test the Armadarr button platform.

Every button's ``press_fn`` reaches straight into the pyarr client, so a button
offered for an app whose client lacks that component raises ``AttributeError``
the moment a user presses it. pyarr 6.8.0 made that failure mode real: it
removed ``backup`` and ``command`` from Bazarr and Dispatcharr, which had
previously answered both with the web UI's HTML page and so appeared to work.

These tests build the real entity list for each app type and press every button
against a real pyarr client with its transport stubbed out, so the attribute
lookups are genuine while no request leaves the process.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from pyarr import (
    AsyncBazarr,
    AsyncDispatcharr,
    AsyncLidarr,
    AsyncProwlarr,
    AsyncRadarr,
    AsyncReadarr,
    AsyncSonarr,
    AsyncWhisparr,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.armadarr.button import async_setup_entry
from custom_components.armadarr.const import (
    CONF_API_KEY,
    CONF_APP_TYPE,
    CONF_URL,
    CONF_VERIFY_SSL,
    DOMAIN,
)

if TYPE_CHECKING:
    from custom_components.armadarr.button import ArmadarrButton

CLIENTS = {
    "Sonarr": AsyncSonarr,
    "Radarr": AsyncRadarr,
    "Lidarr": AsyncLidarr,
    "Readarr": AsyncReadarr,
    "Whisparr": AsyncWhisparr,
    "Prowlarr": AsyncProwlarr,
    "Bazarr": AsyncBazarr,
    "Dispatcharr": AsyncDispatcharr,
}

EXPECTED_KEYS = {
    "Sonarr": {"restart", "backup"},
    "Radarr": {"restart", "backup"},
    "Lidarr": {"restart", "backup"},
    "Readarr": {"restart", "backup"},
    "Whisparr": {"restart", "backup"},
    "Prowlarr": {"restart", "backup", "sync_indexers"},
    # Bazarr has no backup endpoint.
    "Bazarr": {"restart", "search_missing_subtitles"},
    # Dispatcharr has no restart endpoint, and no indexers to sync.
    "Dispatcharr": {"backup", "reload_plugins"},
}


async def _build_buttons(
    hass: HomeAssistant, app_type: str
) -> tuple[list[ArmadarrButton], Any]:
    """Set up the button platform for ``app_type`` and return its entities."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_APP_TYPE: app_type,
            CONF_URL: "http://localhost:8989",
            CONF_API_KEY: "test-api-key",
            CONF_VERIFY_SSL: True,
        },
    )
    entry.add_to_hass(hass)

    client = CLIENTS[app_type]("http://localhost:8989", "test-api-key")

    coordinator = MagicMock()
    coordinator.config_entry = entry
    runtime_data = MagicMock()
    runtime_data.client = client
    runtime_data.standard_coordinator = coordinator
    entry.runtime_data = runtime_data

    added: list[ArmadarrButton] = []
    await async_setup_entry(hass, entry, added.extend)
    return added, client


@pytest.mark.parametrize("app_type", list(CLIENTS))
async def test_button_set_per_app_type(hass: HomeAssistant, app_type: str) -> None:
    """Only buttons the app's client can actually service are created."""
    buttons, _ = await _build_buttons(hass, app_type)

    assert {b.entity_description.key for b in buttons} == EXPECTED_KEYS[app_type]


@pytest.mark.parametrize("app_type", list(CLIENTS))
async def test_every_button_press_resolves_on_the_client(
    hass: HomeAssistant, app_type: str
) -> None:
    """
    Pressing any offered button must not raise AttributeError.

    The pyarr HTTP layer is stubbed, so the component and method lookups on the
    real client are exercised while nothing is sent over the network. This is
    the check that pyarr 6.8.0 would have failed for the Bazarr and Dispatcharr
    backup buttons and the Bazarr subtitle search.
    """
    buttons, client = await _build_buttons(hass, app_type)

    with patch.object(client.http_utils, "request", new=AsyncMock(return_value={})):
        for button in buttons:
            await button.async_press()


async def test_dispatcharr_backup_uses_the_plural_component(
    hass: HomeAssistant,
) -> None:
    """
    Dispatcharr names its backup component `backups`, not `backup`.

    Every other client uses the singular `backup`, so the button has to branch.
    Regression test for the AttributeError pyarr 6.8.0 introduced when it
    removed the singular `backup` from Dispatcharr.
    """
    buttons, client = await _build_buttons(hass, "Dispatcharr")
    backup_button = next(b for b in buttons if b.entity_description.key == "backup")

    with patch.object(client.backups, "create", new=AsyncMock()) as mock_create:
        await backup_button.async_press()

    mock_create.assert_awaited_once()
    assert not hasattr(client, "backup")


async def test_bazarr_subtitle_search_covers_series_and_movies(
    hass: HomeAssistant,
) -> None:
    """
    The Bazarr search button must run search-wanted on both halves of Bazarr.

    It previously posted a `SearchMissingSubtitles` command, which Bazarr never
    implemented: the request returned the web UI's HTML and searched nothing.
    Bazarr's real equivalent is the `search-wanted` action, which has to be run
    against series and movies separately.
    """
    buttons, client = await _build_buttons(hass, "Bazarr")
    search_button = next(
        b for b in buttons if b.entity_description.key == "search_missing_subtitles"
    )

    with (
        patch.object(client.series, "run_action", new=AsyncMock()) as mock_series,
        patch.object(client.movies, "run_action", new=AsyncMock()) as mock_movies,
    ):
        await search_button.async_press()

    mock_series.assert_awaited_once_with(action="search-wanted")
    mock_movies.assert_awaited_once_with(action="search-wanted")
