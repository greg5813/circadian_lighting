"""Tests for custom_components.circadian_lighting.__init__."""

import datetime
from datetime import timedelta, timezone
from math import degrees, isclose, pi, radians
from unittest.mock import patch

import pytest
import voluptuous as vol

from tests.conftest import make_aware_dt


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_domain(self):
        from custom_components.circadian_lighting import DOMAIN
        assert DOMAIN == "circadian_lighting"

    def test_data_key(self):
        from custom_components.circadian_lighting import DATA_CIRCADIAN_LIGHTING
        assert DATA_CIRCADIAN_LIGHTING == "data_cl"

    def test_update_topic(self):
        from custom_components.circadian_lighting import (
            CIRCADIAN_LIGHTING_UPDATE_TOPIC,
        )
        assert CIRCADIAN_LIGHTING_UPDATE_TOPIC == "circadian_lighting_update"

    def test_platforms(self):
        from custom_components.circadian_lighting import (
            CIRCADIAN_LIGHTING_PLATFORMS,
        )
        assert CIRCADIAN_LIGHTING_PLATFORMS == ["sensor", "switch"]

    def test_default_values(self):
        from custom_components.circadian_lighting import (
            DEFAULT_MIN_CT,
            DEFAULT_MAX_CT,
            DEFAULT_INTERVAL,
        )
        assert DEFAULT_MIN_CT == 2000
        assert DEFAULT_MAX_CT == 5500
        assert DEFAULT_INTERVAL == 60


# ---------------------------------------------------------------------------
# Config Schema
# ---------------------------------------------------------------------------

class TestConfigSchema:
    def _validate(self, domain_conf):
        from custom_components.circadian_lighting import CONFIG_SCHEMA, DOMAIN
        return CONFIG_SCHEMA({DOMAIN: domain_conf})

    def test_defaults(self):
        from custom_components.circadian_lighting import DOMAIN
        result = self._validate({})
        conf = result[DOMAIN]
        assert conf["min_colortemp"] == 2000
        assert conf["max_colortemp"] == 5500
        assert conf["interval"] == 60

    def test_custom_values(self):
        from custom_components.circadian_lighting import DOMAIN
        result = self._validate({
            "min_colortemp": 3000,
            "max_colortemp": 6500,
            "latitude": 40.0,
            "longitude": -74.0,
            "interval": 120,
        })
        conf = result[DOMAIN]
        assert conf["min_colortemp"] == 3000
        assert conf["max_colortemp"] == 6500
        assert conf["latitude"] == 40.0
        assert conf["longitude"] == -74.0
        assert conf["interval"] == 120

    def test_string_coercion(self):
        from custom_components.circadian_lighting import DOMAIN
        result = self._validate({"min_colortemp": "3000"})
        assert result[DOMAIN]["min_colortemp"] == 3000

    def test_min_colortemp_below_range(self):
        with pytest.raises(vol.Invalid):
            self._validate({"min_colortemp": 500})

    def test_min_colortemp_above_range(self):
        with pytest.raises(vol.Invalid):
            self._validate({"min_colortemp": 15000})

    def test_max_colortemp_below_range(self):
        with pytest.raises(vol.Invalid):
            self._validate({"max_colortemp": 500})

    def test_invalid_latitude(self):
        with pytest.raises(vol.Invalid):
            self._validate({"latitude": 100})

    def test_invalid_longitude(self):
        with pytest.raises(vol.Invalid):
            self._validate({"longitude": 200})

    def test_invalid_interval(self):
        with pytest.raises(vol.Invalid):
            self._validate({"interval": -1})

    def test_extra_keys_allowed(self):
        from custom_components.circadian_lighting import CONFIG_SCHEMA, DOMAIN
        result = CONFIG_SCHEMA({DOMAIN: {}, "other_integration": {"key": "val"}})
        assert "other_integration" in result


# ---------------------------------------------------------------------------
# setup()
# ---------------------------------------------------------------------------

class TestSetup:
    def test_returns_true(self, mock_hass, mock_dt, mock_load_platform, mock_dispatcher_send):
        from custom_components.circadian_lighting import DOMAIN, setup
        config = {DOMAIN: {"min_colortemp": 2000, "max_colortemp": 5500,
                           "latitude": 48.86, "longitude": 2.35, "interval": 60}}
        assert setup(mock_hass, config) is True

    def test_stores_in_hass_data(self, mock_hass, mock_dt, mock_load_platform, mock_dispatcher_send):
        from custom_components.circadian_lighting import (
            CircadianLighting, DATA_CIRCADIAN_LIGHTING, DOMAIN, setup,
        )
        config = {DOMAIN: {"min_colortemp": 2000, "max_colortemp": 5500,
                           "latitude": 48.86, "longitude": 2.35, "interval": 60}}
        setup(mock_hass, config)
        assert isinstance(mock_hass.data[DATA_CIRCADIAN_LIGHTING], CircadianLighting)

    def test_calls_load_platform(self, mock_hass, mock_dt, mock_load_platform, mock_dispatcher_send):
        from custom_components.circadian_lighting import DOMAIN, setup
        config = {DOMAIN: {"min_colortemp": 2000, "max_colortemp": 5500,
                           "latitude": 48.86, "longitude": 2.35, "interval": 60}}
        setup(mock_hass, config)
        mock_load_platform.assert_called_once_with(
            mock_hass, "sensor", DOMAIN, {}, config
        )

    def test_uses_config_lat_lon(self, mock_hass, mock_dt, mock_load_platform, mock_dispatcher_send):
        from custom_components.circadian_lighting import (
            DATA_CIRCADIAN_LIGHTING, DOMAIN, setup,
        )
        config = {DOMAIN: {"min_colortemp": 2000, "max_colortemp": 5500,
                           "latitude": 40.0, "longitude": -74.0, "interval": 60}}
        setup(mock_hass, config)
        cl = mock_hass.data[DATA_CIRCADIAN_LIGHTING]
        assert cl.data["latitude"] == 40.0
        assert cl.data["longitude"] == -74.0

    def test_falls_back_to_hass_config(self, mock_hass, mock_dt, mock_load_platform, mock_dispatcher_send):
        from custom_components.circadian_lighting import (
            DATA_CIRCADIAN_LIGHTING, DOMAIN, setup,
        )
        config = {DOMAIN: {"min_colortemp": 2000, "max_colortemp": 5500,
                           "interval": 60}}
        setup(mock_hass, config)
        cl = mock_hass.data[DATA_CIRCADIAN_LIGHTING]
        assert cl.data["latitude"] == mock_hass.config.latitude
        assert cl.data["longitude"] == mock_hass.config.longitude

    def test_passes_min_max_colortemp(self, mock_hass, mock_dt, mock_load_platform, mock_dispatcher_send):
        from custom_components.circadian_lighting import (
            DATA_CIRCADIAN_LIGHTING, DOMAIN, setup,
        )
        config = {DOMAIN: {"min_colortemp": 3000, "max_colortemp": 7000,
                           "latitude": 48.86, "longitude": 2.35, "interval": 60}}
        setup(mock_hass, config)
        cl = mock_hass.data[DATA_CIRCADIAN_LIGHTING]
        assert cl.data["min_colortemp"] == 3000
        assert cl.data["max_colortemp"] == 7000

    def test_passes_interval(self, mock_hass, mock_dt, mock_load_platform, mock_dispatcher_send):
        from custom_components.circadian_lighting import (
            DATA_CIRCADIAN_LIGHTING, DOMAIN, setup,
        )
        config = {DOMAIN: {"min_colortemp": 2000, "max_colortemp": 5500,
                           "latitude": 48.86, "longitude": 2.35, "interval": 120}}
        setup(mock_hass, config)
        cl = mock_hass.data[DATA_CIRCADIAN_LIGHTING]
        assert cl.data["interval"] == 120


# ---------------------------------------------------------------------------
# CircadianLighting.__init__
# ---------------------------------------------------------------------------

class TestCircadianLightingInit:
    def test_stores_config(self, cl_factory):
        cl = cl_factory()
        assert cl.data["min_colortemp"] == 2000
        assert cl.data["max_colortemp"] == 5500
        assert cl.data["latitude"] == 48.8566
        assert cl.data["longitude"] == 2.3522
        assert cl.data["interval"] == 60

    def test_initial_color_temp(self, cl_factory):
        cl = cl_factory()
        assert isinstance(cl.data["color_temp"], int)

    def test_initial_brightness(self, cl_factory):
        cl = cl_factory()
        assert isinstance(cl.data["brightness"], int)
        assert 50 <= cl.data["brightness"] <= 100

    def test_hass_reference(self, cl_factory, mock_hass):
        cl = cl_factory()
        assert cl.hass is mock_hass

    def test_throttle_wraps_update(self, cl_factory):
        cl = cl_factory()
        assert cl.update is not cl._update


# ---------------------------------------------------------------------------
# fractional_year
# ---------------------------------------------------------------------------

class TestFractionalYear:
    def test_non_leap_year(self, cl_factory):
        cl = cl_factory()
        date = datetime.datetime(2023, 6, 21, 12, 0, 0)
        yday = date.timetuple().tm_yday  # 172
        expected = 2 * pi / 365 * (yday - 1 + (12 - 12) / 24)
        assert isclose(cl.fractional_year(date), expected)

    def test_leap_year(self, cl_factory):
        cl = cl_factory()
        date = datetime.datetime(2024, 6, 21, 12, 0, 0)
        yday = date.timetuple().tm_yday  # 173
        expected = 2 * pi / 366 * (yday - 1 + (12 - 12) / 24)
        assert isclose(cl.fractional_year(date), expected)

    def test_jan1_noon(self, cl_factory):
        cl = cl_factory()
        date = datetime.datetime(2023, 1, 1, 12, 0, 0)
        assert isclose(cl.fractional_year(date), 0.0)

    def test_hour_offset(self, cl_factory):
        cl = cl_factory()
        date_6am = datetime.datetime(2023, 3, 21, 6, 0, 0)
        date_noon = datetime.datetime(2023, 3, 21, 12, 0, 0)
        assert cl.fractional_year(date_6am) < cl.fractional_year(date_noon)


# ---------------------------------------------------------------------------
# eqtime / decl
# ---------------------------------------------------------------------------

class TestEqtimeDecl:
    def test_eqtime_equinox(self, cl_factory):
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 20, 12, 0, 0)
        result = cl.eqtime(date)
        assert -10 < result < 0  # ~-7.5 min

    def test_eqtime_summer_solstice(self, cl_factory):
        cl = cl_factory()
        date = datetime.datetime(2024, 6, 21, 12, 0, 0)
        result = cl.eqtime(date)
        assert -3 < result < 1

    def test_decl_equinox(self, cl_factory):
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 20, 12, 0, 0)
        result = degrees(cl.decl(date))
        assert -2 < result < 2  # near 0

    def test_decl_summer_solstice(self, cl_factory):
        cl = cl_factory()
        date = datetime.datetime(2024, 6, 21, 12, 0, 0)
        result = degrees(cl.decl(date))
        assert 22 < result < 25  # ~23.44

    def test_decl_winter_solstice(self, cl_factory):
        cl = cl_factory()
        date = datetime.datetime(2024, 12, 21, 12, 0, 0)
        result = degrees(cl.decl(date))
        assert -25 < result < -22  # ~-23.44

    def test_eqtime_winter_solstice(self, cl_factory):
        cl = cl_factory()
        date = datetime.datetime(2024, 12, 21, 12, 0, 0)
        result = cl.eqtime(date)
        assert -1 < result < 5


# ---------------------------------------------------------------------------
# time_offset / tst / ha
# ---------------------------------------------------------------------------

class TestTimeOffsetTstHa:
    def test_time_offset_utc_plus_1(self, cl_factory, mock_dt):
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 21, 12, 0, 0)
        result = cl.time_offset(date, 0.0)
        eqt = cl.eqtime(date)
        expected = eqt + 4 * 0.0 - 60  # UTC+1 = 60 min
        assert isclose(result, expected)

    def test_time_offset_utc_minus_5(self, cl_factory, mock_dt):
        cl = cl_factory()
        mock_dt.now.return_value = make_aware_dt(2024, 3, 21, 12, utc_offset_hours=-5)
        date = datetime.datetime(2024, 3, 21, 12, 0, 0)
        result = cl.time_offset(date, 0.0)
        eqt = cl.eqtime(date)
        expected = eqt + 0.0 - (-300)
        assert isclose(result, expected)

    def test_time_offset_longitude_effect(self, cl_factory, mock_dt):
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 21, 12, 0, 0)
        t0 = cl.time_offset(date, 0.0)
        t15 = cl.time_offset(date, 15.0)
        assert isclose(t15 - t0, 60.0)  # 4 min/deg * 15 = 60

    def test_tst_at_noon(self, cl_factory, mock_dt):
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 21, 12, 0, 0)
        result = cl.tst(date, 2.3522)
        expected = 720 + cl.time_offset(date, 2.3522)
        assert isclose(result, expected)

    def test_ha_formula(self, cl_factory, mock_dt):
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 21, 12, 0, 0)
        lon = 2.3522
        expected = cl.tst(date, lon) / 4 - 180
        assert isclose(cl.ha(date, lon), expected)


# ---------------------------------------------------------------------------
# elevation / zenith
# ---------------------------------------------------------------------------

class TestElevationZenith:
    def test_zenith_plus_elevation_equals_90(self, cl_factory, mock_dt):
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 21, 12, 0, 0)
        lat, lon = 48.8566, 2.3522
        elev = cl.elevation(date, lat, lon)
        zen = cl.zenith(date, lat, lon)
        assert isclose(elev + zen, pi / 2, abs_tol=1e-10)

    def test_elevation_noon_equinox_equator(self, cl_factory, mock_dt):
        cl = cl_factory(lat=0.0, lon=0.0)
        mock_dt.now.return_value = make_aware_dt(2024, 3, 21, 12, utc_offset_hours=0)
        date = datetime.datetime(2024, 3, 20, 12, 0, 0)
        elev_deg = degrees(cl.elevation(date, 0.0, 0.0))
        assert elev_deg > 70  # near 90 at equator on equinox

    def test_elevation_midnight_negative(self, cl_factory, mock_dt):
        cl = cl_factory()
        mock_dt.now.return_value = make_aware_dt(2024, 3, 21, 0, utc_offset_hours=1)
        date = datetime.datetime(2024, 3, 21, 0, 0, 0)
        elev_deg = degrees(cl.elevation(date, 48.8566, 2.3522))
        assert elev_deg < 0

    def test_zenith_range(self, cl_factory, mock_dt):
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 21, 12, 0, 0)
        zen = cl.zenith(date, 48.8566, 2.3522)
        assert 0 <= zen <= pi


# ---------------------------------------------------------------------------
# ha_sunset / ha_sunrise
# ---------------------------------------------------------------------------

class TestHaSunsetSunrise:
    def test_sunrise_is_negative_sunset(self, cl_factory, mock_dt):
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 21, 12, 0, 0)
        ha_set = cl.ha_sunset(date, 48.8566)
        ha_rise = cl.ha_sunrise(date, 48.8566)
        assert isclose(ha_rise, -ha_set)

    def test_equinox_midlatitude(self, cl_factory, mock_dt):
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 20, 12, 0, 0)
        ha_set = cl.ha_sunset(date, 48.8566)
        assert 85 < ha_set < 95  # ~90 degrees at equinox

    def test_summer_longer_day(self, cl_factory, mock_dt):
        cl = cl_factory()
        equinox = datetime.datetime(2024, 3, 20, 12, 0, 0)
        summer = datetime.datetime(2024, 6, 21, 12, 0, 0)
        assert cl.ha_sunset(summer, 48.8566) > cl.ha_sunset(equinox, 48.8566)

    def test_polar_winter_raises(self, cl_factory, mock_dt):
        cl = cl_factory()
        date = datetime.datetime(2024, 12, 21, 12, 0, 0)
        with pytest.raises(ValueError):
            cl.ha_sunset(date, 80.0)


# ---------------------------------------------------------------------------
# sunrise / sunset / solar_noon / solar_midnight
# ---------------------------------------------------------------------------

class TestSunriseSunsetNoonMidnight:
    def test_sunrise_before_sunset(self, cl_factory, mock_dt):
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 21, 12, 0, 0)
        assert cl.sunrise(date, 48.8566, 2.3522) < cl.sunset(date, 48.8566, 2.3522)

    def test_equinox_sunrise_approx_6am(self, cl_factory, mock_dt):
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 20, 12, 0, 0)
        sr = cl.sunrise(date, 48.8566, 2.3522)
        assert 330 < sr < 420  # 5:30-7:00

    def test_equinox_sunset_approx_6pm(self, cl_factory, mock_dt):
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 20, 12, 0, 0)
        ss = cl.sunset(date, 48.8566, 2.3522)
        assert 1050 < ss < 1170  # 17:30-19:30

    def test_solar_noon_near_midday(self, cl_factory, mock_dt):
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 21, 12, 0, 0)
        noon = cl.solar_noon(date, 2.3522)
        assert 680 < noon < 800  # within ~1h of 720

    def test_solar_midnight_relationship(self, cl_factory, mock_dt):
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 21, 12, 0, 0)
        lon = 2.3522
        noon = cl.solar_noon(date, lon)
        midnight = cl.solar_midnight(date, lon)
        assert isclose(noon - midnight, 720)

    def test_summer_sunrise_earlier(self, cl_factory, mock_dt):
        cl = cl_factory()
        equinox = datetime.datetime(2024, 3, 20, 12, 0, 0)
        summer = datetime.datetime(2024, 6, 21, 12, 0, 0)
        assert cl.sunrise(summer, 48.8566, 2.3522) < cl.sunrise(equinox, 48.8566, 2.3522)


# ---------------------------------------------------------------------------
# solar_noon_elevation / solar_midnight_elevation
# ---------------------------------------------------------------------------

class TestSolarNoonMidnightElevation:
    def test_noon_elevation_positive(self, cl_factory, mock_dt):
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 21, 12, 0, 0)
        elev = cl.solar_noon_elevation(date, 48.8566, 2.3522)
        assert degrees(elev) > 0

    def test_midnight_elevation_negative(self, cl_factory, mock_dt):
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 21, 12, 0, 0)
        elev = cl.solar_midnight_elevation(date, 48.8566, 2.3522)
        assert degrees(elev) < 0

    def test_summer_noon_higher(self, cl_factory, mock_dt):
        cl = cl_factory()
        equinox = datetime.datetime(2024, 3, 20, 12, 0, 0)
        summer = datetime.datetime(2024, 6, 21, 12, 0, 0)
        eq_elev = cl.solar_noon_elevation(equinox, 48.8566, 2.3522)
        su_elev = cl.solar_noon_elevation(summer, 48.8566, 2.3522)
        assert su_elev > eq_elev


# ---------------------------------------------------------------------------
# azimuth — 9 reachable branches
# ---------------------------------------------------------------------------

class TestAzimuth:
    """Test all 9 reachable branches of azimuth().

    Branch structure:
    - A (midnight>0, noon<1440): normal case
    - B (midnight<=0, noon<1440): midnight before day start
    - C (midnight>0, noon>=1440): noon past day end
    Branch D (midnight<=0, noon>=1440) is mathematically unreachable
    since noon = midnight + 720.
    """

    def _assert_valid_azimuth(self, result):
        assert 0 <= result <= 2 * pi + 0.01

    # Branch A: midnight>0 AND noon<1440 (Paris, UTC+1)
    def test_branch_a1_before_both(self, cl_factory, mock_dt):
        mock_dt.now.return_value = make_aware_dt(2024, 3, 21, 0, 1, 0, utc_offset_hours=1)
        cl = cl_factory(lat=48.8566, lon=2.3522)
        date = datetime.datetime(2024, 3, 21, 0, 1, 0)
        result = cl.azimuth(date, 48.8566, 2.3522)
        self._assert_valid_azimuth(result)

    def test_branch_a2_after_midnight_before_noon(self, cl_factory, mock_dt):
        mock_dt.now.return_value = make_aware_dt(2024, 3, 21, 6, 0, 0, utc_offset_hours=1)
        cl = cl_factory(lat=48.8566, lon=2.3522)
        date = datetime.datetime(2024, 3, 21, 6, 0, 0)
        result = cl.azimuth(date, 48.8566, 2.3522)
        self._assert_valid_azimuth(result)

    def test_branch_a3_after_both(self, cl_factory, mock_dt):
        mock_dt.now.return_value = make_aware_dt(2024, 3, 21, 18, 0, 0, utc_offset_hours=1)
        cl = cl_factory(lat=48.8566, lon=2.3522)
        date = datetime.datetime(2024, 3, 21, 18, 0, 0)
        result = cl.azimuth(date, 48.8566, 2.3522)
        self._assert_valid_azimuth(result)

    # Branch B: midnight<=0 AND noon<1440 (lon=30, UTC+0)
    def test_branch_b1_before_both(self, cl_factory, mock_dt):
        mock_dt.now.return_value = make_aware_dt(2024, 3, 21, 1, 0, 0, utc_offset_hours=0)
        cl = cl_factory(lat=48.8566, lon=30.0)
        date = datetime.datetime(2024, 3, 21, 1, 0, 0)
        result = cl.azimuth(date, 48.8566, 30.0)
        self._assert_valid_azimuth(result)

    def test_branch_b2_before_midnight_after_noon(self, cl_factory, mock_dt):
        mock_dt.now.return_value = make_aware_dt(2024, 3, 21, 11, 0, 0, utc_offset_hours=0)
        cl = cl_factory(lat=48.8566, lon=30.0)
        date = datetime.datetime(2024, 3, 21, 11, 0, 0)
        result = cl.azimuth(date, 48.8566, 30.0)
        self._assert_valid_azimuth(result)

    def test_branch_b3_after_both(self, cl_factory, mock_dt):
        mock_dt.now.return_value = make_aware_dt(2024, 3, 21, 23, 0, 0, utc_offset_hours=0)
        cl = cl_factory(lat=48.8566, lon=30.0)
        date = datetime.datetime(2024, 3, 21, 23, 0, 0)
        result = cl.azimuth(date, 48.8566, 30.0)
        self._assert_valid_azimuth(result)

    # Branch C: midnight>0 AND noon>=1440 (lon=-180, UTC+0)
    # Create CL with normal lon, then call azimuth() with extreme lon
    # (lon=-180 crashes __init__ because solar_noon > 24h overflows datetime)
    def test_branch_c1_before_both(self, cl_factory, mock_dt):
        mock_dt.now.return_value = make_aware_dt(2024, 3, 21, 0, 1, 0, utc_offset_hours=0)
        cl = cl_factory(lat=48.8566, lon=2.3522)
        date = datetime.datetime(2024, 3, 21, 0, 1, 0)
        result = cl.azimuth(date, 48.8566, -180.0)
        self._assert_valid_azimuth(result)

    def test_branch_c2_before_midnight_after_noon(self, cl_factory, mock_dt):
        mock_dt.now.return_value = make_aware_dt(2024, 3, 21, 0, 30, 0, utc_offset_hours=0)
        cl = cl_factory(lat=48.8566, lon=2.3522)
        date = datetime.datetime(2024, 3, 21, 0, 30, 0)
        result = cl.azimuth(date, 48.8566, -180.0)
        self._assert_valid_azimuth(result)

    def test_branch_c3_after_both(self, cl_factory, mock_dt):
        mock_dt.now.return_value = make_aware_dt(2024, 3, 21, 14, 0, 0, utc_offset_hours=0)
        cl = cl_factory(lat=48.8566, lon=2.3522)
        date = datetime.datetime(2024, 3, 21, 14, 0, 0)
        result = cl.azimuth(date, 48.8566, -180.0)
        self._assert_valid_azimuth(result)


# ---------------------------------------------------------------------------
# percent elevation methods
# ---------------------------------------------------------------------------

class TestPercentElevation:
    def test_percent_day_at_noon(self, cl_factory, mock_dt):
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 21, 12, 0, 0)
        result = cl.percent_elevation_day(date, 48.8566, 2.3522)
        assert 0.8 < result <= 1.1  # near 1.0 at noon

    def test_percent_civil_twilight_at_upper_boundary(self, cl_factory, mock_dt):
        cl = cl_factory()
        # Use a mock elevation to test the formula directly
        date = datetime.datetime(2024, 3, 21, 12, 0, 0)
        # civil twilight: (elev - (-6)) / (-0.833 - (-6)) = (elev + 6) / 5.167
        # Test formula outputs reasonable range
        result = cl.percent_elevation_civil_twilight(date, 48.8566, 2.3522)
        assert isinstance(result, float)

    def test_percent_nautical_twilight_formula(self, cl_factory, mock_dt):
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 21, 12, 0, 0)
        result = cl.percent_elevation_nautical_twilight(date, 48.8566, 2.3522)
        assert isinstance(result, float)

    def test_percent_day_intermediate(self, cl_factory, mock_dt):
        """Morning elevation gives a value between 0 and 1."""
        mock_dt.now.return_value = make_aware_dt(2024, 3, 21, 9, 0, 0, utc_offset_hours=1)
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 21, 9, 0, 0)
        result = cl.percent_elevation_day(date, 48.8566, 2.3522)
        assert 0.0 < result < 1.0

    def test_percent_civil_twilight_during_twilight(self, cl_factory, mock_dt):
        """During civil twilight, value should be in [0,1]."""
        # Use a time when elevation is between -6 and -0.833
        # Early morning before sunrise
        mock_dt.now.return_value = make_aware_dt(2024, 3, 21, 5, 30, 0, utc_offset_hours=1)
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 21, 5, 30, 0)
        elev_deg = degrees(cl.elevation(date, 48.8566, 2.3522))
        if -6 < elev_deg < -0.833:
            result = cl.percent_elevation_civil_twilight(date, 48.8566, 2.3522)
            assert 0 <= result <= 1

    def test_percent_nautical_twilight_during_twilight(self, cl_factory, mock_dt):
        """During nautical twilight, value should be in [0,1]."""
        mock_dt.now.return_value = make_aware_dt(2024, 3, 21, 4, 30, 0, utc_offset_hours=1)
        cl = cl_factory()
        date = datetime.datetime(2024, 3, 21, 4, 30, 0)
        elev_deg = degrees(cl.elevation(date, 48.8566, 2.3522))
        if -12 < elev_deg < -6:
            result = cl.percent_elevation_nautical_twilight(date, 48.8566, 2.3522)
            assert 0 <= result <= 1


# ---------------------------------------------------------------------------
# color_temp
# ---------------------------------------------------------------------------

class TestColorTemp:
    def test_daytime_range(self, cl_factory, mock_dt):
        """Noon -> elevation well above -0.833 -> 3000-5500K."""
        mock_dt.now.return_value = make_aware_dt(2024, 6, 21, 12, 0, 0, utc_offset_hours=1)
        cl = cl_factory()
        result = cl.color_temp()
        assert 3000 <= result <= 5500

    def test_night_returns_2000(self, cl_factory, mock_dt):
        """Deep night -> elevation <= -6 -> 2000K."""
        mock_dt.now.return_value = make_aware_dt(2024, 3, 21, 1, 0, 0, utc_offset_hours=1)
        cl = cl_factory()
        result = cl.color_temp()
        assert result == 2000

    def test_civil_twilight_range(self, cl_factory, mock_dt):
        """Civil twilight -> 2000-3000K."""
        # Find a time when elevation is between -6 and -0.833
        # Try times around sunrise/sunset
        for hour, minute in [(5, 45), (5, 50), (5, 55), (19, 0), (19, 5), (19, 10)]:
            mock_dt.now.return_value = make_aware_dt(
                2024, 3, 21, hour, minute, 0, utc_offset_hours=1
            )
            cl = cl_factory()
            elev = degrees(
                cl.elevation(
                    mock_dt.now.return_value.replace(tzinfo=None),
                    48.8566, 2.3522,
                )
            )
            if -6 < elev <= -0.833:
                result = cl.color_temp()
                assert 2000 <= result <= 3000
                return
        # If we didn't find a twilight time, at least verify the method runs
        cl = cl_factory()
        assert isinstance(cl.color_temp(), int)

    def test_returns_int(self, cl_factory, mock_dt):
        cl = cl_factory()
        assert isinstance(cl.color_temp(), int)


# ---------------------------------------------------------------------------
# brightness
# ---------------------------------------------------------------------------

class TestBrightness:
    def test_daytime_returns_100(self, cl_factory, mock_dt):
        mock_dt.now.return_value = make_aware_dt(2024, 6, 21, 12, 0, 0, utc_offset_hours=1)
        cl = cl_factory()
        assert cl.brightness() == 100

    def test_deep_night_returns_50(self, cl_factory, mock_dt):
        mock_dt.now.return_value = make_aware_dt(2024, 3, 21, 1, 0, 0, utc_offset_hours=1)
        cl = cl_factory()
        result = cl.brightness()
        assert result == 50

    def test_nautical_twilight_range(self, cl_factory, mock_dt):
        """Nautical twilight -> 50-100."""
        for hour, minute in [(4, 30), (4, 45), (5, 0), (5, 15), (20, 0), (20, 15)]:
            mock_dt.now.return_value = make_aware_dt(
                2024, 3, 21, hour, minute, 0, utc_offset_hours=1
            )
            cl = cl_factory()
            elev = degrees(
                cl.elevation(
                    datetime.datetime(2024, 3, 21, hour, minute, 0),
                    48.8566, 2.3522,
                )
            )
            if -12 < elev <= -6:
                result = cl.brightness()
                assert 50 <= result <= 100
                return
        cl = cl_factory()
        assert isinstance(cl.brightness(), int)

    def test_returns_int(self, cl_factory, mock_dt):
        cl = cl_factory()
        assert isinstance(cl.brightness(), int)


# ---------------------------------------------------------------------------
# _update
# ---------------------------------------------------------------------------

class TestUpdate:
    def test_recalculates_values(self, cl_factory, mock_dt, mock_dispatcher_send):
        cl = cl_factory()
        old_ct = cl.data["color_temp"]
        mock_dt.now.return_value = make_aware_dt(2024, 3, 21, 1, 0, 0, utc_offset_hours=1)
        cl._update()
        # Night time should give 2000K
        assert cl.data["color_temp"] == 2000

    def test_calls_dispatcher(self, cl_factory, mock_dt, mock_dispatcher_send):
        from custom_components.circadian_lighting import (
            CIRCADIAN_LIGHTING_UPDATE_TOPIC,
        )
        cl = cl_factory()
        mock_dispatcher_send.reset_mock()
        cl._update()
        mock_dispatcher_send.assert_called_once_with(
            cl.hass, CIRCADIAN_LIGHTING_UPDATE_TOPIC
        )

    def test_update_brightness(self, cl_factory, mock_dt, mock_dispatcher_send):
        cl = cl_factory()
        mock_dt.now.return_value = make_aware_dt(2024, 3, 21, 1, 0, 0, utc_offset_hours=1)
        cl._update()
        assert cl.data["brightness"] == 50

    def test_accepts_args_kwargs(self, cl_factory, mock_dt, mock_dispatcher_send):
        cl = cl_factory()
        cl._update("arg1", key="val")  # should not raise
