"""Test the Armadarr integration."""

from __future__ import annotations

from custom_components.armadarr.const import DOMAIN


async def test_setup() -> None:
    """Test setup of the integration."""
    assert DOMAIN == "armadarr"  # noqa: S101
