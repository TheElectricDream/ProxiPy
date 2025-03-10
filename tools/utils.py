from time import perf_counter_ns
import numpy as np
import json
from classes.Spacecraft import Spacecraft
from classes.Controllers import LinearQuadraticRegulator
from classes.Storage import Storage
import getpass
import time

def get_current_locations_exp(stream_processor, chaser_active, target_active, obstacle_active):
    """
    Get the current locations of the chaser, target, and obstacle spacecraft from the PhaseSpace system.
    This function retrieves the latest states of the chaser, target, and obstacle spacecraft from the
    PhaseSpace system and stores them in the respective variables. If the data is invalid, the function
    will print an error message and skip the current iteration.
    Parameters
    ----------
    stream_processor : StreamProcessor
        The stream processor object used to retrieve the latest states from PhaseSpace.
    chaser_active : bool
        A boolean flag indicating whether the chaser spacecraft is active.
    target_active : bool
        A boolean flag indicating whether the target spacecraft is active.
    obstacle_active : bool
        A boolean flag indicating whether the obstacle spacecraft is active.
    Returns
    -------
    tuple
        A tuple containing the following elements:
        - currentLocationChaser : np.ndarray
            The current location of the chaser spacecraft.
        - currentLocationTarget : np.ndarray
            The current location of the target spacecraft.
        - currentLocationObstacle : np.ndarray
            The current location of the obstacle spacecraft.
        - t_init : float
            The initial time for the clock.
        - skip : bool
            A boolean flag indicating whether to skip the current iteration.
    Notes
    -----
    The function will print an error message if the data is invalid and skip the current iteration.
    """

    # Get the latest states from PhaseSpace
    latest_states = stream_processor.get()

    # Check that the data is valid and chaser is active
    if latest_states.get("chaser") is None and chaser_active:

        # If there is no data but the chaser is active, then wait for new data
        print('Chaser data is invalid; skipping...')
        t_init = time.perf_counter()  # Reset the clock
    
    # Check that the data is valid and target is not active
    elif latest_states.get("chaser") is None and not chaser_active:
        
        # If there is no data and the chaser is not active, then pass to continue the simulation
        skip = True
    
    elif latest_states.get("chaser") is not None and chaser_active:
        currentLocationChaser = np.array([latest_states.get("chaser")['pos'][0],
                        latest_states.get("chaser")['pos'][1],
                        latest_states.get("chaser")['att'],
                        latest_states.get("chaser")['vel'][0],
                        latest_states.get("chaser")['vel'][1],
                        latest_states.get("chaser")['omega']])
        
    else:
        currentLocationChaser = None
        skip = True
    
    if latest_states.get("target") is None and target_active:
        
        # If there is no data but the target is active, then wait for new data
        print('Target data is invalid; skipping...')
        t_init = time.perf_counter()  # Reset the clock

    elif latest_states.get("target") is None and not target_active:
        
        # If there is no data and the target is not active, then pass to continue the simulation
        skip = True

    elif latest_states.get("target") is not None and target_active:
        currentLocationTarget = np.array([latest_states.get("target")['pos'][0],
                        latest_states.get("target")['pos'][1],
                        latest_states.get("target")['att'],
                        latest_states.get("target")['vel'][0],
                        latest_states.get("target")['vel'][1],
                        latest_states.get("target")['omega']])
        
    else:
        currentLocationTarget = None
        skip = True

    if latest_states.get("obstacle") is None and obstacle_active:
        
        # If there is no data but the obstacle is active, then wait for new data
        print('Obstacle data is invalid; skipping...')
        t_init = time.perf_counter()
        
    elif latest_states.get("obstacle") is None and not obstacle_active:
        
        # If there is no data and the obstacle is not active, then pass to continue the simulation
        skip = True
        
    elif latest_states.get("obstacle") is not None and obstacle_active:
    
        currentLocationObstacle = np.array([latest_states.get("obstacle")['pos'][0],
                        latest_states.get("obstacle")['pos'][1],
                        latest_states.get("obstacle")['att'],
                        latest_states.get("obstacle")['vel'][0],
                        latest_states.get("obstacle")['vel'][1],
                        latest_states.get("obstacle")['omega']])
        
    else: 
        currentLocationObstacle = None
        skip = True

    return currentLocationChaser, currentLocationTarget, currentLocationObstacle, t_init, skip

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