# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant custom integration that provides circadian lighting sensors — computing color temperature (Kelvin) and brightness (%) based on sun position using NOAA solar calculation algorithms.

## Development Commands

**Testing** uses pytest with coverage. Test dependencies are in `requirements_test.txt`.
```bash
pip install -r requirements_test.txt
pytest                                        # run all tests
pytest tests/test_daily_profile.py -s         # run daily profile tests (prints 24h sensor tables)
pytest -k "spring_equinox" -s                 # run a single date scenario
```
Coverage reports are generated automatically (terminal + `coverage.xml`). Branch coverage is enabled. Tests live in `tests/` and mock `dt.now()` and HA dispatcher/platform internals via fixtures in `tests/conftest.py`.

**Linting** is handled by MegaLinter in CI. To run locally (auto-fixes and updated-sources reporter are disabled because `git diff` crashes with SIGBUS inside Docker Desktop macOS volume mounts):
```bash
rm -rf megalinter-reports/ && docker run --rm -v "$(pwd):/tmp/lint" -e APPLY_FIXES=none -e UPDATED_SOURCES_REPORTER=false oxsecurity/megalinter:v9
```

**CI validation workflows** (all run in GitHub Actions):
- HACS validation (`hacs.yml`)
- Hassfest validation (`hassfest.yml`)
- MegaLinter (`mega-linter.yml`) — auto-fixes and commits on PRs
- SonarCloud static analysis (`sonarcloud.yml`) — reads `coverage.xml` for coverage metrics

## Architecture

All source code lives in `custom_components/circadian_lighting/`.

### `__init__.py` — Integration setup + solar math engine
- `setup(hass, config)`: HA entry point. Reads config, creates `CircadianLighting` instance, stores it in `hass.data`, loads the sensor platform.
- `CircadianLighting`: Core class implementing NOAA solar position algorithms from scratch using Python `math`. Computes fractional year → equation of time → declination → hour angle → elevation/zenith/azimuth → sunrise/sunset/solar noon. All trig uses radians internally.
  - Config is stored as instance attributes (`min_colortemp`, `max_colortemp`, `latitude`, `longitude`, `interval`); computed state lives in `self.data` dict (`color_temp`, `brightness`).
- `color_temp(date=None)`: Returns Kelvin value based on sun elevation thresholds. Accepts optional datetime; defaults to `dt.now()`. The total range is split 5/7 for daytime and 2/7 for civil twilight. Return values are clamped to `[min_ct, max_ct]`.
  - Above -0.833° (day): `mid_ct`–`max_ct` scaled by percent of max elevation
  - -0.833° to -6° (civil twilight): `min_ct`–`mid_ct`
  - Below -6° (night): fixed `min_ct`
- `brightness(date=None)`: Returns percentage based on elevation. Accepts optional datetime; defaults to `dt.now()`.
  - Above -6°: 100%
  - -6° to -12° (nautical twilight): 50–100% linear
  - Below -12°: 50%
- `force_update()`: Public method to trigger an immediate update bypassing the throttle.
- `_update()` captures `dt.now()` once and passes it to both `color_temp()` and `brightness()` for time consistency. The UTC offset (`_utc_offset_min`) is also cached per update cycle.
- Updates are throttled via `homeassistant.util.Throttle` (configurable interval, default 60s).
- Notifies sensors via `dispatcher_send` on the `circadian_lighting_update` topic.
- `zenith()` is defined as `pi/2 - elevation()` to avoid formula duplication.
- `percent_elevation_day(actual_elevation_deg, date, lat, lon)` accepts pre-computed elevation to avoid redundant recalculation. `percent_elevation_civil_twilight(actual_elevation_deg)` and `percent_elevation_nautical_twilight(actual_elevation_deg)` take only the elevation value.

### `sensor.py` — Sensor entities
- `CircadianLightSensorBase`: Abstract base class extending `homeassistant.helpers.entity.Entity`. Subclasses declare `_data_key`, `_attr_name`, `_attr_entity_id`, and `_attr_unit` as class attributes.
- `CircadianLightColorTemperatureSensor` and `CircadianLightBrightnessSensor` — thin subclasses that only set the four class attributes above.
- Sensors listen for dispatcher updates and implement `update()` which triggers the throttled recalculation. `update_sensor()` calls `schedule_update_ha_state()` to push state changes to HA.
- Registers the `circadian_lighting.values_update` service for manual refresh (calls `force_update()`).

### Configuration (via `configuration.yaml`)

| Key             | Default      | Range        |
|-----------------|--------------|--------------|
| `min_colortemp` | 2000         | 1000–10000   |
| `max_colortemp` | 5500         | 1000–10000   |
| `latitude`      | HA latitude  | valid lat    |
| `longitude`     | HA longitude | valid lon    |
| `interval`      | 60 (seconds) | positive int |

`min_colortemp` must be strictly less than `max_colortemp` (validated at config load).

## Key Conventions

- This is a YAML-configured integration (not config flow) — uses `CONFIG_SCHEMA` + `setup()`, not `async_setup_entry()`.
- No external Python dependencies — only HA built-ins (`voluptuous`, `homeassistant.*`) and stdlib (`math`, `datetime`, `calendar`).
- Solar calculations are self-contained in `CircadianLighting` (no third-party astronomy library).
- Integration version is tracked in `manifest.json`.
- HACS compatibility is maintained via `hacs.json` (`content_in_root: false`).

## Change Workflow

When making modifications, always follow this process using subagents for each step:

1. **Code review** — Review your changes using a subagent. Fix findings using subagents. Iterate until no findings remain.
2. **Security review** — Security-review your changes using a subagent. Fix findings using subagents. Iterate until no findings remain.
3. **Tests** — Verify tests still pass with 100% coverage using a subagent. Fix failures using subagents. Never delete tests to make them pass.
4. **Linters** — Verify linters still pass using a subagent. Fix findings using subagents. Never disable linters.
5. **Update CLAUDE.md** — If the changes affect architecture, conventions, or configuration, update this file.
6. **Commit** — Commit your changes.
