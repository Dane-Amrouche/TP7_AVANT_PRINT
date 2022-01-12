import time
import json
import threading
import paho.mqtt.client as mqtt_client
import os
import sys
from connection import Objet
import RPi.GPIO as GPIO
from uuid import getnode as get_mac
import smbus

class Light_sensor(Objet):

    # class attributes
    FREQUENCY        = 20
    subID            = None  # id of the object instance
    
    # attributes
    _status = None
    courseTime  = 30;       # (seconds) max. time for resend the data


    _curCmd     = None
    _thread     = None      # thread to handle shutter's course

    def __init__(self,unitID=get_mac(), subID=57, MQTT_PUB_TOPIC="1r1/014/lum",MQTT_SUB_TOPIC="1r1/014/lum/command",MQTT_SERVER="192.168.0.206",MQTT_PORT=1883,FREQUENCY=20, *args, **kwargs):
        self.subID = subID
        self.FREQUENCY = FREQUENCY
        super().__init__(unitID,MQTT_PUB_TOPIC,MQTT_SUB_TOPIC,MQTT_SERVER,MQTT_PORT)

      
    def get_luminosity(self):
        
        bus = smbus.SMBus(1)
        #TSL2561 address, 0x39(57)

        bus.write_byte_data(self.subID, 0x00 | 0x80, 0x03)   
        bus.write_byte_data(self.subID, 0x01 | 0x80, 0x02)
        time.sleep(0.5)
            
        data = bus.read_i2c_block_data(self.subID, 0x0C | 0x80, 2)
            
        data1 = bus.read_i2c_block_data(self.subID, 0x0E | 0x80, 2)
          
        ch0 = data[1] * 256 + data[0]
        ch1 = data1[1] * 256 + data1[0]

        #print("Full Spectrum(IR + Visible) :%d lux" %ch0)
        #print("Infrared Value :%d lux" %ch1)
        #print("Visible Value :%d lux" %(ch0 - ch1))
        return ch0
    
    
    def do_every(self):      
        #publish the detected value
        data = {
                "unitID": self.unitID,
                "subID": self.subID,
                "value": self.get_luminosity(),   
                "value-units": "Lux"
         }
        data_out = json.dumps(data)

        # send current data 
        self.connection.publish(self.mqtt_pub_topic, data_out)
        self._thread = threading.Timer(self.FREQUENCY, self.do_every)
        self._thread.start()
        

    

    def on_connect(self, client, userdata, flags, rc):
        if rc==0:
            self.connection.connected_flag = True
            print("Connection returned code: "+ str(rc))
            self.do_every()
            self.connection.subscribe(self.mqtt_sub_topic,qos=0)
        else:
             print("Bad connection Returned code= "+str(rc))
              
        
             
    def on_message(self, client, userdata, msg):
        print("msg received")
        payload = json.loads(msg.payload)
        # if this sensor in the destination
        if payload['dest'] == "all" or payload['dest'] == self.subID :
            #execute the commande
            print(payload)
            if payload['order'] == "frequency":
               self.FREQUENCY = payload['value']
                   
            elif payload['order'] =="capture":
                # sense the luminosity
                data = {
                        "unitID": self.unitID,
                        "subID": self.subID,
                        "value": self.get_luminosity(),   
                        "value-units": "Lux"
                 }
                data_out = json.dumps(data)
                # send the sensed data 
                self.connection.publish(self.mqtt_pub_topic, data_out)
            
            else:
                print("invalid command")
#
# MAIN
#

def main():

    #TODO: implement simple tests of your module
    t = Light_sensor(1,0x39)
    #t.get_Light()

# Execution or import
if __name__ == "__main__":
    # Start executing
    main()



