"""DataUpdateCoordinator for Armadarr."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_helpers import fetch_daily_data, fetch_standard_data
from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import ArmadarrConfigEntry


class StandardCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching standard data from the API (5 min)."""

    config_entry: ArmadarrConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ArmadarrConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=f"{DOMAIN}_{config_entry.data['app_type']}_standard",
            update_interval=timedelta(minutes=5),
        )
        self.config_entry = config_entry
        self.last_history_id: int | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        client = self.config_entry.runtime_data.client
        app_type = self.config_entry.data["app_type"]

        try:
            data, new_last_history_id = await fetch_standard_data(
                client,
                app_type,
                self.last_history_id,
                self.config_entry.entry_id,
                self.hass,
            )
            self.last_history_id = new_last_history_id
        except Exception as exception:
            msg = f"Error communicating with API: {exception}"
            raise UpdateFailed(msg) from exception
        else:
            return data


class DailyCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching daily data from the API (12 hours)."""

    config_entry: ArmadarrConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ArmadarrConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=f"{DOMAIN}_{config_entry.data['app_type']}_daily",
            update_interval=timedelta(hours=12),
        )
        self.config_entry = config_entry

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        client = self.config_entry.runtime_data.client
        app_type = self.config_entry.data["app_type"]

        try:
            return await fetch_daily_data(client, app_type)
        except Exception as exception:
            msg = f"Error communicating with API: {exception}"
            raise UpdateFailed(msg) from exception
