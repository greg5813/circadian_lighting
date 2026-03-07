"""Tests for custom_components.circadian_lighting.sensor."""

from unittest.mock import MagicMock

from custom_components.circadian_lighting import (
    CIRCADIAN_LIGHTING_UPDATE_TOPIC,
    DATA_CIRCADIAN_LIGHTING,
    DOMAIN,
)
from custom_components.circadian_lighting.sensor import (
    CircadianLightBrightnessSensor,
    CircadianLightColorTemperatureSensor,
    setup_platform,
)
from homeassistant.const import PERCENTAGE


def _make_cl_mock():
    cl = MagicMock()
    cl.data = {"color_temp": 4000, "brightness": 100}
    cl.update = MagicMock()
    cl.force_update = MagicMock()
    return cl


# ---------------------------------------------------------------------------
# setup_platform
# ---------------------------------------------------------------------------


class TestSetupPlatform:
    def test_returns_true_when_cl_exists(self, mock_hass, mock_dispatcher_connect):
        cl = _make_cl_mock()
        mock_hass.data[DATA_CIRCADIAN_LIGHTING] = cl
        add_entities = MagicMock()
        assert setup_platform(mock_hass, {}, add_entities) is True

    def test_returns_false_when_cl_missing(self, mock_hass, mock_dispatcher_connect):
        add_entities = MagicMock()
        assert setup_platform(mock_hass, {}, add_entities) is False

    def test_adds_two_entities(self, mock_hass, mock_dispatcher_connect):
        cl = _make_cl_mock()
        mock_hass.data[DATA_CIRCADIAN_LIGHTING] = cl
        add_entities = MagicMock()
        setup_platform(mock_hass, {}, add_entities)
        add_entities.assert_called_once()
        entities = add_entities.call_args[0][0]
        assert len(entities) == 2

    def test_registers_service(self, mock_hass, mock_dispatcher_connect):
        cl = _make_cl_mock()
        mock_hass.data[DATA_CIRCADIAN_LIGHTING] = cl
        setup_platform(mock_hass, {}, MagicMock())
        mock_hass.services.register.assert_called_once()
        call_args = mock_hass.services.register.call_args
        assert call_args[0][0] == DOMAIN
        assert call_args[0][1] == "values_update"

    def test_service_calls_force_update(self, mock_hass, mock_dispatcher_connect):
        cl = _make_cl_mock()
        mock_hass.data[DATA_CIRCADIAN_LIGHTING] = cl
        setup_platform(mock_hass, {}, MagicMock())
        service_callback = mock_hass.services.register.call_args[0][2]
        service_callback()
        cl.force_update.assert_called_once()

    def test_service_accepts_call_param(self, mock_hass, mock_dispatcher_connect):
        cl = _make_cl_mock()
        mock_hass.data[DATA_CIRCADIAN_LIGHTING] = cl
        setup_platform(mock_hass, {}, MagicMock())
        service_callback = mock_hass.services.register.call_args[0][2]
        service_callback(call=MagicMock())  # should not raise

    def test_discovery_info_default(self, mock_hass, mock_dispatcher_connect):
        cl = _make_cl_mock()
        mock_hass.data[DATA_CIRCADIAN_LIGHTING] = cl
        assert setup_platform(mock_hass, {}, MagicMock(), discovery_info=None) is True


# ---------------------------------------------------------------------------
# CircadianLightColorTemperatureSensor
# ---------------------------------------------------------------------------


class TestColorTemperatureSensor:
    def _make_sensor(self, mock_hass, mock_dispatcher_connect):
        cl = _make_cl_mock()
        cl.data = {"color_temp": 4500, "brightness": 80}
        return CircadianLightColorTemperatureSensor(mock_hass, cl), cl

    def test_name(self, mock_hass, mock_dispatcher_connect):
        sensor, _ = self._make_sensor(mock_hass, mock_dispatcher_connect)
        assert sensor.name == "Circadian Light Color Temperature"

    def test_entity_id(self, mock_hass, mock_dispatcher_connect):
        sensor, _ = self._make_sensor(mock_hass, mock_dispatcher_connect)
        assert sensor.entity_id == "sensor.circadian_light_color_temperature"

    def test_initial_state(self, mock_hass, mock_dispatcher_connect):
        sensor, _ = self._make_sensor(mock_hass, mock_dispatcher_connect)
        assert sensor.state == 4500

    def test_unit_of_measurement(self, mock_hass, mock_dispatcher_connect):
        sensor, _ = self._make_sensor(mock_hass, mock_dispatcher_connect)
        assert sensor.unit_of_measurement == "K"

    def test_update_calls_throttled(self, mock_hass, mock_dispatcher_connect):
        sensor, cl = self._make_sensor(mock_hass, mock_dispatcher_connect)
        sensor.update()
        cl.update.assert_called_once()

    def test_update_sensor_updates_state(self, mock_hass, mock_dispatcher_connect):
        sensor, cl = self._make_sensor(mock_hass, mock_dispatcher_connect)
        cl.data["color_temp"] = 3000
        sensor.update_sensor()
        assert sensor.state == 3000

    def test_update_sensor_none_data(self, mock_hass, mock_dispatcher_connect):
        sensor, cl = self._make_sensor(mock_hass, mock_dispatcher_connect)
        original_state = sensor.state
        cl.data = None
        sensor.update_sensor()
        assert sensor.state == original_state

    def test_dispatcher_connect_called(self, mock_hass, mock_dispatcher_connect):
        sensor, _ = self._make_sensor(mock_hass, mock_dispatcher_connect)
        mock_dispatcher_connect.assert_called_with(
            mock_hass, CIRCADIAN_LIGHTING_UPDATE_TOPIC, sensor.update_sensor
        )

    def test_update_sensor_calls_schedule_update(
        self, mock_hass, mock_dispatcher_connect
    ):
        sensor, cl = self._make_sensor(mock_hass, mock_dispatcher_connect)
        sensor.hass = mock_hass
        sensor.schedule_update_ha_state = MagicMock()
        cl.data["color_temp"] = 4500
        sensor.update_sensor()
        sensor.schedule_update_ha_state.assert_called_once()


# ---------------------------------------------------------------------------
# CircadianLightBrightnessSensor
# ---------------------------------------------------------------------------


class TestBrightnessSensor:
    def _make_sensor(self, mock_hass, mock_dispatcher_connect):
        cl = _make_cl_mock()
        cl.data = {"color_temp": 4500, "brightness": 80}
        return CircadianLightBrightnessSensor(mock_hass, cl), cl

    def test_name(self, mock_hass, mock_dispatcher_connect):
        sensor, _ = self._make_sensor(mock_hass, mock_dispatcher_connect)
        assert sensor.name == "Circadian Light Brightness"

    def test_entity_id(self, mock_hass, mock_dispatcher_connect):
        sensor, _ = self._make_sensor(mock_hass, mock_dispatcher_connect)
        assert sensor.entity_id == "sensor.circadian_light_brightness"

    def test_initial_state(self, mock_hass, mock_dispatcher_connect):
        sensor, _ = self._make_sensor(mock_hass, mock_dispatcher_connect)
        assert sensor.state == 80

    def test_unit_of_measurement(self, mock_hass, mock_dispatcher_connect):
        sensor, _ = self._make_sensor(mock_hass, mock_dispatcher_connect)
        assert sensor.unit_of_measurement == PERCENTAGE

    def test_update_calls_throttled(self, mock_hass, mock_dispatcher_connect):
        sensor, cl = self._make_sensor(mock_hass, mock_dispatcher_connect)
        sensor.update()
        cl.update.assert_called_once()

    def test_update_sensor_updates_state(self, mock_hass, mock_dispatcher_connect):
        sensor, cl = self._make_sensor(mock_hass, mock_dispatcher_connect)
        cl.data["brightness"] = 60
        sensor.update_sensor()
        assert sensor.state == 60

    def test_update_sensor_none_data(self, mock_hass, mock_dispatcher_connect):
        sensor, cl = self._make_sensor(mock_hass, mock_dispatcher_connect)
        original_state = sensor.state
        cl.data = None
        sensor.update_sensor()
        assert sensor.state == original_state

    def test_dispatcher_connect_called(self, mock_hass, mock_dispatcher_connect):
        sensor, _ = self._make_sensor(mock_hass, mock_dispatcher_connect)
        mock_dispatcher_connect.assert_called_with(
            mock_hass, CIRCADIAN_LIGHTING_UPDATE_TOPIC, sensor.update_sensor
        )
