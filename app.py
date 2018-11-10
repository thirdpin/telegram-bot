#!/usr/bin/env python

from stuff.common import Device


SPIDER_ID = 1

device = Device(SPIDER_ID)

device.open()
device.initialize()
while True:
	device.blink()