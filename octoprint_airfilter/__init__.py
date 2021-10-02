# coding=utf-8
from __future__ import absolute_import
#import RPi.GPIO as GPIO

### (Don't forget to remove me)
# This is a basic skeleton for your plugin's __init__.py. You probably want to adjust the class name of your plugin
# as well as the plugin mixins it's subclassing from. This is really just a basic skeleton to get you started,
# defining your plugin as a template plugin, settings and asset plugin. Feel free to add or remove mixins
# as necessary.
#
# Take a look at the documentation on what other plugin mixins are available.

import octoprint.plugin

# Hack to allow developing this plugin on non-RPi machines
try:
    __import__("RPi.GPIO as GPIO")
except ImportError as e:
    print("Unable to import RPi.GPIO, using GPIO emulation")
    from octoprint_airfilter.FakeGpio import FakeGpio as FakeGpio
    GPIO = FakeGpio()



class AirfilterPlugin(
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.TemplatePlugin,
):
    pin = None
    pin_string = '-1'
    pin_number = -1
    use_pwm = False
    invert = False
    is_on = False
    printing = False

    def initialize_output(self):
        print('Initializing outputs')
        print(self._settings.get([], merged=True, asdict=True))
        self.use_pwm = self._settings.get_boolean(['is_pwm'], merged=True)
        pwm_frequency = 0
        if self._settings.get(['pwm_frequency']) is not None:
            pwm_frequency = int(self._settings.get(['pwm_frequency'], merged=True))

        if self.pin_string != self._settings.get(['pin_number'], merged=True):
            if self.pin is None:
                if self.pin_number >= 0:
                    GPIO.output(self.pin_number, not self.invert)
            else:
                self.pin.stop()
                if self.invert:
                    GPIO.output(self.pin_number, True)

            self.pin_string = self._settings.get(['pin_number'], merged=True)
            if self.pin_string == None or len(self.pin_string) == 0:
                return

            self.pin_number = int(self.pin_string)
            if self.pin_number < 0:
                return

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
        if self.is_on:
            pass

    ##~~ EventHandler mixin
    def on_event(self, event, payload):
        if event == 'PrintStarted':
            self.printing = True
        elif event == 'PrintFailed' or event == 'PrintDone' or event == 'PrintCancelled':
            self.print = False

    ##~~ SettingsPlugin mixin

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
        }

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.initialize_output()


    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False),
        ]

    ##~~ StartupPlugin mixin
    def on_after_startup(self):
        self.initialize_output()

    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return {
            "js": ["js/airfilter.js"],
            "css": ["css/airfilter.css"],
            "less": ["less/airfilter.less"]
        }

    ##~~ Softwareupdate hook

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
#__plugin_pythoncompat__ = ">=2.7,<3" # only python 2
#__plugin_pythoncompat__ = ">=3,<4" # only python 3
__plugin_pythoncompat__ = ">=2.7,<4" # python 2 and 3

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = AirfilterPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
