#!/usr/bin/python

#==============================================================================
# PREAMBLE
#==============================================================================

import sys
import os
import socket
import struct

# Add the path to the Owl library
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

import lib.owl as owl
import csv
import datetime
import time
import numpy as np

#==============================================================================
# DEFINE PARAMETERS
#==============================================================================

# Set the IP address of the server
SERVER = '192.168.1.109'
TIMEOUT = 10000000
STREAMING = 1  # 0 to disable, 1 for UDP, 2 for TCP, 3 for TCP Broadcast
FREQUENCY = 10  # in Hz
UDP_PORT = 53673

#==============================================================================
# INITIALIZE STREAMING SERVER
#==============================================================================

# Instantiate context
owl_context = owl.Context()

# Connect to server with timeout of 10000000 microseconds
owl_context.open(SERVER, "timeout="+str(TIMEOUT))

# Initialize session
# owl_context.initialize("streaming="+str(STREAMING))  # Set to UDP
owl_context.initialize('streaming='+str(STREAMING)+' frequency='+str(FREQUENCY))  # Set to desired rate

#==============================================================================
# SET UP RIGID BODY TRACKERS
#==============================================================================

# Create the tracker for RED, BLACK, and BLUE rigid bodies
tracker_ID_RED = 0
tracker_ID_BLACK = 2
tracker_ID_BLUE = 3

# Create and define rigid tracker for RED
owl_context.createTracker(tracker_ID_RED, "rigid", "RED_rigid")
owl_context.assignMarker(tracker_ID_RED, 0, "0", "pos=125.509767,143.875167,0")
owl_context.assignMarker(tracker_ID_RED, 6, "6", "pos=125.509767,-135.624833,0")
owl_context.assignMarker(tracker_ID_RED, 4, "4", "pos=-154.990233,-135.624833,0")
owl_context.assignMarker(tracker_ID_RED, 2, "2", "pos=-153.490233,144.375167,0")

# Create and define rigid tracker for BLACK
owl_context.createTracker(tracker_ID_BLACK, "rigid", "BLACK_rigid")
owl_context.assignMarker(tracker_ID_BLACK, 13, "13", "pos=130.251807,141.800150,0")
owl_context.assignMarker(tracker_ID_BLACK, 11, "11", "pos=130.751807,-135.699850,0")
owl_context.assignMarker(tracker_ID_BLACK, 9, "9", "pos=-146.748193,-135.199850,0")
owl_context.assignMarker(tracker_ID_BLACK, 15, "15", "pos=-146.748193,143.300150,0")

# Create and define rigid tracker for BLUE
owl_context.createTracker(tracker_ID_BLUE, "rigid", "BLUE_rigid")
owl_context.assignMarker(tracker_ID_BLUE, 16, "16", "pos=140.000177,152.096588,0")
owl_context.assignMarker(tracker_ID_BLUE, 22, "22", "pos=140.500177,-125.403412,0")
owl_context.assignMarker(tracker_ID_BLUE, 20, "20", "pos=-136.999823,-124.903412,0")
owl_context.assignMarker(tracker_ID_BLUE, 18, "18", "pos=-136.999823,153.596588,0")

#==============================================================================
# START MAIN LOOP
#==============================================================================
# Start a clock
start_time = time.time()

# Initialize data for RED, BLACK, and BLUE rigid bodies
red_data = np.array([[0,0,0,0]])
black_data = np.array([[0,0,0,0]])
blue_data = np.array([[0,0,0,0]])

# Create a UDP socket
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_address = ('<broadcast>', UDP_PORT)
udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

try:
    # Create a filename based on the current datetime
    filename = datetime.datetime.now().strftime("RED_rigid_%Y%m%d_%H%M%S.csv")

    # Create an empty event
    event = None

    # Start the loop
    last_print_time = time.time()
    while event or (owl_context.isOpen() and owl_context.property("initialized")):

        # Poll for events with a timeout (microseconds)
        event = owl_context.nextEvent(1000000)

        # If nothing received, keep waiting
        if not event: continue

        # If something received, process event
        if event.type_id == owl.Type.FRAME:

            # Find any rigid bodies    
            if "rigids" in event:
                for r in event.rigids: 
                    if r.cond > 0:

                        # Save the position of the RED rigid body and attitude
                        if r.id == tracker_ID_RED:

                            # Calculate the yaw of the RED rigid body
                            q0 = r.pose[3]
                            q1 = r.pose[4]
                            q2 = r.pose[5]
                            q3 = r.pose[6]
                            yaw = np.arctan2(2.0 * (q0 * q3 + q1 * q2), 1.0 - 2.0 * (q2 * q2 + q3 * q3))

                            # Append the ECEF position and attitude of the RED rigid body
                            red_data = np.append(red_data, [[time.time()-start_time, r.pose[0], r.pose[1], yaw]], axis=0)

                            # Send the red data over UDP
                            message = struct.pack('fff', r.pose[0]/1000, r.pose[1]/1000, yaw)
                            udp_socket.sendto(message, udp_address)

                            current_time = time.time()
                            # if current_time - last_print_time >= 1/FREQUENCY:  # Print every second
                            #     print(f"Sent: {r.pose[0]}, {r.pose[1]}, {yaw}")
                            #     last_print_time = current_time
                            #print(f"Sent: {r.pose[0]}, {r.pose[1]}, {yaw}")
 
                            
                        # Save the position of the BLACK rigid body and attitude
                        if r.id == tracker_ID_BLACK:

                            # Calculate the yaw of the BLACK rigid body
                            q0 = r.pose[3]
                            q1 = r.pose[4]
                            q2 = r.pose[5]
                            q3 = r.pose[6]
                            yaw = np.arctan2(2.0 * (q0 * q3 + q1 * q2), 1.0 - 2.0 * (q2 * q2 + q3 * q3))

                            # Append the ECEF position and attitude of the BLACK rigid body
                            black_data = np.append(black_data, [[time.time()-start_time, r.pose[0], r.pose[1], yaw]], axis=0)

                        # Save the position of the BLUE rigid body and attitude
                        if r.id == tracker_ID_BLUE:

                            # Calculate the yaw of the BLUE rigid body
                            q0 = r.pose[3]
                            q1 = r.pose[4]
                            q2 = r.pose[5]
                            q3 = r.pose[6]
                            yaw = np.arctan2(2.0 * (q0 * q3 + q1 * q2), 1.0 - 2.0 * (q2 * q2 + q3 * q3))

                            # Append the ECEF position and attitude of the BLUE rigid body
                            blue_data = np.append(blue_data, [[time.time()-start_time, r.pose[0], r.pose[1], yaw]], axis=0)

            # Handle errors
            if event.name == "fatal":
                break
        
        # if time.time() - start_time > 500:
        #     break

        # Handle done event
        elif event.name == "done":
            # Done event is sent when master connection stops session
            break

        # Sleep to maintain the desired frequency
        #time.sleep(1 / FREQUENCY)

except KeyboardInterrupt:
    print("Interrupted by user. Closing connection...")

finally:
    #==============================================================================
    # CLOSE CONNECTION
    #==============================================================================

    # End session
    owl_context.done()

    # Close socket
    owl_context.close()

    # Close UDP socket
    udp_socket.close()
