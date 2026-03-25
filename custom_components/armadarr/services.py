"""Services for Armadarr."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.core import ServiceCall, SupportsResponse
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class ArmadarrServiceError(Exception):
    """Base class for Armadarr service exceptions."""


async def async_get_client(hass: HomeAssistant, entry_id: str) -> Any:
    """Get client for entry_id."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if not entry:
        msg = f"Entry {entry_id} not found"
        raise ArmadarrServiceError(msg)
    return entry.runtime_data.client


async def async_handle_system_task(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle system task service call."""
    entry_id = call.data["entry_id"]
    task = str(call.data["task"])
    client = await async_get_client(hass, entry_id)

    if task.isdigit():
        # It's a task ID, trigger via ExecuteStoredTask command
        await client.command.execute(name="ExecuteStoredTask", taskId=int(task))
    else:
        # It's a command name, use the command endpoint
        await client.command.execute(name=task)


async def async_handle_search_missing(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle search missing service call."""
    entry_id = call.data["entry_id"]
    entry = hass.config_entries.async_get_entry(entry_id)
    if not entry:
        msg = f"Entry {entry_id} not found"
        raise ArmadarrServiceError(msg)

    client = entry.runtime_data.client
    app_type = entry.data["app_type"]

    command = "MissingSeriesSearch"
    if app_type == "Radarr":
        command = "MissingMoviesSearch"
    elif app_type == "Lidarr":
        command = "ArtistSearch"
    elif app_type == "Readarr":
        command = "AuthorSearch"

    await client.command.execute(name=command)


async def async_handle_add_series(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle add series service call."""
    entry_id = call.data["entry_id"]
    client = await async_get_client(hass, entry_id)

    tvdb_id = call.data.get("tvdb_id")
    title = call.data.get("title")

    if tvdb_id:
        series_lookup = await client.series.lookup(item_id=tvdb_id)
    elif title:
        series_lookup = await client.series.lookup(term=title)
    else:
        msg = "Either tvdb_id or title must be provided"
        raise ArmadarrServiceError(msg)

    if not series_lookup:
        msg = f"Series not found: {tvdb_id or title}"
        raise ArmadarrServiceError(msg)

    if len(series_lookup) > 1 and not tvdb_id:
        options = [
            f"{s.get('title')} (TVDB: {s.get('tvdbId')})" for s in series_lookup[:5]
        ]
        msg = (
            f"Multiple series found for '{title}'. Please use tvdb_id. "
            f"Options: {', '.join(options)}"
        )
        raise ArmadarrServiceError(msg)

    await client.series.add(
        series=series_lookup[0],
        root_dir=call.data["root_folder_path"],
        quality_profile_id=call.data["quality_profile_id"],
        language_profile_id=1,  # Default to 1
    )


async def async_handle_add_movie(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle add movie service call."""
    entry_id = call.data["entry_id"]
    client = await async_get_client(hass, entry_id)

    tmdb_id = call.data.get("tmdb_id")
    title = call.data.get("title")

    if tmdb_id:
        movie_lookup = await client.movie.lookup(term=f"tmdb:{tmdb_id}")
    elif title:
        movie_lookup = await client.movie.lookup(term=title)
    else:
        msg = "Either tmdb_id or title must be provided"
        raise ArmadarrServiceError(msg)

    if not movie_lookup:
        msg = f"Movie not found: {tmdb_id or title}"
        raise ArmadarrServiceError(msg)

    if len(movie_lookup) > 1 and not tmdb_id:
        options = [
            f"{m.get('title')} (TMDB: {m.get('tmdbId')})" for m in movie_lookup[:5]
        ]
        msg = (
            f"Multiple movies found for '{title}'. Please use tmdb_id. "
            f"Options: {', '.join(options)}"
        )
        raise ArmadarrServiceError(msg)

    await client.movie.add(
        movie=movie_lookup[0],
        root_dir=call.data["root_folder_path"],
        quality_profile_id=call.data["quality_profile_id"],
    )


async def async_handle_add_artist(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle add artist service call."""
    entry_id = call.data["entry_id"]
    client = await async_get_client(hass, entry_id)

    mb_id = call.data.get("mb_id")
    name = call.data.get("name")

    if mb_id:
        artist_lookup = await client.artist.lookup(term=f"lidarr:{mb_id}")
    elif name:
        artist_lookup = await client.artist.lookup(term=name)
    else:
        msg = "Either mb_id or name must be provided"
        raise ArmadarrServiceError(msg)

    if not artist_lookup:
        msg = f"Artist not found: {mb_id or name}"
        raise ArmadarrServiceError(msg)

    if len(artist_lookup) > 1 and not mb_id:
        options = [
            f"{a.get('artistName')} (MBID: {a.get('foreignArtistId')})"
            for a in artist_lookup[:5]
        ]
        msg = (
            f"Multiple artists found for '{name}'. Please use mb_id. "
            f"Options: {', '.join(options)}"
        )
        raise ArmadarrServiceError(msg)

    await client.artist.add(
        artist=artist_lookup[0],
        root_dir=call.data["root_folder_path"],
        quality_profile_id=call.data["quality_profile_id"],
        metadata_profile_id=call.data["metadata_profile_id"],
    )


async def async_handle_add_author(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle add author service call."""
    entry_id = call.data["entry_id"]
    client = await async_get_client(hass, entry_id)

    author_id = call.data.get("author_id")
    name = call.data.get("name")

    if author_id:
        # Readarr lookup term can be the ID directly or prefixed
        author_lookup = await client.author.lookup(term=author_id)
    elif name:
        author_lookup = await client.author.lookup(term=name)
    else:
        msg = "Either author_id or name must be provided"
        raise ArmadarrServiceError(msg)

    if not author_lookup:
        msg = f"Author not found: {author_id or name}"
        raise ArmadarrServiceError(msg)

    if len(author_lookup) > 1 and not author_id:
        options = [
            f"{a.get('authorName')} (ID: {a.get('foreignAuthorId')})"
            for a in author_lookup[:5]
        ]
        msg = (
            f"Multiple authors found for '{name}'. Please use author_id. "
            f"Options: {', '.join(options)}"
        )
        raise ArmadarrServiceError(msg)

    await client.author.add(
        author=author_lookup[0],
        root_dir=call.data["root_folder_path"],
        quality_profile_id=call.data["quality_profile_id"],
        metadata_profile_id=call.data["metadata_profile_id"],
    )


async def async_handle_lookup_series(
    hass: HomeAssistant, call: ServiceCall
) -> dict[str, Any]:
    """Handle lookup series service call."""
    entry_id = call.data["entry_id"]
    term = call.data["term"]
    client = await async_get_client(hass, entry_id)

    results = await client.series.lookup(term=term)
    return {"data": results}


async def async_handle_lookup_movie(
    hass: HomeAssistant, call: ServiceCall
) -> dict[str, Any]:
    """Handle lookup movie service call."""
    entry_id = call.data["entry_id"]
    term = call.data["term"]
    client = await async_get_client(hass, entry_id)

    results = await client.movie.lookup(term=term)
    return {"data": results}


async def async_handle_lookup_artist(
    hass: HomeAssistant, call: ServiceCall
) -> dict[str, Any]:
    """Handle lookup artist service call."""
    entry_id = call.data["entry_id"]
    term = call.data["term"]
    client = await async_get_client(hass, entry_id)

    results = await client.artist.lookup(term=term)
    return {"data": results}


async def async_handle_lookup_author(
    hass: HomeAssistant, call: ServiceCall
) -> dict[str, Any]:
    """Handle lookup author service call."""
    entry_id = call.data["entry_id"]
    term = call.data["term"]
    client = await async_get_client(hass, entry_id)

    results = await client.author.lookup(term=term)
    return {"data": results}


async def async_handle_get_upcoming_media(
    hass: HomeAssistant, call: ServiceCall
) -> dict[str, Any]:
    """Handle get upcoming media service call."""
    entry_id = call.data["entry_id"]
    days = call.data.get("days", 30)

    entry = hass.config_entries.async_get_entry(entry_id)
    if not entry:
        msg = f"Entry {entry_id} not found"
        raise ArmadarrServiceError(msg)

    client = entry.runtime_data.client
    app_type = entry.data["app_type"]

    start = datetime.now(tz=UTC)
    end = start + timedelta(days=days)

    # Build request parameters to include full resource details
    params: dict[str, Any] = {
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

    # Use http_utils.request directly to pass extra parameters
    # not supported by calendar.get()
    raw_events = await client.http_utils.request("calendar", params=params)

    if not isinstance(raw_events, list):
        return {"data": []}

    events = []
    for event in raw_events:
        item = _parse_event(event, app_type)
        if not item:
            continue

        # Ensure URLs are absolute if they are relative
        base_url = entry.data["url"].rstrip("/")
        api_key = entry.data["api_key"]

        if item.get("poster") and item["poster"].startswith("/"):
            sep = "&" if "?" in item["poster"] else "?"
            item["poster"] = f"{base_url}{item['poster']}{sep}apikey={api_key}"
        if item.get("fanart") and item["fanart"].startswith("/"):
            sep = "&" if "?" in item["fanart"] else "?"
            item["fanart"] = f"{base_url}{item['fanart']}{sep}apikey={api_key}"

        events.append(item)

    return {"data": events}


async def async_handle_delete_queue_item(
    hass: HomeAssistant, call: ServiceCall
) -> None:
    """Handle delete queue item service call."""
    entry_id = call.data["entry_id"]
    item_id = call.data["item_id"]
    client = await async_get_client(hass, entry_id)

    await client.queue.delete(item_id=item_id)


def _parse_images(item: dict[str, Any], images: list[dict[str, Any]]) -> None:
    """Extract poster and fanart from images list."""
    for img in images:
        if img.get("coverType") == "poster":
            item["poster"] = img.get("remoteUrl") or img.get("url")
        elif img.get("coverType") in ["fanart", "banner"]:
            item["fanart"] = img.get("remoteUrl") or img.get("url")


def _parse_resource_data(
    event: dict[str, Any], resource_key: str, item: dict[str, Any]
) -> None:
    """Parse resource data."""
    resource = event.get(resource_key, {})
    item.update(
        {
            "genres": ", ".join(resource.get("genres", [])),
            "summary": event.get("overview", ""),
        }
    )
    _parse_images(item, resource.get("images", []))


def _parse_radarr_event(event: dict[str, Any], item: dict[str, Any]) -> None:
    """Parse radarr event."""
    item.update(
        {
            "studio": event.get("studio", ""),
            "rating": event.get("ratings", {}).get("value", 0),
            "runtime": event.get("runtime", 0),
            "genres": ", ".join(event.get("genres", [])),
            "summary": event.get("overview", ""),
        }
    )
    _parse_images(item, event.get("images", []))


def _parse_sonarr_event(event: dict[str, Any], item: dict[str, Any]) -> None:
    """Parse sonarr and whisparr events."""
    series = event.get("series", {})
    season = event.get("seasonNumber", 0)
    episode = event.get("episodeNumber", 0)
    item.update(
        {
            "episode": event.get("title", ""),
            "title": series.get("title", "Unknown"),
            "number": f"S{season:02d}E{episode:02d}",
            "studio": series.get("network", ""),
            "rating": series.get("ratings", {}).get("value", 0),
            "runtime": series.get("runtime", 0),
        }
    )
    _parse_resource_data(event, "series", item)


def _parse_resource_event(
    event: dict[str, Any], resource_key: str, studio_key: str, item: dict[str, Any]
) -> None:
    """Parse resource event (Lidarr/Readarr)."""
    resource = event.get(resource_key, {})
    item.update(
        {
            "studio": resource.get(studio_key, ""),
            "rating": resource.get("ratings", {}).get("value", 0),
        }
    )
    _parse_resource_data(event, resource_key, item)


def _parse_event(event: dict[str, Any], app_type: str) -> dict[str, Any] | None:
    """Parse a single event based on app type."""
    item: dict[str, Any] = {}

    title = event.get("title")
    series_title = event.get("series", {}).get("title")
    movie_title = event.get("movie", {}).get("title")
    item["title"] = title or series_title or movie_title or "Unknown"

    airdate = (
        event.get("airDateUtc")
        or event.get("releaseDate")
        or event.get("physicalRelease")
    )
    if not airdate:
        return None
    item["airdate"] = airdate

    if app_type in {"Sonarr", "Whisparr"}:
        _parse_sonarr_event(event, item)
    elif app_type == "Radarr":
        _parse_radarr_event(event, item)
    elif app_type == "Lidarr":
        _parse_resource_event(event, "artist", "label", item)
    elif app_type == "Readarr":
        _parse_resource_event(event, "author", "publisher", item)
    return item


# Service schemas
SCHEMA_BASE = vol.Schema({vol.Required("entry_id"): cv.string})
SCHEMA_SYSTEM_TASK = SCHEMA_BASE.extend({vol.Required("task"): cv.string})
SCHEMA_GET_UPCOMING_MEDIA = SCHEMA_BASE.extend(
    {vol.Optional("days", default=30): cv.positive_int}
)
SCHEMA_DELETE_QUEUE_ITEM = SCHEMA_BASE.extend(
    {vol.Required("item_id"): cv.positive_int}
)
SCHEMA_LOOKUP = SCHEMA_BASE.extend({vol.Required("term"): cv.string})
SCHEMA_ADD_BASE = SCHEMA_BASE.extend(
    {
        vol.Required("quality_profile_id"): cv.positive_int,
        vol.Required("root_folder_path"): cv.string,
    }
)
SCHEMA_ADD_SERIES = SCHEMA_ADD_BASE.extend(
    {
        vol.Optional("title"): cv.string,
        vol.Optional("tvdb_id"): cv.positive_int,
    }
)
SCHEMA_ADD_MOVIE = SCHEMA_ADD_BASE.extend(
    {
        vol.Optional("title"): cv.string,
        vol.Optional("tmdb_id"): cv.positive_int,
    }
)
SCHEMA_ADD_ARTIST_AUTHOR_BASE = SCHEMA_ADD_BASE.extend(
    {
        vol.Optional("name"): cv.string,
        vol.Required("metadata_profile_id"): cv.positive_int,
    }
)
SCHEMA_ADD_ARTIST = SCHEMA_ADD_ARTIST_AUTHOR_BASE.extend(
    {vol.Optional("mb_id"): cv.string}
)
SCHEMA_ADD_AUTHOR = SCHEMA_ADD_ARTIST_AUTHOR_BASE.extend(
    {vol.Optional("author_id"): cv.string}
)


async def async_setup_services(hass: HomeAssistant, app_type: str) -> None:
    """Set up services for Armadarr based on app type."""

    def _register(
        name: str,
        handler: Any,
        schema: vol.Schema,
        response: SupportsResponse = SupportsResponse.NONE,
    ) -> None:
        if not hass.services.has_service(DOMAIN, name):
            hass.services.async_register(
                DOMAIN, name, handler, schema=schema, supports_response=response
            )

    # Common services
    _register(
        "system_task",
        lambda call: async_handle_system_task(hass, call),
        SCHEMA_SYSTEM_TASK,
    )
    _register(
        "search_missing",
        lambda call: async_handle_search_missing(hass, call),
        SCHEMA_BASE,
    )
    _register(
        "get_upcoming_media",
        lambda call: async_handle_get_upcoming_media(hass, call),
        SCHEMA_GET_UPCOMING_MEDIA,
        SupportsResponse.ONLY,
    )
    _register(
        "delete_queue_item",
        lambda call: async_handle_delete_queue_item(hass, call),
        SCHEMA_DELETE_QUEUE_ITEM,
    )

    # App-specific services
    app_services: dict[str, list[tuple[Any, ...]]] = {
        "Sonarr": [
            (
                "add_series",
                lambda call: async_handle_add_series(hass, call),
                SCHEMA_ADD_SERIES,
            ),
            (
                "lookup_series",
                lambda call: async_handle_lookup_series(hass, call),
                SCHEMA_LOOKUP,
                SupportsResponse.ONLY,
            ),
        ],
        "Radarr": [
            (
                "add_movie",
                lambda call: async_handle_add_movie(hass, call),
                SCHEMA_ADD_MOVIE,
            ),
            (
                "lookup_movie",
                lambda call: async_handle_lookup_movie(hass, call),
                SCHEMA_LOOKUP,
                SupportsResponse.ONLY,
            ),
        ],
        "Lidarr": [
            (
                "add_artist",
                lambda call: async_handle_add_artist(hass, call),
                SCHEMA_ADD_ARTIST,
            ),
            (
                "lookup_artist",
                lambda call: async_handle_lookup_artist(hass, call),
                SCHEMA_LOOKUP,
                SupportsResponse.ONLY,
            ),
        ],
        "Readarr": [
            (
                "add_author",
                lambda call: async_handle_add_author(hass, call),
                SCHEMA_ADD_AUTHOR,
            ),
            (
                "lookup_author",
                lambda call: async_handle_lookup_author(hass, call),
                SCHEMA_LOOKUP,
                SupportsResponse.ONLY,
            ),
        ],
    }
    app_services["Whisparr"] = app_services["Sonarr"]

    for service_info in app_services.get(app_type, []):
        _register(*service_info)
