#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
@author: guido lutterbach
@contact: guido@smartypies.com
@version: 1.1
@licence: Public Domain

This program implements 4 cases for ADS1115 on raspberry pi with default libraries.
1) single-shot - open drain - timed
2) single-shot - open drain - GPIO alert
3) continuous mode - differential - GPIO alert
4) continuous mode - differential - GPIO alert when value leaves high/low threshold range
Please check the electric circuit that goes with it at www.smartypies.com (ADS1115 project)
For testing 1) + 2) use potentiometer 1
For testing 3) + 4) use potentiometer 2
Enjoy!
'''

import RPi.GPIO as GPIO
import cmd
import logging
import smbus
import time

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

ALERTPIN = 27


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
    if (c >= 2 ** 15):
        c = c - 2 ** 16
    return c


def BEtoLE(c):
    '''BigEndian to LittleEndian conversion for signed 2 Byte integers (2 complement).'''
    if (c < 0):
        c = 2 ** 16 + c
    return swap2Bytes(c)


def resetChip():
    BUS.write_byte(RESET_ADDRESS, RESET_COMMAND)
    return


# Use BCM GPIO references
GPIO.setmode(GPIO.BCM)
GPIO.setup(ALERTPIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  ## read mode, pull up resistor


class ADS1115Runner(cmd.Cmd):
    intro = '''usage: type following commands
          1    - one-shot measurement mode, timed
          2    - one-shot measurement mode, alerted through GPIO
          3    - continuous measurment mode, alerted through GPIO
          4  low high  - continuous mode, alerted when value out of range [low, high]
          q (quit)
          just hitting enter quits any mode 1-4. Enter 'y' to continue in modes 1 and 2.'''
    prompt = 'Enter 1,2,3,4 or q >>'
    file = None

    #    __logfile = None

    def alerted(self, arg):
        data_raw = BUS.read_word_data(DEVICE_ADDRESS, POINTER_CONVERSION)
        print('alerted:' + str(LEtoBE(data_raw)))
        return

    def do_1(self, arg):
        '''One-shot, Read value from channel 0 with wait time'''
        resetChip()

        # compare with configuration settings from ADS115 datasheet
        # start single conversion - AIN2/GND - 4.096V - single shot - 8SPS - X
        # - X - X - disable comparator
        conf = prepareLEconf('1-110-001-1-000-0-0-0-11')

        go = 'y'
        while True and go in ['y', 'Y']:
            BUS.write_word_data(DEVICE_ADDRESS, POINTER_CONFIGURATION, conf)
            # long enough to be safe that data acquisition (conversion) has completed
            # may be calculated from data rate + some extra time for safety.
            # check accuracy in any case.
            time.sleep(0.2)
            value_raw = BUS.read_word_data(DEVICE_ADDRESS, POINTER_CONVERSION)
            value = LEtoBE(value_raw)
            print(value)
            # enter to break, repeat with 'y'
            go = input('continue: n/y')
            if (len(go) == 0):
                go = 'n'
        return

    def do_2(self, arg):
        '''One-shot with GPIO alert'''
        # register callback for alerts
        GPIO.add_event_detect(ALERTPIN, GPIO.RISING, callback=self.alerted)
        # reset call
        resetChip()
        # compare with configuration settings from ADS115 datasheet:
        # start single conversion - AIN2/GND - 4.096V - single shot - 8SPS -
        # trad. comparator - active high - latching - assert after one conversion
        conf = prepareLEconf('1-110-001-1-000-0-1-1-00')
        BUS.write_byte(0b0000000, 0b00000110)  # reset call
        # set High and Low threshold for ALERT pin mode
        BUS.write_word_data(DEVICE_ADDRESS, POINTER_LOW_THRESHOLD, 0xFF7F)  # 0x7FFF in BigEndian
        BUS.write_word_data(DEVICE_ADDRESS, POINTER_HIGH_THRESHOLD, 0x0080)  # 0x8000 in BigEndian
        go = 'y'
        while True and go in ['y', 'Y']:
            BUS.write_word_data(DEVICE_ADDRESS, POINTER_CONFIGURATION, conf)
            # enter to break, repeat with 'y'
            go = input('continue: n/y\n')

        # remove event listener
        GPIO.remove_event_detect(ALERTPIN)
        return

    def do_3(self, arg):
        '''Continuous mode with GPIO alert'''
        # register callback for alerts
        GPIO.add_event_detect(ALERTPIN, GPIO.RISING, callback=self.alerted)
        # reset call
        resetChip()
        # compare with configuration settings from ADS115 datasheet
        # X - AIN0/AIN1 - 2.048V - continuous mode - 64SPS -
        # window comparator - active high - nonlatching - assert after one conversion
        conf = prepareLEconf('0-000-010-0-011-1-1-0-00')
        # set High and Low threshold for ALERT pin mode
        BUS.write_word_data(DEVICE_ADDRESS, POINTER_LOW_THRESHOLD, 0xFF7F)  # 0x7FFF in BigEndian
        BUS.write_word_data(DEVICE_ADDRESS, POINTER_HIGH_THRESHOLD, 0x0080)  # 0x8000 in BigEndian
        # write configuration ONCE
        BUS.write_word_data(DEVICE_ADDRESS, POINTER_CONFIGURATION, conf)

        # wait for input(), enter to break
        input('enter to stop\n')
        # remove event listener to stop execution
        GPIO.remove_event_detect(ALERTPIN)
        return

    def do_4(self, arg):
        ''' Continuous measurements with latch and allowable data range'''
        largs = tuple(map(int, arg.split()))
        if len(largs) != 2:
            print('please call with exactly 2 integer arguments')
            return
        # reset call
        resetChip()
        # compare with configuration settings from ADS115 datasheet
        # X - AIN0/AIN1 - 2.048V - continuous mode - 8SPS -
        # window comparator - active high - latching - assert after one conversion
        conf = prepareLEconf('0-000-010-0-000-1-1-1-00')
        # register callback for alerts
        GPIO.add_event_detect(ALERTPIN, GPIO.RISING, callback=self.alerted)
        # prepare for ALERT pin mode - define window

        low = min(largs)  # Python BigEndian - RaspberryPi LittleEndian
        high = max(largs)
        low_val = BEtoLE(low)
        high_val = BEtoLE(high)
        logger.debug("{:04X} {:04x} {:04x} {:04x} ".format(low, low_val, high, high_val))
        BUS.write_word_data(DEVICE_ADDRESS, POINTER_LOW_THRESHOLD, low_val)
        BUS.write_word_data(DEVICE_ADDRESS, POINTER_HIGH_THRESHOLD, high_val)

        # write configuration ONCE
        BUS.write_word_data(DEVICE_ADDRESS, POINTER_CONFIGURATION, conf)

        # wait for input(), enter to break
        input('enter to stop\n')
        # remove event listener to stop execution
        GPIO.remove_event_detect(ALERTPIN)
        return

    def do_q(self, arg):
        '''Quit.'''
        return True

    def default(self, line):
        print('undefined key')

    def shutdown(self):
        GPIO.cleanup()
        BUS.close()
        pass


if __name__ == "__main__":
    try:
        logging.basicConfig(
            level=logging.DEBUG,
            # format='%(name)-12s: %(levelname)-8s %(message)s')
            format='%(message)s')
        logger = logging.getLogger('ADS1115Runner')
        Runner = ADS1115Runner()
        Runner.cmdloop()
    finally:
        Runner.shutdown()
