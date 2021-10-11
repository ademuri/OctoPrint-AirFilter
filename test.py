# coding=utf-8
from __future__ import absolute_import

import octoprint_airfilter
from octoprint_airfilter import AirfilterPlugin
from octoprint_airfilter import AirFilterSettings
from octoprint.settings import settings
import octoprint.plugin
import octoprint.printer
import logging


class FakePrinter(octoprint.printer.PrinterInterface):
  """Fake implementation of a printer for testing."""

  def is_operational(self, *args, **kwargs):
    return True

  def get_current_temperatures(self, *args, **kwargs):
    return dict()


plugin = AirfilterPlugin()
plugin._logger = logging.getLogger(AirfilterPlugin.__name__)
plugin._printer = FakePrinter()

settings = settings(init=True)
plugin._settings = octoprint.plugin.plugin_settings_for_settings_plugin('airfilter', plugin, settings=settings)
plugin._settings.set_boolean(['fake_sgp40'], True)
plugin._settings.set_int([AirFilterSettings.PIN_NUMBER], 1)

plugin.on_after_startup()

plugin.turn_on()
plugin.turn_off()

plugin.on_event('PrintStarted', dict())
plugin.on_event('PrintFailed', dict())
plugin.on_event('PrintDone', dict())
plugin.on_event('PrintCancelled', dict())

plugin.save_timer()

plugin.update_output()

plugin.on_shutdown()
