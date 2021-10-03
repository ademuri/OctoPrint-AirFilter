# coding=utf-8
from __future__ import absolute_import
import logging


class FakeGpio:
  """Emulation for Raspberry PI GPIO"""

  def __init__(self):
    self.logger_ = logging.getLogger('octoprint.plugins.airfilter')

  def output(self, pin_number, value):
    self.logger_.info(f'Set pin {pin_number} to {1 if value else 0}')

  def PWM(self, pin_number, pwm_frequency):
    return FakePwm(pin_number, pwm_frequency)


class FakePwm:
  def __init__(self, pin, frequency):
    self.logger_ = logging.getLogger('octoprint.plugins.airfilter')
    self.logger_.info(f'Initialize PWM {pin} with frequency {frequency}')
    self.pin = pin
    self.frequency = frequency

  def ChangeFrequency(self, frequency):
    self.logger_.info(f'Change PWM {self.pin} to frequency {self.frequency}')

  def start(self, duty_cycle):
    self.logger_.info(f'Start PWM {self.pin} at {duty_cycle}%')

  def stop(self):
    self.logger_.info(f'Stop PWM {self.pin}')
