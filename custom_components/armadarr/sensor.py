"""Sensor platform for Armadarr."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity

from .entity import ArmadarrEntity
from .sensor_descriptions import (
    ArmadarrSensorEntityDescription,
    get_app_specific_sensors,
    get_common_sensors,
    get_disk_space_sensors,
    get_media_sensors,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import DailyCoordinator, StandardCoordinator
    from .data import ArmadarrConfigEntry


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ArmadarrConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    standard_coordinator = entry.runtime_data.standard_coordinator
    daily_coordinator = entry.runtime_data.daily_coordinator
    app_type = entry.data["app_type"]

    entities: list[ArmadarrSensor] = []

    # Common Sensors (Standard Coordinator)
    if app_type not in ["Bazarr", "Prowlarr"]:
        entities.extend(
            ArmadarrSensor(standard_coordinator, description)
            for description in get_common_sensors()
        )

        # Disk Space Sensors (Dynamic per root folder)
        root_folders = standard_coordinator.data.get("root_folder", [])
        entities.extend(
            ArmadarrSensor(standard_coordinator, description)
            for description in get_disk_space_sensors(root_folders)
        )

    # App-Specific Sensors (Daily Coordinator)
    if app_type in ["Sonarr", "Whisparr", "Radarr", "Lidarr", "Readarr"]:
        entities.extend(
            ArmadarrSensor(daily_coordinator, description)
            for description in get_media_sensors()
        )

    for description in get_app_specific_sensors(app_type):
        # Prowlarr indexer_errors uses standard_coordinator, others use daily
        coordinator = (
            standard_coordinator
            if description.key == "indexer_errors"
            else daily_coordinator
        )
        entities.append(ArmadarrSensor(coordinator, description))

    async_add_entities(entities)


class ArmadarrSensor(ArmadarrEntity, SensorEntity):
    """Armadarr Sensor class."""

    entity_description: ArmadarrSensorEntityDescription

    def __init__(
        self,
        coordinator: StandardCoordinator | DailyCoordinator,
        description: ArmadarrSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description)

    @property
    def native_value(self) -> Any:
        """Return the native value of the sensor."""
        # Use self.coordinator.data directly
        return self.entity_description.value_fn(self.coordinator.data)
