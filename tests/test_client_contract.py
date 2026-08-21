"""
Pin the pyarr surface that Armadarr depends on.

pyarr 6.8.0 removed components from the clients whose APIs never answered them,
so a call that used to fail at the network (a Prowlarr 404, or a Bazarr and
Dispatcharr 200 carrying the web UI's HTML) now raises ``AttributeError`` at
attribute lookup. Nothing in the integration exercised those paths under test,
so the breakage was invisible until runtime.

These tests walk every ``client.<component>.<method>`` path the integration
references and assert it resolves on a real pyarr client. They need no network:
constructing a client and looking up an attribute is entirely local. A future
pyarr release that moves or drops a component fails here instead of in a user's
Home Assistant log.
"""

from __future__ import annotations

import pytest
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

# StandardCoordinator, for every app that is not Bazarr/Prowlarr/Dispatcharr.
STANDARD_PATHS = [
    "queue.get",
    "system.get_health",
    "root_folder.get",
    "quality_profile.get",
    "history.get",
    "calendar.get",
]

# StandardCoordinator._fetch_dispatcharr, plus the Dispatcharr-only buttons.
DISPATCHARR_PATHS = [
    "channels.get",
    "streams.get",
    "vod.get_all",
    "plugins.get",
    "plugins.reload",
    "backups.get",
    "backups.create",
    "m3u.get_accounts",
    "m3u.refresh",
    "epg.get_sources",
    "proxy.get_ts_status",
    "channel_groups.get",
    "channel_profiles.get",
    "connect.get_integrations",
    "hdhr.get_devices",
]

# DailyCoordinator and the add/lookup services, per app. Whisparr is
# movie-based, so it takes Radarr's paths rather than Sonarr's.
DAILY_PATHS = {
    "Sonarr": ["series.get", "series.add", "series.lookup", "wanted.get"],
    "Radarr": ["movie.get", "movie.add", "movie.lookup", "wanted.get"],
    "Lidarr": ["artist.get", "artist.add", "artist.lookup", "wanted.get"],
    "Readarr": [
        "author.get",
        "author.add",
        "author.lookup",
        "wanted.get",
        "metadata_profile.get",
    ],
    "Whisparr": ["movie.get", "movie.add", "movie.lookup", "wanted.get"],
}


def _expected_paths(app_type: str) -> list[str]:
    """Return every pyarr attribute path the integration uses for ``app_type``."""
    # system.get_status is fetched for every app, Bazarr included.
    paths = ["system.get_status"]

    if app_type in MEDIA_APPS:
        paths += STANDARD_PATHS
        paths += DAILY_PATHS[app_type]
        # Buttons and service handlers.
        paths += ["system.request_restart", "backup.create", "command.execute"]
    elif app_type == "Prowlarr":
        paths += ["indexer.get", "indexer.get_stats"]
        paths += ["system.request_restart", "backup.create", "command.execute"]
    elif app_type == "Bazarr":
        # The Search Missing Subtitles button, which 6.8.0 moved off `command`.
        paths += ["series.run_action", "movies.run_action"]
        paths += ["system.request_restart"]
    elif app_type == "Dispatcharr":
        paths += DISPATCHARR_PATHS

    return paths


def _resolve(client: object, path: str) -> object:
    """Walk a dotted ``component.method`` path on ``client``, or raise."""
    target = client
    for part in path.split("."):
        target = getattr(target, part)
    return target


@pytest.mark.parametrize("app_type", list(CLIENTS))
def test_client_exposes_every_path_the_integration_uses(app_type: str) -> None:
    """Every component and method the integration references must exist."""
    client = CLIENTS[app_type]("http://localhost", "test-api-key")

    missing = []
    for path in _expected_paths(app_type):
        try:
            _resolve(client, path)
        except AttributeError:
            missing.append(path)

    assert not missing, f"{app_type} client is missing: {', '.join(missing)}"


@pytest.mark.parametrize(
    ("app_type", "absent"),
    [
        # Removed by pyarr 6.8.0 because Prowlarr answered each with a 404.
        ("Prowlarr", "queue"),
        ("Prowlarr", "root_folder"),
        ("Prowlarr", "quality_profile"),
        ("Prowlarr", "calendar"),
        # Removed because Bazarr served the web UI's HTML instead of data.
        ("Bazarr", "backup"),
        ("Bazarr", "command"),
        ("Bazarr", "queue"),
        ("Bazarr", "history"),
        # Same for Dispatcharr, which is an IPTV proxy with no indexers at all.
        ("Dispatcharr", "backup"),
        ("Dispatcharr", "command"),
        ("Dispatcharr", "indexer"),
        ("Dispatcharr", "queue"),
        ("Dispatcharr", "root_folder"),
        ("Dispatcharr", "quality_profile"),
    ],
)
def test_component_absent_so_callers_must_stay_guarded(
    app_type: str, absent: str
) -> None:
    """
    Components pyarr 6.8.0 removed must stay absent.

    The integration guards these by app_type rather than probing for them, so a
    guard that loses its app_type is a runtime AttributeError. Asserting the
    absence keeps the guards honest: if pyarr ever restores one of these, this
    test fails and the guard can be revisited deliberately.
    """
    client = CLIENTS[app_type]("http://localhost", "test-api-key")

    assert not hasattr(client, absent)


def test_bazarr_exposes_real_wanted_endpoints_not_yet_used() -> None:
    """
    Bazarr's renamed wanted endpoints are available but unconsumed.

    pyarr 6.8.0 replaced Bazarr's `wanted` accessor, which pointed at a
    `subtitles/wanted` path that does not exist, with `wanted_episodes` and
    `wanted_movies`. Both return real data. Bazarr currently gets almost no
    sensors from this integration, so these are the obvious way to give it a
    missing-subtitles count. Recorded here so the capability is not forgotten.
    """
    client = AsyncBazarr("http://localhost", "test-api-key")

    assert hasattr(client.wanted_episodes, "get")
    assert hasattr(client.wanted_movies, "get")
    assert not hasattr(client, "wanted")


def test_whisparr_is_movie_based_not_series_based() -> None:
    """
    Whisparr must be treated as Radarr-shaped, never Sonarr-shaped.

    Whisparr models scenes as movies and exposes `movie`, never `series`, in
    both pyarr 6.6.0 and 6.8.0. The integration used to group Whisparr with
    Sonarr throughout, so every Whisparr daily update raised AttributeError on
    `client.series.get()` and no daily sensor ever populated.

    This pins the reason the grouping is what it is, so a future change that
    moves Whisparr back alongside Sonarr fails here.
    """
    client = AsyncWhisparr("http://localhost", "test-api-key")

    assert not hasattr(client, "series")
    assert not hasattr(client, "episode")
    assert hasattr(client, "movie")


def test_lidarr_has_no_metadata_profile_component() -> None:
    """
    Pyarr exposes metadata profiles for Readarr only, not Lidarr.

    Lidarr's `metadata` component is metadata consumers - the nfo writers - and
    not the metadata profiles that add_artist's metadata_profile_id refers to.
    The get_config_data service used to ask Lidarr for `metadata_profile`, which
    raised AttributeError and failed the whole call.

    Lidarr's own API does serve /api/v1/metadataprofile, so this is a gap in
    pyarr rather than something Lidarr cannot do. Until pyarr covers it,
    get_config_data returns metadata profiles for Readarr alone.
    """
    client = AsyncLidarr("http://localhost", "test-api-key")

    assert not hasattr(client, "metadata_profile")
    # The similarly-named component that does exist, and is not a substitute.
    assert hasattr(client, "metadata")
    assert hasattr(AsyncReadarr("http://localhost", "k"), "metadata_profile")
