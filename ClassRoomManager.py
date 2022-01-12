import time
import json
import threading
import paho.mqtt.client as mqtt_client
import os
import sys
import RPi.GPIO as GPIO
from uuid import getnode as get_mac
from time import sleep
from datetime import datetime
from connection import Objet
from Light import Light_sensor
from presence import Presence_sensor
from Shutter import Shutter
from led import OnOff_led

class Light_manage(Objet):

    _condition  = None      
    _thread     = None      
    presence = False

    def __init__(self, unitID=0, MQTT_PUB_TOPIC="1r1/014/shutter/command",MQTT_SUB_TOPIC="1r1/014/presence",MQTT_SERVER="192.168.0.206",MQTT_PORT=1883,shutterID="Front",lampeID =1, presenceSensorId=120, lumSensorId=57, *args, **kwargs):
       	#les topic dans lesquel le module de gestion de luminosité publie ses commandes sont :
       	self.ShutterCmdTopic = "1r1/014/shutter/command"
        self.LightCmdTopic   = "1r1/014/light/command"
       	self.LumCmdTopic     = "1r1/014/lum/command"
       	self.AlarmTopic	     = "1r1/014/alarm/command"
    
       	self.ShutterTopic    = "1r1/014/shutter"
       	self.PresenceTopic   = "1r1/014/presence"
       	self.LumTopic     = "1r1/014/lum"   
    
       	#Ids des composants de la salle
       	self.shutterID = shutterID
       	self.lampeID   = lampeID
       	self.presenceSensorId = presenceSensorId
       	self.lumSensorId = lumSensorId
    
       	#pour le test modulaire on instancie les composants ici
       	ShutterThread = threading.Thread(target=Shutter,args=(self.shutterID,"1r1/014/shutter","1r1/014/shutter/command","192.168.0.206",1883))
        ShutterThread.start()
        
        LampeThread = threading.Thread(target=OnOff_led,args=(self.lampeID, "1r1/014/light", "1r1/014/light/command","192.168.0.206",1883,"light",5))
        LampeThread.start()
        
        PresSensThread = threading.Thread(target=Presence_sensor,args=(12, get_mac(), self.presenceSensorId, "1r1/014/presence", "192.168.0.206",1883,"1r1/014/presence/command"))
        PresSensThread.start()  
        LumSensThread = threading.Thread(target=Light_sensor,args=(get_mac(),self.lumSensorId , "1r1/014/lum", "1r1/014/lum/command", "192.168.0.206",1883,20))
        LumSensThread.start()   
       	self.presence = False
       	self.SuttersOpen = False
    
       	super().__init__(unitID,MQTT_PUB_TOPIC,MQTT_SUB_TOPIC,MQTT_SERVER,MQTT_PORT)
    
    def on_connect(self, client, userdata, flags, rc):
    	if rc==0:
    		self.connection.connected_flag = True
    		print("Connection returned code: "+ str(rc))
    		self.connection.subscribe(self.ShutterTopic ,qos=0)
    		self.connection.subscribe(self.PresenceTopic,qos=0)
    		self.connection.subscribe(self.LumTopic,qos=0)
    	else:
    		print("Bad connection Returned code= "+str(rc))
             
    def get_date_time(self):
        weekdays= ("Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche")
        time = datetime.now().strftime("%H")
        date = datetime.today().weekday()
        return (weekdays[date],time)
    
    def Shutter_cmd(self,id,order):
        data = {
                "dest": id,
                "order": order
            }
        data_out = json.dumps(data)
        self.connection.publish(self.ShutterCmdTopic, data_out)


    def Light_cmd(self,id,order):
        data = {
                "dest": id,
                
                "order": order
            }
        data_out = json.dumps(data)
        self.connection.publish(self.LightCmdTopic, data_out)

    def Lum_cmd(self,id,order):
        data = {
                "dest": id,
                "order": order
            }
        data_out = json.dumps(data)
        self.connection.publish(self.LumCmdTopic, data_out)    

    def Alarm(self):
        print("alarm On")
        data = { 
            "Alerte": "Intrus detecte"
        }
        data_out = json.dumps(data)
        self.connection.publish(self.AlarmTopic, data_out)

    def on_message(self,client,userdata,msg):
        (day, hour) = self.get_date_time()
        hour = int(hour)
        payload = json.loads(msg.payload)
	
        if (payload['subID'] == self.presenceSensorId):
            print("Presence reçue= ",payload['value'])
            if (payload['value']):  
               self.presence = True
               #self.Lum_cmd(self.lumSensorId,"capture")
            else:
               self.presence = False
               self.Light_cmd("all","Off")

        if (day == "Dimanche" or day == "Samedi") or (hour < 7 or hour > 21):
            print("Journee feriee")
            self.Shutter_cmd("all","Down")
            self.Light_cmd("all","Off")
            print("presence mercredi = ",self.presence)
            if(self.presence):
                self.Alarm()
                return

        if (payload['subID'] == self.lumSensorId):
            print("lumSensorId")	
            print("presence",self.presence)
            if((payload['value'] < 400) and (self.presence)):
                if(self.SuttersOpen):
                   print("SHutters Opened")
                   self.Light_cmd("all","On")
                else:
                    print("Shutters Closed")
                    self.Shutter_cmd("all","Up")
                    time.sleep(5)
                    self.Lum_cmd(self.lumSensorId,"capture")

        if (payload['unitID'] == self.shutterID):
             if (int(payload['status'])== 1):
                self.SuttersOpen = True
             else:
                self.SuttersOpen = False

def main():
    test = Light_manage()


# Execution or import
if __name__ == "__main__":
    main()




