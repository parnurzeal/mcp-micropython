# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

# Basic example of clearing and drawing a pixel on a LED matrix display.
# This example and library is meant to work with Adafruit CircuitPython API.
# Author: Tony DiCola
# License: Public Domain

# Import all board pins.
import time
from machine import I2C, Pin

# Import the HT16K33 LED matrix module.
from ht16k33 import matrix


# Create the I2C interface.
i2c = I2C(0, scl=Pin(21), sda=Pin(20))
address = i2c.scan()[0]

# Create the matrix class.
# This creates a 16x8 matrix:
matrix = matrix.Matrix8x8(i2c, address=address)

def turn_on():
  # Clear the matrix.
  matrix.fill(0)
  matrix.fill(1)

def turn_off():
  matrix.fill(0)

if __name__ == '__main__':
  print('Turning on...')
  turn_on()
  time.sleep(5)
  print('Turning off...')
  turn_off()
