import Jetson.GPIO as GPIO  
import time

# Define the pin for the pucks
PIN = 11

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

# Set default to off
GPIO.setup(PIN, GPIO.OUT)
GPIO.output(PIN, GPIO.LOW)

try:

    # Set a pucks to open
    GPIO.setup(PIN, GPIO.OUT)
    GPIO.output(PIN, GPIO.HIGH)

    while True:
        time.sleep(5)
        print("Pucks are still on, press Ctrl+C to turn off....")


except KeyboardInterrupt:

    GPIO.output(PIN,GPIO.LOW)
    print("\nExiting...")

finally:

    GPIO.output(PIN,GPIO.LOW)
    GPIO.cleanup()