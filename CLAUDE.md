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

**Linting** is handled by MegaLinter in CI. To run locally:
```bash
docker run --rm -v "$(pwd):/tmp/lint" oxsecurity/megalinter:v9
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
- `color_temp()`: Returns Kelvin value based on sun elevation thresholds:
  - Above -0.833° (day): 3000–5500K scaled by percent of max elevation
  - -0.833° to -6° (civil twilight): 2000–3000K
  - Below -6° (night): fixed 2000K
- `brightness()`: Returns percentage based on elevation:
  - Above -6°: 100%
  - -6° to -12° (nautical twilight): 50–100% linear
  - Below -12°: 50%
- Updates are throttled via `homeassistant.util.Throttle` (configurable interval, default 60s).
- Notifies sensors via `dispatcher_send` on the `circadian_lighting_update` topic.

### `sensor.py` — Sensor entities
- `CircadianLightColorTemperatureSensor` and `CircadianLightBrightnessSensor` — both extend `homeassistant.helpers.entity.Entity`.
- Listen for dispatcher updates and also implement `update()` which triggers the throttled recalculation.
- Registers the `circadian_lighting.values_update` service for manual refresh.

### Configuration (via `configuration.yaml`)
| Key | Default | Range |
|-----|---------|-------|
| `min_colortemp` | 2000 | 1000–10000 |
| `max_colortemp` | 5500 | 1000–10000 |
| `latitude` | HA latitude | valid lat |
| `longitude` | HA longitude | valid lon |
| `interval` | 60 (seconds) | positive int |

## Key Conventions

- This is a YAML-configured integration (not config flow) — uses `CONFIG_SCHEMA` + `setup()`, not `async_setup_entry()`.
- No external Python dependencies — only HA built-ins (`voluptuous`, `homeassistant.*`) and stdlib (`math`, `datetime`, `calendar`).
- Solar calculations are self-contained in `CircadianLighting` (no third-party astronomy library).
- Integration version is tracked in `manifest.json`.
- HACS compatibility is maintained via `hacs.json` (`content_in_root: false`).
