#==============================================================================
# PREAMBLE
#==============================================================================

# Import system libraries
import os
import sys
import argparse

# Add the project path so that lib files can be read
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

# Import required Python libraries
import time
import numpy as np
import cProfile
import pstats

# Import custom libraries
from tools.utils import precise_delay_microsecond, class_init, create_phase_tracker, get_platform_id, handle_data_logging, enable_disable_pucks, set_platform_configuration, handle_loop_timing
from classes.Phasespace import OwlStreamProcessor
from classes.Thrusters import Thrusters
from classes.BMI160 import IMUProcessor

def main():

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run ProxiPy experiment or simulation')
    parser.add_argument('--experiment', action='store_true', help='Run in experiment mode (default: simulation mode)')
    parser.add_argument('--debug', action='store_true', help='Skip PhaseSpace but run on hardware (default: as fast as possible)')
    args = parser.parse_args()
    
    # Set experiment flag based on command line argument
    IS_EXPERIMENT = args.experiment
    IS_DEBUG = args.debug

    #IS_EXPERIMENT = True
    
    # Set these to None initially so they can be safely accessed in finally block
    streamChaser = None
    streamTarget = None
    streamObstacle = None
    imuChaser = None
    imuTarget = None
    imuObstacle = None
    thrustersChaser = None
    thrustersTarget = None
    thrustersObstacle = None
    dataContainer = None

    chaserGyroAccel = {}
    targetGyroAccel = {}
    obstacleGyroAccel = {}

    phase0_clock = 0
    phase1_clock = 0
    phase2_clock = 0
    phase3_clock = 0
    phase4_clock = 0
    phase5_clock = 0

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

        # Get the identity of the hardware
        PLATFORM = get_platform_id()

        # If this is an experiment, set the platform configuration
        if IS_EXPERIMENT:

            streamChaser, streamTarget, streamObstacle, \
                imuChaser, imuTarget, imuObstacle = set_platform_configuration(CHASER_ACTIVE, TARGET_ACTIVE, OBSTACLE_ACTIVE, \
                                                                               PLATFORM, OwlStreamProcessor, IMUProcessor)

        while True:
                
            if IS_EXPERIMENT:

                print('Waiting for valid data from PhaseSpace...')

                # Get the latest states from PhaseSpace
                if PLATFORM == 1:
                    latest_states = streamChaser.get()
                elif PLATFORM == 2:
                    latest_states = streamTarget.get()
                else:
                    print('Invalid platform selected; terminating control loop...')
                    break

                # Check that the data is valid and chaser is active
                if latest_states.get("chaser") is None and CHASER_ACTIVE:

                    # If there is no data but the chaser is active, then wait for new data
                    print('Chaser data is invalid; waiting for good data...')
                    currentLocationChaser = None
                    time.sleep(2)
                    continue

                # Check that the data is valid and target is active
                if latest_states.get("target") is None and TARGET_ACTIVE:

                    # If there is no data but the target is active, then wait for new data
                    print('Target data is invalid; waiting for good data...')
                    currentLocationTarget = None
                    time.sleep(2)
                    continue

                # Check that the data is valid and obstacle is active
                if latest_states.get("obstacle") is None and OBSTACLE_ACTIVE:

                    # If there is no data but the obstacle is active, then wait for new data
                    print('Obstacle data is invalid;  waiting for good data...')
                    currentLocationObstacle = None
                    time.sleep(2)
                    continue
                    
                
                # If this part of the loop is reached, then all data is valid
                break 

            else:
                
                # This is not an experiment, stop the loop
                break        


        # Handle GPIO logic for the thrustersChaser
        thrustersChaser = Thrusters(pwm_frequency=5, is_experiment=IS_EXPERIMENT)

        # Handle GPIO logic for the thrustersTarget
        thrustersTarget = Thrusters(pwm_frequency=5, is_experiment=IS_EXPERIMENT)

        # Handle GPIO logic for the thrustersObstacle
        thrustersObstacle = Thrusters(pwm_frequency=5, is_experiment=IS_EXPERIMENT)

        # Set the start time for the experiment
        if IS_EXPERIMENT:
            # Get the latest states from PhaseSpace
            if PLATFORM == 1:
                latest_states = streamChaser.get()
                t_init = latest_states.get("chaser")['t']
            elif PLATFORM == 2:
                latest_states = streamTarget.get()
                t_init = latest_states.get("target")['t']
            else:
                print('Invalid platform selected; terminating control loop...')
            
        else:

            # Set the start time for simulations
            t_now = 0
            t_rt = time.perf_counter()

        # Start the thrustersChaser
        thrustersChaser.start()
        thrustersTarget.start()
        thrustersObstacle.start()

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
            # HANDLE DATA FETCHING 
            #========================================#

            if IS_EXPERIMENT:

                # Get the latest states from PhaseSpace
                if PLATFORM == 1:
                    latest_states = streamChaser.get()
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
                elif PLATFORM == 2:
                    latest_states = streamTarget.get()
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
                else:
                    print('Invalid platform selected; terminating control loop...')
                    break
                
                # Get the latest IMU data
                if PLATFORM == 1:
                    chaserGyroAccel = imuChaser.get()
                    targetGyroAccel = np.array([0, 0, 0, 0, 0, 0])
                    obstacleGyroAccel = np.array([0, 0, 0, 0, 0, 0])
                elif PLATFORM == 2:
                    chaserGyroAccel = np.array([0, 0, 0, 0, 0, 0])
                    targetGyroAccel = imuTarget.get()
                    obstacleGyroAccel = np.array([0, 0, 0, 0, 0, 0])
                elif PLATFORM == 3:
                    chaserGyroAccel = np.array([0, 0, 0, 0, 0, 0])
                    targetGyroAccel = np.array([0, 0, 0, 0, 0, 0])
                    obstacleGyroAccel = imuObstacle.get()
            
                
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
                
                # Placeholder values for simulations
                chaserGyroAccel = {'gx': 0.0, 'gy': 0.0, 'gz': 0.0, 'ax': 0.0, 'ay': 0.0, 'az': 0.0}
                targetGyroAccel = {'gx': 0.0, 'gy': 0.0, 'gz': 0.0, 'ax': 0.0, 'ay': 0.0, 'az': 0.0}
                obstacleGyroAccel = {'gx': 0.0, 'gy': 0.0, 'gz': 0.0, 'ax': 0.0, 'ay': 0.0, 'az': 0.0}

            #========================================#
            # HANDLE TERMINATION CONDITIONS
            #========================================#

            # Check if the experiment duration has been reached
            if IS_EXPERIMENT:

                if PLATFORM == 1:

                    if latest_states.get("chaser")['t'] - t_init >= DURATION:
                        print('Experiment complete; terminating control loop...')
                        break

                    t_now = latest_states.get("chaser")['t']-t_init

                elif PLATFORM == 2:

                    if latest_states.get("target")['t'] - t_init >= DURATION:
                        print('Experiment complete; terminating control loop...')
                        break

                    t_now = latest_states.get("target")['t']-t_init

                elif PLATFORM == 3:

                    if latest_states.get("obstacle")['t'] - t_init >= DURATION:
                        print('Experiment complete; terminating control loop...')
                        break

                    t_now = latest_states.get("obstacle")['t']-t_init

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

                if IS_EXPERIMENT:
                    # Set the PUCKS
                    enable_disable_pucks(False)

                # Update the phase clock
                phase0_clock += PERIOD

            #----------------------------------------#
            # PHASE 1: Pucks
            #----------------------------------------#

            elif is_phase(1):

                # Define the desired location for the chaser
                desiredLocationChaser = np.array([0, 0, 0, 0, 0, 0])
                desiredLocationTarget = np.array([0, 0, 0, 0, 0, 0])
                desiredLocationObstacle = np.array([0, 0, 0, 0, 0, 0])

                if IS_EXPERIMENT:
                    # Set the PUCKS
                    enable_disable_pucks(True)

                # Update the phase clock
                phase1_clock += PERIOD

            #----------------------------------------#
            # PHASE 2: Approach
            #----------------------------------------#
            
            elif is_phase(2):

                # Define the desired location for the chaser
                # [m, m, rad, m/s, m/s, rad/s]
                desiredLocationChaser = np.array([2.2558, 1.2096, np.pi, 0.0, 0.0, 0.0])  
                
                # Define the desired location for the target
                # [m, m, rad, m/s, m/s, rad/s]
                desiredLocationTarget = np.array([1.7558, 1.2096, 0.0, 0.0, 0.0, 0.0])  

                # Define the desired location for the obstacle
                # [m, m, rad, m/s, m/s, rad/s]
                desiredLocationObstacle = np.array([1.7558, 1.2096, 0.0, 0.0, 0.0, 0.0])  

                # Update the phase clock
                phase2_clock += PERIOD
                
            #----------------------------------------#
            # PHASE 3: User Experiments
            #----------------------------------------#

            elif is_phase(3):

                # Calculate a new time for this phase that starts at zero and increments

                # Define the desired location for the chaser
                # [m, m, rad, m/s, m/s, rad/s]
                # desiredLocationChaser = np.array([1.7558, 1.7096, np.pi, 0.0, 0.0, 0.0])  
                
                # Define the desired location for the target
                # [m, m, rad, m/s, m/s, rad/s]
                
                # Set a rotation rate
                desiredAngularVelocity = 3.0 * np.pi / 180.0

                # Based on the current time, calculate the desired angle
                desiredAngle = desiredAngularVelocity * phase3_clock

                desiredLocationChaser = np.array([2.2558, 1.2096, np.pi, 0.0, 0.0, 0.0]) 

                desiredLocationTarget = np.array([1.7558, 1.2096, 0.0, 0.0, 0.0, 0.0]) 
                
                #desiredLocationTarget = np.array([1.7558, 1.2096, desiredAngle, 0.0, 0.0, desiredAngularVelocity])  
                
                # Define the desired location for the obstacle
                # [m, m, rad, m/s, m/s, rad/s]
                desiredLocationObstacle = np.array([1.7558, 0.7096, 0.0, 0.0, 0.0, 0.0])

                # Update the phase clock
                phase3_clock += PERIOD
                
            #----------------------------------------#
            # PHASE 4: Home
            #----------------------------------------#

            elif is_phase(4):

                # Define the desired location for the chaser
                # [m, m, rad, m/s, m/s, rad/s]
                desiredLocationChaser = np.array([2.2558, 1.2096, np.pi, 0.0, 0.0, 0.0]) 
                
                # Define the desired location for the target
                # [m, m, rad, m/s, m/s, rad/s]
                desiredLocationTarget = np.array([1.7558, 1.2096, 0.0, 0.0, 0.0, 0.0])  
                
                # Define the desired location for the obstacle
                # [m, m, rad, m/s, m/s, rad/s]
                desiredLocationObstacle = np.array([1.7558, 1.2096, np.pi, 0.0, 0.0, 0.0]) 

                # Update the phase clock
                phase4_clock += PERIOD
                
            #----------------------------------------#
            # PHASE 5: Shutdown
            #----------------------------------------#

            elif is_phase(5):

                # Define the desired location for the chaser
                desiredLocationChaser = np.array([0, 0, 0, 0, 0, 0])
                desiredLocationTarget = np.array([0, 0, 0, 0, 0, 0])
                desiredLocationObstacle = np.array([0, 0, 0, 0, 0, 0])

                if IS_EXPERIMENT:
                    # Set the PUCKS
                    enable_disable_pucks(False)

                # Update the phase clock
                phase5_clock += PERIOD
        
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

                # Compute saturated duty cycle
                chaserControl.compute_saturated_control_signal(attitude = latest_states.get("chaser")['att'])

                if IS_EXPERIMENT:

                    if PLATFORM == 1:
                        thrustersChaser.set_all_duty_cycles(chaserControl.dutyCycle.tolist())

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
                    
                    if PLATFORM == 2:
                        thrustersTarget.set_all_duty_cycles(targetControl.dutyCycle.tolist())


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

                    if PLATFORM == 3:
                        thrustersObstacle.set_all_duty_cycles(obstacleControl.dutyCycle.tolist())

                else:
                    
                    # Update the model in simulation
                    obstacleModel.apply_force(obstacleControl.saturatedControlSignal[:2], obstacleControl.saturatedControlSignal[2])
                    obstacleModel.update(PERIOD)

            #========================================#
            # HANDLE DATA STORAGE
            #========================================#

            handle_data_logging(t_now, latest_states, chaserControl, thrustersChaser, targetControl, thrustersTarget, obstacleControl, thrustersObstacle, chaserGyroAccel, targetGyroAccel, obstacleGyroAccel, dataContainer, CHASER_ACTIVE, TARGET_ACTIVE, OBSTACLE_ACTIVE)
            
            #========================================#
            # HANDLE LOOP SLEEP CONDITIONS
            #========================================#

            t_now = handle_loop_timing(t_now, t_rt, latest_states, PERIOD, IS_EXPERIMENT, PLATFORM, IS_REALTIME)

        #========================================#
        # HANDLE SHUTDOWN
        #========================================#       

        if IS_EXPERIMENT:

            # Stop the background data stream gracefully
            if PLATFORM == 1:
                streamChaser.stop()
                imuChaser.stop()
            elif PLATFORM == 2:
                streamTarget.stop()
                imuTarget.stop()
            elif PLATFORM == 3:
                streamObstacle.stop()
                imuObstacle.stop()

            # Ensure the pucks are off
            enable_disable_pucks(False)

        # Stop the thrustersChaser
        thrustersChaser.stop()  # Clean shutdown    
        thrustersTarget.stop()  # Clean shutdown
        thrustersObstacle.stop()  # Clean shutdown        
                        
        # Export the data
        print('Exporting data container to /data/ directory...')

        dataContainer.write_to_npy()

    except KeyboardInterrupt:
        print("Program interrupted by user")
    finally:
        print('Program completed...')

    # except KeyboardInterrupt:
    #     print("Program interrupted by user")
    # except Exception as e:
    #     print(f"Exception occurred: {e}")
    # finally:
    #     print("Executing cleanup operations...")
        
    #     # Ensure data is saved
    #     try:
    #         if dataContainer:
    #             print("Saving data...")
    #             dataContainer.write_to_npy()
    #             print("Data saved successfully")
    #     except Exception as e:
    #         print(f"Failed to write data: {e}")
            
    #     # Ensure pucks are disabled
    #     try:
    #         print("Disabling pucks...")
    #         if IS_EXPERIMENT:
    #             # Set the PUCKS
    #             enable_disable_pucks(False)
    #         print("Pucks disabled")
    #     except Exception as e:
    #         print(f"Failed to disable pucks: {e}")
            
    #     # Shutdown hardware resources
    #     try:
    #         if IS_EXPERIMENT and stream_processor:
    #             stream_processor.stop()
    #         if IS_EXPERIMENT and imu_processor:
    #             imu_processor.stop()
    #     except Exception as e:
    #         print(f"Failed to stop processors: {e}")
            
    #     # Stop thrusters
    #     try:
    #         if thrustersChaser:
    #             thrustersChaser.stop()
    #         if thrustersTarget:
    #             thrustersTarget.stop()
    #         if thrustersObstacle:
    #             thrustersObstacle.stop()
    #         print("Thrusters stopped")
    #     except Exception as e:
    #         print(f"Failed to stop thrusters: {e}")
            
    #     print("Cleanup complete")



if __name__ == '__main__':
    main()  # Run the main function which handles command line arguments
    
    # Uncomment below for profiling if needed
    # profiler = cProfile.Profile()
    # profiler.enable()
    # main()
    # profiler.disable()
    # stats = pstats.Stats(profiler).sort_stats('cumulative')
    # stats.print_stats(100)  # Print the 100 slowest functions