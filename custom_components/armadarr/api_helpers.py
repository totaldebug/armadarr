"""API helpers for Armadarr data fetching."""

from __future__ import annotations

import contextlib
from datetime import UTC, datetime, timedelta
from typing import Any

from .const import LOGGER


async def fetch_standard_data(
    client: Any,
    app_type: str,
    last_history_id: int | None,
    entry_id: str,
    hass: Any,
    upcoming_days: int,
) -> tuple[dict[str, Any], int | None]:
    """Fetch standard data (5 min interval)."""
    data = {}
    new_last_history_id = last_history_id

    # Common data for most apps
    if app_type not in ["Bazarr", "Prowlarr"]:
        data["queue"] = await client.queue.get()
        data["health"] = await client.system.get_health()
        data["root_folder"] = await client.root_folder.get()
        data["quality_profile"] = await client.quality_profile.get()
        data["system_status"] = await client.system.get_status()

        # Fetch history for events
        history = await client.history.get(page=1, page_size=10)
        if history and "records" in history:
            records = history["records"]
            if last_history_id is not None:
                for record in reversed(records):  # Process oldest to newest
                    if record.get("id", 0) > last_history_id:
                        event_data = {
                            "app_type": app_type,
                            "entry_id": entry_id,
                            "event_type": record.get("eventType"),
                            "source_title": record.get("sourceTitle"),
                            "date": record.get("date"),
                        }
                        hass.bus.async_fire("armadarr_history_event", event_data)

            if records:
                new_last_history_id = max(r.get("id", 0) for r in records)

    # Calendar data
    if app_type in ["Sonarr", "Radarr", "Lidarr", "Readarr", "Whisparr"]:
        data["calendar"] = await _fetch_calendar_data(client, app_type, upcoming_days)

    if app_type == "Bazarr":
        with contextlib.suppress(Exception):
            data["system_status"] = await client.system.get_status()

    if app_type == "Prowlarr":
        data["indexer_status"] = await client.indexer.get()

    return data, new_last_history_id


async def _fetch_calendar_data(client: Any, app_type: str, upcoming_days: int) -> Any:
    """Fetch calendar data with app-specific parameters."""
    start = datetime.now(tz=UTC)
    end = start + timedelta(days=upcoming_days)

    params = {
        "start": start.strftime("%Y-%m-%d"),
        "end": end.strftime("%Y-%m-%d"),
        "unmonitored": "true",
    }
    if app_type in ["Sonarr", "Whisparr"]:
        params["includeSeries"] = "true"
    elif app_type == "Radarr":
        params["includeMovie"] = "true"
    elif app_type == "Lidarr":
        params["includeArtist"] = "true"
    elif app_type == "Readarr":
        params["includeAuthor"] = "true"

    return await client.http_utils.request("calendar", params=params)


async def fetch_daily_data(
    client: Any, app_type: str, entry_id: str, hass: Any, wanted_count: int
) -> dict[str, Any]:
    """Fetch daily data (12 hour interval)."""
    data = {}

    if app_type in ["Sonarr", "Whisparr"]:
        data["series"] = await client.series.get()
        data["unmonitored_count"] = sum(
            1 for s in data["series"] if not s.get("monitored")
        )
    elif app_type == "Radarr":
        data["movies"] = await client.movie.get()
        data["unmonitored_count"] = sum(
            1 for m in data["movies"] if not m.get("monitored")
        )
    elif app_type == "Lidarr":
        data["artists"] = await client.artist.get()
        data["unmonitored_count"] = sum(
            1 for a in data["artists"] if not a.get("monitored")
        )
    elif app_type == "Readarr":
        data["authors"] = await client.author.get()
        data["unmonitored_count"] = sum(
            1 for a in data["authors"] if not a.get("monitored")
        )
    elif app_type == "Prowlarr":
        data["indexers"] = await client.indexer_proxy.get()

    if app_type in ["Sonarr", "Whisparr", "Radarr", "Lidarr", "Readarr"]:
        data["missing_count"] = await _fetch_missing_count(client, app_type)
        data["wanted"] = await _fetch_wanted_data(client, app_type, wanted_count)

    return data


async def _fetch_wanted_data(
    client: Any, app_type: str, wanted_count: int
) -> list[dict[str, Any]]:
    """Fetch wanted data."""
    params = {
        "page": 1,
        "pageSize": wanted_count,
        "sortKey": "airDateUtc" if app_type in ["Sonarr", "Whisparr"] else "releaseDate",
        "sortDirection": "descending",
    }
    if app_type in ["Sonarr", "Whisparr"]:
        params["includeSeries"] = "true"
    elif app_type == "Radarr":
        params["includeMovie"] = "true"
    elif app_type == "Lidarr":
        params["includeArtist"] = "true"
    elif app_type == "Readarr":
        params["includeAuthor"] = "true"

    try:
        raw_data = await client.http_utils.request("wanted/missing", params=params)
        if isinstance(raw_data, dict) and "records" in raw_data:
            return raw_data["records"]
    except Exception as e:  # noqa: BLE001
        LOGGER.warning("Failed to fetch wanted data for %s: %s", app_type, e)
    return []


async def _fetch_missing_count(client: Any, app_type: str) -> int:
    """Fetch missing count for the app."""
    try:
        missing_data = await client.http_utils.request(
            "wanted/missing", params={"page": 1, "pageSize": 1}
        )
        return int(missing_data.get("totalRecords", 0))
    except Exception as e:  # noqa: BLE001
        LOGGER.warning("Failed to fetch missing count for %s: %s", app_type, e)
        return 0
