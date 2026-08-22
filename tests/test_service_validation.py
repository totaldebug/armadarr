"""
Test that services reject config entries of an app type they cannot serve.

Services are registered once per domain, so every service accepts any
``entry_id`` regardless of which app type caused it to be registered. A user
running both Sonarr and Radarr could call `armadarr.add_series` with the Radarr
entry, and the call reached pyarr and died with a raw AttributeError on a
component Radarr does not have.

Each service now states which app types it can serve and raises
ArmadarrServiceError naming the mismatch instead.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant, ServiceCall
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.armadarr.const import (
    CONF_API_KEY,
    CONF_APP_TYPE,
    CONF_URL,
    CONF_VERIFY_SSL,
    DOMAIN,
)
from custom_components.armadarr.services.handlers import (
    MEDIA_APPS,
    MOVIE_APPS,
    SERIES_APPS,
    ArmadarrServiceError,
    async_get_client,
    async_handle_get_config_data,
)


def _entry(hass: HomeAssistant, app_type: str) -> MockConfigEntry:
    """Register a config entry of ``app_type`` with a sentinel client."""
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

    class _Runtime:
        """Minimal runtime_data holder."""

        client = "sentinel-client"

    entry.runtime_data = _Runtime()
    return entry


async def test_matching_app_type_returns_the_client(hass: HomeAssistant) -> None:
    """A permitted app type resolves to its client as before."""
    entry = _entry(hass, "Sonarr")

    assert await async_get_client(hass, entry.entry_id, SERIES_APPS) == (
        "sentinel-client"
    )


async def test_series_service_rejects_a_radarr_entry(hass: HomeAssistant) -> None:
    """
    The case that motivated this: add_series against a Radarr entry.

    Radarr has no `series` component, so this used to surface as
    AttributeError from inside pyarr with no indication of the real mistake.
    """
    entry = _entry(hass, "Radarr")

    with pytest.raises(ArmadarrServiceError) as excinfo:
        await async_get_client(hass, entry.entry_id, SERIES_APPS)

    message = str(excinfo.value)
    assert "Sonarr" in message
    assert "Radarr" in message
    assert entry.entry_id in message


async def test_whisparr_is_accepted_by_movie_services(hass: HomeAssistant) -> None:
    """
    Whisparr must be allowed wherever Radarr is.

    Whisparr is movie-based and exposes pyarr's `movie` component, so the movie
    services are exactly the ones it can serve.
    """
    entry = _entry(hass, "Whisparr")

    assert await async_get_client(hass, entry.entry_id, MOVIE_APPS) == (
        "sentinel-client"
    )
    assert "Whisparr" in MOVIE_APPS
    assert "Whisparr" not in SERIES_APPS


@pytest.mark.parametrize("app_type", ["Bazarr", "Prowlarr", "Dispatcharr"])
async def test_media_services_reject_non_media_apps(
    hass: HomeAssistant, app_type: str
) -> None:
    """
    Queue and search services must reject the apps with no such components.

    pyarr 6.8.0 removed `queue` from all three, so these calls could only ever
    raise AttributeError.
    """
    entry = _entry(hass, app_type)

    with pytest.raises(ArmadarrServiceError):
        await async_get_client(hass, entry.entry_id, MEDIA_APPS)


async def test_no_app_types_accepts_anything(hass: HomeAssistant) -> None:
    """Passing no app types keeps the previous unrestricted behaviour."""
    entry = _entry(hass, "Dispatcharr")

    assert await async_get_client(hass, entry.entry_id) == "sentinel-client"
    assert await async_get_client(hass, entry.entry_id, None) == "sentinel-client"


async def test_unknown_entry_still_raises(hass: HomeAssistant) -> None:
    """A missing entry_id must raise before any app type check."""
    with pytest.raises(ArmadarrServiceError) as excinfo:
        await async_get_client(hass, "does-not-exist", SERIES_APPS)

    assert "not found" in str(excinfo.value)


def test_app_groups_are_consistent() -> None:
    """
    Every app-specific group must be a subset of the media apps.

    Guards against a group drifting to include an app that cannot serve it,
    which is the class of bug this validation exists to catch.
    """
    for group in (SERIES_APPS, MOVIE_APPS):
        assert set(group) <= set(MEDIA_APPS)


@pytest.mark.parametrize("app_type", ["Lidarr", "Readarr"])
async def test_get_config_data_returns_metadata_profiles(
    hass: HomeAssistant, app_type: str
) -> None:
    """
    Lidarr and Readarr both report metadata profiles.

    Lidarr was excluded because pyarr had no binding for its metadataprofile
    endpoint, so add_artist's required metadata_profile_id could not be
    discovered through the integration. pyarr 6.9.0 added it.
    """
    entry = _entry(hass, app_type)
    client = AsyncMock()
    client.root_folder.get = AsyncMock(return_value=[{"id": 1, "path": "/media"}])
    client.quality_profile.get = AsyncMock(return_value=[{"id": 1, "name": "Any"}])
    client.metadata_profile.get = AsyncMock(
        return_value=[{"id": 1, "name": "Standard"}]
    )
    entry.runtime_data.client = client

    call = ServiceCall(hass, DOMAIN, "get_config_data", {"entry_id": entry.entry_id})
    result = await async_handle_get_config_data(hass, call)

    assert result["data"]["metadata_profiles"] == [{"id": 1, "name": "Standard"}]
    client.metadata_profile.get.assert_awaited_once()


@pytest.mark.parametrize("app_type", ["Sonarr", "Radarr", "Whisparr"])
async def test_get_config_data_skips_metadata_profiles_elsewhere(
    hass: HomeAssistant, app_type: str
) -> None:
    """Apps without metadata profiles must not be asked for them."""
    entry = _entry(hass, app_type)
    client = AsyncMock()
    client.root_folder.get = AsyncMock(return_value=[])
    client.quality_profile.get = AsyncMock(return_value=[])
    entry.runtime_data.client = client

    call = ServiceCall(hass, DOMAIN, "get_config_data", {"entry_id": entry.entry_id})
    result = await async_handle_get_config_data(hass, call)

    assert "metadata_profiles" not in result["data"]
    client.metadata_profile.get.assert_not_awaited()
