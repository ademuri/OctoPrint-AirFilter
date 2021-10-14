# coding=utf-8
from __future__ import absolute_import

# (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin, settings and asset plugin. Feel free to add or remove mixins
# as necessary.
#
# Take a look at the documentation on what other plugin mixins are available.

import flask
import importlib
import logging
import time
import datetime
import octoprint.plugin
from octoprint.util import RepeatedTimer

from octoprint_airfilter.CountdownTimer import CountdownTimer
from octoprint_airfilter.Stopwatch import Stopwatch
from octoprint_airfilter.fakes import FakeHtu21d, FakeSgp40
from octoprint_airfilter.settings import AirFilterSettings

# Hack to allow developing this plugin on non-RPi machines
try:
  GPIO = importlib.import_module("RPi.GPIO")
  GPIO.setmode(GPIO.BCM)
except ImportError as e:
  logging.getLogger(__name__).info(
      "Unable to import RPi.GPIO, using GPIO emulation", exc_info=True)
  FakeGpio = importlib.import_module("octoprint_airfilter.FakeGpio").FakeGpio
  GPIO = FakeGpio()

board = None
busio = None
adafruit_sgp40 = None
try:
  board = importlib.import_module("board")
  busio = importlib.import_module("busio")
  adafruit_sgp40 = importlib.import_module("adafruit_sgp40")
  adafruit_htu21d = importlib.import_module("adafruit_htu21d")
except ImportError as e:
  logging.getLogger(__name__).info(
      "Unable to import SGP40 support libraries", exc_info=True)


class AirfilterPlugin(
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.BlueprintPlugin,
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.ShutdownPlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.TemplatePlugin,
):
  filter_settings_ = None
  pin = None
  is_on = False
  # Whether the air filter was manually turned on/off in the UI
  manual_on = False
  manual_off = False
  printing = False
  print_end_timer = None
  poll_timer = None
  filter_stopwatch = Stopwatch()

  # Air quality sensor SGP40
  sgp = None
  temp_sensor = None
  sgp_index = -1
  sgp_raw = -1
  sgp_index_history = []
  sgp_raw_history = []
  sgp_index_buffer = []
  sgp_raw_buffer = []
  sgp_last_history = 0
  sgp_history_interval = 15 * 60
  sgp_history_size = 100

  def turn_on(self):
    if self.pin == None:
      GPIO.output(self.filter_settings_.pin_number, not self.filter_settings_.invert)
    else:
      self.pin.start(self.filter_settings_.pwm_duty_cycle)
    self.is_on = True
    self.filter_stopwatch.start()
    self.manual_off = False

  def turn_off(self):
    if self.is_on:
      self.save_timer()
      if self.pin is None:
        if self.filter_settings_.pin_number >= 0:
          GPIO.output(self.filter_settings_.pin_number, self.filter_settings_.invert)
      else:
        self.pin.stop()
        if self.filter_settings_.invert:
          GPIO.output(self.filter_settings_.pin_number, True)
    self.is_on = False
    self.filter_stopwatch.stop()
    self.manual_on = False

  def initialize_output(self):
    new_settings = AirFilterSettings(self._settings)
    # Settings validation
    if new_settings.pin_number == None:
      self.turn_off()
      return

    if new_settings.is_pwm:
      if new_settings.pwm_frequency == None:
        raise RuntimeError("is_pwm is set, but pwm_frequency was not")
      if new_settings.pwm_duty_cycle == None:
        raise RuntimeError("is_pwm is set, but pwm_duty_cycle was not")

    if self.filter_settings_ == None or self.filter_settings_.pin_number == None:
      # Previous settings or pin number was not set
      if new_settings.pin_number == None or new_settings.pin_number < 0:
        return

      GPIO.setup(new_settings.pin_number, GPIO.OUT)
      if new_settings.is_pwm:
        self.pin = GPIO.PWM(new_settings.pin_number, new_settings.pwm_frequency)
    elif new_settings.pin_number != self.filter_settings_.pin_number:
      # Pin number changed
      self.turn_off()

      if new_settings.pin_number == None or new_settings.pin_number < 0:
        return

      GPIO.setup(new_settings.pin_number, GPIO.OUT)

      if new_settings.is_pwm:
        self.pin = GPIO.PWM(new_settings.pin_number, new_settings.pwm_frequency)
    elif self.filter_settings_.is_pwm and not new_settings.is_pwm:
      # Stop using PWM
      self.pin.stop()
      self.pin = None
      if self.is_on:
        self.turn_on()
    elif not self.filter_settings_.is_pwm and new_settings.is_pwm:
      # Start using PWM
      self.pin = GPIO.PWM(self.filter_settings_.pin_number, new_settings.pwm_frequency)
      if self.is_on:
        self.turn_on()
    else:
      if new_settings.is_pwm and self.filter_settings_.is_pwm and new_settings.pwm_frequency != self.filter_settings_.pwm_frequency:
        self.pin.ChangeFrequency(new_settings.pwm_frequency)

    pwm_duty_changed = (self.filter_settings_ != None and new_settings.pwm_duty_cycle != self.filter_settings_.pwm_duty_cycle and self.is_on)
    self.filter_settings_ = new_settings
    self.update_output()
    
    if pwm_duty_changed:
      self.turn_on()

  def update_output(self):
    if self.is_on and self.manual_on:
      return

    print_start_trigger = self._settings.get_boolean(['print_start_trigger'])
    current_temperatures = None
    current_temperature = 0
    if self._printer.is_operational():
      current_temperatures = self._printer.get_current_temperatures()
      if 'tool0' in current_temperatures and 'actual' in current_temperatures['tool0']:
        current_temperature = current_temperatures['tool0']['actual']
      else:
        self._logger.warn(
            'Warning: tool0->actual_temp not found in printer temps: %s', current_temperatures)

    if self.is_on:
      if self.filter_settings_.enable_temperature_threshold and current_temperature != None and current_temperature >= self.filter_settings_.temperature_threshold:
        return

      if print_start_trigger and not self.printing and self.print_end_timer.expired():
        self.turn_off()
      elif current_temperature != None and self.filter_settings_.temperature_threshold != None and current_temperature < self.filter_settings_.temperature_threshold:
        if not (print_start_trigger and self.printing):
          self.turn_off()

    else:
      # not self.is_on
      if print_start_trigger and self.printing:
        self.turn_on()
      elif self.filter_settings_.enable_temperature_threshold and current_temperature != None and current_temperature >= self.filter_settings_.temperature_threshold:
        self.turn_on()
      else:
        self.manual_off = False

  def save_timer(self):
    running = self.filter_stopwatch.is_running()
    current_timer_life = self._settings.get_float(
        ['filter_life'], min=0.0, merged=True)
    self.filter_stopwatch.stop()
    if self.filter_stopwatch.get() > 0:
      self._settings.set_float(
          ['filter_life'], current_timer_life + self.filter_stopwatch.get())
      self._settings.save()
    self.filter_stopwatch.reset()
    if running:
      self.filter_stopwatch.start()

  # ~~ EventHandler mixin
  def on_event(self, event, payload):
    if event == 'PrintStarted':
      self.printing = True
      self.update_output()
    elif event == 'PrintFailed' or event == 'PrintDone' or event == 'PrintCancelled':
      self.printing = False
      self.print_end_timer.reset()
      self.update_output()

  # ~~ SettingsPlugin mixin

  def get_settings_defaults(self):
    return {
        AirFilterSettings.PIN_NUMBER: None,
        AirFilterSettings.IS_PWM: False,
        AirFilterSettings.INVERT: False,
        AirFilterSettings.PWM_FREQUENCY: 1000,
        AirFilterSettings.PWM_DUTY_CYCLE: 90,
        AirFilterSettings.ENABLE_TEMPERATURE_THRESHOLD: False,
        AirFilterSettings.TEMPERATURE_THRESHOLD: 60,
        'print_start_trigger': True,
        'print_end_delay': 600,
        'filter_life': 0.0,
        'fake_sgp40': False,
    }

  def on_settings_save(self, data):
    octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
    self.initialize_output()

  def get_template_configs(self):
    return [
        dict(type="settings", custom_bindings=False),
    ]

  @octoprint.plugin.BlueprintPlugin.route("/set", methods=["POST"])
  def set_filter(self):
    if not 'state' in flask.request.values or not (flask.request.get('state') in [True, False]):
      raise RuntimeError('Invalid set request: %s', flask.request.values)
    if flask.request.get('state')['state'] is True:
      self.turn_on()
      self.manual_on = True
    else:
      # TODO: if there is currently a trigger making the filter be on, ignore it until it goes away
      self.turn_off()
    return flask.jsonify({'success': True})

  @octoprint.plugin.BlueprintPlugin.route("/toggle", methods=["POST"])
  def toggle_filter(self):
    try:
      if self.is_on:
        self.turn_off()
        self.manual_off = True
      else:
        self.turn_on()
        self.manual_on = True
      return flask.jsonify({'success': True})
    except Exception:
      self._logger.error('Exception while toggling state', exc_info=True)
      return flask.jsonify({'success': False})

  @octoprint.plugin.BlueprintPlugin.route("/state", methods=["GET"])
  def get_state(self):
    state = dict()
    state['state'] = self.is_on
    try:
      if self.sgp != None:
        state['sgp_index'] = self.sgp_index
        state['sgp_raw'] = self.sgp_raw
      if self.temp_sensor != None:
        state['temperature'] = self.temp_sensor.temperature
        state['relative_humidity'] = self.temp_sensor.relative_humidity
    except Exception:
      self._logger.error('Exception while getting state', exc_info=True)
    return flask.jsonify(state)

  @octoprint.plugin.BlueprintPlugin.route("/history", methods=["GET"])
  def get_history(self):
    history = []
    for i in range(0, len(self.sgp_raw_history)):
      history_time = datetime.datetime.now() - datetime.timedelta(seconds = i * self.sgp_history_interval + time.monotonic() - self.sgp_last_history)
      history.append({'index': self.sgp_index_history[i], 'raw': self.sgp_raw_history[i], 'time': history_time.strftime('%H:%M')})

    return flask.jsonify({'history': history})

  def update_sgp40(self):
    try:
      self.update_sgp40_impl()
    except Exception:
      self._logger.error('Exception while updating SGP40', exc_info=True)

  def update_sgp40_impl(self):
    self.sgp_raw = self.sgp.raw
    self.sgp_raw_buffer.append(self.sgp_raw)

    if self.temp_sensor == None:
      self.sgp_index = self.sgp.measure_index()
    else:
      self.sgp_index = self.sgp.measure_index(temperature = self.temp_sensor.temperature, relative_humidity = self.temp_sensor.relative_humidity)

    self.sgp_index_buffer.append(self.sgp_index)

    now = time.monotonic()
    buffer_full = False
    if self.sgp_last_history <= 0:
      # Align to even intervals (e.g. every 15 minutes means 0, 15, 30, and 45 minutes past the hour)
      start_at_minutes = round(self.sgp_history_interval / 60)
      if start_at_minutes <= 0:
        start_at_minutes = 1
      if time.localtime().tm_min % start_at_minutes <= 0:
        buffer_full = True
    else:
      if now - self.sgp_last_history >= self.sgp_history_interval:
        buffer_full = True

    if buffer_full:
      self.sgp_last_history = now
      self.sgp_raw_history.insert(
          0, sum(self.sgp_raw_buffer) / len(self.sgp_raw_buffer))
      self.sgp_raw_buffer.clear()
      self.sgp_index_history.insert(
          0, sum(self.sgp_index_buffer) / len(self.sgp_index_buffer))
      self.sgp_index_buffer.clear()

      if len(self.sgp_raw_history) > self.sgp_history_size:
        self.sgp_raw_history = self.sgp_raw_history[0:self.sgp_history_size]

      if len(self.sgp_index_history) > self.sgp_history_size:
        self.sgp_index_history = self.sgp_index_history[0:self.sgp_history_size]

  # ~~ StartupPlugin mixin
  def on_after_startup(self):
    self.print_end_timer = CountdownTimer(
        self._settings.get_int(['print_end_delay']))
    self.initialize_output()
    self.poll_timer = RepeatedTimer(20, self.update_output)
    self.poll_timer.start()

    self.filter_life_timer = RepeatedTimer(30 * 60, self.save_timer)
    self.filter_life_timer.start()

    # Note: only run update_sgp40 in the timer, because it is blocking which can cause issues.
    if adafruit_sgp40 == None:
      if self._settings.get_boolean(['fake_sgp40']):
        self._logger.info("Using fake SGP40 air quality sensor")
        self.sgp = FakeSgp40()
        self.temp_sensor = FakeHtu21d()
    else:
      self._logger.info('Initializing SGP40 air quality sensor')
      i2c = busio.I2C(board.SCL, board.SDA)
      self.sgp = adafruit_sgp40.SGP40(i2c)
      if adafruit_htu21d != None:
        self._logger.info('Initializing HTU21D temperature sensor')
        self.temp_sensor = adafruit_htu21d.HTU21D(i2c)

    if self.sgp != None:
      self.sgp40_timer = RepeatedTimer(1, self.update_sgp40)
      self.sgp40_timer.start()

  def on_shutdown(self):
    self.save_timer()
    self.turn_off()
    if self.filter_settings_.pin_number != None and self.filter_settings_.pin_number >= 0:
      GPIO.cleanup(self.filter_settings_.pin_number)

  # ~~ AssetPlugin mixin

  def get_assets(self):
    # Define your plugin's asset files to automatically include in the
    # core UI here.
    return {
        "js": ["js/airfilter.js"],
        "css": ["css/airfilter.css"],
        "less": ["less/airfilter.less"]
    }

  # ~~ Softwareupdate hook

  def get_update_information(self):
    # Define the configuration for your plugin to use with the Software Update
    # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
    # for details.
    return {
        "airfilter": {
            "displayName": "Air Filter",
            "displayVersion": self._plugin_version,

            # version check: github repository
            "type": "github_release",
            "user": "ademuri",
            "repo": "OctoPrint-AirFilter",
            "current": self._plugin_version,

            # update method: pip
            "pip": "https://github.com/ademuri/OctoPrint-AirFilter/archive/{target_version}.zip",
        }
    }


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Air Filter"

# Starting with OctoPrint 1.4.0 OctoPrint will also support to run under Python 3 in addition to the deprecated
# Python 2. New plugins should make sure to run under both versions for now. Uncomment one of the following
# compatibility flags according to what Python versions your plugin supports!
# __plugin_pythoncompat__ = ">=2.7,<3" # only python 2
# __plugin_pythoncompat__ = ">=3,<4" # only python 3
__plugin_pythoncompat__ = ">=2.7,<4"  # python 2 and 3


def __plugin_load__():
  global __plugin_implementation__
  __plugin_implementation__ = AirfilterPlugin()

  global __plugin_hooks__
  __plugin_hooks__ = {
      "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
  }
