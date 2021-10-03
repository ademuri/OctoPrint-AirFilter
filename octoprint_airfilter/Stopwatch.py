# coding=utf-8
from __future__ import absolute_import
import time


class Stopwatch:
  """A stopwatch - counts elapsed wall time."""

  elapsed_seconds_ = 0
  last_started_ = -1

  def __init__(self):
    pass

  def start(self):
    if self.last_started_ >= 0:
      return

    self.last_started_ = time.monotonic()

  def stop(self):
    if self.last_started_ < 0:
      return

    now = time.monotonic()
    self.elapsed_seconds_ += now - self.last_started_
    self.last_started_ = -1

  def get(self):
    return self.elapsed_seconds_ / (60 * 60)

  def reset(self):
    self.last_started_ = -1
    self.elapsed_seconds_ = 0