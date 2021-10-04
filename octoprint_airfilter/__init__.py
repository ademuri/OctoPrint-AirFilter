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
import octoprint.plugin
from octoprint.util import RepeatedTimer

from octoprint_airfilter.CountdownTimer import CountdownTimer
from octoprint_airfilter.Stopwatch import Stopwatch
from octoprint_airfilter.FakeSgp40 import FakeSgp40

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
  pin = None
  pin_string = '-1'
  pin_number = -1
  use_pwm = False
  invert = False
  is_on = False
  # Whether the air filter was manually turned on in the UI
  manual_on = False
  printing = False
  print_end_timer = None
  poll_timer = None
  filter_stopwatch = Stopwatch()

  # Air quality sensor SGP40
  sgp = None
  sgp_index = -1
  sgp_raw = -1
  sgp_index_history = []
  sgp_raw_history = []
  sgp_index_buffer = []
  sgp_raw_buffer = []
  sgp_last_history = 0
  sgp_history_interval = 5
  sgp_history_size = 2

  def turn_on(self):
    if self.pin == None:
      GPIO.output(self.pin_number, not self.invert)
    else:
      self.pin.start(self._settings.get_int(['pwm_duty_cycle']))
    self.is_on = True
    self.filter_stopwatch.start()

  def turn_off(self):
    if self.is_on:
      self.save_timer()
      if self.pin is None:
        if self.pin_number >= 0:
          GPIO.output(self.pin_number, not self.invert)
      else:
        self.pin.stop()
        if self.invert:
          GPIO.output(self.pin_number, True)
    self.is_on = False
    self.filter_stopwatch.stop()
    self.manual_on = False

  def initialize_output(self):
    self.use_pwm = self._settings.get_boolean(['is_pwm'], merged=True)
    pwm_frequency = 0
    if self._settings.get(['pwm_frequency']) is not None:
      pwm_frequency = int(self._settings.get(['pwm_frequency'], merged=True))

    if self.pin_string != self._settings.get(['pin_number'], merged=True):
      self.turn_off()

      self.pin_string = self._settings.get(['pin_number'], merged=True)
      if self.pin_string == None or len(self.pin_string) == 0:
        return

      self.pin_number = int(self.pin_string)
      if self.pin_number < 0:
        return
      GPIO.setup(self.pin_number, GPIO.OUT)

      if self.use_pwm:
        self.pin = GPIO.PWM(self.pin_number, pwm_frequency)
    elif self.use_pwm and not self._settings.get_boolean(['is_pwm']):
      # Stop using PWM
      self.pin.stop()
      self.pin = None
    elif not self.use_pwm and self._settings.get_boolean(['is_pwm']):
      # Start using PWM
      self.pin = GPIO.PWM(self.pin_number, pwm_frequency)

    if self.pin is not None:
      self.pin.ChangeFrequency(pwm_frequency)

    self.invert = self._settings.get(['invert'], merged=True)
    self.update_output()

  def update_output(self):
    if self.is_on and self.manual_on:
      return

    print_start_trigger = self._settings.get_boolean(['print_start_trigger'])
    enable_temperature_threshold = self._settings.get_boolean(
        ['enable_temperature_threshold'])
    temperature_threshold = self._settings.get_int(['temperature_threshold'])
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
      if enable_temperature_threshold and current_temperature != None and current_temperature >= temperature_threshold:
        return

      if print_start_trigger and not self.printing and self.print_end_timer.expired():
        self.turn_off()
      elif current_temperature != None and current_temperature < temperature_threshold:
        if not (print_start_trigger and self.printing):
          self.turn_off()

    else:
      # not self.is_on
      if print_start_trigger and self.printing:
        self.turn_on()
      elif enable_temperature_threshold and current_temperature != None and current_temperature >= temperature_threshold:
        self.turn_on()

  def save_timer(self):
    current_timer_life = self._settings.get_float(
        ['filter_life'], min=0.0, merged=True)
    self.filter_stopwatch.stop()
    if self.filter_stopwatch.get() > 0:
      self._settings.set_float(
          ['filter_life'], current_timer_life + self.filter_stopwatch.get())
      self._settings.save()
    self.filter_stopwatch.reset()
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
        'pin_number': None,
        'invert': False,
        'is_pwm': True,
        'pwm_frequency': 1000,
        'pwm_duty_cycle': 90,
        'enable_temperature_threshold': False,
        'temperature_threshold': 60,
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

  # ~~ SimpleApiPlugin mixin
  def get_api_commands(self):
    return dict(
        set=["state"],
        toggle=[],
    )

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
    if self.is_on:
      self.turn_off()
    else:
      self.turn_on()
      self.manual_on = True
    return flask.jsonify({'success': True})

  @octoprint.plugin.BlueprintPlugin.route("/state", methods=["GET"])
  def get_state(self):
    state = dict()
    state['state'] = self.is_on
    if self.sgp != None:
      state['sgp_index'] = self.sgp_index
      state['sgp_raw'] = self.sgp_raw
    return flask.jsonify(state)

  def update_sgp40(self):
    self.sgp_raw = self.sgp.raw
    self.sgp_index = self.sgp.measure_index()
    self.sgp_raw_buffer.append(self.sgp_raw)
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
    else:
      self._logger.info('Initializing SGP40 air quality sensor')
      i2c = busio.I2C(board.SCL, board.SDA)
      self.sgp = adafruit_sgp40.SGP40(i2c)

    if self.sgp != None:
      self.sgp40_timer = RepeatedTimer(1, self.update_sgp40)
      self.sgp40_timer.start()

  def on_shutdown(self):
    self.save_timer()
    self.turn_off()
    if self.pin_number != None and self.pin_number >= 0:
      GPIO.cleanup(self.pin_number)

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
