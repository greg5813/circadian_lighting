"""Platform for sensor integration."""

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.dispatcher import dispatcher_connect
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from custom_components.circadian_lighting import (
    DOMAIN,
    CIRCADIAN_LIGHTING_UPDATE_TOPIC,
    DATA_CIRCADIAN_LIGHTING,
)


DEPENDENCIES = ["circadian_lighting"]


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    cl = hass.data.get(DATA_CIRCADIAN_LIGHTING)
    if cl:
        clcts = CircadianLightColorTemperatureSensor(hass, cl)
        clbs = CircadianLightBrightnessSensor(hass, cl)
        add_entities([clcts, clbs])

        def update(call=None):
            """Update component."""
            cl._update()

        service_name = "values_update"
        hass.services.register(DOMAIN, service_name, update)
        return True
    else:
        return False


class CircadianLightColorTemperatureSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, hass, cl):
        """Initialize the sensor."""
        self._cl = cl
        self._name = "Circadian Light Color Temperature"
        self._entity_id = "sensor.circadian_light_color_temperature"
        self._state = self._cl.data["color_temp"]
        self._unit_of_measurement = UnitOfTemperature.TEMP_KELVIN

        """Register callbacks."""
        dispatcher_connect(
            hass, CIRCADIAN_LIGHTING_UPDATE_TOPIC, self.update_sensor
        )

    @property
    def entity_id(self):
        """Return the entity ID of the sensor."""
        return self._entity_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    def update(self):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._cl.update()

    def update_sensor(self):
        """Set sensor data from circadian lighting."""
        if self._cl.data is not None:
            self._state = self._cl.data["color_temp"]


class CircadianLightBrightnessSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, hass, cl):
        """Initialize the sensor."""
        self._cl = cl
        self._name = "Circadian Light Brightness"
        self._entity_id = "sensor.circadian_light_brightness"
        self._state = self._cl.data["brightness"]
        self._unit_of_measurement = PERCENTAGE

        """Register callbacks."""
        dispatcher_connect(
            hass, CIRCADIAN_LIGHTING_UPDATE_TOPIC, self.update_sensor
        )

    @property
    def entity_id(self):
        """Return the entity ID of the sensor."""
        return self._entity_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    def update(self):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        self._cl.update()

    def update_sensor(self):
        """Set sensor data from circadian lighting."""
        if self._cl.data is not None:
            self._state = self._cl.data["brightness"]
