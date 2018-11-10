#!/usr/bin/env python

from stuff.common import DoorOpener


SPIDER_ID = 1

device = DoorOpener(SPIDER_ID)
device.open()
device.initialize()

while True:
	device.door_stuff()