# OctoPrint-AirFilter

This plugin controls an air filter. It supports turning the air filter on when a print starts, or when the hotend is above a certain temperature. It can output either an on/off or a PWM signal.

## Setup

Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
or manually using this URL:

    https://github.com/ademuri/OctoPrint-AirFilter/archive/main.zip

This plugin includes VOC level monitoring using an SGP40 sensor (via I2C). To use this sensor, you should connect the sensor's SDA and SCL to the Pi's corresponding pins - GPIO2/pin 3 and GPIO3/pin 5, respectively. You'll also need to install the Adafruit Python library for it:

```bash
sudo pip3 install adafruit-circuitpython-sgp40
sudo pip3 install adafruit-circuitpython-htu21d
```

## Configuration

**TODO:** Describe your plugin's configuration options (if any).
