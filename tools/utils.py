from time import perf_counter_ns
import numpy as np
import json
from classes.Spacecraft import Spacecraft
from classes.Controllers import LinearQuadraticRegulator
from classes.Storage import Storage
import getpass
import time

try:
    import Jetson.GPIO as GPIO
except ImportError:
    print('Unable to import Jetson.GPIO, running in simulation mode.')

def enable_disable_pucks(enable=False):

    # Define the pin for the pucks
    PIN = 11

    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)

    if enable:

        try:

            # Set a pucks to open
            GPIO.setup(PIN, GPIO.OUT)
            GPIO.output(PIN, GPIO.HIGH)

        except:

            print("Unable to set the pucks to HIGH")

    else:

        try:

            # Set a pucks to open
            GPIO.setup(PIN, GPIO.OUT)
            GPIO.output(PIN, GPIO.LOW)

        except:

            print("Unable to set the pucks to LOW")

def handle_data_logging(t_now, latest_states, chaserControl, thrustersChaser, targetControl, thrustersTarget, obstacleControl, thrustersObstacle, currentGyroAccel, dataContainer, CHASER_ACTIVE, TARGET_ACTIVE, OBSTACLE_ACTIVE):
    """
    Handle the data logging.
    This function appends the current time and spacecraft states to the data container.
    Parameters
    ----------
    t_now : float
        The current time.
    latest_states : dict
        A dictionary containing the latest states of the chaser, target, and obstacle spacecraft.
    chaserControl : LinearQuadraticRegulator
        The controller for the chaser spacecraft.
    thrustersChaser : Thrusters
        The thrusters for the chaser spacecraft.
    dataContainer : Storage
        Container for storing data.
    Returns
    -------
    None
    """

    # Instead of multiple individual appends:

    batch_data_general = {
            'Time (s)': t_now
    }
    if CHASER_ACTIVE:
        batch_data_chaser = {
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
            'Chaser PWM [1]': thrustersChaser.get_state(1),
            'Chaser PWM [2]': thrustersChaser.get_state(2),
            'Chaser PWM [3]': thrustersChaser.get_state(3),
            'Chaser PWM [4]': thrustersChaser.get_state(4),
            'Chaser PWM [5]': thrustersChaser.get_state(5),
            'Chaser PWM [6]': thrustersChaser.get_state(6),
            'Chaser PWM [7]': thrustersChaser.get_state(7),
            'Chaser PWM [8]': thrustersChaser.get_state(8),
            'Chaser Gyro X (rad/s)': currentGyroAccel['gx'],
            'Chaser Gyro Y (rad/s)': currentGyroAccel['gy'],
            'Chaser Gyro Z (rad/s)': currentGyroAccel['gz'],
            'Chaser Accel X (m/s²)': currentGyroAccel['ax'],
            'Chaser Accel Y (m/s²)': currentGyroAccel['ay'],
            'Chaser Accel Z (m/s²)': currentGyroAccel['az']
        }

    else:

        batch_data_chaser = {}

    if TARGET_ACTIVE:

        batch_data_target = {
            'Target Px (m)': latest_states.get("target")['pos'][0],
            'Target Py (m)': latest_states.get("target")['pos'][1],
            'Target Rz (rad)': latest_states.get("target")['att'],
            'Target Vx (m/s)': latest_states.get("target")['vel'][0],
            'Target Vy (m/s)': latest_states.get("target")['vel'][1],
            'Target Wz (rad/s)': latest_states.get("target")['omega'],
            'Target Duty Cycle [1]': targetControl.dutyCycle[0],
            'Target Duty Cycle [2]': targetControl.dutyCycle[1],
            'Target Duty Cycle [3]': targetControl.dutyCycle[2],
            'Target Duty Cycle [4]': targetControl.dutyCycle[3],
            'Target Duty Cycle [5]': targetControl.dutyCycle[4],
            'Target Duty Cycle [6]': targetControl.dutyCycle[5],
            'Target Duty Cycle [7]': targetControl.dutyCycle[6],
            'Target Duty Cycle [8]': targetControl.dutyCycle[7],
            'Target PWM [1]': thrustersTarget.get_state(1),
            'Target PWM [2]': thrustersTarget.get_state(2),
            'Target PWM [3]': thrustersTarget.get_state(3),
            'Target PWM [4]': thrustersTarget.get_state(4),
            'Target PWM [5]': thrustersTarget.get_state(5),
            'Target PWM [6]': thrustersTarget.get_state(6),
            'Target PWM [7]': thrustersTarget.get_state(7),
            'Target PWM [8]': thrustersTarget.get_state(8)
        }

    else:

        batch_data_target = {}

    if OBSTACLE_ACTIVE:

        batch_data_obstacle = {
            'Obstacle Px (m)': latest_states.get("obstacle")['pos'][0],
            'Obstacle Py (m)': latest_states.get("obstacle")['pos'][1],
            'Obstacle Rz (rad)': latest_states.get("obstacle")['att'],
            'Obstacle Vx (m/s)': latest_states.get("obstacle")['vel'][0],
            'Obstacle Vy (m/s)': latest_states.get("obstacle")['vel'][1],
            'Obstacle Wz (rad/s)': latest_states.get("obstacle")['omega'],
            'Obstacle Duty Cycle [1]': obstacleControl.dutyCycle[0],
            'Obstacle Duty Cycle [2]': obstacleControl.dutyCycle[1],
            'Obstacle Duty Cycle [3]': obstacleControl.dutyCycle[2],
            'Obstacle Duty Cycle [4]': obstacleControl.dutyCycle[3],
            'Obstacle Duty Cycle [5]': obstacleControl.dutyCycle[4],
            'Obstacle Duty Cycle [6]': obstacleControl.dutyCycle[5],
            'Obstacle Duty Cycle [7]': obstacleControl.dutyCycle[6],
            'Obstacle Duty Cycle [8]': obstacleControl.dutyCycle[7],
            'Obstacle PWM [1]': thrustersObstacle.get_state(1),
            'Obstacle PWM [2]': thrustersObstacle.get_state(2),
            'Obstacle PWM [3]': thrustersObstacle.get_state(3),
            'Obstacle PWM [4]': thrustersObstacle.get_state(4),
            'Obstacle PWM [5]': thrustersObstacle.get_state(5),
            'Obstacle PWM [6]': thrustersObstacle.get_state(6),
            'Obstacle PWM [7]': thrustersObstacle.get_state(7),
            'Obstacle PWM [8]': thrustersObstacle.get_state(8)
        }

    else:

        batch_data_obstacle = {}


    # Merge the dictionaries
    batch_data = {**batch_data_general, **batch_data_chaser, **batch_data_target, **batch_data_obstacle}

    # Append the data to the container
    dataContainer.append_data_batch(batch_data)

def get_platform_id():
    """
    Get the platform ID from the system time.

    This function generates a platform ID based on username.

    Returns:
        str: The platform ID.
    """
    platform_name = getpass.getuser()

    if platform_name == 'spot-red':
        whoami = 1
    elif platform_name == 'spot-black':
        whoami = 2
    elif platform_name == 'spot-blue':
        whoami = 3
    else:
        whoami = 0
        print(f"Unknown platform: {platform_name}, running in simulation mode.")

    return whoami

def class_init(PERIOD):
    """
    Initialize spacecraft models, controllers, and data storage based on configuration files.
    This function reads spacecraft parameters from JSON configuration files, creates spacecraft
    models and their respective controllers, calculates the optimal gain matrices for the 
    controllers, and initializes a data storage container.
    Parameters
    ----------
    PERIOD : float
        The time step for the controller simulation.
    Returns
    -------
    tuple
        A tuple containing the following elements:
        - chaserModel : Spacecraft
            The initialized chaser spacecraft model.
        - targetModel : Spacecraft
            The initialized target spacecraft model.
        - obstacleModel : Spacecraft
            The initialized obstacle spacecraft model.
        - chaserControl : LinearQuadraticRegulator
            The controller for the chaser spacecraft.
        - targetControl : LinearQuadraticRegulator
            The controller for the target spacecraft.
        - obstacleControl : LinearQuadraticRegulator
            The controller for the obstacle spacecraft.
        - dataContainer : Storage
            Container for storing simulation data.
        - chaser_params : dict
            Dictionary containing the chaser spacecraft parameters.
        - target_params : dict
            Dictionary containing the target spacecraft parameters.
        - obstacle_params : dict
            Dictionary containing the obstacle spacecraft parameters.
    Notes
    -----
    The function loads parameters from the following configuration files:
    - 'config/chaser.json'
    - 'config/target.json'
    - 'config/obstacle.json'
    Each spacecraft is initialized with default zero velocity and angular velocity.
    """

    # Load the JSON file
    with open('config/chaser.json') as f:
        chaser_json = json.load(f)
    
    with open('config/target.json') as f:
        target_json = json.load(f)
    
    with open('config/obstacle.json') as f:
        obstacle_json = json.load(f)

    # Create a dictionary to store the parameters
    chaser_params = {}
    target_params = {}
    obstacle_params = {}

    # Convert the mass and inertia and store 
    chaser_params['CHASER_MASS'] = float(chaser_json['mass']['value'])
    chaser_params['CHASER_INERTIA'] = float(chaser_json['inertia']['value'])
    chaser_params['CHASER_DROP'] = [float(value) for value in chaser_json['drop_states']['value']]
    chaser_params['CHASER_INIT'] = [float(value) for value in chaser_json['init_states']['value']]
    chaser_params['CHASER_HOME'] = [float(value) for value in chaser_json['home_states']['value']]
    chaser_params['CHASER_THRUST_DIST2CG'] = [float(value) for value in chaser_json['thruster_dist2CG']['value']]
    chaser_params['CHASER_THRUST_F'] = [float(value) for value in chaser_json['thruster_force']['value']]

    target_params['TARGET_MASS'] = float(target_json['mass']['value'])
    target_params['TARGET_INERTIA'] = float(target_json['inertia']['value'])
    target_params['TARGET_DROP'] = [float(value) for value in target_json['drop_states']['value']]
    target_params['TARGET_INIT'] = [float(value) for value in target_json['init_states']['value']]
    target_params['TARGET_HOME'] = [float(value) for value in target_json['home_states']['value']]
    target_params['TARGET_THRUST_DIST2CG'] = [float(value) for value in target_json['thruster_dist2CG']['value']]
    target_params['TARGET_THRUST_F'] = [float(value) for value in target_json['thruster_force']['value']]

    obstacle_params['OBSTACLE_MASS'] = float(obstacle_json['mass']['value'])
    obstacle_params['OBSTACLE_INERTIA'] = float(obstacle_json['inertia']['value'])
    obstacle_params['OBSTACLE_DROP'] = [float(value) for value in obstacle_json['drop_states']['value']]
    obstacle_params['OBSTACLE_INIT'] = [float(value) for value in obstacle_json['init_states']['value']]
    obstacle_params['OBSTACLE_HOME'] = [float(value) for value in obstacle_json['home_states']['value']]
    obstacle_params['OBSTACLE_THRUST_DIST2CG'] = [float(value) for value in obstacle_json['thruster_dist2CG']['value']]
    obstacle_params['OBSTACLE_THRUST_F'] = [float(value) for value in obstacle_json['thruster_force']['value']]

    print('Initializing spacecraft and controller classes...')

    # Initialize the spacecraft class
    chaserModel = Spacecraft(mass=chaser_params['CHASER_MASS'], 
                             inertia=chaser_params['CHASER_INERTIA'],
                             position=chaser_params['CHASER_DROP'][:2], 
                             attitude=chaser_params['CHASER_DROP'][2],
                             velocity=[0, 0],
                             angular_velocity=0,
                             sc_id='chaser')
                             
    targetModel = Spacecraft(mass=target_params['TARGET_MASS'],
                             inertia=target_params['TARGET_INERTIA'],
                             position=target_params['TARGET_DROP'][:2],
                             attitude=target_params['TARGET_DROP'][2],
                             velocity=[0, 0],
                             angular_velocity=0,
                             sc_id='target')
                             
    obstacleModel = Spacecraft(mass=obstacle_params['OBSTACLE_MASS'],
                               inertia=obstacle_params['OBSTACLE_INERTIA'],
                               position=obstacle_params['OBSTACLE_DROP'][:2],
                               attitude=obstacle_params['OBSTACLE_DROP'][2],
                               velocity=[0, 0],
                               angular_velocity=0,
                               sc_id='obstacle')
    
    # Initialize the controller class
    chaserControl = LinearQuadraticRegulator(mass=chaser_params['CHASER_MASS'], 
                                             inertia=chaser_params['CHASER_INERTIA'], 
                                             thruster_dist2CG=chaser_params['CHASER_THRUST_DIST2CG'],
                                             thruster_F=chaser_params['CHASER_THRUST_F'],
                                             dt=PERIOD)

    targetControl = LinearQuadraticRegulator(mass=target_params['TARGET_MASS'],
                                             inertia=target_params['TARGET_INERTIA'],
                                             thruster_dist2CG=target_params['TARGET_THRUST_DIST2CG'],
                                             thruster_F=target_params['TARGET_THRUST_F'],
                                             dt=PERIOD)
    
    obstacleControl = LinearQuadraticRegulator(mass=obstacle_params['OBSTACLE_MASS'],
                                               inertia=obstacle_params['OBSTACLE_INERTIA'],
                                               thruster_dist2CG=obstacle_params['OBSTACLE_THRUST_DIST2CG'],
                                               thruster_F=obstacle_params['OBSTACLE_THRUST_F'],
                                               dt=PERIOD)
    
    # Calculate the optimal gain matrix
    chaserControl.solve()
    targetControl.solve()
    obstacleControl.solve()

    # Initialize the data storage
    dataContainer = Storage()

    return chaserModel, targetModel, obstacleModel, chaserControl, targetControl, obstacleControl, dataContainer, chaser_params, target_params, obstacle_params

def create_phase_tracker(phases):
    """
    Creates a phase tracker that will print phase transitions only once.
    
    Args:
        phases (dict): A dictionary containing phase durations with keys like 'PHASE_0_DURATION'
    
    Returns:
        function: A function that takes the current time and prints phase transitions
    """
    # Calculate phase transition points
    transition_points = {}
    current_time = 0
    
    for i, phase_key in enumerate(sorted(phases.keys())):
        current_time += phases[phase_key]
        transition_points[i] = current_time - phases[phase_key]  # Start time of each phase
    
    # Create a closure to track the current phase
    def track_phase(current_time):
        # Static variable to keep track of the last printed phase
        if not hasattr(track_phase, 'last_phase'):
            track_phase.last_phase = -1
        
        # Determine current phase
        current_phase = None
        for phase, start_time in transition_points.items():
            if current_time >= start_time:
                current_phase = phase
                
        # Print phase transition if it's a new phase
        if current_phase is not None and current_phase > track_phase.last_phase:
            print(f"=== STARTING PHASE {current_phase} (t = {current_time:.2f} s) ===")
            track_phase.last_phase = current_phase

    def is_phase(phase):
        return track_phase.last_phase == phase
            
    return track_phase, is_phase

def precise_delay_microsecond(delay_us):
    """
    Delays the execution of the program for a specified number of microseconds.

    This function uses a busy-wait loop to achieve a precise delay. It calculates
    the target time in nanoseconds and continuously checks the current time until
    the target time is reached.

    Args:
        delay_us (int): The delay duration in microseconds.

    Returns:
        None
    """
    target_time = perf_counter_ns() + delay_us * 1000
    while perf_counter_ns() < target_time:
        pass