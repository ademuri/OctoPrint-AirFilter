# coding=utf-8
from __future__ import absolute_import


class AirFilterSettings:
  """Holds settings for this plugin."""
  PIN_NUMBER = 'pin_number'
  IS_PWM = 'is_pwm'
  INVERT = 'invert'
  PWM_FREQUENCY = 'pwm_frequency'
  PWM_DUTY_CYCLE = 'pwm_duty_cycle'

  def __init__(self, settings):
    self.pin_number = settings.get_int([self.PIN_NUMBER], merged=True)
    self.is_pwm = settings.get_boolean([self.IS_PWM], merged=True)
    self.invert = settings.get_boolean([self.INVERT], merged=True)
    self.pwm_frequency = settings.get_int([self.PWM_FREQUENCY], merged=True)
    self.pwm_duty_cycle = settings.get_int([self.PWM_DUTY_CYCLE], merged=True)

  def __str__(self):
    return f'AirFilterSettings(pin_number: {self.pin_number}, is_pwm: {self.is_pwm}, invert: {self.invert}, pwm_frequency: {self.pwm_frequency}, pwm_duty_cycle: {self.pwm_duty_cycle})'
