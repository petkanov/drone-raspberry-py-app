import time, logging
import RPi.GPIO as GPIO
from dronekit import VehicleMode, Command
from engine import Engine
from servo_controller import ServoController
from pymavlink import mavutil

DROP_PACKAGE_PIN = 21
IGNITE_LED_PIN = 2

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(DROP_PACKAGE_PIN,GPIO.OUT)
GPIO.output(DROP_PACKAGE_PIN,GPIO.HIGH)

GPIO.setup(IGNITE_LED_PIN,GPIO.OUT)
GPIO.output(IGNITE_LED_PIN,GPIO.HIGH)

class ControlTab:
    def __init__(self, drone):
        self.vehicle = drone.vehicle
        self.drone = drone
        
        self.light_state = GPIO.HIGH
        self.ignitor_state = GPIO.HIGH
        
        self.camera_angle = 140 # 60 - Lowest ; 230 Max value;
        self.servo_camera = ServoController(self.camera_angle)
        self.servo_camera.start()
        
        self.speed_x = 0
        self.speed_y = 0
        self.speed_z = 0
        self.increment_value_x = 0.5
        self.increment_value_y = 0.5
        self.increment_value_z = 0.2
        self.rotation_angle = 10
        self.engine = Engine(drone, self)
        self.engine.start()
        
    def stopMovement(self):
        self.speed_x = 0
        self.speed_y = 0
        self.speed_z = 0
        self.engine.executeChangesNow()
        
    def rotateLeft(self, angle):
        self.engine.rotate(-1, angle)
    
    def rotateRight(self, angle):
        self.engine.rotate(1, angle)
        
    def increaseSpeedX(self):
        self.speed_x = self.speed_x + self.increment_value_x
        self.engine.executeChangesNow()
        
    def decreaseSpeedX(self):
        self.speed_x = self.speed_x - self.increment_value_x
        self.engine.executeChangesNow()
   
    def leftSpeedY(self):
        self.speed_y = self.speed_y - self.increment_value_y
        self.engine.executeChangesNow()
        
    def rightSpeedY(self):
        self.speed_y = self.speed_y + self.increment_value_y
        self.engine.executeChangesNow()
        
    def stopSpeedXY(self):
        self.speed_x = 0
        self.speed_y = 0
        self.engine.executeChangesNow()
        
    def increaseSpeedZ(self):
        self.speed_z = self.speed_z - self.increment_value_z
        self.engine.executeChangesNow()
        
    def decreaseSpeedZ(self):
        self.speed_z = self.speed_z + self.increment_value_z
        self.engine.executeChangesNow()
        
    def stopSpeedZ(self):
        self.speed_z = 0
        self.engine.executeChangesNow()
        
    def killMotorsNow(self):
        self.engine.killMotorsNow()
        
    def armAndTakeoff(self, takeoff_alt):
        logging.info("Arming") 
        
        self.vehicle.mode = VehicleMode("GUIDED")   

        self.vehicle.armed = True
        time.sleep(1)
    
        while not self.vehicle.armed:
            logging.debug('self.vehicle.armed: '+str(self.vehicle.armed))
            self.vehicle.armed = True
            time.sleep(1)
        
        self.vehicle.simple_takeoff(takeoff_alt)
        logging.info("Takeoff")

        while True:
            current_hight = self.vehicle.location.global_relative_frame.alt
        
            if current_hight >= takeoff_alt * 0.95:
                logging.info("Altitude reached")
                #commanding movement to the same location to unlock Yaw
                self.vehicle.simple_goto( self.vehicle.location.global_relative_frame)
                break
            time.sleep(1)
        
    def goHome(self, rtl_alt):
        logging.info('Going Home')
        self.vehicle.mode = VehicleMode("GUIDED")

        for _ in range(0,10):
            self.increaseSpeedZ()
            time.sleep(0.5)
        
        while True:
            current_hight = self.vehicle.location.global_relative_frame.alt
        
            if current_hight >= rtl_alt * 0.95:
                logging.info("Safe RTL Altitude reached")
                self.vehicle.mode = VehicleMode("RTL")
                break
            time.sleep(1)

    def togleLights(self):
        
        self.ignitor_state = GPIO.LOW
        GPIO.output(IGNITE_LED_PIN,GPIO.LOW)
        time.sleep(1)
        self.ignitor_state = GPIO.HIGH
        GPIO.output(IGNITE_LED_PIN,GPIO.HIGH)
        
        self.light_state = GPIO.LOW
        GPIO.output(DROP_PACKAGE_PIN,GPIO.LOW)
        time.sleep(1)
        self.light_state = GPIO.HIGH
        GPIO.output(DROP_PACKAGE_PIN,GPIO.HIGH) 

    def cameraUP(self):
        if self.camera_angle > 60:
            self.camera_angle = self.camera_angle - 20
            self.servo_camera.setAngle(self.camera_angle)
            logging.debug("Current Camera Angle: %s", str( self.camera_angle))

    def cameraDOWN(self):
        if self.camera_angle < 220:
            self.camera_angle = self.camera_angle + 20
            self.servo_camera.setAngle(self.camera_angle)
            logging.debug("Current Camera Angle: %s", str( self.camera_angle))
        
    def cancelMission(self):
        self.vehicle.mode = VehicleMode("GUIDED")
        self.vehicle.commands.next = 0
        self.engine.lastMissionCmndIndex = -1
        cmds = self.vehicle.commands
        cmds.clear()
        cmds.upload()
        
    def activateMission(self, points_data):
        if self.vehicle.mode == VehicleMode("AUTO"):
            self.vehicle.mode = VehicleMode("GUIDED")
            self.drone.state = "MISSION PAUSE"
            self.drone.freeze()
            return
        
        if self.vehicle.commands.next > 0 and self.vehicle.mode == VehicleMode("GUIDED"):
            self.drone.state = "MISSION RESUME"
            self.vehicle.mode = VehicleMode("AUTO")
            return
        
        self.vehicle.commands.next = 0
        cmds = self.vehicle.commands
        cmds.clear()
        # add & remove command because of the bug(not seeing first time added command)
        cmds.add(Command( 0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, 
                          mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, 
                          float(0), float(0), float(0)  ))
        cmds.clear()
        
        if not self.vehicle.armed:
            self.armAndTakeoff( self.drone.takeoff_alt)
        
        for point in points_data.point:
            cmds.add(Command( 0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, 
                             mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, 
                             float(point.latitude), float(point.longitude), float(point.altitude)
                    ))
        #add dummy waypoint (to let us know we have reached the destination)
        cmds.add(Command( 0, 0, 0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, 
                          mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 0, 0, 0, 0, 0, 0, 
                          float(0), float(0), float(0)  ))
        self.engine.lastMissionCmndIndex = cmds.count
        cmds.upload()
        
        self.vehicle.mode = VehicleMode("AUTO")
        
    def land(self):
        logging.info("Landing")
        self.vehicle.channels.overrides = {}
        self.vehicle.mode = VehicleMode("LAND")

