"""The circadian lighting integration."""

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.util import Throttle, dt
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.dispatcher import dispatcher_send
from datetime import timedelta
import calendar
import datetime
from math import pi, sin, cos, tan, asin, acos, degrees, radians, modf, floor
import logging


_LOGGER = logging.getLogger(__name__)

DOMAIN = "circadian_lighting"
CIRCADIAN_LIGHTING_PLATFORMS = ["sensor", "switch"]
CIRCADIAN_LIGHTING_UPDATE_TOPIC = "{0}_update".format(DOMAIN)
DATA_CIRCADIAN_LIGHTING = "data_cl"

CONF_MIN_CT = "min_colortemp"
DEFAULT_MIN_CT = 2000
CONF_MAX_CT = "max_colortemp"
DEFAULT_MAX_CT = 5500
CONF_INTERVAL = "interval"
DEFAULT_INTERVAL = 60

def _validate_colortemp_range(config):
    """Validate that min_colortemp is less than max_colortemp."""
    if config[CONF_MIN_CT] >= config[CONF_MAX_CT]:
        raise vol.Invalid("min_colortemp must be less than max_colortemp")
    return config


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            vol.Schema(
                {
                    vol.Optional(CONF_MIN_CT, default=DEFAULT_MIN_CT): vol.All(
                        vol.Coerce(int), vol.Range(min=1000, max=10000)
                    ),
                    vol.Optional(CONF_MAX_CT, default=DEFAULT_MAX_CT): vol.All(
                        vol.Coerce(int), vol.Range(min=1000, max=10000)
                    ),
                    vol.Optional(CONF_LATITUDE): cv.latitude,
                    vol.Optional(CONF_LONGITUDE): cv.longitude,
                    vol.Optional(
                        CONF_INTERVAL, default=DEFAULT_INTERVAL
                    ): cv.positive_int,
                }
            ),
            _validate_colortemp_range,
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


def setup(hass, config):
    """Set circadian lighting integration."""
    conf = config[DOMAIN]
    min_colortemp = conf.get(CONF_MIN_CT)
    max_colortemp = conf.get(CONF_MAX_CT)
    latitude = conf.get(CONF_LATITUDE, hass.config.latitude)
    longitude = conf.get(CONF_LONGITUDE, hass.config.longitude)
    interval = conf.get(CONF_INTERVAL)

    cl = CircadianLighting(
        hass, min_colortemp, max_colortemp, latitude, longitude, interval
    )

    hass.data[DATA_CIRCADIAN_LIGHTING] = cl

    load_platform(hass, "sensor", DOMAIN, {}, config)

    return True


class CircadianLighting(object):
    """Circadian lighting class."""

    def __init__(
        self, hass, min_colortemp, max_colortemp, latitude, longitude, interval
    ):
        """Init circadian lighting class."""
        self.hass = hass
        self.data = {}
        self.data["min_colortemp"] = min_colortemp
        self.data["max_colortemp"] = max_colortemp
        self.data["latitude"] = latitude
        self.data["longitude"] = longitude
        self.data["interval"] = interval
        self.data["color_temp"] = self.color_temp()
        self.data["brightness"] = self.brightness()

        self.update = Throttle(timedelta(seconds=interval))(self._update)

    def fractional_year(self, date):
        """Compute the fractional year."""
        tt = date.timetuple()
        days_in_year = 366 if calendar.isleap(tt.tm_year) else 365
        return 2 * pi / days_in_year * (tt.tm_yday - 1 + (tt.tm_hour - 12) / 24)

    def eqtime(self, date):
        """Compute the equation of time."""
        fy = self.fractional_year(date)
        return 229.18 * (
            0.000075
            + 0.001868 * cos(fy)
            - 0.032077 * sin(fy)
            - 0.014615 * cos(2 * fy)
            - 0.040849 * sin(2 * fy)
        )

    def decl(self, date):
        """Compute the declination of the Sun."""
        fy = self.fractional_year(date)
        return (
            0.006918
            - 0.399912 * cos(fy)
            + 0.070257 * sin(fy)
            - 0.006758 * cos(2 * fy)
            + 0.000907 * sin(2 * fy)
            - 0.002697 * cos(3 * fy)
            + 0.00148 * sin(3 * fy)
        )

    def _utc_offset_minutes(self, date):
        """Get the UTC offset in minutes for the given date's timezone."""
        tz = dt.DEFAULT_TIME_ZONE
        offset = date.replace(tzinfo=None).replace(tzinfo=tz).utcoffset()
        if offset is None:
            offset = dt.now().utcoffset()
        return round(offset.total_seconds() / 60)

    def time_offset(self, date, longitude):
        """Compute the time offset of the solar time."""
        return (
            self.eqtime(date)
            + 4 * longitude
            - self._utc_offset_minutes(date)
        )

    def tst(self, date, longitude):
        """Compute the true solar time."""
        return (
            date.timetuple().tm_hour * 60
            + date.timetuple().tm_min
            + date.timetuple().tm_sec / 60
            + self.time_offset(date, longitude)
        )

    def ha(self, date, longitude):
        """Compute the hour angle of the Sun."""
        return (self.tst(date, longitude) / 4) - 180

    def elevation(self, date, latitude, longitude):
        """Compute the elevation of the Sun."""
        val = (
            sin(radians(latitude)) * sin(self.decl(date))
            + cos(radians(latitude))
            * cos(self.decl(date))
            * cos(radians(self.ha(date, longitude)))
        )
        return asin(max(-1.0, min(1.0, val)))

    def zenith(self, date, latitude, longitude):
        """Compute the zenith of the Sun."""
        val = (
            sin(radians(latitude)) * sin(self.decl(date))
            + cos(radians(latitude))
            * cos(self.decl(date))
            * cos(radians(self.ha(date, longitude)))
        )
        return acos(max(-1.0, min(1.0, val)))

    def ha_sunset(self, date, latitude):
        """Compute the hour angle of the sunset."""
        val = (
            cos(radians(90.833))
            / (cos(radians(latitude)) * cos(self.decl(date)))
            - (tan(radians(latitude)) * tan(self.decl(date)))
        )
        return degrees(acos(max(-1.0, min(1.0, val))))

    def ha_sunrise(self, date, latitude):
        """Compute the hour angle of the sunrise."""
        val = (
            cos(radians(90.833))
            / (cos(radians(latitude)) * cos(self.decl(date)))
            - (tan(radians(latitude)) * tan(self.decl(date)))
        )
        return degrees(-acos(max(-1.0, min(1.0, val))))

    def sunrise(self, date, latitude, longitude):
        """Compute the sunrise in minutes from midnight."""
        return (
            720
            - 4 * (longitude - self.ha_sunrise(date, latitude))
            - self.eqtime(date)
            + self._utc_offset_minutes(date)
        )

    def sunset(self, date, latitude, longitude):
        """Compute the sunset in minutes from midnight."""
        return (
            720
            - 4 * (longitude - self.ha_sunset(date, latitude))
            - self.eqtime(date)
            + self._utc_offset_minutes(date)
        )

    def solar_noon(self, date, longitude):
        """Compute the solar noon in minutes from midnight."""
        return (
            720
            - 4 * longitude
            - self.eqtime(date)
            + self._utc_offset_minutes(date)
        )

    def solar_midnight(self, date, longitude):
        """Compute the solar midnight in minutes from midnight."""
        return (
            -4 * longitude
            - self.eqtime(date)
            + self._utc_offset_minutes(date)
        )

    def _minutes_to_datetime(self, date, minutes):
        """Convert minutes from midnight to a datetime, handling day wrapping."""
        total_seconds = int(minutes % 1440 * 60)
        hours, remainder = divmod(total_seconds, 3600)
        mins, secs = divmod(remainder, 60)
        return datetime.datetime(date.year, date.month, date.day, hours, mins, secs)

    def solar_noon_elevation(self, date, latitude, longitude):
        """Compute the solar noon elevation."""
        noon = self.solar_noon(date, longitude)
        date_noon = self._minutes_to_datetime(date, noon)
        return self.elevation(date_noon, latitude, longitude)

    def solar_midnight_elevation(self, date, latitude, longitude):
        """Compute the solar midnight elevation."""
        midnight = self.solar_midnight(date, longitude)
        date_midnight = self._minutes_to_datetime(date, midnight)
        return self.elevation(date_midnight, latitude, longitude)

    def azimuth(self, date, latitude, longitude):
        """Compute the azimuth of the Sun."""
        date_seconds = date.hour * 60 + date.minute + date.second / 60
        midnight = self.solar_midnight(date, longitude)
        noon = self.solar_noon(date, longitude)
        midnight0 = midnight > 0
        noon1440 = noon < 1440
        before_midnight = (date_seconds - midnight % 1440) < 0
        before_noon = (date_seconds - noon % 1440) < 0
        if midnight0 and noon1440:
            if before_midnight and before_noon:
                azimuth = (
                    -acos(
                        (
                            sin(self.decl(date))
                            - sin(radians(latitude))
                            * cos(self.zenith(date, latitude, longitude))
                        )
                        / (
                            cos(radians(latitude))
                            * sin(self.zenith(date, latitude, longitude))
                        )
                    )
                    + 2 * pi
                )
            elif not before_midnight and before_noon:
                azimuth = acos(
                    (
                        sin(self.decl(date))
                        - sin(radians(latitude))
                        * cos(self.zenith(date, latitude, longitude))
                    )
                    / (
                        cos(radians(latitude))
                        * sin(self.zenith(date, latitude, longitude))
                    )
                )
            elif not before_midnight and not before_noon:
                azimuth = (
                    -acos(
                        (
                            sin(self.decl(date))
                            - sin(radians(latitude))
                            * cos(self.zenith(date, latitude, longitude))
                        )
                        / (
                            cos(radians(latitude))
                            * sin(self.zenith(date, latitude, longitude))
                        )
                    )
                    + 2 * pi
                )
        elif not midnight0 and noon1440:
            if before_midnight and before_noon:
                azimuth = acos(
                    (
                        sin(self.decl(date))
                        - sin(radians(latitude))
                        * cos(self.zenith(date, latitude, longitude))
                    )
                    / (
                        cos(radians(latitude))
                        * sin(self.zenith(date, latitude, longitude))
                    )
                )
            elif before_midnight and not before_noon:
                azimuth = (
                    -acos(
                        (
                            sin(self.decl(date))
                            - sin(radians(latitude))
                            * cos(self.zenith(date, latitude, longitude))
                        )
                        / (
                            cos(radians(latitude))
                            * sin(self.zenith(date, latitude, longitude))
                        )
                    )
                    + 2 * pi
                )
            elif not before_midnight and not before_noon:
                azimuth = acos(
                    (
                        sin(self.decl(date))
                        - sin(radians(latitude))
                        * cos(self.zenith(date, latitude, longitude))
                    )
                    / (
                        cos(radians(latitude))
                        * sin(self.zenith(date, latitude, longitude))
                    )
                )
        elif midnight0 and not noon1440:
            if before_midnight and before_noon:
                azimuth = acos(
                    (
                        sin(self.decl(date))
                        - sin(radians(latitude))
                        * cos(self.zenith(date, latitude, longitude))
                    )
                    / (
                        cos(radians(latitude))
                        * sin(self.zenith(date, latitude, longitude))
                    )
                )
            elif before_midnight and not before_noon:
                azimuth = (
                    -acos(
                        (
                            sin(self.decl(date))
                            - sin(radians(latitude))
                            * cos(self.zenith(date, latitude, longitude))
                        )
                        / (
                            cos(radians(latitude))
                            * sin(self.zenith(date, latitude, longitude))
                        )
                    )
                    + 2 * pi
                )
            elif not before_midnight and not before_noon:
                azimuth = acos(
                    (
                        sin(self.decl(date))
                        - sin(radians(latitude))
                        * cos(self.zenith(date, latitude, longitude))
                    )
                    / (
                        cos(radians(latitude))
                        * sin(self.zenith(date, latitude, longitude))
                    )
                )
        return azimuth

    def _percent_elevation(self, actual, min_elev, max_elev):
        """Compute clamped percentage of elevation within a range."""
        if max_elev <= min_elev:
            return 0.0
        return max(0.0, min(1.0, (actual - min_elev) / (max_elev - min_elev)))

    def percent_elevation_day(self, date, latitude, longitude):
        """Compute the percentage of the Sun elevation for the day."""
        max_elevation = degrees(
            self.solar_noon_elevation(date, latitude, longitude)
        )
        actual_elevation = degrees(self.elevation(date, latitude, longitude))
        return self._percent_elevation(actual_elevation, -0.833, max_elevation)

    def percent_elevation_civil_twilight(self, date, latitude, longitude):
        """Percentage of the Sun elevation for the civil twilight."""
        actual_elevation = degrees(self.elevation(date, latitude, longitude))
        return self._percent_elevation(actual_elevation, -6, -0.833)

    def percent_elevation_nautical_twilight(self, date, latitude, longitude):
        """Percentage of the Sun elevation for the nautical twilight."""
        actual_elevation = degrees(self.elevation(date, latitude, longitude))
        return self._percent_elevation(actual_elevation, -12, -6)

    def color_temp(self):
        """Compute the circadian color temperature."""
        date = dt.now()
        latitude = self.data["latitude"]
        longitude = self.data["longitude"]
        min_ct = self.data["min_colortemp"]
        max_ct = self.data["max_colortemp"]
        ct_range = max_ct - min_ct
        ct_twilight_boundary = min_ct + ct_range * 2 / 7
        actual_elevation = degrees(self.elevation(date, latitude, longitude))
        if actual_elevation > -0.833:
            return round(
                self.percent_elevation_day(date, latitude, longitude)
                * (max_ct - ct_twilight_boundary)
                + ct_twilight_boundary
            )
        elif actual_elevation > -6:
            return round(
                self.percent_elevation_civil_twilight(
                    date, latitude, longitude
                )
                * (ct_twilight_boundary - min_ct)
                + min_ct
            )
        else:
            return min_ct

    def brightness(self):
        """Compute the circadian brightness."""
        date = dt.now()
        latitude = self.data["latitude"]
        longitude = self.data["longitude"]
        actual_elevation = degrees(self.elevation(date, latitude, longitude))
        if actual_elevation > -6:
            return 100
        elif actual_elevation <= -6 and actual_elevation > -12:
            return round(
                self.percent_elevation_nautical_twilight(
                    date, latitude, longitude
                )
                * 50
                + 50
            )
        else:
            return 50

    def _update(self, *args, **kwargs):
        """Update Circadian Values."""
        self.data["color_temp"] = self.color_temp()
        self.data["brightness"] = self.brightness()
        dispatcher_send(self.hass, CIRCADIAN_LIGHTING_UPDATE_TOPIC)
