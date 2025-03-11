import signal

# Existing imports
try:
    import Jetson.GPIO as GPIO
except ImportError:
    print("Jetson.GPIO not available. Running in simulation mode.")

import time
from time import perf_counter_ns, perf_counter
import ctypes
import multiprocessing

def precise_delay_microsecond(delay_us):
    """
    Delays execution for the specified microseconds using a busy-wait loop.
    """
    target_time = perf_counter_ns() + delay_us * 1000
    while perf_counter_ns() < target_time:
        pass

class Thrusters:
    """
    A class to control 8 thrusters via PWM signals on GPIO pins.
    The PWM loop runs in a separate process with an attempt to set
    a real-time scheduling policy for consistent timing.
    """
    
    def __init__(self, pwm_frequency=5, is_experiment=False):
        """
        Initialize the Thrusters class.
        
        Args:
            pwm_frequency (float): The PWM frequency in Hz.
            is_experiment (bool): If True, send commands to GPIO pins.
                                  If False, run in simulation mode.
        """
        self.THRUSTER_PINS = [7, 12, 13, 15, 16, 18, 22, 23]
        self.NUM_THRUSTERS = len(self.THRUSTER_PINS)
        self.pwm_frequency = pwm_frequency
        self.PERIOD = 1.0 / pwm_frequency
        self.is_experiment = is_experiment

        # Use a multiprocessing Manager for shared state between processes
        manager = multiprocessing.Manager()
        self.duty_cycles = manager.list([0.0] * self.NUM_THRUSTERS)
        self.requested_duty_cycles = manager.list([0.0] * self.NUM_THRUSTERS)
        self.current_states = manager.list([False] * self.NUM_THRUSTERS)
        self.duty_cycle_lock = manager.Lock()
        self.duty_cycle_updated = manager.Value('b', False)
        # Shared flag for running the PWM process
        self.running = multiprocessing.Value('b', False)
        self.process = None

        if self.is_experiment:
            # Initialize GPIO pins if in experiment mode
            GPIO.setmode(GPIO.BOARD)
            for pin in self.THRUSTER_PINS:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)

        # Register signal handlers
        signal.signal(signal.SIGINT, self._handle_exit)
        signal.signal(signal.SIGTERM, self._handle_exit)
    
    def _handle_exit(self, signum, frame):
        """Handle exit signals by setting the running flag to False."""
        print("Thrusters stopping...")
        
        # Only set running to False, don't do any cleanup yet
        with self.running.get_lock():
            self.running.value = False
        
        # If in main process, call stop
        if multiprocessing.current_process().name == 'MainProcess':
            self.stop()
        
    # Don't do anything else in the signal handler
    
    def start(self):
        """Start the PWM control process."""
        with self.running.get_lock():
            if not self.running.value:
                self.running.value = True
        # Choose the appropriate loop
        if self.is_experiment:
            target = self._pwm_control_loop
        else:
            target = self._simulate_pwm_control_loop
        
        self.process = multiprocessing.Process(target=target)
        self.process.daemon = True
        self.process.start()

    def stop(self):
        """Stop the PWM control process and clean up GPIO if needed."""
        # Set running to False if not already
        with self.running.get_lock():
            self.running.value = False
        
        if self.process and self.process.is_alive():
            try:
                # Give the process time to exit gracefully
                time.sleep(0.5)
                self.process.join(timeout=1.0)
                # Force terminate if still alive
                if self.process.is_alive():
                    self.process.terminate()
            except Exception as e:
                print(f"Process termination warning (safe to ignore): {e}")
        
        # Only cleanup in the main process
        if multiprocessing.current_process().name == 'MainProcess' and self.is_experiment:
            try:
                for pin in self.THRUSTER_PINS:
                    try:
                        GPIO.output(pin, GPIO.LOW)
                    except:
                        pass  # Ignore errors during shutdown
                GPIO.cleanup()
            except Exception as e:
                print(f"GPIO cleanup error (safe to ignore): {e}")
        
        print("Thrusters stopped.")
    
    def set_duty_cycle(self, thruster_index, duty_cycle):
        """
        Set the duty cycle for a specific thruster.
        
        Args:
            thruster_index (int): The thruster index (1-8)
            duty_cycle (float): The duty cycle value (0.0-1.0)
        """
        if 1 <= thruster_index <= self.NUM_THRUSTERS:
            clamped_duty_cycle = max(0.0, min(1.0, duty_cycle))
            with self.duty_cycle_lock:
                self.requested_duty_cycles[thruster_index - 1] = clamped_duty_cycle
                self.duty_cycle_updated.value = True
        else:
            raise ValueError(f"Thruster index must be between 1 and {self.NUM_THRUSTERS}")
    
    def set_all_duty_cycles(self, duty_cycles):
        """
        Set duty cycles for all thrusters at once.
        
        Args:
            duty_cycles (list): List of duty cycle values (0.0-1.0) for each thruster.
        """
        if len(duty_cycles) != self.NUM_THRUSTERS:
            raise ValueError(f"Must provide {self.NUM_THRUSTERS} duty cycle values")
        
        with self.duty_cycle_lock:
            for i, duty_cycle in enumerate(duty_cycles):
                self.requested_duty_cycles[i] = max(0.0, min(1.0, duty_cycle))
            self.duty_cycle_updated.value = True
    
    def get_state(self, thruster_index):
        """
        Get the current ON/OFF state of a specific thruster.
        """
        if 1 <= thruster_index <= self.NUM_THRUSTERS:
            return self.current_states[thruster_index - 1]
        else:
            raise ValueError(f"Thruster index must be between 1 and {self.NUM_THRUSTERS}")
    
    def get_all_states(self):
        """Return a copy of the current states of all thrusters."""
        return list(self.current_states)
    
    def get_duty_cycle(self, thruster_index):
        """
        Get the current duty cycle for a specific thruster.
        """
        if 1 <= thruster_index <= self.NUM_THRUSTERS:
            return self.duty_cycles[thruster_index - 1]
        else:
            raise ValueError(f"Thruster index must be between 1 and {self.NUM_THRUSTERS}")
    
    def get_all_duty_cycles(self):
        """Return a copy of the current duty cycles of all thrusters."""
        return list(self.duty_cycles)
    
    def set_pwm_frequency(self, frequency):
        """
        Set the PWM frequency.
        """
        if frequency <= 0:
            raise ValueError("PWM frequency must be greater than 0")
        self.pwm_frequency = frequency
        self.PERIOD = 1.0 / frequency

    def _set_realtime_priority(self):
        """
        Attempt to set SCHED_FIFO scheduling for the current process.
        """
        try:
            libc = ctypes.CDLL("libc.so.6")
            SCHED_FIFO = 1
            class sched_param(ctypes.Structure):
                _fields_ = [("sched_priority", ctypes.c_int)]
            param = sched_param()
            param.sched_priority = 99  # High priority
            if libc.sched_setscheduler(0, SCHED_FIFO, ctypes.byref(param)) != 0:
                print("Warning: Could not set real-time scheduler.")
        except Exception as e:
            print("Real-time scheduling not available:", e)

    def _pwm_control_loop(self):
        """
        The PWM control loop with error handling for safe shutdown.
        """
        self._set_realtime_priority()
        
        # Guard against exceptions during shutdown
        try:
            while self.running.value:
                cycle_start_time = perf_counter()
                
                # Update duty cycles if requested
                with self.duty_cycle_lock:
                    if self.duty_cycle_updated.value:
                        for i in range(self.NUM_THRUSTERS):
                            self.duty_cycles[i] = self.requested_duty_cycles[i]
                        self.duty_cycle_updated.value = False
                
                # Turn ON thrusters with exception handling
                for i in range(self.NUM_THRUSTERS):
                    try:
                        if self.running.value and self.duty_cycles[i] > 0:
                            GPIO.output(self.THRUSTER_PINS[i], GPIO.HIGH)
                            self.current_states[i] = True
                        elif self.running.value:
                            GPIO.output(self.THRUSTER_PINS[i], GPIO.LOW)
                            self.current_states[i] = False
                    except Exception:
                        # If error occurs (e.g. during shutdown), mark as off
                        self.current_states[i] = False
                
                elapsed_time = 0
                # PWM cycle with exception handling
                while elapsed_time < self.PERIOD and self.running.value:
                    current_time = perf_counter()
                    elapsed_time = current_time - cycle_start_time
                    
                    for i in range(self.NUM_THRUSTERS):
                        try:
                            on_duration = self.duty_cycles[i] * self.PERIOD
                            if self.running.value and self.current_states[i] and elapsed_time >= on_duration:
                                GPIO.output(self.THRUSTER_PINS[i], GPIO.LOW)
                                self.current_states[i] = False
                        except Exception:
                            # If error during shutdown, mark as off
                            self.current_states[i] = False
                    
                    # Short sleep to avoid CPU hogging
                    time.sleep(0.0001)
                
                # Exit early if we're shutting down
                if not self.running.value:
                    break
                    
                # Wait for next cycle
                remaining_time = self.PERIOD - elapsed_time
                if remaining_time > 0:
                    time.sleep(max(0, remaining_time))
        
        except Exception as e:
            print(f"PWM control loop error: {e}")
        
        finally:
            # Ensure cleanup in the process before exiting
            if self.is_experiment:
                try:
                    for i in range(self.NUM_THRUSTERS):
                        try:
                            GPIO.output(self.THRUSTER_PINS[i], GPIO.LOW)
                            self.current_states[i] = False
                        except:
                            pass
                except Exception:
                    pass

    def _simulate_pwm_control_loop(self):
        """
        A simulation PWM control loop that mirrors the hardware PWM logic
        but does not actually send commands to the GPIO. Instead, it updates
        internal states and prints events for debugging.
        """
        self._set_realtime_priority()
        while self.running.value:
            cycle_start_time = perf_counter()
            # Update duty cycles if requested at the beginning of the cycle
            with self.duty_cycle_lock:
                if self.duty_cycle_updated.value:
                    for i in range(self.NUM_THRUSTERS):
                        self.duty_cycles[i] = self.requested_duty_cycles[i]
                    self.duty_cycle_updated.value = False
            
            # Simulate turning ON thrusters based on duty cycle
            for i in range(self.NUM_THRUSTERS):
                if self.duty_cycles[i] > 0:
                    self.current_states[i] = True
                    #print(f"Thruster {i+1} simulated ON at t=0")
                else:
                    self.current_states[i] = False
            
            elapsed_time = 0
            # Simulate the PWM cycle: turn off thrusters when their on-duration expires
            while elapsed_time < self.PERIOD and self.running.value:
                current_time = perf_counter()
                elapsed_time = current_time - cycle_start_time
                for i in range(self.NUM_THRUSTERS):
                    on_duration = self.duty_cycles[i] * self.PERIOD
                    if self.current_states[i] and elapsed_time >= on_duration:
                        self.current_states[i] = False
                        #print(f"Thruster {i+1} simulated OFF at t={elapsed_time:.6f}s")
                # Small sleep to avoid hogging CPU while maintaining timing accuracy
                time.sleep(0.0001)
            
            # Maintain the PWM period precisely
            remaining_time = self.PERIOD - elapsed_time
            if remaining_time > 0:
                if remaining_time > 0.001:  # For delays longer than 1ms use time.sleep
                    time.sleep(remaining_time - 0.001)
                precise_delay_microsecond((remaining_time % 0.001) * 1e6)

    
    def _debug_pwm_control_loop(self):
        """
        A simplified PWM loop for simulation mode that prints cycle timing.
        Runs in a separate process with real-time scheduling.
        """
        self._set_realtime_priority()
        while self.running.value:
            cycle_start = perf_counter()
            # Simulate work
            for i in range(5):
                a = 5  # Dummy work
            
            elapsed = perf_counter() - cycle_start
            remaining_time = self.PERIOD - elapsed
            if remaining_time > 0:
                precise_delay_microsecond(remaining_time * 1e6)
            
            cycle_end = perf_counter()
            actual_cycle_time = cycle_end - cycle_start
            print(f"This loop took {actual_cycle_time:.6f} s (target: {self.PERIOD:.6f} s)")
