from bs4 import BeautifulSoup
import requests

import logging
logger = logging.getLogger('Weather Station')

class weatherStation():

    def __init__(self,url:str = "http://192.168.0.99/livedata.htm") -> None:
        self.url = url
        logger.info("Weather Station Initalized") 
    

    def read(self):
        ''' Parse Wheater Station WH2600 Webpage and convert to dictionary.
        '''
        data_dict = {}
        unused_entries = ("CurrTime", "IndoorID", "Outdoor1ID", "Outdoor2ID", "outBattSta2")
        string_entires= ("inBattSta", "outBattSta1")

        try:
            r = requests.get(self.url)
            soup = BeautifulSoup(r.content, 'lxml')
        except Exception as err:
            logger.error("Weather Station Request failed: %s" %str(err)) 
            return data_dict
       

        #Iterate als input field
        for input in soup.table.form.find_all('input'):
            name = input.get('name') 
            # Only store relevant fields
            if name not in unused_entries:
                # Store as float
                if name not in string_entires:
                    try:
                        data_dict.update({name : float(input.get('value'))})
                    except Exception as err:
                        logger.error("Dict name %s yields: %s" %(name, str(err))) 
                        data_dict.update({name : None})
                    
                else: #Otherwise as string
                    data_dict.update({name : input.get('value')})
                    
        return data_dict