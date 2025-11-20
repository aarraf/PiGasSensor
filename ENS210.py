import time
import struct
from micropython import const
from adafruit_bus_device import i2c_device
from adafruit_register.i2c_struct import ROUnaryStruct, UnaryStruct
from adafruit_register.i2c_bit import RWBit, ROBit
from adafruit_register.i2c_bits import ROBits

try:
    from typing import Dict, Optional, Union, List
    from typing_extensions import Literal
    from busio import I2C
except ImportError:
    pass

import logging
logger = logging.getLogger('measure')



ENS210_I2CADDR_DEFAULT: int = const(0x43)  # Default I2C address

#Chip constants
ENS210_PARTID           = const(0x0210) # The expected part id of the ENS210
ENS210_BOOTING          = const(0.002)  # Booting time in seconds (also after reset, or going to high power)
ENS210_THCONV_SINGLE_S  = const(0.130)  # Conversion time in seconds for single shot T/H measurement
ENS210_THCONV_CONT_S    = const(0.238)  # Conversion time in seconds for continuous T/H measurement

# Addresses of the ENS210 registers
ENS210_REG_PART_ID    = const(0x00)
ENS210_REG_UID        = const(0x04)
ENS210_REG_SYS_CTRL   = const(0x10)
ENS210_REG_SYS_STAT   = const(0x11)
ENS210_REG_SENS_RUN   = const(0x21)
ENS210_REG_SENS_START = const(0x22)
ENS210_REG_SENS_STOP  = const(0x23)
ENS210_REG_SENS_STAT  = const(0x24)
ENS210_REG_T_VAL      = const(0x30)
ENS210_REG_T_STAT     = const(0x32)
ENS210_REG_H_VAL      = const(0x33)
ENS210_REG_H_STAT     = const(0x35)



class ENS210:
    """Driver for the ENS210 temperature and humidity sensor

    :param ~busio.I2C i2c_bus: The I2C bus the ENS210 is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x43`
    """
    
    # Explaination: https://docs.python.org/3/library/struct.html#format-strings
    #  - <H -> 16Bit little endian unsigned integer
    #  - <B -> 8Bit little endian unsigned integer

    # Register Map of I2C device
    part_id     = ROUnaryStruct(ENS210_REG_PART_ID, "<H") # 2Byte
    uid         = ROUnaryStruct(ENS210_REG_UID, "<Q") #8Byte
    sys_ctl     = UnaryStruct(ENS210_REG_SYS_CTRL, "<B") #1Byte RW
    sys_stat    = ROUnaryStruct(ENS210_REG_SYS_STAT, "<B") #1Byte
    sens_run    = UnaryStruct(ENS210_REG_SENS_RUN, "<B") #1Byte RW
    sens_start  = UnaryStruct(ENS210_REG_SENS_START, "<B") #1Byte RW
    sens_stop   = UnaryStruct(ENS210_REG_SENS_STOP, "<B") #1Byte RW
    sens_stat   = ROUnaryStruct(ENS210_REG_SENS_STAT, "<B") #1Byte
    t_val       = ROUnaryStruct(ENS210_REG_T_VAL, "<H") # 2Byte
    t_stat      = ROUnaryStruct(ENS210_REG_T_STAT, "<B") #1Byte
    h_val       = ROUnaryStruct(ENS210_REG_H_VAL, "<H") # 2Byte
    h_stat      = ROUnaryStruct(ENS210_REG_H_STAT, "<B") #1Byte


    def __init__(self, i2c_bus: I2C, address: int = ENS210_I2CADDR_DEFAULT) -> None:
        ''' Initialize ENS210 on I2C bus and adress.
        '''
        
        # I2C Device
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)
        # Data Dictionary
        self.data = {"T": None,"H": None, "T_status":None, "H_status":None}
        # Temperature Correction
        self.soldercorrection = 0 # 50*64/1000

        # Perform a soft reset
        self.reset(True)

        # Singe shot (True) ore continuos measurement mode
        self.singleMode = True
        self.setSingleMode(self.singleMode)

        # Power Mode (Low Power = False)
        self.setPowerMode(False)
        
        time.sleep(ENS210_BOOTING)
        logger.info('ENS210 Initialized')



    def reset(self, enable:bool) -> None:
        ''' Perform a soft reset. '''
        if enable:
            self.sys_ctl = const(0x80)

        time.sleep(ENS210_BOOTING) 


    def setPowerMode(self, enable:bool):
        ''' Sets ENS210 to low (true) or high (false) power.
        '''
        if enable:
            self.sys_ctl = const(0x01)
        else:
            self.sys_ctl = const(0x00)

        time.sleep(ENS210_BOOTING) 


    def setSingleMode(self, enable:bool):
        ''' Configures ENS210 measurement mode false for continuous mode / true for single shot measurement. 
            Returns false on I2C problems.
        '''
        if enable:
            self.sens_run = const(0x00)
        else:
            self.sens_run = const(0x03)


    def measure(self):
        ''' Performe measuremtn and save reading to data dictionary
        '''
        # Perform Single Shot Measurement
        if self.singleMode:
            self.setSingleMode(True)

        # Start Measurement
        self.sens_start = const(0x03)

        # Wait for 
        if self.singleMode:
            time.sleep(ENS210_THCONV_SINGLE_S) 
        else:
            time.sleep(ENS210_THCONV_CONT_S) 


        self.data_to_dict()


    def data_to_dict(self) -> dict:
        ''' Save sensor data and status to dictionary
        '''

        self.data["T_status"] = 0
        self.data["T"] = self.getTempCelcius(self.t_val)
        self.data["H_status"] = 0
        self.data["H"] = self.getHumidityPercent(self.h_val)

        if (self.t_stat & 0x01) == 0x01: # 
            self.data["T_status"] = 1 # Valid
        if (self.h_stat & 0x01) == 0x01:
            self.data["H_status"] = 1 # Valid



    def getTempCelcius(self, temp) -> float:
        ''' Convert raw value to temperatur in degres celcius (°C).
        '''
        return (int(temp) - self.soldercorrection) / 64.0 - 273.15

    def getHumidityPercent(self, humi) -> float:
        ''' Convert raw value to relative humidity (%).
        '''
        return  humi/ 512



if __name__ == "__main__":
    pass