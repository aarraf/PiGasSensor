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



ENS160_I2CADDR_DEFAULT: int = const(0x53)  # Default I2C address

# Addresses of the ENS160 registers
ENS160_REG_PARTID  = const(0x00)
ENS160_REG_OPMODE  = const(0x10)
ENS160_REG_CONFIG  = const(0x11)
ENS160_REG_COMMAND = const(0x12)
ENS160_REG_TEMPIN  = const(0x13)
ENS160_REG_RHIN    = const(0x15)
ENS160_REG_STATUS  = const(0x20)
ENS160_REG_AQI     = const(0x21)
ENS160_REG_TVOC    = const(0x22)
ENS160_REG_ECO2    = const(0x24)
ENS160_REG_GPRREAD = const(0x48)

# 
MODE_SLEEP = 0x00
MODE_IDLE = 0x01
MODE_STANDARD = 0x02
MODE_RESET = 0xF0
MODE_CUSTOM = 0xC0
valid_modes = (MODE_SLEEP, MODE_IDLE, MODE_STANDARD, MODE_RESET, MODE_CUSTOM)

NORMAL_OP = 0x00
WARM_UP = 0x01
START_UP = 0x02
INVALID_OUT = 0x03

COMMAND_NOP = 0x00
COMMAND_CLRGPR = 0xCC
COMMAND_GETAPPVER = 0x0E

# Not Implemented!

class ENS160:
    """Driver for the ENS210 temperature and humidity sensor

    :param ~busio.I2C i2c_bus: The I2C bus the ENS210 is connected to.
    :param int address: The I2C device address. Defaults to :const:`0x43`
    """
    # Explaination: https://docs.python.org/3/library/struct.html#format-strings
    #  - <H -> 16Bit little endian unsigned integer
    #  - <B -> 8Bit little endian unsigned integer

    # Register Map of I2C device
    part_id            = ROUnaryStruct(ENS160_REG_PARTID, "<H")
    operation_mode     = UnaryStruct(ENS160_REG_OPMODE, "<B")
    temp_in            = UnaryStruct(ENS160_REG_TEMPIN, "<H")
    rh_in              = UnaryStruct(ENS160_REG_RHIN, "<H")
    status             = UnaryStruct(ENS160_REG_STATUS, "<B")
    # sensor data registers
    command = UnaryStruct(ENS160_REG_COMMAND, "<B")
    new_GPR_available  = ROBit(ENS160_REG_STATUS, 0)
    new_data_available = ROBit(ENS160_REG_STATUS, 1)
    data_validity      = ROBits(2, ENS160_REG_STATUS, 2)
    AQI                = ROBits(2, ENS160_REG_AQI, 0)
    TVOC               = ROUnaryStruct(ENS160_REG_TVOC, "<H")
    eCO2               = ROUnaryStruct(ENS160_REG_ECO2, "<H")
    # interrupt register bits
    interrupt_polarity = RWBit(ENS160_REG_CONFIG, 6)
    interrupt_pushpull = RWBit(ENS160_REG_CONFIG, 5)
    interrupt_on_GPR   = RWBit(ENS160_REG_CONFIG, 3)
    interrupt_on_data  = RWBit(ENS160_REG_CONFIG, 1)
    interrupt_enable   = RWBit(ENS160_REG_CONFIG, 0)

    def __init__(self, i2c_bus: I2C, address: int = ENS210_I2CADDR_DEFAULT) -> None:
    ''' Initialize ENS160 on I2C bus and adress.
    '''
    
        # I2C Device
        self.i2c_device = i2c_device.I2CDevice(i2c_bus, address)
        if self.part_id != 0x160:
            raise RuntimeError("Unable to find ENS160, check your wiring")

        self.mode = MODE_STANDARD