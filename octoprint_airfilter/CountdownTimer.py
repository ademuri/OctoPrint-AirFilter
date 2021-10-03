# coding=utf-8
from __future__ import absolute_import
import time


class CountdownTimer:
  """Resettable countdown timer."""

  def __init__(self, interval):
    self.interval = interval
    self.start = time.monotonic()
    self.read = False

  def reset(self):
    self.start = time.monotonic()
    self.read = False

  def set_interval(self, interval):
      self.interval = interval

  def expired(self):
    if self.read:
      return False

    if time.monotonic() > (self.start + self.interval):
      self.read = True
      return True

    return False
