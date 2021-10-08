# coding=utf-8
from __future__ import absolute_import
import random

class FakeSgp40:
  raw = 30000

  def measure_index(self):
    self.raw = random.randrange(25000, 30000)
    return random.randrange(0, 500)
