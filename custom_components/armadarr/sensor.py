"""Sensor platform for Armadarr."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity

from .entity import ArmadarrEntity
from .parsers import parse_event
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

    # App-Specific Sensors
    if app_type in ["Sonarr", "Whisparr", "Radarr", "Lidarr", "Readarr"]:
        for description in get_media_sensors():
            coordinator = (
                standard_coordinator
                if description.key == "upcoming_media"
                else daily_coordinator
            )
            entities.append(ArmadarrSensor(coordinator, description))

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

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attrs = {
            "entry_id": self.config_entry.entry_id,
            "app_type": self.config_entry.data["app_type"],
        }

        if self.entity_description.key in ["upcoming_media", "wanted_media"]:
            attrs["type"] = self.entity_description.key
            data_key = (
                "calendar"
                if self.entity_description.key == "upcoming_media"
                else "wanted"
            )
            raw_data = self.coordinator.data.get(data_key, [])
            app_type = self.config_entry.data["app_type"]
            base_url = self.config_entry.data["url"].rstrip("/")
            api_key = self.config_entry.data["api_key"]

            items = []
            # Add template item at index 0 for compatibility with upcoming-media-card
            template = {
                "title_default": "$title",
                "line1_default": "$episode" if app_type in ["Sonarr", "Whisparr"] else "$release",
                "line2_default": "$number" if app_type in ["Sonarr", "Whisparr"] else "$runtime",
                "line3_default": "$airdate" if app_type in ["Sonarr", "Whisparr"] else "$rating",
                "line4_default": "$studio" if app_type in ["Sonarr", "Whisparr"] else "$genres",
                "icon": "mdi:television" if app_type in ["Sonarr", "Whisparr"] else "mdi:movie",
            }
            if app_type == "Lidarr":
                template.update({"line1_default": "$artist", "line2_default": "$album", "icon": "mdi:music"})
            elif app_type == "Readarr":
                template.update({"line1_default": "$author", "line2_default": "$release", "icon": "mdi:book"})
            
            items.append(template)

            for event in raw_data:
                item = parse_event(event, app_type)
                if not item:
                    continue

                # Ensure URLs are absolute if they are relative
                if item.get("poster") and item["poster"].startswith("/"):
                    sep = "&" if "?" in item["poster"] else "?"
                    item["poster"] = f"{base_url}{item['poster']}{sep}apikey={api_key}"
                if item.get("fanart") and item["fanart"].startswith("/"):
                    sep = "&" if "?" in item["fanart"] else "?"
                    item["fanart"] = f"{base_url}{item['fanart']}{sep}apikey={api_key}"

                items.append(item)

            attrs["data"] = items

        return attrs
