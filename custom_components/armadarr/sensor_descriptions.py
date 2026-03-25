"""Sensor descriptions for Armadarr."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfInformation

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True, kw_only=True)
class ArmadarrSensorEntityDescription(SensorEntityDescription):
    """Class describing Armadarr sensor entities."""

    value_fn: Callable[[Any], Any]


def get_common_sensors() -> list[ArmadarrSensorEntityDescription]:
    """Get common sensors for most apps."""
    return [
        ArmadarrSensorEntityDescription(
            key="queue_size",
            name="Queue Size",
            icon="mdi:tray-full",
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda data: (
                (
                    data.get("queue", {}).get(
                        "totalRecords",
                        len(data.get("queue", {}).get("records", [])),
                    )
                    if isinstance(data.get("queue"), dict)
                    else len(data.get("queue", []))
                )
                if data
                else 0
            ),
        ),
        ArmadarrSensorEntityDescription(
            key="health_warnings",
            name="Health Warnings",
            icon="mdi:alert-circle",
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda data: (
                len(
                    [
                        h
                        for h in data.get("health", [])
                        if isinstance(h, dict) and h.get("type") == "warning"
                    ]
                )
                if data
                else 0
            ),
        ),
    ]


def get_disk_space_sensors(
    root_folders: list[dict[str, Any]],
) -> list[ArmadarrSensorEntityDescription]:
    """Get disk space sensors dynamically based on root folders."""
    sensors = []
    for folder in root_folders:
        path = str(folder.get("path", ""))
        if not path:
            continue

        def _get_free_space(data: dict[str, Any] | None, p: str = path) -> float | None:
            if not data:
                return None
            return next(
                (
                    round(f.get("freeSpace", 0) / (1024**3), 2)
                    for f in data.get("root_folder", [])
                    if isinstance(f, dict) and f.get("path") == p
                ),
                None,
            )

        sensors.append(
            ArmadarrSensorEntityDescription(
                key=f"disk_space_{path}",
                name=f"Disk Space ({path})",
                icon="mdi:harddisk",
                native_unit_of_measurement=UnitOfInformation.GIBIBYTES,
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=_get_free_space,
            )
        )
    return sensors


def get_media_sensors() -> list[ArmadarrSensorEntityDescription]:
    """Get common media sensors."""
    return [
        ArmadarrSensorEntityDescription(
            key="missing_count",
            name="Missing Items",
            icon="mdi:magnify-minus-outline",
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda data: int(data.get("missing_count", 0)) if data else 0,
        ),
        ArmadarrSensorEntityDescription(
            key="unmonitored_count",
            name="Unmonitored Items",
            icon="mdi:eye-off",
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda data: int(data.get("unmonitored_count", 0)) if data else 0,
        ),
        ArmadarrSensorEntityDescription(
            key="upcoming_media",
            name="Upcoming Media",
            icon="mdi:calendar-star",
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda data: len(data.get("calendar", [])) if data else 0,
        ),
        ArmadarrSensorEntityDescription(
            key="wanted_media",
            name="Wanted Media",
            icon="mdi:magnify-plus-outline",
            state_class=SensorStateClass.MEASUREMENT,
            value_fn=lambda data: len(data.get("wanted", [])) if data else 0,
        ),
    ]


def get_app_specific_sensors(app_type: str) -> list[ArmadarrSensorEntityDescription]:
    """Get sensors specific to an app type."""
    if app_type in ["Sonarr", "Whisparr"]:
        return [
            ArmadarrSensorEntityDescription(
                key="series_count",
                name="Series Count",
                icon="mdi:television",
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda data: len(data.get("series", [])) if data else 0,
            )
        ]
    if app_type == "Radarr":
        return [
            ArmadarrSensorEntityDescription(
                key="movie_count",
                name="Movie Count",
                icon="mdi:movie",
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda data: len(data.get("movies", [])) if data else 0,
            )
        ]
    if app_type == "Lidarr":
        return [
            ArmadarrSensorEntityDescription(
                key="artist_count",
                name="Artist Count",
                icon="mdi:account-music",
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda data: len(data.get("artists", [])) if data else 0,
            )
        ]
    if app_type == "Readarr":
        return [
            ArmadarrSensorEntityDescription(
                key="author_count",
                name="Author Count",
                icon="mdi:book-open-variant",
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda data: len(data.get("authors", [])) if data else 0,
            )
        ]
    if app_type == "Prowlarr":
        return [
            ArmadarrSensorEntityDescription(
                key="indexer_count",
                name="Indexer Count",
                icon="mdi:format-list-bulleted",
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda data: len(data.get("indexers", [])) if data else 0,
            ),
            ArmadarrSensorEntityDescription(
                key="indexer_errors",
                name="Indexers with Errors",
                icon="mdi:alert-circle",
                state_class=SensorStateClass.MEASUREMENT,
                value_fn=lambda data: (
                    len(
                        [
                            i
                            for i in data.get("indexer_status", [])
                            if isinstance(i, dict) and i.get("status") == "error"
                        ]
                    )
                    if data
                    else 0
                ),
            ),
        ]
    return []
