# Servo Control
import time, threading, logging
import wiringpi

servoPIN = 18 #only works on this GPIO PIN

# use 'GPIO naming'
wiringpi.wiringPiSetupGpio()

# set #18 to be a PWM output
wiringpi.pinMode(servoPIN, wiringpi.GPIO.PWM_OUTPUT)

# set the PWM mode to milliseconds type
wiringpi.pwmSetMode(wiringpi.GPIO.PWM_MODE_MS)

# divide down clock
wiringpi.pwmSetClock(192)
wiringpi.pwmSetRange(2000)

# value for pwm 60 - 230, in:   wiringpi.pwmWrite([pin value], [pwm value])

class ServoController (threading.Thread):
   def __init__(self, startAngle):
      threading.Thread.__init__(self)
      self.daemon = True
      self.servoAngle = startAngle
      self.delay_period = 0.01
      
   def setAngle(self, angle):
       self.servoAngle = angle
   
   def run(self):
      while(True):
          try:
              wiringpi.pwmWrite(servoPIN, self.servoAngle)
              time.sleep(self.delay_period) 
          except Exception as e:
              logging.error(str(e))
              break
 
