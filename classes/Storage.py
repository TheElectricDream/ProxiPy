import numpy as np
from datetime import datetime

class Storage:
    def __init__(self, expected_size=1000):
        """
        Initializes a storage container with pre-allocated arrays.
        
        Args:
            expected_size (int): Expected number of data points to store
        """
        self.expected_size = expected_size
        self.data = {}
        self.current_index = 0
        
    def initialize_arrays(self, keys):
        """
        Pre-allocate arrays for all expected keys.
        
        Args:
            keys (list): List of keys to initialize
        """
        for key in keys:
            self.data[key] = np.zeros(self.expected_size)
        
    def append_data_batch(self, data_dict):
        """
        Append multiple data points at once.
        
        Args:
            data_dict (dict): Dictionary mapping keys to values
        """
        if self.current_index >= self.expected_size:
            # Resize arrays if needed
            self._resize_arrays()
            
        for key, value in data_dict.items():
            if key not in self.data:
                # Initialize a new array if this key wasn't pre-allocated
                self.data[key] = np.zeros(self.expected_size)
            
            self.data[key][self.current_index] = value
            
        self.current_index += 1
        
    def _resize_arrays(self):
        """Resize all arrays to accommodate more data points"""
        new_size = self.expected_size * 2
        for key in self.data:
            temp = np.zeros(new_size)
            temp[:self.expected_size] = self.data[key]
            self.data[key] = temp
        
        self.expected_size = new_size
    
    def get_all_data(self, key):
        """Get all data for a given key up to the current index"""
        if key in self.data:
            return self.data[key][:self.current_index]
        return np.array([])
    
    def get_latest_data(self, key):
        """Get the most recent value for a key"""
        if key in self.data and self.current_index > 0:
            return self.data[key][self.current_index - 1]
        return None
    
    def write_to_npy(self):
        """Save data to a .npy file, truncating arrays to actual used size"""
        # Create a new dictionary with truncated arrays
        output_data = {}
        for key in self.data:
            output_data[key] = self.data[key][:self.current_index]
            
        filename = f"data/data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.npy"
        np.save(filename, output_data)