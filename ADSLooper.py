#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
@author: guido lutterbach
@contact: guido@smartypies.com
@version: 1.0
@licence: Public Domain

Sample code derived from ADSRunner to demonstrate the usage for a specific purpose.
This code handles the alternate readings of AIN0 and AIN1 against ground.
The wait time for each reading can be much less than 0.5 sec.
I wrote this, when Pasquale asked for some help for connecting Soil Watch 10 analog sensors from Pino-Tech.

Start for continuous readings with: python ADSLooper.py
To stop use: Ctrl-C.
'''

import cmd
import time
import logging
import smbus
import RPi.GPIO as GPIO

# ADS1115 + hardware constants
I2C_BUS = 1
DEVICE_ADDRESS = 0x4B
POINTER_CONVERSION = 0x0
POINTER_CONFIGURATION = 0x1
POINTER_LOW_THRESHOLD = 0x2
POINTER_HIGH_THRESHOLD = 0x3

RESET_ADDRESS = 0b0000000
RESET_COMMAND = 0b00000110

# Open I2C device
BUS = smbus.SMBus(I2C_BUS)
BUS.open(I2C_BUS)


def swap2Bytes(c):
    '''Revert Byte order for Words (2 Bytes, 16 Bit).'''
    return (c >> 8 | c << 8) & 0xFFFF


def prepareLEconf(BEconf):
    '''Prepare LittleEndian Byte pattern from BigEndian configuration string, with separators.'''
    c = int(BEconf.replace('-', ''), base=2)
    return swap2Bytes(c)


def LEtoBE(c):
    '''Little Endian to BigEndian conversion for signed 2Byte integers (2 complement).'''
    c = swap2Bytes(c)
    if (c >= 2**15):
        c = c-2**16
    return c


def BEtoLE(c):
    '''BigEndian to LittleEndian conversion for signed 2 Byte integers (2 complement).'''
    if (c < 0):
        c = 2**16 + c
    return swap2Bytes(c)


def resetChip():
    BUS.write_byte(RESET_ADDRESS, RESET_COMMAND)
    return


# Use BCM GPIO references
GPIO.setmode(GPIO.BCM)

def readLoopA0A1():
    ''' read A0 and A1 continously '''
    resetChip()
    # compare with configuration settings from ADS115 datasheet, chapter 'Register Map'
    # start single conversion - AIN0/GND or AIN1/GND  - 4.096V - single shot - 128SPS - X
    # - X - X - disable comparator
    confA0 = prepareLEconf('1-100-001-1-100-0-0-0-11')
    confA1 = prepareLEconf('1-101-001-1-100-0-0-0-11')

    while True:
        # configure for reading A0
        BUS.write_word_data(DEVICE_ADDRESS, POINTER_CONFIGURATION, confA0)
        # long enough to be safe that data acquisition (conversion) has completed
        # may be calculated from data rate + some extra time for safety.
        # check accuracy in any case.
        time.sleep(0.5)
        value_raw = BUS.read_word_data(DEVICE_ADDRESS, POINTER_CONVERSION)
        value = LEtoBE(value_raw)
        print("A0:", value)
        # configure for reading A1
        BUS.write_word_data(DEVICE_ADDRESS, POINTER_CONFIGURATION, confA1)
        # long enough to be safe that data acquisition (conversion) has completed
        # may be calculated from data rate + some extra time for safety.
        # check accuracy in any case.
        time.sleep(0.5)
        value_raw = BUS.read_word_data(DEVICE_ADDRESS, POINTER_CONVERSION)
        value = LEtoBE(value_raw)
        print("A1:", value)


if __name__ == "__main__":
    try:
        readLoopA0A1()
    finally:
        GPIO.cleanup()
        BUS.close()
