"""
Test the Armadarr binary sensor platform.

Regression tests for issue #30: `update_available` reported `on` unconditionally
because it compared `system_status.version` against `system_status.latestVersion`,
and the *arr `system/status` payload has no `latestVersion` field. `.get()`
returned None, `version != None` was always true, and the sensor had no state in
which it could report `off`.

Update state comes from the update endpoint instead, whose entries carry real
`installed` and `latest` flags.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.armadarr.binary_sensor import (
    ArmadarrBinarySensor,
    _update_available,
    async_setup_entry,
)
from custom_components.armadarr.const import (
    CONF_API_KEY,
    CONF_APP_TYPE,
    CONF_URL,
    CONF_VERIFY_SSL,
    DOMAIN,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from homeassistant.helpers.entity import Entity

# The exact system/status payload from the issue report. Prowlarr 2.4.0.5397,
# fully up to date, and note there is no latestVersion key anywhere in it.
PROWLARR_STATUS = {
    "appName": "Prowlarr",
    "instanceName": "Prowlarr",
    "version": "2.4.0.5397",
    "buildTime": "2026-06-10T07:23:39Z",
    "isProduction": True,
    "osName": "Windows",
    "branch": "master",
    "databaseType": "sqLite",
    "packageUpdateMechanism": "builtIn",
}

# The matching update payload: the running version is both installed and latest.
UP_TO_DATE = [
    {"version": "2.4.0.5397", "installed": True, "latest": True},
    {"version": "2.3.5.5327", "installed": False, "latest": False},
    {"version": "2.3.0.5236", "installed": False, "latest": False},
]

# The same instance one release behind.
UPDATE_PENDING = [
    {"version": "2.5.0.5500", "installed": False, "latest": True},
    {"version": "2.4.0.5397", "installed": True, "latest": False},
]


def test_up_to_date_instance_reports_off() -> None:
    """
    The reported bug: an up-to-date instance must report off.

    Before the fix this returned True for any payload at all, because the
    comparison was always `version != None`.
    """
    assert (
        _update_available({"system_status": PROWLARR_STATUS, "update": UP_TO_DATE})
        is False
    )


def test_pending_update_reports_on() -> None:
    """An instance a release behind must report on."""
    assert (
        _update_available({"system_status": PROWLARR_STATUS, "update": UPDATE_PENDING})
        is True
    )


def test_status_payload_alone_cannot_turn_the_sensor_on() -> None:
    """
    system_status must no longer influence the result at all.

    This is the heart of issue #30: the old implementation derived the answer
    from a field that payload never contains.
    """
    assert _update_available({"system_status": PROWLARR_STATUS}) is False
    assert "latestVersion" not in PROWLARR_STATUS


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (None, False),
        ({}, False),
        ({"update": []}, False),
        ({"update": None}, False),
        # Malformed entries must not raise.
        ({"update": ["not-a-dict", None]}, False),
        # A latest entry that is also installed means no update.
        ({"update": [{"version": "1.0", "installed": True, "latest": True}]}, False),
        # Missing flags are treated as absent, not as true.
        ({"update": [{"version": "1.0"}]}, False),
    ],
)
def test_update_available_edge_cases(data: Any, expected: bool) -> None:
    """Empty, absent and malformed update payloads must report off, not raise."""
    assert _update_available(data) is expected


async def _build_sensors(
    hass: HomeAssistant, app_type: str, data: dict[str, Any]
) -> list[ArmadarrBinarySensor]:
    """Set up the binary sensor platform for ``app_type`` over ``data``."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_APP_TYPE: app_type,
            CONF_URL: "http://localhost:9696",
            CONF_API_KEY: "test-api-key",
            CONF_VERIFY_SSL: True,
        },
    )
    entry.add_to_hass(hass)

    class _Coordinator:
        """Minimal coordinator exposing just what the entities read."""

        def __init__(self) -> None:
            self.data = data
            self.config_entry = entry
            self.last_update_success = True

        def async_add_listener(self, *_args: Any, **_kwargs: Any) -> Any:
            """Return a no-op unsubscribe callback."""
            return lambda: None

    coordinator = _Coordinator()

    class _Runtime:
        """Minimal runtime_data holder."""

        standard_coordinator = coordinator

    entry.runtime_data = _Runtime()

    added: list[ArmadarrBinarySensor] = []

    def _add(new_entities: Iterable[Entity], update_before_add: bool = False) -> None:  # noqa: FBT002
        """Collect the entities the platform adds."""
        added.extend(e for e in new_entities if isinstance(e, ArmadarrBinarySensor))

    await async_setup_entry(hass, entry, _add)
    return added


async def test_prowlarr_sensor_is_off_when_up_to_date(hass: HomeAssistant) -> None:
    """End to end over the reported payload: the entity itself must read off."""
    sensors = await _build_sensors(
        hass,
        "Prowlarr",
        {"system_status": PROWLARR_STATUS, "update": UP_TO_DATE},
    )

    by_key = {s.entity_description.key: s for s in sensors}
    assert by_key["update_available"].is_on is False
    # Connectivity is unaffected and still reports reachable.
    assert by_key["connectivity"].is_on is True


@pytest.mark.parametrize("app_type", ["Bazarr", "Dispatcharr"])
async def test_no_update_sensor_where_no_endpoint_exists(
    hass: HomeAssistant, app_type: str
) -> None:
    """
    Bazarr and Dispatcharr must not get an update_available sensor at all.

    Neither exposes an update endpoint, so the sensor could only ever report a
    fabricated answer. Offering a sensor that cannot be correct is what made the
    original bug invisible for so long.
    """
    sensors = await _build_sensors(hass, app_type, {"system_status": {"version": "1"}})

    keys = {s.entity_description.key for s in sensors}
    assert keys == {"connectivity"}
