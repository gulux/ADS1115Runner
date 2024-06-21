#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
@author: pasquale delli paoli, guido lutterbach
@contact: pasqualedellipaoli@libero.it
@version: 1.0
@licence: Public Domain

'''
  
import time, smbus
    
# ADS1115 + hardware constants
I2C_BUS = 1
DEVICE_ADDRESS = 0x48
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
    return (c>>8 |c<<8)&0xFFFF
    
def prepareLEconf(BEconf):
    '''Prepare LittleEndian Byte pattern from BigEndian configuration string, with separators.'''
    c = int(BEconf.replace('-',''), base=2)
    return swap2Bytes(c)
    
def LEtoBE(c):
    '''Little Endian to BigEndian conversion for signed 2Byte integers (2 complement).'''
    c = swap2Bytes(c)
    if(c >= 2**15):
        c= c-2**16
    return c
    
def BEtoLE(c):
    '''BigEndian to LittleEndian conversion for signed 2 Byte integers (2 complement).'''
    if(c < 0):
        c= 2**16 + c
    return swap2Bytes(c)
    
def resetChip():
    BUS.write_byte(RESET_ADDRESS, RESET_COMMAND)
    return

# read A0 and A1 once
resetChip()
# compare with configuration settings from ADS115 datasheet
# start single conversion - AIN2/GND - 4.096V - single shot - 8SPS - X
# - X - X - disable comparator
confA0 = prepareLEconf('1-100-001-1-100-0-0-0-11')
confA1 = prepareLEconf('1-101-001-1-100-0-0-0-11') 

BUS.write_word_data(DEVICE_ADDRESS, POINTER_CONFIGURATION, confA0)
# long enough to be safe that data acquisition (conversion) has completed
# may be calculated from data rate + some extra time for safety.
# check accuracy in any case.
time.sleep(0.5)
value_raw = BUS.read_word_data(DEVICE_ADDRESS, POINTER_CONVERSION)
value = LEtoBE(value_raw)
#print("A0:", value)
A0Volt=value*(4.096/32767)
print('the soil moisture value in sensor 1 in volts is ',A0Volt)
BS1 = 2.8432*A0Volt**3 - 9.1993*A0Volt**2 + 20.2553*A0Volt - 4.1882
bs1=round(BS1,2)
#print("il contenuto idrico in  volume del suolo del sensore 1 è ", BS1)
BUS.write_word_data(DEVICE_ADDRESS, POINTER_CONFIGURATION, confA1)
# long enough to be safe that data acquisition (conversion) has completed
# may be calculated from data rate + some extra time for safety.
# check accuracy in any case.
time.sleep(0.5)
value_raw = BUS.read_word_data(DEVICE_ADDRESS, POINTER_CONVERSION)
value = LEtoBE(value_raw)
#print("A1:",value)
A1Volt=value*(4.096/32767)
print('the soil moisture value in sensor 2 in volts is ',A1Volt)
BS2 = 2.8432*A1Volt**3 - 9.1993*A1Volt**2 + 20.2553*A1Volt - 4.1882
bs2=round(BS2,2)
     
#bs1, bs2 = readA0A1()
print('the soil moisture value in sensor 1 in volume % is ',bs1)
print('the soil moisture value in sensor 2 in volume % is ',bs2)
# Close I2C device
BUS.close()




