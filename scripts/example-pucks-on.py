# Import system libraries
import os
import sys

# Add the project path so that lib files can be read
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from tools.utils import enable_disable_pucks

# Enable all pucks
enable_disable_pucks(False)

