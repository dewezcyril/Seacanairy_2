import serial  # install libraries
import time
import RPi.GPIO as GPIO

ser = serial.Serial("/dev/serial0", 9600)
GPIO.setmode(GPIO.BCM)
GPIO.setup(25, GPIO.IN)

last_value = 0

ser.flush()

while True:
    reading = ser.read_all()
    reading = str(reading,'utf-8')
    print(reading)
    ser.flush
    time.sleep(.99)
