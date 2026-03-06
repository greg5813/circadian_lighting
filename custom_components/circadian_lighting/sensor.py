"""Platform for sensor integration."""

from custom_components.circadian_lighting import (
    CIRCADIAN_LIGHTING_UPDATE_TOPIC,
    DATA_CIRCADIAN_LIGHTING,
    DOMAIN,
)
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.dispatcher import dispatcher_connect
from homeassistant.helpers.entity import Entity


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    cl = hass.data.get(DATA_CIRCADIAN_LIGHTING)
    if cl:
        clcts = CircadianLightColorTemperatureSensor(hass, cl)
        clbs = CircadianLightBrightnessSensor(hass, cl)
        add_entities([clcts, clbs])

        def update(call=None):
            """Update component."""
            cl.force_update()

        service_name = "values_update"
        hass.services.register(DOMAIN, service_name, update)
        return True
    else:
        return False


class CircadianLightSensorBase(Entity):
    """Base class for circadian lighting sensors."""

    _data_key: str
    _attr_name: str
    _attr_entity_id: str
    _attr_unit: str

    def __init__(self, hass, cl):
        """Initialize the sensor."""
        super().__init__()
        self._cl = cl
        self._name = self._attr_name
        self._entity_id = self._attr_entity_id
        self._state = self._cl.data[self._data_key]
        self._unit_of_measurement = self._attr_unit
        dispatcher_connect(hass, CIRCADIAN_LIGHTING_UPDATE_TOPIC, self.update_sensor)

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
            self._state = self._cl.data[self._data_key]
            if self.hass is not None:
                self.schedule_update_ha_state()


class CircadianLightColorTemperatureSensor(CircadianLightSensorBase):
    """Representation of a color temperature sensor."""

    _data_key = "color_temp"
    _attr_name = "Circadian Light Color Temperature"
    _attr_entity_id = "sensor.circadian_light_color_temperature"
    _attr_unit = "K"


class CircadianLightBrightnessSensor(CircadianLightSensorBase):
    """Representation of a brightness sensor."""

    _data_key = "brightness"
    _attr_name = "Circadian Light Brightness"
    _attr_entity_id = "sensor.circadian_light_brightness"
    _attr_unit = PERCENTAGE
