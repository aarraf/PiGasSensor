import board
import adafruit_ens160 as AdaENS160
import time
from datetime import datetime, timedelta

import logging
import time
import pandas as pd
import numpy as np
from micropython import const
from ENS210 import ENS210
from weather_station import weatherStation
from database import influxDB


ENS160_I2CADDR: int = const(0x52)  # ENS160 I2C address


SAMPLING_TIME_S_ENS= 1. #in sec
SAMPLING_TIME_S_WS = 8.

# Logging
logger = logging.getLogger('measure')
logging.basicConfig(filename='measure.log', level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')



def init_ENS160() -> AdaENS160.ENS160:
    ''' Initialize ENS160 in standard mode- 
    '''
    i2c = board.I2C()  # uses board.SCL and board.SDA
    ens160 = AdaENS160.ENS160(i2c, ENS160_I2CADDR)

    while ens160.mode is not AdaENS160.MODE_STANDARD:
        time.sleep(0.1)

    # Set temperature compensation 
    ens160.temperature_compensation = 23
    # Set humidity compensation
    ens160.humidity_compensation = 50

    # We can have the INT pin tell us when new data is available
    ens160.interrupt_pushpull = True  # use pushpull 3V, not open-drain
    ens160.interrupt_on_data = True  # Tell us when there's new calculated data
    ens160.interrupt_polarity = False  # Active 'low' (false)
    ens160.interrupt_enable = True  # enable pin

    logger.info('ENS160 Initialized')

    return ens160

def update_ens160_compensation(ens160:AdaENS160.ENS160, ens210:ENS210):
    ens160.temperature_compensation = ens210.data["T"]
    ens160.humidity_compensation = ens210.data["H"]

def init_ENS210() -> ENS210:
    i2c = board.I2C() 
    return ENS210(i2c)



def eval_sensor_data(db:influxDB):

    current_time = datetime.now()
    start_time = current_time - timedelta(seconds=20)
    
    start_time = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time = current_time.strftime('%Y-%m-%dT%H:%M:%SZ')

    data = db.read('ENS160', "R0", start_time , end_time)


def read_ens160(ens160:AdaENS160.ENS160):
    
    data = ens160.read_all_sensors()
    status = ens160.data_validity
    
    ens_status = 0
    if status == AdaENS160.NORMAL_OP:
        ens_status = 1
    if status == AdaENS160.WARM_UP:
        ens_status = 2
    if status == AdaENS160.START_UP:
        ens_status = 3
    if status == AdaENS160.INVALID_OUT:
        ens_status = 4

    return {"status": ens_status, "AQI":data["AQI"], "TVOC": data["TVOC"], "eCO2": data["eCO2"], 
            "R0":data["Resistances"][0], "R1":data["Resistances"][1], "R2":data["Resistances"][2], "R3":data["Resistances"][3]}

     

def read_ens210(ens210:ENS210):
    ens210.measure()
    return ens210.data


#########################################################################################################


if __name__ == "__main__":
    
    db = influxDB()
    ens160 = init_ENS160()
    ens210 = init_ENS210()
    ws = weatherStation(url="http://192.168.0.99/livedata.htm")

    #current_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time = (datetime.now() + timedelta(hours=0))
    start_time = (end_time - timedelta(hours=24))

    start_time = datetime(2024,10,7,13,15,55)
    end_time   = datetime(2024,10,7,13,18,13)

    #read_db('ENS160', "R0", (start_time.strftime('%Y-%m-%dT%H:%M:%SZ') ), (end_time.strftime('%Y-%m-%dT%H:%M:%SZ')))
    #print(read_db('ENS160', "R0", start_time, end_time))

    # Loop
    counter = 0
    while True:

        # continue if no new data available
        if ens160.new_data_available:
            ens210_data = read_ens210(ens210)
            update_ens160_compensation(ens160, ens210)
            ens160_data = read_ens160(ens160)
            db.save_dict(measurement="ENS160", fields=ens160_data)
            db.save_dict(measurement="ENS210", fields=ens210_data)
        
        if counter == int(SAMPLING_TIME_S_ENS / SAMPLING_TIME_S_ENS):
            ws_data = ws.read()
            db.save_dict(measurement="WeatherStation", fields=ws_data)
            counter = 0

            if 1:
                print(ens160_data)
                print(ens210_data)
                print(ws_data)

        else:
            counter = counter + 1



        
        time.sleep(SAMPLING_TIME_S_ENS) #Delay