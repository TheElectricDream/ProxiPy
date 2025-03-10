import socket
import struct
import numpy as np
from scipy.optimize import minimize
import select

class SimpleController:
    def __init__(self, kp_pos, kd_pos, kp_att, kd_att):
        self.kp_pos = kp_pos
        self.kd_pos = kd_pos
        self.kp_att = kp_att
        self.kd_att = kd_att
        self.prev_error_pos = [0, 0]
        self.prev_error_att = 0

    def update(self, desired_pos, current_pos, desired_att, current_att, dt):
        # Calculate position errors
        error_pos = [desired_pos[0] - current_pos[0], desired_pos[1] - current_pos[1]]
        error_att = desired_att - current_att

        print(f"Error position: {error_pos}, error attitude: {error_att}")

        # Calculate derivative of errors
        d_error_pos = [(error_pos[0] - self.prev_error_pos[0]) / dt, (error_pos[1] - self.prev_error_pos[1]) / dt]
        d_error_att = (error_att - self.prev_error_att) / dt

        # PD control for position
        force_x = -(self.kp_pos * error_pos[0] + self.kd_pos * d_error_pos[0])
        force_y = -(self.kp_pos * error_pos[1] + self.kd_pos * d_error_pos[1])

        # PD control for attitude
        torque = self.kp_att * error_att + self.kd_att * d_error_att

        # Update previous errors
        self.prev_error_pos = error_pos
        self.prev_error_att = error_att

        return force_x, force_y, torque

def udp_server(controller, desired_pos, desired_att, dt, udp_ip='', udp_port=53673):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((udp_ip, udp_port))
    sock.setblocking(False)  # Set socket to non-blocking mode

    print(f"Listening for UDP packets on {udp_ip}:{udp_port}")

    udp_send_ip = "127.0.0.1"
    udp_send_port = 48291
    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        # Use select to check for available data without blocking
        readable, _, _ = select.select([sock], [], [], 0)
        
        if readable:
            # Drain all available packets, keeping only the most recent
            latest_data = None
            while True:
                try:
                    # Attempt to read the next packet
                    data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes
                    latest_data = data
                except BlockingIOError:
                    # No more data available
                    break
            
            if latest_data is not None:
                # Process only the most recent packet
                current_pos = struct.unpack('ff', latest_data[:8])
                current_att = struct.unpack('f', latest_data[8:12])[0]
                
                # Use a simple PD controller to calculate the forces
                force_x, force_y, torque = controller.update(desired_pos, current_pos, desired_att, current_att, dt)
                
                # Calculate the duty cycles
                duty_cycles = forces_to_duty_cycle(force_x, force_y, torque, current_att)

                # Pack the duty cycles as doubles and send over UDP
                safety_bit = 568471  # Example safety bit, set to 1 for safety enabled
                pwm_freq = 5  # Example PWM frequency in Hz
                message = struct.pack('d' * 10, safety_bit, pwm_freq, *duty_cycles)
                send_sock.sendto(message, (udp_send_ip, udp_send_port))
                print(f"Sent duty cycles: {duty_cycles}")

def forces_to_duty_cycle(force_x, force_y, torque, yaw):

    THRUSTER_DIST2_CG = np.array([64.335708595202250,-67.66429140479772,93.129636186598190,-51.370363813401790,70.664291404797720,-63.335708595202256,43.870363813401780,-85.629636186598220]).T

    # Calculate rotation matrix
    C_bI = np.array([[np.cos(yaw), -np.sin(yaw)],
                      [np.sin(yaw), np.cos(yaw)]])
    
    # Calculate the body forces
    F_b = C_bI @ np.array([force_x, force_y]) 

    # Calculate the force distribution matrix, H
    Vec1 = np.array([[-1],[-1],[0],[0],[1],[1],[0],[0]])
    Vec2 = np.array([[0],[0],[1],[1],[0],[0],[-1],[-1]])
    Vec3 = THRUSTER_DIST2_CG/1000

    Mat1 = np.concatenate((Vec1, Vec2, np.reshape(Vec3,(8,1))), axis=1).T
    Mat2 = np.diag(np.array([0.2825,0.2825,0.2825,0.2825,0.2825,0.2825,0.2825,0.2825])/2)

    H = Mat1 @ Mat2

    # Take the pinv of H
    Hinv = np.linalg.pinv(H)

    # Calculate the duty cycles
    duty_cycles_initial = Hinv @ np.append(F_b, torque)
    print(duty_cycles_initial)

    Q = 2 * (H.T @ H)
    c = -2 * H.T @ np.append(F_b, torque)
    lb = np.zeros(8)
    ub = np.ones(8)

    # Define the objective function for the optimizer
    def objective(duty_cycles):
        return 0.5 * duty_cycles.T @ Q @ duty_cycles + c.T @ duty_cycles

    # Define the bounds for the optimizer
    bounds = [(0, 100) for _ in range(H.shape[1])]

    # Solve for optimal duty cycles
    result = minimize(objective, duty_cycles_initial, bounds=bounds, options={'maxiter': 20})

    # Extract the duty cycles
    duty_cycles = result.x

    return duty_cycles

if __name__ == "__main__":
    controller = SimpleController(kp_pos=5.0, kd_pos=3.6, kp_att=0.5, kd_att=1.8)
    desired_pos = [3.025, 1.993]
    desired_att = -2.202
    dt = 0.1

    udp_server(controller, desired_pos, desired_att, dt)