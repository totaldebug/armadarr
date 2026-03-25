"""Global fixtures for Armadarr tests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator
    from unittest.mock import MagicMock


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations in Home Assistant."""
    return


@pytest.fixture
def mock_setup_entry() -> Generator[MagicMock]:
    """Mock setting up a config entry."""
    with patch(
        "custom_components.armadarr.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup
