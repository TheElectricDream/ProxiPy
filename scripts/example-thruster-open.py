import Jetson.GPIO as GPIO  
import socket
import struct
import time
import signal

# Define the 8 pins we want to use
PINS = [7, 12, 13, 15, 16, 18, 22, 23]

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

for pin in PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

try:

    for pin in PINS:
        # Set a thruster to open
        GPIO.output(pin, GPIO.HIGH)

        # Wait 0.5 seconds
        time.sleep(0.5)

        # Set a thruster to close
        GPIO.output(pin, GPIO.LOW)

except KeyboardInterrupt:
    GPIO.output(PINS[0],GPIO.LOW)
    GPIO.output(PINS[1],GPIO.LOW)
    GPIO.output(PINS[2],GPIO.LOW)
    GPIO.output(PINS[3],GPIO.LOW)
    GPIO.output(PINS[4],GPIO.LOW)
    GPIO.output(PINS[5],GPIO.LOW)
    GPIO.output(PINS[6],GPIO.LOW)
    GPIO.output(PINS[7],GPIO.LOW)
    GPIO.cleanup()
    print("\nExiting...")

finally:
    GPIO.output(PINS[0],GPIO.LOW)
    GPIO.output(PINS[1],GPIO.LOW)
    GPIO.output(PINS[2],GPIO.LOW)
    GPIO.output(PINS[3],GPIO.LOW)
    GPIO.output(PINS[4],GPIO.LOW)
    GPIO.output(PINS[5],GPIO.LOW)
    GPIO.output(PINS[6],GPIO.LOW)
    GPIO.output(PINS[7],GPIO.LOW)
    GPIO.cleanup()