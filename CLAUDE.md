# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant custom component that calculates circadian lighting values (color temperature and brightness) based on sun position using astronomical formulas. Distributed via HACS. No external dependencies — uses only Home Assistant built-ins and Python standard library.

## CI/CD

There are no tests or linters configured locally. CI runs three GitHub Actions workflows (on push, PR, and weekly schedule):

- **HACS validation**: `hacs/action@main` — validates HACS compatibility
- **Hassfest**: `home-assistant/actions/hassfest@master` — validates HA component standards
- **SonarCloud**: `SonarSource/sonarqube-scan-action@v7` — code quality analysis (Python 3.13)

## Architecture

All source lives under `custom_components/circadian_lighting/`.

### `__init__.py` — Core engine

- `setup()` entry point: reads YAML config, creates `CircadianLighting` instance, stores it in `hass.data`, and loads the sensor platform via `load_platform()`
- `CircadianLighting` class: implements solar position math (fractional year, equation of time, declination, hour angle, elevation) using trigonometric formulas from NOAA
- `color_temp()`: returns Kelvin value based on sun elevation thresholds, using configured `min_colortemp`/`max_colortemp`:
  - Above -0.833°: twilight boundary to max_colortemp (linearly scaled by % of noon elevation)
  - Between -6° and -0.833° (civil twilight): min_colortemp to twilight boundary
  - Below -6°: fixed min_colortemp
- `brightness()`: returns percentage based on sun elevation:
  - Above -6°: 100%
  - Between -12° and -6° (nautical twilight): 50%–100%
  - Below -12°: fixed 50%
- Updates are throttled via `homeassistant.util.Throttle` (configurable interval, default 60s)
- Notifies sensors via `dispatcher_send(CIRCADIAN_LIGHTING_UPDATE_TOPIC)`

### `sensor.py` — HA sensor entities

- `CircadianLightColorTemperatureSensor` (unit: K) and `CircadianLightBrightnessSensor` (unit: %)
- Both inherit from `SensorEntity` with `unique_id`, `state_class=MEASUREMENT`
- Dispatcher listener registered in `async_added_to_hass()` with proper cleanup via `async_on_remove()`
- Registers `circadian_lighting.values_update` service for manual recalculation

### Update flow

1. HA polls sensor → `sensor.update()` → `CircadianLighting.update()` (throttled)
2. If throttle allows: recalculates color_temp/brightness → `dispatcher_send()`
3. Dispatcher triggers `sensor._update_sensor()` → sensor state refreshed + `schedule_update_ha_state()`

### Configuration (YAML)

```yaml
circadian_lighting:
  min_colortemp: 2000      # range: 1000-10000
  max_colortemp: 5500      # range: 1000-10000
  latitude: ...            # defaults to HA config
  longitude: ...           # defaults to HA config
  interval: 60             # seconds between recalculations
```
