"""Fixtures."""
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def markets_payload():
    return json.loads((FIXTURES / "markets.json").read_text())


@pytest.fixture(autouse=True)
def skip_frontend(hass):
    """The card needs the real frontend/http; tests only cover the integration."""
    from unittest.mock import AsyncMock, patch

    hass.config.components.update({"frontend", "http", "person", "zone", "image_upload"})
    with patch("custom_components.caripasarmalam.async_register_card", AsyncMock()), patch(
        "custom_components.caripasarmalam.async_unregister_card", AsyncMock()
    ):
        yield
