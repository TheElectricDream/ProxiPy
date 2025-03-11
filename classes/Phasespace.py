#!/usr/bin/python

import time
import numpy as np
import threading
import lib.owl as owl

class OwlStreamProcessor:
    """
    This class encapsulates the setup and streaming of rigid body data from the Owl system.
    
    It initializes the server and rigid body trackers, and starts a background thread that
    continuously processes incoming events. The latest state for each rigid body can be
    retrieved using the `get()` method.
    """
    def __init__(self, TIMEOUT, STREAMING, FREQUENCY, SERVER, mode='master'):
        """
        Initializes the Owl stream processor.

        Args:
            TIMEOUT (int): Timeout value for connecting to the server.
            STREAMING (str): Streaming mode (e.g., "UDP").
            FREQUENCY (int): Desired streaming frequency.
            SERVER (str): Server address.
            mode (str): Mode of operation, either 'master' or 'slave'.
        """
        self.mode = mode
        # Initialize Owl context (server)
        self.owl_context = self._initialize_server(TIMEOUT, STREAMING, FREQUENCY, SERVER, mode)
        
        # Set up rigid body trackers and get their IDs
        self.tracker_ID_CHASER, self.tracker_ID_TARGET, self.tracker_ID_OBSTACLE = self._initialize_rigid_bodies(self.owl_context)
        
        # Dictionary to hold the latest state data for each rigid body
        self.states = {"chaser": None, "target": None, "obstacle": None}
        self.prev_states = {"chaser": None, "target": None, "obstacle": None}  # To store previous measurements
        self.lock = threading.Lock()  # For thread-safe access to self.states
        
        # Event to signal thread termination
        self._stop_event = threading.Event()
        
        # Start the data streaming in a background thread
        self.thread = threading.Thread(target=self._execute_data_stream, daemon=True)
        self.thread.start()


    def _initialize_server(self, TIMEOUT, STREAMING, FREQUENCY, SERVER, mode):
        """
        Initializes and returns an Owl context connected to the server.

        Args:
            TIMEOUT (int): Timeout value in microseconds.
            STREAMING (str): Streaming mode.
            FREQUENCY (int): Desired streaming frequency.
            SERVER (str): Server address.
            mode (str): Mode of operation, either 'master' or 'slave'.

        Returns:
            owl.Context: The initialized Owl context.
        """
        owl_context = owl.Context()
        owl_context.open(SERVER, "timeout=" + str(TIMEOUT))
        if mode == 'master':
            owl_context.initialize('streaming=' + str(STREAMING) + ' frequency=' + str(FREQUENCY))
        elif mode == 'slave':
            owl_context.initialize('streaming=' + str(STREAMING) + ' frequency=' + str(FREQUENCY) + ' slave=1')
        return owl_context

    def _initialize_rigid_bodies(self, owl_context):
        """
        Creates and configures the rigid body trackers.

        Args:
            owl_context (owl.Context): The Owl context.

        Returns:
            tuple: Tracker IDs for RED, BLACK, and BLUE.
        """
        tracker_ID_CHASER = 0
        tracker_ID_TARGET = 2
        tracker_ID_OBSTACLE = 3

        # Define RED rigid body
        owl_context.createTracker(tracker_ID_CHASER, "rigid", "CHASER_rigid")
        owl_context.assignMarker(tracker_ID_CHASER, 0, "0", "pos=125.509767,143.875167,0")
        owl_context.assignMarker(tracker_ID_CHASER, 6, "6", "pos=125.509767,-135.624833,0")
        owl_context.assignMarker(tracker_ID_CHASER, 4, "4", "pos=-154.990233,-135.624833,0")
        owl_context.assignMarker(tracker_ID_CHASER, 2, "2", "pos=-153.490233,144.375167,0")

        # Define BLACK rigid body
        owl_context.createTracker(tracker_ID_TARGET, "rigid", "TARGET_rigid")
        owl_context.assignMarker(tracker_ID_TARGET, 13, "13", "pos=130.251807,141.800150,0")
        owl_context.assignMarker(tracker_ID_TARGET, 11, "11", "pos=130.751807,-135.699850,0")
        owl_context.assignMarker(tracker_ID_TARGET, 9, "9", "pos=-146.748193,-135.199850,0")
        owl_context.assignMarker(tracker_ID_TARGET, 15, "15", "pos=-146.748193,143.300150,0")

        # Define BLUE rigid body
        owl_context.createTracker(tracker_ID_OBSTACLE, "rigid", "OBSTACLE_rigid")
        owl_context.assignMarker(tracker_ID_OBSTACLE, 16, "16", "pos=140.000177,152.096588,0")
        owl_context.assignMarker(tracker_ID_OBSTACLE, 22, "22", "pos=140.500177,-125.403412,0")
        owl_context.assignMarker(tracker_ID_OBSTACLE, 20, "20", "pos=-136.999823,-124.903412,0")
        owl_context.assignMarker(tracker_ID_OBSTACLE, 18, "18", "pos=-136.999823,153.596588,0")

        return tracker_ID_CHASER, tracker_ID_TARGET, tracker_ID_OBSTACLE

    def _execute_data_stream(self):
        """
        Runs in a background thread to continuously poll and process incoming events.

        It updates the state of each rigid body (CHASER, TARGET, OBSTACLE) with the latest position,
        computed yaw angle, and calculates the translational velocity and angular velocity.
        """
        try:
            event = None
            while not self._stop_event.is_set() and (self.owl_context.isOpen() and self.owl_context.property("initialized")):
                # Poll for an event with a 1-second timeout (in microseconds)
                event = self.owl_context.nextEvent(1000000)
                if not event:
                    continue

                if event.type_id == owl.Type.FRAME and "rigids" in event:
                    for r in event.rigids:
                        if r.cond > 0:
                            # Compute yaw from the quaternion (q0, q1, q2, q3)
                            q0, q1, q2, q3 = r.pose[3:7]
                            yaw = np.arctan2(2.0 * (q0 * q3 + q1 * q2),
                                            1.0 - 2.0 * (q2 * q2 + q3 * q3))
                            # Determine which rigid body this measurement belongs to
                            key = None
                            if r.id == self.tracker_ID_CHASER:
                                key = "chaser"
                            elif r.id == self.tracker_ID_TARGET:
                                key = "target"
                            elif r.id == self.tracker_ID_OBSTACLE:
                                key = "obstacle"
                            
                            if key is not None:
                                # Get the current time for delta calculations
                                current_time = time.perf_counter()
                                # Current measurement: [x, y, yaw]
                                current_data = np.array([r.pose[0], r.pose[1], yaw])
                                
                                # Retrieve previous state for this rigid body (if any)
                                prev = self.prev_states.get(key)
                                if prev is None:
                                    # First measurement; velocity values are zero
                                    vel = np.array([0.0, 0.0])
                                    omega = 0.0
                                else:
                                    dt = current_time - prev["time"]
                                    if dt > 0:
                                        vel = (current_data[:2] - prev["pos"][:2]) / dt
                                        omega = (current_data[2] - prev["pos"][2]) / dt
                                    else:
                                        vel = np.array([0.0, 0.0])
                                        omega = 0.0
                                
                                # Update previous state with current measurement and time
                                self.prev_states[key] = {"pos": current_data, "time": current_time}
                                
                                # Update the state dictionary in a thread-safe manner
                                with self.lock:
                                    self.states[key] = {
                                        "pos": current_data[:2]/1000,  # [x, y]
                                        "att": current_data[2],   # yaw angle
                                        "vel": vel/1000,               # [vx, vy]
                                        "omega": omega            # angular velocity (ω)
                                    }
        except KeyboardInterrupt:
            print("Interrupted by user. Closing connection...")
        finally:
            self.owl_context.done()
            self.owl_context.close()


    def get(self):
        """
        Returns the latest state for each rigid body.

        Returns:
            dict: A copy of the dictionary containing the latest data for "red", "black", and "blue".
        """
        with self.lock:
            return self.states.copy()

    def stop(self):
        """
        Signals the background thread to stop and waits for it to terminate.
        """
        self._stop_event.set()
        self.thread.join()
