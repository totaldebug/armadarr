"""
Test the Armadarr coordinators against real pyarr clients.

The coordinators pick which components to touch from the config entry's app
type, so a component that pyarr no longer exposes for that app takes down the
whole update: the fetch happens inside one try block that turns any exception
into UpdateFailed, so a single bad attribute blanks every sensor for that app.

pyarr 6.8.0 removed `indexer` from Dispatcharr, which is correct - Dispatcharr
is an IPTV proxy and has no indexers - and that killed the Dispatcharr standard
update entirely. These tests run the coordinators against real clients with the
transport stubbed, so every attribute lookup is genuine.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

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

from custom_components.armadarr.const import (
    CONF_API_KEY,
    CONF_APP_TYPE,
    CONF_URL,
    CONF_VERIFY_SSL,
    DOMAIN,
)
from custom_components.armadarr.coordinator import DailyCoordinator, StandardCoordinator

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

MEDIA_APPS = ["Sonarr", "Radarr", "Lidarr", "Readarr", "Whisparr"]

# The data key each media app's daily update fills. Whisparr is movie-based, so
# it reports movies like Radarr rather than series like Sonarr.
DAILY_KEY = {
    "Sonarr": "series",
    "Radarr": "movies",
    "Lidarr": "artists",
    "Readarr": "authors",
    "Whisparr": "movies",
}


async def _stub_request(path: str, *_args: Any, **_kwargs: Any) -> Any:
    """
    Stand in for pyarr's HTTP layer, matching each endpoint's expected shape.

    pyarr validates the response type per endpoint and raises on a mismatch, so
    the stub has to hand back a list where a list is expected. Only calendar
    differs among the endpoints the coordinators touch.
    """
    if "calendar" in path:
        return []
    if path == "wanted/missing":
        return {"totalRecords": 2, "records": [{"id": 1}, {"id": 2}]}
    return {}


def _entry(hass: HomeAssistant, app_type: str) -> tuple[MockConfigEntry, Any]:
    """Build a config entry for ``app_type`` wired to a real pyarr client."""
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
    return entry, client


@pytest.mark.parametrize("app_type", list(CLIENTS))
async def test_standard_update_touches_only_available_components(
    hass: HomeAssistant, app_type: str
) -> None:
    """
    The standard update must complete for every app type.

    Any component missing from the client raises inside the coordinator's try
    block and surfaces as UpdateFailed, so this passing means every attribute
    the app_type branch reaches for genuinely exists on that client.
    """
    entry, client = _entry(hass, app_type)
    coordinator = StandardCoordinator(hass, entry)
    entry.runtime_data = SimpleNamespace(client=client)

    with patch.object(client.http_utils, "request", new=AsyncMock(
        side_effect=_stub_request
    )):
        data = await coordinator._async_update_data()

    assert isinstance(data, dict)


async def test_dispatcharr_update_does_not_request_indexers(
    hass: HomeAssistant,
) -> None:
    """
    Dispatcharr has no indexers, so the update must not ask for any.

    pyarr 6.8.0 removed the `indexer` component from Dispatcharr because the
    endpoint only ever returned the web UI's HTML page. The coordinator used to
    fetch it into `indexer_status`, which both fed a nonsense Indexer Count
    sensor and, from 6.8.0 on, raised AttributeError and failed every update.
    """
    entry, client = _entry(hass, "Dispatcharr")
    coordinator = StandardCoordinator(hass, entry)
    entry.runtime_data = SimpleNamespace(client=client)

    with patch.object(client.http_utils, "request", new=AsyncMock(
        side_effect=_stub_request
    )):
        data = await coordinator._async_update_data()

    assert "indexer_status" not in data
    assert not hasattr(client, "indexer")
    # The Dispatcharr-specific payload must still be fetched.
    assert "channels" in data
    assert "streams" in data
    assert "hdhr_devices" in data


@pytest.mark.parametrize("app_type", MEDIA_APPS)
async def test_daily_update_populates_the_right_media_key(
    hass: HomeAssistant, app_type: str
) -> None:
    """
    Every media app's daily update must complete and fill its own data key.

    Whisparr is the reason this exists: it was grouped with Sonarr and asked for
    `client.series.get()`, which Whisparr has never exposed, so the update raised
    and left missing_count and wanted empty too - they share one try block.
    """
    entry, client = _entry(hass, app_type)
    coordinator = DailyCoordinator(hass, entry)
    entry.runtime_data = SimpleNamespace(client=client)

    with patch.object(client.http_utils, "request", new=AsyncMock(
        side_effect=_stub_request
    )):
        data = await coordinator._async_update_data()

    assert DAILY_KEY[app_type] in data
    assert "unmonitored_count" in data
    assert data["missing_count"] == 2
    assert len(data["wanted"]) == 2


async def test_whisparr_daily_update_asks_for_movies_not_series(
    hass: HomeAssistant,
) -> None:
    """
    Whisparr's daily update must hit the movie endpoint with movie parameters.

    Beyond the endpoint itself, the wanted query used to sort by airDateUtc and
    ask for includeSeries, both of which are episode concepts Whisparr has no
    field for. It now sorts by releaseDate and asks for includeMovie.
    """
    entry, client = _entry(hass, "Whisparr")
    coordinator = DailyCoordinator(hass, entry)
    entry.runtime_data = SimpleNamespace(client=client)

    requested: list[tuple[str, dict[str, Any] | None]] = []

    async def _record(path: str, *_args: Any, **kwargs: Any) -> Any:
        requested.append((path, kwargs.get("params")))
        return await _stub_request(path)

    with patch.object(client.http_utils, "request", new=AsyncMock(
        side_effect=_record
    )):
        data = await coordinator._async_update_data()

    paths = [path for path, _ in requested]
    assert "movie" in paths
    assert "series" not in paths
    assert data["movies"] is not None

    wanted_params = [
        params for path, params in requested if path == "wanted/missing" and params
    ]
    sorted_query = next(p for p in wanted_params if "sortKey" in p)
    assert sorted_query["sortKey"] == "releaseDate"
    assert sorted_query.get("includeMovie") is True
    assert "includeSeries" not in sorted_query
