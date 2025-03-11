import threading
import time
import numpy as np
from BMI160_i2c import Driver

class IMUProcessor:
    """
    This class encapsulates the setup and streaming of IMU data from a BMI160 sensor.
    
    It initializes the sensor and starts a background thread that continuously reads
    and processes incoming IMU data. The latest state can be retrieved using the
    `get()` method.
    """
    def __init__(self, i2c_address=0x69, read_frequency=100):
        """
        Initializes the IMU processor.

        Args:
            i2c_address (int): I2C address of the BMI160 sensor (default: 0x69)
            read_frequency (int): How many times per second to read the sensor (default: 100)
        """
        self.i2c_address = i2c_address
        self.read_delay = 1.0 / read_frequency
        
        # Initialize the sensor
        self.sensor = self._initialize_sensor()
        
        # Dictionary to hold the latest IMU data
        self.imu_data = {
            'gx': 0.0, 'gy': 0.0, 'gz': 0.0,  # Gyroscope (rad/s)
            'ax': 0.0, 'ay': 0.0, 'az': 0.0,  # Accelerometer (m/s²)
            'timestamp': 0.0                   # Time of reading
        }
        
        # For computing angular velocity and linear acceleration
        self.prev_data = None
        self.prev_time = None
        
        # Thread synchronization
        self.lock = threading.Lock()
        self._stop_event = threading.Event()
        
        # Start the data streaming in a background thread
        self.thread = threading.Thread(target=self._read_imu_data, daemon=True)
        self.thread.start()
    
    def _initialize_sensor(self):
        """
        Initializes and returns a BMI160 sensor instance.

        Returns:
            Driver: The initialized BMI160 sensor driver.
        """
        try:
            print('Initializing BMI160 sensor...')
            sensor = Driver(self.i2c_address)
            print('Sensor initialization complete')
            return sensor
        except Exception as e:
            print(f"Error initializing sensor: {e}")
            raise

    def _read_imu_data(self):
        """
        Runs in a background thread to continuously read IMU data.
        
        If the sensor returns all zeros, it attempts to reinitialize the sensor.
        """
        consecutive_failures = 0
        max_failures = 5
        
        try:
            while not self._stop_event.is_set():
                try:
                    # Read raw data from the IMU
                    data = self.sensor.getMotion6()
                    current_time = time.perf_counter()
                    
                    # Check if all values are zero (potential sensor failure)
                    if all(val == 0 for val in data):
                        consecutive_failures += 1
                        print(f"Warning: Sensor returned all zeros ({consecutive_failures}/{max_failures})")
                        
                        if consecutive_failures >= max_failures:
                            print("Multiple sensor failures detected. Reinitializing...")
                            self.sensor = self._initialize_sensor()
                            consecutive_failures = 0
                    else:
                        consecutive_failures = 0
                        
                        # Update the state dictionary in a thread-safe manner
                        with self.lock:
                            self.imu_data = {
                                'gx': data[0],  # Gyro X (rad/s)
                                'gy': data[1],  # Gyro Y (rad/s)
                                'gz': data[2],  # Gyro Z (rad/s)
                                'ax': data[3],  # Accel X (m/s²)
                                'ay': data[4],  # Accel Y (m/s²)
                                'az': data[5],  # Accel Z (m/s²)
                                'timestamp': current_time
                            }
                    
                    # Sleep for the specified delay
                    time.sleep(self.read_delay)
                
                except Exception as e:
                    print(f"Error reading from sensor: {e}")
                    # Try to recover by reinitializing the sensor
                    try:
                        self.sensor = self._initialize_sensor()
                    except:
                        # If reinitialization fails, wait longer before trying again
                        time.sleep(1.0)
                        
        except KeyboardInterrupt:
            print("IMU reading interrupted by user")
        finally:
            print("IMU reading thread terminated")

    def get(self):
        """
        Returns the latest IMU data readings.

        Returns:
            dict: A copy of the dictionary containing the latest IMU data.
        """
        with self.lock:
            return self.imu_data.copy()
    
    def get_orientation(self):
        """
        Calculates and returns the orientation based on accelerometer data.
        
        Returns:
            tuple: (roll, pitch) in radians, representing orientation
        """
        with self.lock:
            data = self.imu_data.copy()
        
        # Calculate roll and pitch from accelerometer data
        # (this is a simple complementary filter approach)
        ax, ay, az = data['ax'], data['ay'], data['az']
        
        # Normalize the accelerometer vector
        acc_norm = np.sqrt(ax*ax + ay*ay + az*az)
        if acc_norm == 0:
            return (0, 0)  # Can't determine orientation
            
        ax, ay, az = ax/acc_norm, ay/acc_norm, az/acc_norm
        
        # Calculate roll (rotation around X-axis) and pitch (rotation around Y-axis)
        roll = np.arctan2(ay, az)
        pitch = np.arctan2(-ax, np.sqrt(ay*ay + az*az))
        
        return (roll, pitch)

    def stop(self):
        """
        Signals the background thread to stop and waits for it to terminate.
        """
        self._stop_event.set()
        self.thread.join(timeout=2.0)  # Wait up to 2 seconds for the thread to stop


# Example usage:
if __name__ == "__main__":
    try:
        # Create the IMU processor with default settings
        imu = IMUProcessor()
        
        # Read data for 10 seconds
        for _ in range(10):
            # Get the latest IMU data
            data = imu.get()
            print(f"Gyro: X={data['gx']:.2f}, Y={data['gy']:.2f}, Z={data['gz']:.2f} rad/s")
            print(f"Accel: X={data['ax']:.2f}, Y={data['ay']:.2f}, Z={data['az']:.2f} m/s²")
            
            # Get the orientation (roll and pitch)
            roll, pitch = imu.get_orientation()
            print(f"Orientation: Roll={np.degrees(roll):.1f}°, Pitch={np.degrees(pitch):.1f}°")
            print("-" * 50)
            
            time.sleep(1.0)
    
    except KeyboardInterrupt:
        print("Program interrupted by user")
    finally:
        # Clean up resources
        imu.stop()
        print("Program terminated")