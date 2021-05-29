"""The circadian lighting integration."""

import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.light import VALID_TRANSITION
from homeassistant.const import (CONF_LATITUDE, CONF_LONGITUDE)
from homeassistant.util import Throttle, dt
from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers.dispatcher import dispatcher_send
from datetime import timedelta
import calendar, datetime
from math import pi, sin, cos, tan, asin, acos, degrees, radians, modf, floor
import logging

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'circadian_lighting'
CIRCADIAN_LIGHTING_PLATFORMS = ['sensor', 'switch']
CIRCADIAN_LIGHTING_UPDATE_TOPIC = '{0}_update'.format(DOMAIN)
DATA_CIRCADIAN_LIGHTING = 'data_cl'

CONF_MIN_CT = 'min_colortemp'
DEFAULT_MIN_CT = 2000
CONF_MAX_CT = 'max_colortemp'
DEFAULT_MAX_CT = 5500
CONF_INTERVAL = 'interval'
DEFAULT_INTERVAL = 60

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Optional(CONF_MIN_CT, default=DEFAULT_MIN_CT):
            vol.All(vol.Coerce(int), vol.Range(min=1000, max=10000)),
        vol.Optional(CONF_MAX_CT, default=DEFAULT_MAX_CT):
            vol.All(vol.Coerce(int), vol.Range(min=1000, max=10000)),
        vol.Optional(CONF_LATITUDE): cv.latitude,
        vol.Optional(CONF_LONGITUDE): cv.longitude,
        vol.Optional(CONF_INTERVAL, default=DEFAULT_INTERVAL): cv.positive_int,
    }),
}, extra=vol.ALLOW_EXTRA)

def setup(hass, config):

    conf = config[DOMAIN]
    min_colortemp = conf.get(CONF_MIN_CT)
    max_colortemp = conf.get(CONF_MAX_CT)
    latitude = conf.get(CONF_LATITUDE, hass.config.latitude)
    longitude = conf.get(CONF_LONGITUDE, hass.config.longitude)
    interval = conf.get(CONF_INTERVAL)

    load_platform(hass, 'sensor', DOMAIN, {}, config)

    cl = CircadianLighting(hass, min_colortemp, max_colortemp, latitude, longitude, interval)

    hass.data[DATA_CIRCADIAN_LIGHTING] = cl

    return True

class CircadianLighting(object):

    def __init__(self, hass, min_colortemp, max_colortemp, latitude, longitude, interval):

        self.hass = hass
        self.data = {}
        self.data['min_colortemp'] = min_colortemp
        self.data['max_colortemp'] = max_colortemp
        self.data['latitude'] = latitude
        self.data['longitude'] = longitude
        self.data['interval'] = interval
        self.data['color_temp'] = self.color_temp()
        self.data['brightness'] = self.brightness()

        self.update = Throttle(timedelta(seconds=interval))(self._update)

    def fractional_year(self, date):
        if calendar.isleap(date.timetuple().tm_year):
            fractional_year = 2 * pi / 366 * ( date.timetuple().tm_yday - 1 + ( date.timetuple().tm_hour - 12 ) / 24 )
        else:
            fractional_year = 2 * pi / 365 * ( date.timetuple().tm_yday - 1 + ( date.timetuple().tm_hour - 12 ) / 24 )
        return fractional_year

    def eqtime(self, date):
        return 229.18 * ( 0.000075 + 0.001868 * cos(self.fractional_year(date)) - 0.032077 * sin(self.fractional_year(date)) - 0.014615 * cos(2*self.fractional_year(date)) - 0.040849 * sin(2*self.fractional_year(date)) )

    def decl(self, date):
        return 0.006918 - 0.399912 * cos(self.fractional_year(date)) + 0.070257 * sin(self.fractional_year(date)) - 0.006758 * cos(2*self.fractional_year(date)) + 0.000907 * sin(2*self.fractional_year(date)) - 0.002697 * cos(3*self.fractional_year(date)) + 0.00148 * sin(3*self.fractional_year(date))

    def time_offset(self, date, longitude):
        return self.eqtime(date) + 4 * longitude - round(dt.now().utcoffset().total_seconds() / 60)

    def tst(self, date, longitude):
        return date.timetuple().tm_hour * 60 + date.timetuple().tm_min + date.timetuple().tm_sec / 60 + self.time_offset(date, longitude)

    def ha(self, date, longitude):
        return ( self.tst(date, longitude) / 4 ) - 180

    def elevation(self, date, latitude, longitude):
        return asin(sin(radians(latitude))*sin(self.decl(date))+cos(radians(latitude))*cos(self.decl(date))*cos(radians(self.ha(date, longitude))))

    def zenith(self, date, latitude, longitude):
        return acos(sin(radians(latitude))*sin(self.decl(date))+cos(radians(latitude))*cos(self.decl(date))*cos(radians(self.ha(date, longitude))))

    def ha_sunset(self, date, latitude):
        return degrees(acos(cos(radians(90.833))/(cos(radians(latitude))*cos(self.decl(date)))-(tan(radians(latitude))*tan(self.decl(date)))))

    def ha_sunrise(self, date, latitude):
        return degrees(-acos(cos(radians(90.833))/(cos(radians(latitude))*cos(self.decl(date)))-(tan(radians(latitude))*tan(self.decl(date)))))

    def sunrise(self, date, latitude, longitude):
        return 720 - 4 * (longitude - self.ha_sunrise(date, latitude)) - self.eqtime(date)+ round(dt.now().utcoffset().total_seconds() / 60)

    def sunset(self, date, latitude, longitude):
        return 720 - 4 * (longitude - self.ha_sunset(date, latitude)) - self.eqtime(date) + round(dt.now().utcoffset().total_seconds() / 60)

    def solar_noon(self, date, longitude):
        return 720 - 4 * longitude - self.eqtime(date) + round(dt.now().utcoffset().total_seconds() / 60)

    def solar_midnight(self, date, longitude):
        return - 4 * longitude - self.eqtime(date) + round(dt.now().utcoffset().total_seconds() / 60)

    def solar_noon_elevation(self, date, latitude, longitude):
        noon = self.solar_noon(date, longitude)
        date_noon = datetime.datetime(date.year,date.month,date.day,int(modf(noon/60)[1]),int(modf(60*modf(noon/60)[0])[1]),floor(60*modf(60*modf(noon/60)[0])[0]))
        return self.elevation(date_noon, latitude, longitude)

    def solar_midnight_elevation(self, date, latitude, longitude):
        midnight = self.solar_midnight(date, longitude)
        date_midnight = datetime.datetime(date.year,date.month,date.day,int(modf(midnight/60)[1]),int(modf(60*modf(midnight/60)[0])[1]),floor(60*modf(60*modf(midnight/60)[0])[0]))
        return self.elevation(date_midnight, latitude, longitude)

    def azimuth(self, date, latitude, longitude):
        date_seconds = date.hour * 60 + date.minute + date.second / 60
        midnight = self.solar_midnight(date, longitude)
        noon = self.solar_noon(date, longitude)
        midnight0 = midnight > 0
        noon1440 = noon < 1440
        before_midnight = (date_seconds - midnight % 1440) < 0
        before_noon = (date_seconds - noon % 1440) < 0
        if (midnight0 and noon1440):
            if (before_midnight and before_noon):
                azimuth = -acos((sin(self.decl(date))-sin(radians(latitude))*cos(self.zenith(date,latitude,longitude)))/(cos(radians(latitude))*sin(self.zenith(date,latitude,longitude))))+2*pi
            elif (not before_midnight and before_noon):
                azimuth = acos((sin(self.decl(date))-sin(radians(latitude))*cos(self.zenith(date,latitude,longitude)))/(cos(radians(latitude))*sin(self.zenith(date,latitude,longitude))))
            elif (not before_midnight and not before_noon):
                azimuth = -acos((sin(self.decl(date))-sin(radians(latitude))*cos(self.zenith(date,latitude,longitude)))/(cos(radians(latitude))*sin(self.zenith(date,latitude,longitude))))+2*pi
        elif (not midnight0 and noon1440):
            if (before_midnight and before_noon):
                azimuth = acos((sin(self.decl(date))-sin(radians(latitude))*cos(self.zenith(date,latitude,longitude)))/(cos(radians(latitude))*sin(self.zenith(date,latitude,longitude))))
            elif (before_midnight and not before_noon):
                azimuth = -acos((sin(self.decl(date))-sin(radians(latitude))*cos(self.zenith(date,latitude,longitude)))/(cos(radians(latitude))*sin(self.zenith(date,latitude,longitude))))+2*pi
            elif (not before_midnight and not before_noon):
                azimuth = acos((sin(self.decl(date))-sin(radians(latitude))*cos(self.zenith(date,latitude,longitude)))/(cos(radians(latitude))*sin(self.zenith(date,latitude,longitude))))
        elif (midnight0 and not noon1440):
            if (before_midnight and before_noon):
                azimuth = acos((sin(self.decl(date))-sin(radians(latitude))*cos(self.zenith(date,latitude,longitude)))/(cos(radians(latitude))*sin(self.zenith(date,latitude,longitude))))
            elif (before_midnight and not before_noon):
                azimuth = -acos((sin(self.decl(date))-sin(radians(latitude))*cos(self.zenith(date,latitude,longitude)))/(cos(radians(latitude))*sin(self.zenith(date,latitude,longitude))))+2*pi
            elif (not before_midnight and not before_noon):
                azimuth = acos((sin(self.decl(date))-sin(radians(latitude))*cos(self.zenith(date,latitude,longitude)))/(cos(radians(latitude))*sin(self.zenith(date,latitude,longitude))))
        return azimuth

    def percent_elevation_day(self, date, latitude, longitude):
        max_elevation = degrees(self.solar_noon_elevation(date, latitude, longitude))
        min_elevation = -0.833
        actual_elevation = degrees(self.elevation(date, latitude, longitude))
        return (actual_elevation-min_elevation)/(max_elevation-min_elevation)

    def percent_elevation_civil_twilight(self, date, latitude, longitude):
        max_elevation = -0.833
        min_elevation = -6
        actual_elevation = degrees(self.elevation(date, latitude, longitude))
        return (actual_elevation-min_elevation)/(max_elevation-min_elevation)

    def percent_elevation_nautical_twilight(self, date, latitude, longitude):
        max_elevation = -6
        min_elevation = -12
        actual_elevation = degrees(self.elevation(date, latitude, longitude))
        return (actual_elevation-min_elevation)/(max_elevation-min_elevation)

    def color_temp(self):
        date = dt.now()
        latitude = self.data['latitude']
        longitude = self.data['longitude']
        actual_elevation = degrees(self.elevation(date, latitude, longitude))
        if (actual_elevation > -0.833):
            return round(self.percent_elevation_day(date, latitude, longitude) * 2500 + 3000)
        elif (actual_elevation <= -0.833 and actual_elevation > -6):
            return round(self.percent_elevation_civil_twilight(date, latitude, longitude) * 1000 + 2000)
        else:
            return 2000

    def brightness(self):
        date = dt.now()
        latitude = self.data['latitude']
        longitude = self.data['longitude']
        actual_elevation = degrees(self.elevation(date, latitude, longitude))
        if (actual_elevation > -6):
            return 100
        elif (actual_elevation <= -6 and actual_elevation > -12):
            return round(self.percent_elevation_nautical_twilight(date, latitude, longitude) * 50 + 50)
        else:
            return 50

    def _update(self, *args, **kwargs):
        """Update Circadian Values."""
        self.data['color_temp'] = self.color_temp()
        self.data['brightness'] = self.brightness()
        dispatcher_send(self.hass, CIRCADIAN_LIGHTING_UPDATE_TOPIC)