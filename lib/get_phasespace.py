#!/usr/bin/python

#==============================================================================
# PREAMBLE
#==============================================================================

import sys
import os

# Add the path to the Owl library
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

import lib.owl as owl
import datetime
import time
import numpy as np

#==============================================================================
# INITIALIZE STREAMING SERVER
#==============================================================================

def initialize_server(TIMEOUT, STREAMING, FREQUENCY, SERVER):
    """
    Initializes the streaming server and sets up the rigid body trackers.

    Args:
        None

    Returns:
        owl.Context: The Owl context object.
    """

    # Instantiate context
    owl_context = owl.Context()

    # Connect to server with timeout of 10000000 microseconds
    owl_context.open(SERVER, "timeout="+str(TIMEOUT))

    # Initialize session
    # owl_context.initialize("streaming="+str(STREAMING))  # Set to UDP
    owl_context.initialize('streaming='+str(STREAMING)+' frequency='+str(FREQUENCY))  # Set to desired rate

    return owl_context

#==============================================================================
# SET UP RIGID BODY TRACKERS
#==============================================================================

def initialize_rigid_bodies(owl_context):

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

    return tracker_ID_RED, tracker_ID_BLACK, tracker_ID_BLUE, owl_context

#==============================================================================
# MAIN DATA GETTER
#==============================================================================

def get_latest_states(owl_context, tracker_ID_RED, tracker_ID_BLACK, tracker_ID_BLUE):

    try:

        # Create an empty event
        event = None

        # Start the loop
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
                                red_data = np.array([[r.pose[0], r.pose[1], yaw]])  
                                
                            # Save the position of the BLACK rigid body and attitude
                            if r.id == tracker_ID_BLACK:

                                # Calculate the yaw of the BLACK rigid body
                                q0 = r.pose[3]
                                q1 = r.pose[4]
                                q2 = r.pose[5]
                                q3 = r.pose[6]
                                yaw = np.arctan2(2.0 * (q0 * q3 + q1 * q2), 1.0 - 2.0 * (q2 * q2 + q3 * q3))

                                # Append the ECEF position and attitude of the BLACK rigid body
                                black_data = np.array([[r.pose[0], r.pose[1], yaw]]) 

                            # Save the position of the BLUE rigid body and attitude
                            if r.id == tracker_ID_BLUE:

                                # Calculate the yaw of the BLUE rigid body
                                q0 = r.pose[3]
                                q1 = r.pose[4]
                                q2 = r.pose[5]
                                q3 = r.pose[6]
                                yaw = np.arctan2(2.0 * (q0 * q3 + q1 * q2), 1.0 - 2.0 * (q2 * q2 + q3 * q3))

                                # Append the ECEF position and attitude of the BLUE rigid body
                                blue_data = np.array([[r.pose[0], r.pose[1], yaw]]) 

                return red_data, black_data, blue_data
            

    except KeyboardInterrupt:
        print("Interrupted by user. Closing connection...")

# finally:
#     #==============================================================================
#     # CLOSE CONNECTION
#     #==============================================================================

#     # End session
#     owl_context.done()

#     # Close socket
#     owl_context.close()

#     # Close UDP socket
#     udp_socket.close()
