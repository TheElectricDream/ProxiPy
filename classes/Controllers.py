import numpy as np
import scipy.linalg
from scipy.optimize import minimize

class LinearQuadraticRegulator:
    def __init__(self, mass, inertia, thruster_dist2CG, thruster_F, dt, pwm_freq=5):
        """
        Initialize the controller with given mass, inertia, and time step.

        Parameters:
        mass (float): The mass of the system.
        inertia (float): The inertia of the system.
        thruster_dist2CG (list): The distances from each thruster to the center of gravity.
        thruster_F (list): The maximum thrust force of each thruster.
        dt (float): The time step for discretization.
        pwm_freq (float): PWM frequency in Hz for thruster control.
        """
        self.mass = mass
        self.inertia = inertia
        self.thruster_dist2CG = thruster_dist2CG
        self.thruster_F = thruster_F
        self.pwm_freq = pwm_freq
        self.valve_time = 0.007  # Minimum valve open time in seconds
        self.min_duty_cycle = self.valve_time * self.pwm_freq
        self.enable_control = False
        
        # System matrices
        self.A = np.array([
            [0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 1],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0]
        ])
        
        self.B = np.array([
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
            [1/mass, 0, 0],
            [0, 1/mass, 0],
            [0, 0, 1/inertia]
        ])
        
        # Cost matrices
        self.Q = np.diag([1, 1, 0.05, 10, 10, 1])
        self.R = np.diag([6, 6, 6])
        
        # Discretize system
        self.A_d = scipy.linalg.expm(self.A * dt)
        self.B_d = np.dot(np.linalg.pinv(self.A) @ (self.A_d - np.eye(6)), self.B)
        
        # Controller and thruster mapping
        self.K = None
        self.H = None
        self._initialize_H_matrix()
        
        # Control signals
        self.controlSignal = None
        self.controlSignalBodyFrame = None
        self.saturatedControlSignal = None
        self.saturatedControlSignalBodyFrame = None
        self.dutyCycle = None
        self.current_decay_factor = 1.0

    def _initialize_H_matrix(self):
        """Initialize the H matrix that maps thruster forces to control forces/torques"""
        V1 = np.array([[-1],[-1],[0],[0],[1],[1],[0],[0]])
        V2 = np.array([[0],[0],[1],[1],[0],[0],[-1],[-1]])
        V3 = np.array(self.thruster_dist2CG)
        
        H1 = np.hstack([V1, V2, V3.reshape((8,1))/1000]).T
        H2 = np.diag(np.array(self.thruster_F) / 2)
        
        self.H = H1 @ H2

    def solve(self):
        """
        Solve the discrete-time algebraic Riccati equation to compute the LQR gain matrix.
        """
        P = np.matrix(scipy.linalg.solve_discrete_are(self.A_d, self.B_d, self.Q, self.R))
        self.K = np.matrix(scipy.linalg.pinv(self.R) @ self.B_d.T @ P)
    
    def compute_control(self, state, target):
        """
        Compute the control input based on the current state and target state.

        Parameters:
        state (dict): Current system state with keys 'position', 'attitude', 'velocity', 'angular_velocity'.
        target (dict): Target system state with the same keys as state.

        Returns:
        np.ndarray: The computed thruster duty cycles.
        """
        if self.K is None:
            self.solve()
                
        # Compute error for x and y
        error_x = state[0] - target[0]
        error_y = state[1] - target[1]

        # Computer the error for attitude correctly
        error_attitude = (state[2] - target[2] + np.pi) % (2 * np.pi) - np.pi

        # Stack the errors
        error = np.array([error_x, error_y, error_attitude, state[3] - target[3], state[4] - target[4], state[5] - target[5]])

        #error = state - target

        if self.enable_control:
            self.controlSignal = np.array(-self.K @ error)
        else:
            self.controlSignal = np.array([np.zeros(3)])
        
        # Transform to body frame
        self.compute_control_body_frame(state[2])
        
        # Compute thruster duty cycles with integrated constraints
        self.compute_duty_cycle()

    def compute_control_body_frame(self, attitude):
        """
        Transform control signals from inertial frame to body frame.
        
        Parameters:
        attitude (float): Current attitude of the system in radians.
        """
        # Rotation matrix from inertial to body frame
        C_bI = np.array([
            [np.cos(attitude), np.sin(attitude)],
            [-np.sin(attitude), np.cos(attitude)]
        ])
        
        # Transform linear forces
        body_forces = C_bI @ self.controlSignal[0][:2]
        
        # Combine with angular control
        self.controlSignalBodyFrame = np.append(body_forces, self.controlSignal[0][2])

    def compute_duty_cycle(self):
        """
        Compute optimized thruster duty cycles with integrated constraints and decay effects.
        """
        if self.controlSignalBodyFrame is None:
            raise ValueError("Control signal in body frame not available")
            
        # Optimize duty cycles with integrated constraints
        self.dutyCycle = self.optimize_duty_cycle_fast(self.controlSignalBodyFrame)

    def optimize_duty_cycle(self, u_desired, max_iters=100, tol=1e-6):
        """
        Optimize thruster duty cycles with integrated constraints.
        """
        num_thrusters = len(self.thruster_dist2CG)
        
        # Fixed decay factor for initial optimization
        self.current_decay_factor = 1.0
        H = self._make_H_with_decay(self.current_decay_factor)
        
        # Define a simple objective function (quadratic error)
        def objective(x):
            return np.sum((H @ x - u_desired) ** 2)
        
        # Define bounds
        bounds = [(0, 1.0) for _ in range(num_thrusters)]
        
        # Initial guess - start with a least-squares solution and bound it
        # Use pseudoinverse for an initial guess
        initial_guess = np.linalg.pinv(H) @ u_desired
        
        # Bound the initial guess between 0 and 1
        initial_guess = np.clip(initial_guess, 0, 1.0)
        
        # Make sure initial_guess is not all zeros - if it is, use small values
        if np.all(initial_guess < 1e-6):
            initial_guess = np.ones(num_thrusters) * 0.1
        
        # Single optimization step
        result = minimize(
            objective,
            initial_guess,
            method='L-BFGS-B',
            bounds=bounds,
            options={'maxiter': 5}
        )
        
        duty_cycles = result.x
        
        # Post-process duty cycles with minimum on-time constraint
        for i in range(len(duty_cycles)):
            if 0 < duty_cycles[i] < self.min_duty_cycle:
                duty_cycles[i] = 0
        
        # Recalculate decay factor based on final duty cycles
        self.current_decay_factor = self._calculate_thrust_decay(duty_cycles)
        
        # Calculate final control signal with updated decay
        H_decayed = self._make_H_with_decay(self.current_decay_factor)
        self.saturatedControlSignalBodyFrame = H_decayed @ duty_cycles
        
        return duty_cycles
    
    def optimize_duty_cycle_fast(self, u_desired):
        """
        A faster method to distribute control among thrusters using
        direct pseudoinverse calculation instead of iterative optimization.
        
        Parameters:
        u_desired (np.ndarray): Desired control forces/torques in body frame
        
        Returns:
        np.ndarray: Optimized thruster duty cycles
        """
        num_thrusters = len(self.thruster_dist2CG)
        
        # Apply current decay factor to H matrix
        H = self._make_H_with_decay(self.current_decay_factor)
        
        # Calculate pseudoinverse solution
        duty_cycles = np.linalg.pinv(H) @ u_desired
        
        # Apply saturation (clip to [0,1])
        duty_cycles = np.clip(duty_cycles, 0, 1.0)
        
        # Apply minimum on-time constraint
        duty_cycles[duty_cycles < self.min_duty_cycle] = 0.0
        
        # Recalculate decay factor based on final duty cycles
        self.current_decay_factor = self._calculate_thrust_decay(duty_cycles)
        
        # Calculate final control signal with updated decay
        H_decayed = self._make_H_with_decay(self.current_decay_factor)
        self.saturatedControlSignalBodyFrame = H_decayed @ duty_cycles
        
        return duty_cycles

    def _make_H_with_decay(self, decay_factor):
        """
        Create H matrix with decay factor applied to thruster forces.
        
        Parameters:
        decay_factor (float): Factor to scale thruster forces.
        
        Returns:
        np.ndarray: Updated H matrix.
        """
        V1 = np.array([[-1],[-1],[0],[0],[1],[1],[0],[0]])
        V2 = np.array([[0],[0],[1],[1],[0],[0],[-1],[-1]])
        V3 = np.array(self.thruster_dist2CG)
        
        H1 = np.hstack([V1, V2, V3.reshape((8,1))/1000]).T
        H2 = np.diag(np.array(self.thruster_F) * decay_factor / 2)
        
        return H1 @ H2

    def _calculate_thrust_decay(self, duty_cycles):
        """
        Calculate thrust decay factor based on duty cycles.
        """
        # Limit how much the decay factor can decrease
        active_thrusters = np.sum(duty_cycles > 0)
        if active_thrusters == 0:
            return 1.0  # No active thrusters, no decay
            
        mean_duty = np.sum(duty_cycles) / active_thrusters
        decay_factor = max(0.8, 1.0 - 0.15 * mean_duty)
        
        return decay_factor
    
    def get_control_signal(self):
        """Get the current control signal in inertial frame."""
        return self.controlSignal[0] if self.controlSignal is not None else None
    
    def get_control_signal_body_frame(self):
        """Get the current control signal in body frame."""
        return self.controlSignalBodyFrame
    
    def get_saturated_control_signal_body_frame(self):
        """Get the current saturated control signal in body frame."""
        return self.saturatedControlSignalBodyFrame
    
    def compute_saturated_control_signal(self, attitude):

        # Rotation matrix from inertial to body frame
        C_bI = np.array([
            [np.cos(attitude), np.sin(attitude)],
            [-np.sin(attitude), np.cos(attitude)]
        ])
        
        # Transform linear forces
        body_forces = C_bI.T @ self.saturatedControlSignalBodyFrame[:2]
        
        # Combine with angular control
        self.saturatedControlSignal = np.append(body_forces, self.saturatedControlSignalBodyFrame[2])

    
    def get_duty_cycle(self):
        """Get the current thruster duty cycles."""
        return self.dutyCycle