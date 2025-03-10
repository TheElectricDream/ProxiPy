
#==============================================================================
# PREAMBLE
#==============================================================================

# Import system libraries
import os
import sys

# Add the project path so that lib files can be read
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

# Import required Python libraries
import time
import numpy as np
import cProfile
import pstats

# Import custom libraries
from tools.utils import precise_delay_microsecond, class_init, create_phase_tracker, get_platform_id, get_current_locations_exp
from classes.Phasespace import OwlStreamProcessor
from classes.Thrusters import Thrusters


def main():

    try:
        print('Setting initial control loop parameters...')

        # Set loop parameters
        SAMPLERATE = 20  # Hz
        PERIOD = 1 / SAMPLERATE  # seconds

        # Set phase durations 
        phases = {}
        phases['PHASE_0_DURATION'] = 5  # seconds
        phases['PHASE_1_DURATION'] = 5  # seconds
        phases['PHASE_2_DURATION'] = 40  # seconds
        phases['PHASE_3_DURATION'] = 170  # seconds
        phases['PHASE_4_DURATION'] = 30  # seconds
        phases['PHASE_5_DURATION'] = 20  # seconds

        # Calculate duration of the experiment
        DURATION = sum([phases[key] for key in phases.keys()])

        # Create a phase tracker
        track_phase, is_phase = create_phase_tracker(phases)

        # Set experiment parameters
        IS_EXPERIMENT = False

        # Set simulation parameters
        IS_REALTIME = False

        # Set active platforms
        CHASER_ACTIVE = True
        TARGET_ACTIVE = True
        OBSTACLE_ACTIVE = False

        print('Importing JSON configuration files...')

        # Initializations of the spacecraft and controller classes
        chaserModel, targetModel, obstacleModel, \
        chaserControl, targetControl, obstacleControl, \
        dataContainer, chaser_params, target_params, \
        obstacle_params = class_init(PERIOD)

        if IS_EXPERIMENT:

            # Set phasespace parameters
            SERVER = '192.168.1.109'
            TIMEOUT = 10000000      # in microseconds
            STREAMING = 1           # 0 to disable, 1 for UDP, 2 for TCP, 3 for TCP Broadcast
            PS_FREQUENCY = 10       # in Hz

            print('Starting up PhaseSpace system for real-time pose data...')

            # Create an instance of OwlStreamProcessor.
            # This will initialize the server, set up the rigid bodies, and start the background thread.
            stream_processor = OwlStreamProcessor(TIMEOUT, STREAMING, PS_FREQUENCY, SERVER)

        # Handle GPIO logic for the thrusters
        thrusters = Thrusters()
        thrusters = Thrusters(pwm_frequency=5, is_experiment=IS_EXPERIMENT)

        # Set the start time for the experiment
        t_init = time.perf_counter()

        # Set the start time for simulations
        t_now = 0
        t_rt = time.perf_counter()

        # Get the identity of the hardware
        PLATFORM = get_platform_id()

        # Start the thrusters
        thrusters.start()

        # Check if the experiment duration has been reached
        if IS_EXPERIMENT:
            print('Experiment mode has been selected; Experiment running in REAL-TIME...')

        else:

            if IS_REALTIME:
                print('Simulation mode has been selected; Simulation running in REAL-TIME...')
            else:
                print('Simulation mode has been selected; Simulation running AS FAST AS POSSIBLE...')

        while True:

            #========================================#
            # HANDLE TERMINATION CONDITIONS
            #========================================#

            # Check if the experiment duration has been reached
            if IS_EXPERIMENT:

                if time.perf_counter() - t_init >= DURATION:
                    print('Experiment complete; terminating control loop...')
                    break

                t_now = time.perf_counter()-t_init

            else:

                if t_now >= DURATION:
                    print('Simulation complete; terminating control loop...')
                    break

                if IS_REALTIME:

                    # Set the real-time 
                    t_rt = time.perf_counter() 

            #========================================#
            # HANDLE PHASE TRANSITIONS
            #========================================#

            track_phase(t_now)

            #========================================#
            # MAIN LOOP PROCESSING 
            #========================================#

            if IS_EXPERIMENT:

                # Get the latest states from the PhaseSpace system
                currentLocationChaser, currentLocationTarget, currentLocationObstacle, t_init, skip_loop = get_current_locations_exp(stream_processor)

                if skip_loop:
                    pass

                
            else:

                # Get the latest states from all models
                latest_states_chaser = chaserModel.get()
                latest_states_target = targetModel.get()
                latest_states_obstacle = obstacleModel.get()

                # Create a latest_states variable to mimic the PhaseSpace data structure
                latest_states = {
                    "chaser": latest_states_chaser.get("chaser"),
                    "target": latest_states_target.get("target"),
                    "obstacle": latest_states_obstacle.get("obstacle")
                }

                # Get the current location for each spacecraft
                currentLocationChaser = np.array([latest_states.get("chaser")['pos'][0],
                                                    latest_states.get("chaser")['pos'][1],
                                                    latest_states.get("chaser")['att'],
                                                    latest_states.get("chaser")['vel'][0],
                                                    latest_states.get("chaser")['vel'][1],
                                                    latest_states.get("chaser")['omega']])

                currentLocationTarget = np.array([latest_states.get("target")['pos'][0],
                                                latest_states.get("target")['pos'][1],
                                                latest_states.get("target")['att'],
                                                latest_states.get("target")['vel'][0],
                                                latest_states.get("target")['vel'][1],
                                                latest_states.get("target")['omega']])

                currentLocationObstacle = np.array([latest_states.get("obstacle")['pos'][0],
                                                    latest_states.get("obstacle")['pos'][1],
                                                    latest_states.get("obstacle")['att'],
                                                    latest_states.get("obstacle")['vel'][0],
                                                    latest_states.get("obstacle")['vel'][1],
                                                    latest_states.get("obstacle")['omega']])

            #========================================#
            # HANDLE MAIN PHASE LOGIC
            #========================================#

            #----------------------------------------#
            # PHASE 0: Initialization
            #----------------------------------------#

            if is_phase(0):

                # Define the desired location for the chaser
                desiredLocationChaser = np.array([0, 0, 0, 0, 0, 0])
                desiredLocationTarget = np.array([0, 0, 0, 0, 0, 0])
                desiredLocationObstacle = np.array([0, 0, 0, 0, 0, 0])

                # Set the PUCKS
                # [WRITE A METHOD TO TURN OFF THE PUCKS]

            #----------------------------------------#
            # PHASE 1: Pucks
            #----------------------------------------#

            elif is_phase(1):

                # Define the desired location for the chaser
                desiredLocationChaser = np.array([0, 0, 0, 0, 0, 0])
                desiredLocationTarget = np.array([0, 0, 0, 0, 0, 0])
                desiredLocationObstacle = np.array([0, 0, 0, 0, 0, 0])

                # Set the PUCKS
                # [WRITE A METHOD TO TURN ON THE PUCKS]

            #----------------------------------------#
            # PHASE 2: Approach
            #----------------------------------------#
            
            elif is_phase(2):

                # Define the desired location for the chaser
                desiredLocationChaser = np.array([chaser_params['CHASER_INIT'][0],
                                                    chaser_params['CHASER_INIT'][1],
                                                    chaser_params['CHASER_INIT'][2],
                                                    0,
                                                    0,
                                                    0])
                
                # Define the desired location for the target
                desiredLocationTarget = np.array([target_params['TARGET_INIT'][0],
                                                    target_params['TARGET_INIT'][1],
                                                    target_params['TARGET_INIT'][2],
                                                    0,
                                                    0,
                                                    0])
                
                # Define the desired location for the obstacle
                desiredLocationObstacle = np.array([obstacle_params['OBSTACLE_INIT'][0],
                                                    obstacle_params['OBSTACLE_INIT'][1],
                                                    obstacle_params['OBSTACLE_INIT'][2],
                                                    0,
                                                    0,
                                                    0])
                
            #----------------------------------------#
            # PHASE 3: User Experiments
            #----------------------------------------#

            elif is_phase(3):

                # Define the desired location for the chaser
                desiredLocationChaser = np.array([chaser_params['CHASER_INIT'][0],
                                                    chaser_params['CHASER_INIT'][1],
                                                    chaser_params['CHASER_INIT'][2],
                                                    0,
                                                    0,
                                                    0])
                
                # Define the desired location for the target
                desiredLocationTarget = np.array([target_params['TARGET_INIT'][0],
                                                    target_params['TARGET_INIT'][1],
                                                    target_params['TARGET_INIT'][2],
                                                    0,
                                                    0,
                                                    0])
                
                # Define the desired location for the obstacle
                desiredLocationObstacle = np.array([obstacle_params['OBSTACLE_INIT'][0],
                                                    obstacle_params['OBSTACLE_INIT'][1],
                                                    obstacle_params['OBSTACLE_INIT'][2],
                                                    0,
                                                    0,
                                                    0])
                
            #----------------------------------------#
            # PHASE 4: Home
            #----------------------------------------#

            elif is_phase(4):

                # Define the desired location for the chaser
                desiredLocationChaser = np.array([chaser_params['CHASER_HOME'][0],
                                                    chaser_params['CHASER_HOME'][1],
                                                    chaser_params['CHASER_HOME'][2],
                                                    0,
                                                    0,
                                                    0])
                
                # Define the desired location for the target
                desiredLocationTarget = np.array([target_params['TARGET_HOME'][0],
                                                    target_params['TARGET_HOME'][1],
                                                    target_params['TARGET_HOME'][2],
                                                    0,
                                                    0,
                                                    0])
                
                # Define the desired location for the obstacle
                desiredLocationObstacle = np.array([obstacle_params['OBSTACLE_HOME'][0],
                                                    obstacle_params['OBSTACLE_HOME'][1],
                                                    obstacle_params['OBSTACLE_HOME'][2],
                                                    0,
                                                    0,
                                                    0])
                
            #----------------------------------------#
            # PHASE 5: Shutdown
            #----------------------------------------#

            elif is_phase(5):

                # Define the desired location for the chaser
                desiredLocationChaser = np.array([0, 0, 0, 0, 0, 0])
                desiredLocationTarget = np.array([0, 0, 0, 0, 0, 0])
                desiredLocationObstacle = np.array([0, 0, 0, 0, 0, 0])

                # Set the PUCKS
                # [WRITE A METHOD TO TURN OFF THE PUCKS]
        
            #========================================#
            # HANDLE CONTROL LOGIC
            #========================================#
            # The control logic will never change.
            # It is simply disabled for certain phases and enabled for others
                
            # For all phases other then 0, 1, and 5, enable control 
            if is_phase(0) or is_phase(1) or is_phase(5):
                chaserControl.enable_control = False
                targetControl.enable_control = False
                obstacleControl.enable_control = False
            else:
                chaserControl.enable_control = True
                targetControl.enable_control = True
                obstacleControl.enable_control = True

            #----------------------------------------#
            # CHASER CONTROL
            #----------------------------------------#

            if CHASER_ACTIVE:

                # Compute the control input 
                chaserControl.compute_control(state = currentLocationChaser, 
                                            target = desiredLocationChaser)
                
                chaserControl.compute_control_body_frame(attitude = latest_states.get("chaser")['att'])

                # Computer the duty cycle
                chaserControl.compute_duty_cycle()

                # Apply the control signal to the thrusters
                thrusters.set_all_duty_cycles(chaserControl.dutyCycle.tolist())

                # Compute saturated duty cycle
                chaserControl.compute_saturated_control_signal(attitude = latest_states.get("chaser")['att'])

                if IS_EXPERIMENT:

                    pass

                else:

                    # Update the model in simulation
                    chaserModel.apply_force(chaserControl.saturatedControlSignal[:2], chaserControl.saturatedControlSignal[2])
                    chaserModel.update(PERIOD)

            #----------------------------------------#
            # TARGET CONTROL
            #----------------------------------------#

            if TARGET_ACTIVE:

                # Compute the control input
                targetControl.compute_control(state = currentLocationTarget,
                                                target = desiredLocationTarget)
                
                targetControl.compute_control_body_frame(attitude = latest_states.get("target")['att'])

                # Computer the duty cycle
                targetControl.compute_duty_cycle()

                # Compute saturated duty cycle
                targetControl.compute_saturated_control_signal(attitude = latest_states.get("target")['att'])

                if IS_EXPERIMENT:
                    
                    pass

                else:

                    # Update the model in simulation
                    targetModel.apply_force(targetControl.saturatedControlSignal[:2], targetControl.saturatedControlSignal[2])
                    targetModel.update(PERIOD)

            #----------------------------------------#
            # OBSTACLE CONTROL
            #----------------------------------------#

            if OBSTACLE_ACTIVE:

                # Compute the control input
                obstacleControl.compute_control(state = currentLocationObstacle,
                                                target = desiredLocationObstacle)
                
                obstacleControl.compute_control_body_frame(attitude = latest_states.get("obstacle")['att'])

                # Computer the duty cycle
                obstacleControl.compute_duty_cycle()

                # Compute saturated duty cycle
                obstacleControl.compute_saturated_control_signal(attitude = latest_states.get("obstacle")['att'])

                if IS_EXPERIMENT:

                    pass

                else:
                    
                    # Update the model in simulation
                    obstacleModel.apply_force(obstacleControl.saturatedControlSignal[:2], obstacleControl.saturatedControlSignal[2])
                    obstacleModel.update(PERIOD)

            #========================================#
            # HANDLE DATA STORAGE
            #========================================#

            # Instead of multiple individual appends:
            batch_data = {
                'Time (s)': t_now,
                'Chaser Px (m)': latest_states.get("chaser")['pos'][0],
                'Chaser Py (m)': latest_states.get("chaser")['pos'][1],
                'Chaser Rz (rad)': latest_states.get("chaser")['att'],
                'Chaser Vx (m/s)': latest_states.get("chaser")['vel'][0],
                'Chaser Vy (m/s)': latest_states.get("chaser")['vel'][1],
                'Chaser Wz (rad/s)': latest_states.get("chaser")['omega'],
                'Chaser Duty Cycle [1]': chaserControl.dutyCycle[0],
                'Chaser Duty Cycle [2]': chaserControl.dutyCycle[1],
                'Chaser Duty Cycle [3]': chaserControl.dutyCycle[2],
                'Chaser Duty Cycle [4]': chaserControl.dutyCycle[3],
                'Chaser Duty Cycle [5]': chaserControl.dutyCycle[4],
                'Chaser Duty Cycle [6]': chaserControl.dutyCycle[5],
                'Chaser Duty Cycle [7]': chaserControl.dutyCycle[6],
                'Chaser Duty Cycle [8]': chaserControl.dutyCycle[7],
                'Chaser PWM [1]': thrusters.get_state(1),
                'Chaser PWM [2]': thrusters.get_state(2),
                'Chaser PWM [3]': thrusters.get_state(3),
                'Chaser PWM [4]': thrusters.get_state(4),
                'Chaser PWM [5]': thrusters.get_state(5),
                'Chaser PWM [6]': thrusters.get_state(6),
                'Chaser PWM [7]': thrusters.get_state(7),
                'Chaser PWM [8]': thrusters.get_state(8)
            }
            dataContainer.append_data_batch(batch_data)
            
            #========================================#
            # HANDLE LOOP SLEEP CONDITIONS
            #========================================#

            if IS_EXPERIMENT:

                # Calculate elapsed time and determine sleep time for consistent loop timing
                t_elapsed = time.perf_counter() - t_now
                sleep_time = PERIOD - t_elapsed

                if sleep_time > 0:
                    if sleep_time > 0.001:  # if sleep time is greater than 1 ms, use time.sleep
                        time.sleep(sleep_time - 0.001)
                    precise_delay_microsecond((sleep_time % 0.001) * 1e6)

            else:

                t_now += PERIOD

                if IS_REALTIME:

                    # Calculate the time to sleep
                    t_elapsed = time.perf_counter() - t_rt
                    sleep_time = PERIOD - t_elapsed

                    # Handle the loop timing to ensure a consistent loop rate
                    if sleep_time > 0:
                        if sleep_time > 0.001:
                            time.sleep(sleep_time - 0.001)
                        precise_delay_microsecond((sleep_time % 0.001) * 1e6)


        if IS_EXPERIMENT:

            # Stop the background data stream gracefully
            stream_processor.stop()

        # Stop the thrusters
        thrusters.stop()  # Clean shutdown            
                        
        # Export the data
        #print('Exporting data container to /data/ directory...')


    except KeyboardInterrupt:
        try:
            dataContainer.write_to_npy()
        except:
            print('Failed to write data...')
    finally:
        try:
            dataContainer.write_to_npy()
        except:
            print('Failed to write data...')




if __name__ == '__main__':
    # profiler = cProfile.Profile()
    # profiler.enable()
    main()  # Run the code you want to profile
    # profiler.disable()

    # # Create a Stats object and sort the results
    # stats = pstats.Stats(profiler).sort_stats('cumulative')
    # stats.print_stats(100)  # Print the 10 slowest functions