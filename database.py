import pandas as pd
import numpy as np
from influxdb import InfluxDBClient, DataFrameClient
from datetime import datetime, timedelta
import logging

logger = logging.getLogger('influxDB')

# Constants
INFLUXDB_ADDRESS = 'influxdb' # for Docker Compose
INFLUXDB_ADDRESS = 'localhost' # otherwise
INFLUXDB_USER = 'mimose'
INFLUXDB_PASSWORD = 'demo'
INFLUXDB_DATABASE = 'sensornode'



class influxDB():
    def __init__(self):
        ''' Initialize the influxDB database. Create new or connecte to exisiting.
        '''
  
        self.client = InfluxDBClient(INFLUXDB_ADDRESS, 8086, INFLUXDB_USER, INFLUXDB_PASSWORD, None)
        self.df_client = DataFrameClient(INFLUXDB_ADDRESS, 8086, INFLUXDB_USER,  INFLUXDB_PASSWORD, INFLUXDB_DATABASE)

        databases = self.client.get_list_database()
        if len(list(filter(lambda x: x['name'] == INFLUXDB_DATABASE, databases))) == 0:
            self.client.create_database(INFLUXDB_DATABASE) # Create new DB
            logger.info("Successfully created new database: " + INFLUXDB_DATABASE) 
        # Switch to database
        self.client.switch_database(INFLUXDB_DATABASE)
        logger.info("Successfully connected to existing database: " + INFLUXDB_DATABASE) 


    def read(self, measurement:str, field_key:str, start_time:datetime, end_time:datetime) -> pd.DataFrame:

        # Convert to UTC time
        start_time = ( start_time - timedelta(hours=2) ).strftime('%Y-%m-%dT%H:%M:%SZ')
        end_time   = ( end_time  - timedelta(hours=2) ).strftime('%Y-%m-%dT%H:%M:%SZ')

        query = "SELECT %s FROM %s WHERE time >= '%s' AND time <= '%s'" %(field_key, measurement, start_time, end_time)

        result = self.df_client.query(query)  

        points = pd.DataFrame(result[measurement])
        points.index.name = 'datetime'

        return points


    def save_dict(self, measurement:str, fields:dict):
        ''' Save data dict fields to influxDB measurement. Time stamps are in UTC time. '''

        # Return if field is empty
        if not fields:
            logger.error('Field dict of measurement %s is empty. Nothing written to DB.' %measurement)
            return 
        
        try:

            json_body = [
            {
                "measurement": measurement,
                "tags": {},
                "fields": fields
            } 
            ]

            self.client.write_points(json_body)
            logger.debug('Sensordata: ' + str(json_body))

        except Exception as err:
            logger.error('Could not write data to InfluxDB: ' + str(err))