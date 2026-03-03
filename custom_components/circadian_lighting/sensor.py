"""Platform for sensor integration."""

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.const import PERCENTAGE
from custom_components.circadian_lighting import (
    DOMAIN,
    CIRCADIAN_LIGHTING_UPDATE_TOPIC,
    DATA_CIRCADIAN_LIGHTING,
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    cl = hass.data.get(DATA_CIRCADIAN_LIGHTING)
    if cl:
        clcts = CircadianLightColorTemperatureSensor(cl)
        clbs = CircadianLightBrightnessSensor(cl)
        add_entities([clcts, clbs])

        def update(call=None):
            """Force an immediate recalculation of circadian values."""
            cl.update()

        hass.services.register(DOMAIN, "values_update", update)
        return True
    else:
        return False


class CircadianLightColorTemperatureSensor(SensorEntity):
    """Circadian light color temperature sensor."""

    _attr_name = "Circadian Light Color Temperature"
    _attr_unique_id = "circadian_light_color_temperature"
    _attr_native_unit_of_measurement = "K"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:thermometer"

    def __init__(self, cl):
        """Initialize the sensor."""
        self._cl = cl
        self._attr_native_value = self._cl.data["color_temp"]

    async def async_added_to_hass(self):
        """Register dispatcher listener when added to hass."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                CIRCADIAN_LIGHTING_UPDATE_TOPIC,
                self._update_sensor,
            )
        )

    def _update_sensor(self):
        """Set sensor data from circadian lighting."""
        if self._cl.data is not None:
            self._attr_native_value = self._cl.data["color_temp"]
            self.schedule_update_ha_state()

    def update(self):
        """Fetch new state data for the sensor."""
        self._cl.update()


class CircadianLightBrightnessSensor(SensorEntity):
    """Circadian light brightness sensor."""

    _attr_name = "Circadian Light Brightness"
    _attr_unique_id = "circadian_light_brightness"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:brightness-6"

    def __init__(self, cl):
        """Initialize the sensor."""
        self._cl = cl
        self._attr_native_value = self._cl.data["brightness"]

    async def async_added_to_hass(self):
        """Register dispatcher listener when added to hass."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                CIRCADIAN_LIGHTING_UPDATE_TOPIC,
                self._update_sensor,
            )
        )

    def _update_sensor(self):
        """Set sensor data from circadian lighting."""
        if self._cl.data is not None:
            self._attr_native_value = self._cl.data["brightness"]
            self.schedule_update_ha_state()

    def update(self):
        """Fetch new state data for the sensor."""
        self._cl.update()
