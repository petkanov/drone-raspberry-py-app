import logging, threading

import ProtoData_pb2 as proto_library
from command_data_dto import CommandData
from utils import Utils

class DataReceiver (threading.Thread):
   def __init__(self, socket, drone):
      threading.Thread.__init__(self)
      self.daemon = True
      self.socket = socket
      self.drone = drone
      self.isActive = True
      
   def run(self):
      while(self.isActive):
          try:
              data = Utils.readNetworkMessage(self.socket)
              
              command = proto_library.Command()
              command.ParseFromString(data)
              
              commandData = CommandData()
              commandData.code = command.code
              
              if(command.code == 14):
                  missionData = proto_library.MissionData()
                  missionData.ParseFromString(command.payload)
                  
                  commandData.data = missionData
              
              self.drone.executeCommand(commandData)
              
          except Exception as e:
              logging.error('DataReceiver: '+str(e), exc_info=True)
   
   def stop(self):
       self.isActive = False