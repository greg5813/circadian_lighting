"""Display sensor values for a full day in Toulouse for solstices and equinoxes.

Run with: pytest tests/test_daily_profile.py -s
"""

import datetime
from datetime import timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

# Toulouse, France
TOULOUSE_LAT = 43.6047
TOULOUSE_LON = 1.4442

# (label, year, month, day, utc_offset_hours)
DATES = [
    ("Spring Equinox", 2026, 3, 20, 1),  # CET (UTC+1)
    ("Summer Solstice", 2026, 6, 21, 2),  # CEST (UTC+2)
    ("Autumn Equinox", 2026, 9, 22, 2),  # CEST (UTC+2)
    ("Winter Solstice", 2026, 12, 21, 1),  # CET (UTC+1)
]


@pytest.mark.parametrize(
    "label,year,month,day,utc_offset",
    DATES,
    ids=["spring_equinox", "summer_solstice", "autumn_equinox", "winter_solstice"],
)
def test_sensor_values_full_day(label, year, month, day, utc_offset):
    """Display color temperature and brightness sensor values every 30 min."""
    from custom_components.circadian_lighting import CircadianLighting
    from custom_components.circadian_lighting.sensor import (
        CircadianLightBrightnessSensor,
        CircadianLightColorTemperatureSensor,
    )

    tz = timezone(timedelta(hours=utc_offset))
    hass = MagicMock()

    with patch("custom_components.circadian_lighting.dt") as mock_dt, patch(
        "custom_components.circadian_lighting.dispatcher_send"
    ), patch("custom_components.circadian_lighting.sensor.dispatcher_connect"):

        # Bootstrap at midnight
        mock_dt.now.return_value = datetime.datetime(
            year, month, day, 0, 0, 0, tzinfo=tz
        )
        cl = CircadianLighting(hass, 2000, 5500, TOULOUSE_LAT, TOULOUSE_LON, 60)

        ct_sensor = CircadianLightColorTemperatureSensor(hass, cl)
        br_sensor = CircadianLightBrightnessSensor(hass, cl)

        print(f"\n{'=' * 70}")
        print(
            f"  {label} — {year}-{month:02d}-{day:02d}"
            f" — Toulouse ({TOULOUSE_LAT}°N, {TOULOUSE_LON}°E) UTC+{utc_offset}"
        )
        print(f"{'=' * 70}")
        print(f"  {'Time':>5}  {'Color Temp (K)':>14}  {'Brightness (%)':>14}")
        print(f"  {'-' * 5}  {'-' * 14}  {'-' * 14}")

        color_temps = []
        brightnesses = []

        for minutes in range(0, 24 * 60, 30):
            h, m = divmod(minutes, 60)
            current = datetime.datetime(year, month, day, h, m, 0, tzinfo=tz)
            mock_dt.now.return_value = current

            ct = cl.color_temp()
            br = cl.brightness()

            # Simulate dispatcher update cycle
            cl.data["color_temp"] = ct
            cl.data["brightness"] = br
            ct_sensor.update_sensor()
            br_sensor.update_sensor()

            # Verify sensors reflect the computed values
            assert ct_sensor.state == ct
            assert br_sensor.state == br

            color_temps.append(ct)
            brightnesses.append(br)

            print(f"  {h:02d}:{m:02d}  {ct:>14}  {br:>14}")

        print()

        # Sanity checks across the whole day
        assert (
            min(color_temps) >= 2000
        ), "Color temp should never drop below min_colortemp"
        assert max(color_temps) <= 5500, "Color temp should never exceed max_colortemp"
        assert min(brightnesses) >= 50, "Brightness should never drop below 50%"
        assert max(brightnesses) <= 100, "Brightness should never exceed 100%"

        # Daytime should reach higher color temps than night
        assert max(color_temps) > 2000, "Should reach above 2000K during daytime"
        assert max(brightnesses) == 100, "Should reach 100% brightness during daytime"
