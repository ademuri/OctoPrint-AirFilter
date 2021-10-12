# coding=utf-8
from __future__ import absolute_import
import random


class FakeSgp40:
  raw = 30000

  def measure_index(self, temperature=None, relative_humidity=None):
    self.raw = random.randrange(25000, 30000)
    return random.randrange(0, 500)


class FakeHtu21d:
  temperature = 10
  relative_humidity = 50 