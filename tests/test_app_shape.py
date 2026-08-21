"""
Test the per-app-type wiring: which sensors, services and parser each app gets.

Whisparr is the reason this file exists. pyarr models Whisparr as Radarr-shaped
- it exposes `movie` and has no `series` or `episode` component - but the
integration used to group Whisparr with Sonarr everywhere, so it was offered
series sensors fed by a data key nothing filled, and add_series/lookup_series
services that could only ever raise AttributeError.

These tests pin the grouping at each place it is decided, so a future change
that moves Whisparr back alongside Sonarr fails here rather than silently.
"""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from custom_components.armadarr.parsers import parse_event
from custom_components.armadarr.sensor_descriptions import get_app_specific_sensors
from custom_components.armadarr.services import async_setup_services


def test_whisparr_gets_the_same_sensors_as_radarr() -> None:
    """Whisparr reports movies, so its sensor set must match Radarr's."""
    whisparr = [d.key for d in get_app_specific_sensors("Whisparr")]

    assert whisparr == [d.key for d in get_app_specific_sensors("Radarr")]
    assert whisparr == ["movie_count"]
    assert "series_count" not in whisparr


@pytest.mark.parametrize(
    ("app_type", "expected"),
    [
        ("Sonarr", ["series_count"]),
        ("Radarr", ["movie_count"]),
        ("Whisparr", ["movie_count"]),
        ("Lidarr", ["artist_count"]),
        ("Readarr", ["author_count"]),
    ],
)
def test_media_sensor_keys_per_app(app_type: str, expected: list[str]) -> None:
    """Each media app reports the count of the resource it actually holds."""
    assert [d.key for d in get_app_specific_sensors(app_type)] == expected


async def test_whisparr_registers_movie_services_not_series(
    hass: HomeAssistant,
) -> None:
    """
    Whisparr must get add_movie and lookup_movie, never the series pair.

    add_series calls client.series.lookup, which Whisparr does not have, so the
    service was guaranteed to raise the moment anyone called it.
    """
    await async_setup_services(hass, "Whisparr")

    assert hass.services.has_service("armadarr", "add_movie")
    assert hass.services.has_service("armadarr", "lookup_movie")
    assert not hass.services.has_service("armadarr", "add_series")
    assert not hass.services.has_service("armadarr", "lookup_series")


def test_whisparr_events_parse_as_movies() -> None:
    """
    A Whisparr calendar event carries movie fields at the top level.

    Whisparr's calendar returns movie resources, so the parser must read studio,
    genres and images off the event itself rather than looking for a nested
    series object the way the Sonarr parser does.
    """
    event = {
        "id": 7,
        "title": "A Scene",
        "releaseDate": "2026-08-21T00:00:00Z",
        "studio": "A Studio",
        "runtime": 42,
        "genres": ["One", "Two"],
        "ratings": {"value": 8.5},
        "images": [{"coverType": "poster", "remoteUrl": "http://img/poster.jpg"}],
    }

    item = parse_event(event, "Whisparr")

    assert item is not None
    assert item["title"] == "A Scene"
    assert item["studio"] == "A Studio"
    assert item["runtime"] == 42
    assert item["genres"] == "One, Two"
    assert item["rating"] == 8.5
    assert item["poster"] == "http://img/poster.jpg"
    # Sonarr-only episode numbering must not appear.
    assert "number" not in item
