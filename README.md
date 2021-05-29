# circadian_lighting

![codeql-analysis](https://github.com/greg5813/circadian_lighting/actions/workflows/codeql-analysis.yml/badge.svg)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

Circadian lighting custom component for Home Assistant that brings several features that help to mimick the Sun light with connected lights.

## Features

### Brightness

The `Brightness` returns a brightness percentage between 0% and 100% depending on:

* the date and time
* the latitude
* the longitude

Current configuration is as follow:

* during civil twilight ( sun elevation > -6° ): Brightness = 100%
* between civil and nautical twilight ( -12° < sun elevation < -6° ): Brightness = linear function of sun elevation between 50% and 100%
* during the night ( sun elevation < -12° ): Brightness = 50%

![image](./doc/brightness.png)

### Color temperature

The  `Color Temperature` returns a color temperature in Kelvin between 2000K and 5500K depending on:

* the date and time
* the latitude
* the longitude

Current configuration is as follow:

* during twilight ( sun elevation > -0.833° ): ColorTemp = linear function of sun elevation between 3000K and 5500K
* between twilight and civil twilight ( -6° < sun elevation < -0.833° ): ColorTemp = linear function of sun elevation between 2000K and 3000K
* during the night ( sun elevation < -6° ): ColorTemp = 2000K

![image](./doc/color-temp.png)

## Installation

### Manual installation

Copy this folder to `<config_dir>/custom_components/circadian_lighting/` in your Home Assistant installation.

### HACS installation

You can also use [HACS](https://hacs.xyz/docs/faq/custom_repositories/) to install this component and keep it up to date.

## Configuration

Add the following to your `configuration.yaml` file:

```yaml
# Example configuration.yaml entry

circadian_lighting:
```

This will create two new sensors:
* sensor.circadian_light_brightness
* sensor.circadian_light_color_temperature

You can use these two sensors in your automations to set your lights brightness and color temperature.