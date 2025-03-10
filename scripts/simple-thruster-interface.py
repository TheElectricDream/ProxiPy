import Jetson.GPIO as GPIO  
import socket
import struct
import time
import signal
import select

# Define the 8 pins we want to use
PINS = [7, 12, 13, 15, 16, 18, 22, 23]

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

for pin in PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

# UDP setup
IP_ADDRESS = '127.0.0.1'
PORT = 48291
NUM_DOUBLES = 10

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = (IP_ADDRESS, PORT)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(server_address)
server_socket.setblocking(0)

def signal_handler(sig, frame):
    raise KeyboardInterrupt

signal.signal(signal.SIGTERM, signal_handler)

SAFETY_BIT = 568471
duty_cycles = [0] * len(PINS)
pwm_frequency = 5  # Default to 5Hz
period_duration = 1 / pwm_frequency

# Initialize timestamps and states for each pin
pin_states = [GPIO.LOW] * len(PINS)
period_start_time = time.time()

try:
    while True:
        current_time = time.time()

        # Check if the current PWM cycle should start
        if current_time - period_start_time >= period_duration:
            period_start_time += period_duration

        time_in_period = current_time - period_start_time

        # Ensure that the time in period is within a reasonable range
        if time_in_period < 0:
            time_in_period = 0
        elif time_in_period >= period_duration:
            time_in_period = period_duration - 1e-6

        # Update pin states based on duty cycle
        for i, pin in enumerate(PINS):
            high_time = (duty_cycles[i] / 100) * period_duration
            if time_in_period < high_time:
                desired_state = GPIO.HIGH
            else:
                desired_state = GPIO.LOW

            if pin_states[i] != desired_state:
                GPIO.output(pin, desired_state)
                pin_states[i] = desired_state

        # Use select to check for available data without blocking
        readable, _, _ = select.select([server_socket], [], [], 0)
        
        if readable:
            # Drain all available packets, keeping only the most recent
            latest_data = None
            while True:
                try:
                    # Attempt to read the next packet
                    more_data, client_address = server_socket.recvfrom(NUM_DOUBLES * 8)
                    latest_data = more_data
                except BlockingIOError:
                    # No more data available
                    break
            
            # Process only the most recent packet
            if latest_data is not None and len(latest_data) == NUM_DOUBLES * 8:
                doubles = struct.unpack('d' * NUM_DOUBLES, latest_data)
                if int(doubles[0]) == SAFETY_BIT:
                    pwm_frequency = doubles[1]
                    period_duration = 1 / pwm_frequency
                    duty_cycles = list(doubles[2:10])

except KeyboardInterrupt:
    for pin in PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
    server_socket.close()
    print("\nExiting...")

finally:
    for pin in PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
    server_socket.close()