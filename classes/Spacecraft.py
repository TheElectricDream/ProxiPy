

class Spacecraft:
    def __init__(self, mass, inertia, position, attitude, velocity, angular_velocity, sc_id):
        """
        Initialize a Spacecraft object.

        Parameters:
        mass (float): The mass of the spacecraft.
        inertia (float): The inertia of the spacecraft.
        position (list of float): The position of the spacecraft [x, y].
        attitude (float): The attitude (yaw) of the spacecraft.
        velocity (list of float): The velocity of the spacecraft [vx, vy].
        angular_velocity (float): The angular velocity (gz) of the spacecraft.
        sc_id (string): The unique identifier for the spacecraft.
        
        """
        self.mass = mass
        self.inertia = inertia
        self.position = position  # [x, y]
        self.attitude = attitude  # [yaw]
        self.velocity = velocity  # [vx, vy]
        self.angular_velocity = angular_velocity  # [gz]
        self.acceleration = [0, 0]  # [ax, ay]
        self.angular_acceleration = 0  # [alpz]
        self.sc_id = sc_id
        self.states = {}

        self.states[self.sc_id] = {
            "pos": [self.position[0], self.position[1]],  # [x, y]
            "att": self.attitude,   # yaw angle
            "vel": [self.velocity[0], self.velocity[1]],               # [vx, vy]
            "omega": self.angular_velocity            # angular velocity (ω)
        }


    def apply_force(self, force, torque):
        """
        Apply a force and torque to the spacecraft to update its linear and angular acceleration.

        Parameters:
        force (tuple): A tuple representing the force vector (Fx, Fy) applied to the spacecraft.
        torque (float): The torque applied to the spacecraft.

        Returns:
        None
        """
        # F = m * a => a = F / m
        self.acceleration[0] = force[0] / self.mass
        self.acceleration[1] = force[1] / self.mass
        self.angular_acceleration = torque / self.inertia

    def update(self, dt):
        """
        Update the spacecraft's state based on the elapsed time.

        Parameters:
        dt (float): The time interval over which to update the spacecraft's state.

        Updates the following attributes:
        - velocity: Updates the velocity based on the current acceleration and time interval.
        - angular_velocity: Updates the angular velocity based on the current angular acceleration and time interval.
        - position: Updates the position based on the current velocity and time interval.
        - attitude: Updates the attitude based on the current angular velocity and time interval.

        Resets the following attributes after update:
        - acceleration: Resets to [0, 0] after each update.
        - angular_acceleration: Resets to 0 after each update.
        """
        # Update velocity: v = u + at
        self.velocity[0] += self.acceleration[0] * dt
        self.velocity[1] += self.acceleration[1] * dt
        self.angular_velocity += self.angular_acceleration * dt

        # Update position: s = s0 + vt
        self.position[0] += self.velocity[0] * dt
        self.position[1] += self.velocity[1] * dt
        self.attitude += self.angular_velocity * dt

        # Store the updated state and check the id
        if self.sc_id not in self.states:
            raise ValueError(f"Invalid spacecraft ID: {self.sc_id}")

        self.states[self.sc_id] = {
            "pos": [self.position[0], self.position[1]],  # [x, y]
            "att": self.attitude,   # yaw angle
            "vel": [self.velocity[0], self.velocity[1]],               # [vx, vy]
            "omega": self.angular_velocity            # angular velocity (ω)
        }

        # Reset acceleration after each update
        self.acceleration = [0, 0]
        self.angular_acceleration = 0

    def get(self):
        """
        Returns the latest state for each rigid body.

        Returns:
            dict: A copy of the dictionary containing the latest data for "red", "black", and "blue".
        """
        return self.states.copy()
        
        