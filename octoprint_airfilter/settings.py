# coding=utf-8
from __future__ import absolute_import


class AirFilterSettings:
  """Holds settings for this plugin."""
  PIN_NUMBER = 'pin_number'
  IS_PWM = 'is_pwm'
  INVERT = 'invert'
  PWM_FREQUENCY = 'pwm_frequency'
  PWM_DUTY_CYCLE = 'pwm_duty_cycle'
  ENABLE_TEMPERATURE_THRESHOLD = 'enable_temperature_threshold'
  TEMPERATURE_THRESHOLD = 'temperature_threshold'

  def __init__(self, settings):
    self.pin_number = settings.get_int([self.PIN_NUMBER], merged=True)
    self.is_pwm = settings.get_boolean([self.IS_PWM], merged=True)
    self.invert = settings.get_boolean([self.INVERT], merged=True)
    self.pwm_frequency = settings.get_int([self.PWM_FREQUENCY], merged=True)
    self.pwm_duty_cycle = settings.get_int([self.PWM_DUTY_CYCLE], merged=True)
    self.enable_temperature_threshold = settings.get_boolean([self.ENABLE_TEMPERATURE_THRESHOLD], merged=True)
    self.temperature_threshold = settings.get_int([self.TEMPERATURE_THRESHOLD], merged=True)

  def __str__(self):
    return (f'AirFilterSettings(pin_number: {self.pin_number}, is_pwm: {self.is_pwm}, invert: {self.invert}, '
        f'pwm_frequency: {self.pwm_frequency}, pwm_duty_cycle: {self.pwm_duty_cycle}), '
        f'enable_temperature_threshold: {self.enable_temperature_threshold}, temperature_threshold: {self.temperature_threshold}')
