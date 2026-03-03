"""Shared fixtures for circadian lighting tests."""

import datetime
from datetime import timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest


def make_aware_dt(year, month, day, hour=12, minute=0, second=0, utc_offset_hours=1):
    """Create a timezone-aware datetime."""
    tz = timezone(timedelta(hours=utc_offset_hours))
    return datetime.datetime(year, month, day, hour, minute, second, tzinfo=tz)


@pytest.fixture
def mock_hass():
    """Create a minimal mock Home Assistant instance."""
    hass = MagicMock()
    hass.config.latitude = 48.8566
    hass.config.longitude = 2.3522
    hass.data = {}
    return hass


@pytest.fixture
def mock_dt():
    """Patch dt.now() to return a controlled timezone-aware datetime."""
    with patch("custom_components.circadian_lighting.dt") as mock:
        mock.now.return_value = make_aware_dt(2024, 3, 21, 12, 0, 0)
        yield mock


@pytest.fixture
def mock_load_platform():
    """Patch load_platform."""
    with patch("custom_components.circadian_lighting.load_platform") as mock:
        yield mock


@pytest.fixture
def mock_dispatcher_send():
    """Patch dispatcher_send in __init__.py."""
    with patch("custom_components.circadian_lighting.dispatcher_send") as mock:
        yield mock


@pytest.fixture
def mock_dispatcher_connect():
    """Patch dispatcher_connect in sensor.py."""
    with patch(
        "custom_components.circadian_lighting.sensor.dispatcher_connect"
    ) as mock:
        yield mock


@pytest.fixture
def cl_factory(mock_hass, mock_dt, mock_dispatcher_send):
    """Factory to create CircadianLighting instances with controlled time."""
    from custom_components.circadian_lighting import CircadianLighting

    def create(
        min_ct=2000, max_ct=5500, lat=48.8566, lon=2.3522, interval=60
    ):
        return CircadianLighting(mock_hass, min_ct, max_ct, lat, lon, interval)

    return create
