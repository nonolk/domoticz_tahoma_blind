# Tahoma/Conexoon IO blind plugin
#
# Author: Nonolk, 2019-2020
# FirstFree function courtesy of @moroen https://github.com/moroen/IKEA-Tradfri-plugin
"""
<plugin key="tahomaIO" name="Tahoma or conexoon IO blind plugin" author="nonolk" version="1.0.5" externallink="https://github.com/nonolk/domoticz_tahoma_blind">
    <description>Tahoma/Conexoon plugin for IO blinds, this plugin require internet connexion.<br/>Please provide your email and password used to connect Tahoma/Conexoon</description>
    <params>
        <param field="Username" label="Username" width="200px" required="true" default=""/>
        <param field="Password" label="Password" width="200px" required="true" default="" password="true"/>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal"  default="true" />
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz
import urllib.parse
import json

class BasePlugin:
    enabled = False
    def __init__(self):
        self.httpConn = None
        self.srvaddr = "tahomalink.com"
        self.cookie = ""
        self.logged_in = False
        self.startup = True
        self.heartbeat = False
        self.devices = None
        self.filtred_devices = None
        self.heartbeat_delay = 1
        self.con_delay = 0
        self.wait_delay = 30
        self.json_data = None
        self.command = False
        self.refresh = True
        self.actions_serialized = []
        return

    def onStart(self):
        Domoticz.Status("Starting Tahoma blind plugin")
        if Parameters["Mode6"] == "Debug":
           Domoticz.Debugging(1)
        self.httpConn = Domoticz.Connection(Name="Secure Connection", Transport="TCP/IP", Protocol="HTTPS", Address=self.srvaddr, Port="443")
        self.httpConn.Connect()

    def onStop(self):
        self.heartbeat = False
        self.httpConn = None

    def onConnect(self, Connection, Status, Description):


        if (Status == 0 and not self.logged_in):
          Login = str(Parameters["Username"])
          pwd = str(Parameters["Password"])
          Headers = { 'Host': self.srvaddr,"Connection": "keep-alive","Accept-Encoding": "gzip, deflate", "Accept": "*/*", "Content-Type": "application/x-www-form-urlencoded"}
          postData = "userId="+urllib.parse.quote(Login)+"&userPassword="+urllib.parse.quote(pwd)+""
          self.httpConn.Send({'Verb':'POST', 'Headers': Headers, 'URL':'/enduser-mobile-web/enduserAPI/login', 'Data': postData})
        elif (self.cookie and self.logged_in and self.heartbeat and (not self.command)):
          self.refresh = True
          Headers = { 'Host': self.srvaddr,"Connection": "keep-alive","Accept-Encoding": "gzip, deflate", "Accept": "*/*", "Content-Type": "application/json", "Cookie": self.cookie}
          self.httpConn.Send({'Verb':'POST', 'Headers': Headers, 'URL':'/enduser-mobile-web/enduserAPI/setup/devices/states/refresh', 'Data': None})
        elif (self.command):
          Headers = { 'Host': self.srvaddr,"Connection": "keep-alive","Accept-Encoding": "gzip, deflate", "Accept": "*/*", "Content-Type": "application/json", "Cookie": self.cookie}
          self.httpConn.Send({'Verb':'POST', 'Headers': Headers, 'URL':'/enduser-mobile-web/enduserAPI/exec/apply', 'Data': self.json_data})
          Domoticz.Log("Processing command")
          self.command = False
          self.heartbeat = False
          self.actions_serialized = []
        else:
          Domoticz.Log("Failed to connect to tahoma api")


    def onMessage(self, Connection, Data):
        Status = int(Data["Status"])

        if (Status == 200 and not self.logged_in):
          self.logged_in = True
          Domoticz.Status("Tahoma auth succeed")
          tmp = Data["Headers"]
          self.cookie = tmp["Set-Cookie"]

        elif (Status == 401):
          strData = Data["Data"].decode("utf-8", "ignore")
          Domoticz.Error("Tahoma auth error")
          self.logged_in = False
          self.cookie = None

          if ("Too many" in strData):
            Domoticz.Error("Too much connexions must wait")
            self.heartbeat = True
            return
          if ("Bad credentials" in strData):
            Domoticz.Error("Bad credentials please update credentials and restart device")
            self.heartbeat =  False
            return

          if (not self.logged_in):
            Login = str(Parameters["Username"])
            pwd = str(Parameters["Password"])
            Headers = { 'Host': self.srvaddr,"Connection": "keep-alive","Accept-Encoding": "gzip, deflate", "Accept": "*/*", "Content-Type": "application/x-www-form-urlencoded"}
            postData = "userId="+urllib.parse.quote(Login)+"&userPassword="+urllib.parse.quote(pwd)+""
            self.httpConn.Send({'Verb':'POST', 'Headers': Headers, 'URL':'/enduser-mobile-web/enduserAPI/login', 'Data': postData})

          self.heartbeat_delay = 0
          return

        elif (Status == 200 and self.logged_in and self.heartbeat and self.refresh):
          self.refresh = False
          Headers = { 'Host': self.srvaddr,"Connection": "keep-alive","Accept-Encoding": "gzip, deflate", "Accept": "*/*", "Content-Type": "application/x-www-form-urlencoded", "Cookie": self.cookie}
          self.httpConn.Send({'Verb':'GET', 'Headers': Headers, 'URL':'/enduser-mobile-web/enduserAPI/setup/devices'})
          return

        elif (Status == 200 and self.logged_in and self.heartbeat and (not self.refresh)):
          strData = Data["Data"].decode("utf-8", "ignore")

          if (not "uiClass" in strData):
            Domoticz.Debug(str(strData))
            return

          self.devices = json.loads(strData)

          self.filtered_devices = list()
          for device in self.devices:
             Domoticz.Debug("Device name: "+device["label"]+" Device class: "+device["uiClass"])
             if (((device["uiClass"] == "RollerShutter") or (device["uiClass"] == "ExteriorScreen") or (device["uiClass"] == "Screen") or (device["uiClass"] == "Awning") or (device["uiClass"] == "Pergola") or (device["uiClass"] == "GarageDoor") or (device["uiClass"] == "Window") or (device["uiClass"] == "VenetianBlind") or (device["uiClass"] == "ExteriorVenetianBlind")) and ((device["deviceURL"].startswith("io://")) or (device["deviceURL"].startswith("rts://")))):
               self.filtered_devices.append(device)

          if (len(Devices) == 0 and self.startup):
            count = 1
            for device in self.filtered_devices:
               Domoticz.Status("Creating device: "+device["label"])
               swtype = None
               
               if (device["deviceURL"].startswith("io://")):
                    swtype = 16
               elif (device["deviceURL"].startswith("rts://")):
                    swtype = 6
          
               Domoticz.Device(Name=device["label"], Unit=count, Type=244, Subtype=73, Switchtype=swtype, DeviceID=device["deviceURL"]).Create()
               
               if not (count in Devices):
                   Domoticz.Error("Device creation not allowed, please allow device creation")
               else:
                   Domoticz.Status("Device created: "+device["label"])
                   count += 1

          if ((len(Devices) < len(self.filtered_devices)) and len(Devices) != 0 and self.startup):
            Domoticz.Log("New device(s) detected")
            found = False

            for device in self.filtered_devices:
               for dev in Devices:
                  UnitID = Devices[dev].Unit
                  if Devices[dev].DeviceID == device["deviceURL"]:
                    found = True
                    break
               if (not found):
                 idx = firstFree()
                 swtype = None
                 
                 Domoticz.Status("Must create device: "+device["label"])
                 
                 if (device["deviceURL"].startswith("io://")):
                    swtype = 16
                 elif (device["deviceURL"].startswith("rts://")):
                    swtype = 6
          
                 Domoticz.Device(Name=device["label"], Unit=idx, Type=244, Subtype=73, Switchtype=swtype, DeviceID=device["deviceURL"]).Create()

                 if not (idx in Devices):
                     Domoticz.Error("Device creation not allowed, please allow device creation")
                 else:
                     Domoticz.Status("New device created: "+device["label"])
               else:
                  found = False

          self.startup = False

          for dev in Devices:
             for device in self.filtered_devices:

               if (Devices[dev].DeviceID == device["deviceURL"]) and (device["deviceURL"].startswith("io://")):
                 level = 0
                 status_l = False
                 status = None
                 states = device["states"]
                 for state in states:

                    if state["name"] == "core:ClosureState":
                      level = state["value"]
                      level = 100 - level
                      status_l = True
                    if status_l:
                      if (Devices[dev].sValue):
                        int_level = int(Devices[dev].sValue)
                      else:
                        int_level = 0
                      if (level != int_level):

                        Domoticz.Log("Updating device:"+Devices[dev].Name)
                        if (level == 0):
                          Devices[dev].Update(0,"0")
                        if (level == 100):
                          Devices[dev].Update(1,"100")
                        if (level != 0 and level != 100):
                          Devices[dev].Update(2,str(level))
                        break
        elif (Status == 200 and (not self.heartbeat)):
          return
        else:
          Domoticz.Log("Return status"+str(Status))

    def onCommand(self, Unit, Command, Level, Hue):
        commands_serialized = []
        action = {}
        commands = {}
        params = []


        if (str(Command) == "Off"):
          commands["name"] = "close"
        elif (str(Command) == "On"):
          commands["name"] = "open"
        elif ("Set Level" in str(Command)):
          commands["name"] = "setClosure"
          tmp = 100 - int(Level)
          params.append(tmp)
          commands["parameters"] = params

        commands_serialized.append(commands)
        action["deviceURL"] = Devices[Unit].DeviceID
        action["commands"] = commands_serialized
        self.actions_serialized.append(action)
        data = {"label": "Domoticz - "+Devices[Unit].Name+" - "+commands["name"], "actions": self.actions_serialized}
        self.json_data = json.dumps(data, indent=None, sort_keys=True)

        if (not self.httpConn.Connected()):
          Domoticz.Log("Not connected before processing command, must connect")
          self.command = True
          self.httpConn.Connect()
        else:
          Headers = { 'Host': self.srvaddr,"Connection": "keep-alive","Accept-Encoding": "gzip, deflate", "Accept": "*/*", "Content-Type": "application/json", "Cookie": self.cookie}
          self.httpConn.Send({'Verb':'POST', 'Headers': Headers, 'URL':'/enduser-mobile-web/enduserAPI/exec/apply', 'Data': self.json_data})
          Domoticz.Log("Sending command to tahoma api")
          self.heartbeat = False
          self.actions_serialized = []


    def onDisconnect(self, Connection):
        return

    def onHeartbeat(self):
        if (self.cookie and self.logged_in and ((not self.heartbeat) or self.heartbeat_delay == 3)):
          if (not self.httpConn.Connected()):
            self.httpConn.Connect()
          else:
            Headers = { 'Host': self.srvaddr,"Connection": "keep-alive","Accept-Encoding": "gzip, deflate", "Accept": "*/*", "Content-Type": "application/json", "Cookie": self.cookie}
            self.httpConn.Send({'Verb':'POST', 'Headers': Headers, 'URL':'/enduser-mobile-web/enduserAPI/setup/devices/states/refresh', 'Data': None})
          self.heartbeat =True
          self.heartbeat_delay = 1

        elif (self.heartbeat and (self.heartbeat_delay <= 2) and self.logged_in):
          self.heartbeat_delay += 1

        elif (self.heartbeat and (self.con_delay < self.wait_delay) and (not self.logged_in)):
          self.con_delay +=1
          Domoticz.Status("Too much connections waiting before authenticating again")

        elif (self.heartbeat and (self.con_delay == self.wait_delay) and (not self.logged_in)):
          if (not self.httpConn.Connected()):
            self.httpConn.Connect()
          self.heartbeat =True
          self.heartbeat_delay = 0
          self.con_delay = 0

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return

def DumpHTTPResponseToLog(httpResp, level=0):
    if (level==0): Domoticz.Debug("HTTP Details ("+str(len(httpResp))+"):")
    indentStr = ""
    for x in range(level):
        indentStr += "----"
    if isinstance(httpResp, dict):
        for x in httpResp:
            if not isinstance(httpResp[x], dict) and not isinstance(httpResp[x], list):
                Domoticz.Debug(indentStr + ">'" + x + "':'" + str(httpResp[x]) + "'")
            else:
                Domoticz.Debug(indentStr + ">'" + x + "':")
                DumpHTTPResponseToLog(httpResp[x], level+1)
    elif isinstance(httpResp, list):
        for x in httpResp:
            Domoticz.Debug(indentStr + "['" + x + "']")
    else:
        Domoticz.Debug(indentStr + ">'" + x + "':'" + str(httpResp[x]) + "'")

def firstFree():
    for num in range(1, 250):
        if num not in Devices:
            return num
    return
