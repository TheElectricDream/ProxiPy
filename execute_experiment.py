import os
import paramiko
import shlex
from scp import SCPClient
import time

class ProjectTransfer:
    def __init__(self, remote_host, remote_user, remote_path, remote_password=None, ssh_key_path=None):
        """Initialize the ProjectTransfer with connection details.
        
        Args:
            remote_host: The hostname or IP address of the remote server
            remote_user: The username for the remote server
            remote_path: The destination directory on the remote server
            remote_password: The password for the remote server (None if using SSH key)
            ssh_key_path: Path to the SSH key file (None if using password)
        """
        self.remote_host = remote_host
        self.remote_user = remote_user
        self.remote_password = remote_password
        self.remote_path = os.path.normpath(remote_path)
        self.ssh_key_path = ssh_key_path
        
        # Directories to exclude
        self.exclude_dirs = [".venv", ".git"]
        
        # File extensions to exclude
        self.exclude_extensions = [".npy"]
        
        # Required packages for the virtual environment
        self.required_packages = ["pybind11", "numpy", "plotly", "matplotlib", "BMI160_i2c"]
        
        # Get the script's directory and file name
        self.script_path = os.path.abspath(__file__)
        self.folder_to_copy = os.path.dirname(self.script_path)
        self.script_name = os.path.basename(self.script_path)
        
        # Normalize paths
        self.folder_to_copy = os.path.normpath(self.folder_to_copy)
    
    def should_skip_file(self, filename):
        """Determine if a file should be skipped during transfer.
        
        Args:
            filename: The name of the file to check
            
        Returns:
            bool: True if the file should be skipped, False otherwise
        """
        # Skip the script itself
        if filename == self.script_name:
            return True
            
        # Skip files with excluded extensions
        for ext in self.exclude_extensions:
            if filename.endswith(ext):
                return True
                
        return False
    
    def should_skip_directory(self, dirname):
        """Determine if a directory should be skipped during transfer.
        
        Args:
            dirname: The name of the directory to check
            
        Returns:
            bool: True if the directory should be skipped, False otherwise
        """
        return dirname in self.exclude_dirs
    
    def count_eligible_files(self):
        """Count the number of files that will be transferred.
        
        Returns:
            int: The number of eligible files
        """
        eligible_files = 0
        for root, dirs, files in os.walk(self.folder_to_copy):
            # Skip excluded directories
            dirs_to_remove = [d for d in dirs if self.should_skip_directory(d)]
            for d in dirs_to_remove:
                dirs.remove(d)
            
            # Count eligible files
            for file in files:
                if not self.should_skip_file(file):
                    eligible_files += 1
        
        return eligible_files
    
    def connect_ssh(self):
        """Establish an SSH connection to the remote server.
        
        Returns:
            paramiko.SSHClient: An established SSH client
        """
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect using password or SSH key
        if self.ssh_key_path:
            ssh.connect(self.remote_host, username=self.remote_user, key_filename=self.ssh_key_path)
        else:
            ssh.connect(self.remote_host, username=self.remote_user, password=self.remote_password)
        
        return ssh
    
    def transfer_files(self):
        """Transfer files to the remote server.
        
        Returns:
            int: The number of files transferred
        """
        # Set up SSH client
        ssh = self.connect_ssh()
        
        # Create SCP client
        scp = SCPClient(ssh.get_transport())
        
        # Count eligible files
        eligible_files = self.count_eligible_files()
        print(f"Preparing to transfer {eligible_files} files to {self.remote_host}...")
        
        # Walk through the folder and transfer files
        file_count = 0
        skipped_count = 0
        
        for root, dirs, files in os.walk(self.folder_to_copy):
            # Skip excluded directories
            dirs_to_remove = [d for d in dirs if self.should_skip_directory(d)]
            for d in dirs_to_remove:
                dirs.remove(d)
            
            # Calculate relative path
            rel_path = os.path.relpath(root, self.folder_to_copy)
            remote_folder = os.path.join(self.remote_path, rel_path)
            remote_folder = remote_folder.replace("\\", "/")  # Ensure proper format for remote system
            
            # Ensure remote directory exists
            ssh.exec_command(f"mkdir -p {shlex.quote(remote_folder)}")
            
            # Copy files
            for file in files:
                if self.should_skip_file(file):
                    print(f"Skipping: {file}")
                    skipped_count += 1
                    continue
                    
                local_file_path = os.path.join(root, file)
                remote_file_path = os.path.join(remote_folder, file).replace("\\", "/")
                
                print(f"Copying [{file_count+1}/{eligible_files}]: {file} to {self.remote_host}")
                scp.put(local_file_path, remote_file_path)
                file_count += 1
        
        print(f"Successfully transferred {file_count} files to {self.remote_host}.")
        print(f"Skipped {skipped_count} files (including .npy files).")
        
        # Close connections
        scp.close()
        ssh.close()
        
        return file_count
    
    def check_venv_exists(self, venv_name=".venv"):
        """Check if a virtual environment exists on the remote server.
        
        Args:
            venv_name: The name of the virtual environment directory
            
        Returns:
            bool: True if the virtual environment exists, False otherwise
        """
        ssh = self.connect_ssh()
        remote_venv_path = os.path.join(self.remote_path, venv_name).replace("\\", "/")
        
        # Check if the venv directory exists
        stdin, stdout, stderr = ssh.exec_command(f"test -d {shlex.quote(remote_venv_path)} && echo 'exists'")
        exists = stdout.read().decode().strip() == 'exists'
        
        # Check if the python executable exists in the venv
        if exists:
            stdin, stdout, stderr = ssh.exec_command(
                f"test -f {shlex.quote(remote_venv_path)}/bin/python && echo 'exists'"
            )
            python_exists = stdout.read().decode().strip() == 'exists'
            exists = exists and python_exists
        
        ssh.close()
        return exists
    
    def check_venv_packages(self, venv_name=".venv"):
        """Check if the virtual environment has all required packages.
        
        Args:
            venv_name: The name of the virtual environment directory
            
        Returns:
            bool: True if all required packages are installed, False otherwise
        """
        ssh = self.connect_ssh()
        remote_venv_path = os.path.join(self.remote_path, venv_name).replace("\\", "/")
        
        # Get list of installed packages
        cmd = f"{shlex.quote(remote_venv_path)}/bin/pip freeze"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        installed_packages = stdout.read().decode().lower()
        
        # Check if each required package is installed
        all_packages_installed = True
        missing_packages = []
        
        for package in self.required_packages:
            # Check if package is in the pip freeze output
            # This handles different formats like package==version or package-name==version
            package_lower = package.lower()
            if not any(line.lower().startswith(package_lower + "==") or 
                     line.lower().startswith(package_lower.replace("_", "-") + "==") for line in installed_packages.split('\n')):
                all_packages_installed = False
                missing_packages.append(package)
        
        ssh.close()
        return all_packages_installed, missing_packages
    
    def check_venv_python_version(self, venv_name=".venv"):
        """Check the Python version in the virtual environment.
        
        Args:
            venv_name: The name of the virtual environment directory
            
        Returns:
            str: The Python version or None if not available
        """
        ssh = self.connect_ssh()
        remote_venv_path = os.path.join(self.remote_path, venv_name).replace("\\", "/")
        
        # Get Python version
        cmd = f"{shlex.quote(remote_venv_path)}/bin/python --version"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        version_output = stdout.read().decode().strip()
        
        ssh.close()
        return version_output if version_output else None
    
    def create_virtual_environment(self, venv_name=".venv"):
        """Create a virtual environment on the remote server with the specified dependencies.
        If a valid environment already exists, it will be kept.
        
        Args:
            venv_name: The name of the virtual environment directory
            
        Returns:
            bool: True if successful, False if there was an error
        """
        print(f"\nChecking virtual environment '{venv_name}' on {self.remote_host}...")
        
        # Check if virtual environment exists
        venv_exists = self.check_venv_exists(venv_name)
        
        if venv_exists:
            # Check Python version
            python_version = self.check_venv_python_version(venv_name)
            print(f"Found existing virtual environment with {python_version}")
            
            # Check if all required packages are installed
            all_packages_installed, missing_packages = self.check_venv_packages(venv_name)
            
            if all_packages_installed:
                print(f"The existing virtual environment has all required packages installed.")
                print(f"Skipping virtual environment creation.")
                return True
            else:
                print(f"The existing virtual environment is missing the following packages: {', '.join(missing_packages)}")
                print(f"Will install missing packages in the existing environment.")
                
                # Install missing packages only
                return self._install_packages(venv_name, missing_packages)
        else:
            print(f"No valid virtual environment found. Creating a new one...")
            return self._create_new_venv(venv_name)
    
    def _create_new_venv(self, venv_name=".venv"):
        """Create a new virtual environment and install all required packages.
        
        Args:
            venv_name: The name of the virtual environment directory
            
        Returns:
            bool: True if successful, False if there was an error
        """
        # Establish SSH connection
        ssh = self.connect_ssh()
        
        try:
            # Full path to the virtual environment
            remote_venv_path = os.path.join(self.remote_path, venv_name).replace("\\", "/")
            
            # Remove existing virtual environment if it exists
            print(f"Removing any existing '{venv_name}' directory...")
            ssh.exec_command(f"rm -rf {shlex.quote(remote_venv_path)}")
            
            # Create new virtual environment with system site packages
            print(f"Creating new virtual environment with system site packages...")
            cmd_create_venv = f"cd {shlex.quote(self.remote_path)} && /usr/bin/python3.8 -m venv --system-site-packages {shlex.quote(venv_name)}"
            
            stdin, stdout, stderr = ssh.exec_command(cmd_create_venv)
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status != 0:
                print(f"Error creating virtual environment: {stderr.read().decode()}")
                ssh.close()
                return False
            
            # Install pybind11 first
            print("Installing pybind11...")
            cmd_install_pybind = f"cd {shlex.quote(self.remote_path)} && {shlex.quote(remote_venv_path)}/bin/pip install pybind11"
            stdin, stdout, stderr = ssh.exec_command(cmd_install_pybind)
            self._stream_output(stdout)
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status != 0:
                print(f"Error installing pybind11: {stderr.read().decode()}")
                ssh.close()
                return False
            
            # Upgrade pip and wheel
            print("Upgrading pip and wheel...")
            cmd_upgrade_pip = f"cd {shlex.quote(self.remote_path)} && {shlex.quote(remote_venv_path)}/bin/pip install --upgrade pip wheel"
            stdin, stdout, stderr = ssh.exec_command(cmd_upgrade_pip)
            self._stream_output(stdout)
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status != 0:
                print(f"Error upgrading pip and wheel: {stderr.read().decode()}")
                ssh.close()
                return False
            
            # Upgrade scipy
            print("Upgrading scipy...")
            cmd_upgrade_scipy = f"cd {shlex.quote(self.remote_path)} && {shlex.quote(remote_venv_path)}/bin/pip install --upgrade scipy"
            stdin, stdout, stderr = ssh.exec_command(cmd_upgrade_scipy)
            self._stream_output(stdout)
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status != 0:
                print(f"Error upgrading scipy: {stderr.read().decode()}")
                ssh.close()
                return False
            
            # Install other required packages
            packages_to_install = [p for p in self.required_packages if p != "pybind11"]  # pybind11 already installed
            print(f"Installing required packages: {', '.join(packages_to_install)}...")
            cmd_install_packages = f"cd {shlex.quote(self.remote_path)} && {shlex.quote(remote_venv_path)}/bin/pip install {' '.join(packages_to_install)}"
            stdin, stdout, stderr = ssh.exec_command(cmd_install_packages)
            self._stream_output(stdout)
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status != 0:
                print(f"Error installing required packages: {stderr.read().decode()}")
                ssh.close()
                return False
            
            print(f"Virtual environment '{venv_name}' created successfully on {self.remote_host}.")
            ssh.close()
            return True
            
        except Exception as e:
            print(f"Error setting up virtual environment: {str(e)}")
            ssh.close()
            return False
    
    def _install_packages(self, venv_name, packages):
        """Install specific packages in an existing virtual environment.
        
        Args:
            venv_name: The name of the virtual environment directory
            packages: List of packages to install
            
        Returns:
            bool: True if successful, False if there was an error
        """
        if not packages:
            return True
            
        ssh = self.connect_ssh()
        remote_venv_path = os.path.join(self.remote_path, venv_name).replace("\\", "/")
        
        try:
            # Check if we need to upgrade pip and wheel
            print("Upgrading pip and wheel...")
            cmd_upgrade_pip = f"cd {shlex.quote(self.remote_path)} && {shlex.quote(remote_venv_path)}/bin/pip install --upgrade pip wheel"
            stdin, stdout, stderr = ssh.exec_command(cmd_upgrade_pip)
            self._stream_output(stdout)
            
            # Check if scipy upgrade is needed
            if "scipy" in packages:
                print("Upgrading scipy...")
                cmd_upgrade_scipy = f"cd {shlex.quote(self.remote_path)} && {shlex.quote(remote_venv_path)}/bin/pip install --upgrade scipy"
                stdin, stdout, stderr = ssh.exec_command(cmd_upgrade_scipy)
                self._stream_output(stdout)
                packages.remove("scipy")
            
            # Install remaining packages
            if packages:
                print(f"Installing missing packages: {', '.join(packages)}...")
                cmd_install_packages = f"cd {shlex.quote(self.remote_path)} && {shlex.quote(remote_venv_path)}/bin/pip install {' '.join(packages)}"
                stdin, stdout, stderr = ssh.exec_command(cmd_install_packages)
                self._stream_output(stdout)
                exit_status = stdout.channel.recv_exit_status()
                
                if exit_status != 0:
                    print(f"Error installing packages: {stderr.read().decode()}")
                    ssh.close()
                    return False
            
            print(f"All required packages installed successfully in existing virtual environment.")
            ssh.close()
            return True
            
        except Exception as e:
            print(f"Error installing packages in existing virtual environment: {str(e)}")
            ssh.close()
            return False
    
    def _stream_output(self, stdout):
        """Stream the output from a remote command.
        
        Args:
            stdout: The stdout from the command
        """
        while not stdout.channel.exit_status_ready():
            if stdout.channel.recv_ready():
                output = stdout.channel.recv(1024).decode()
                print(output, end='')
    
    def add_excluded_extension(self, extension):
        """Add a file extension to the exclusion list.
        
        Args:
            extension: The file extension to exclude (e.g., '.npy')
        """
        if not extension.startswith('.'):
            extension = '.' + extension
        if extension not in self.exclude_extensions:
            self.exclude_extensions.append(extension)
    
    def add_excluded_directory(self, dirname):
        """Add a directory name to the exclusion list.
        
        Args:
            dirname: The directory name to exclude (e.g., '.git')
        """
        if dirname not in self.exclude_dirs:
            self.exclude_dirs.append(dirname)

    def execute_remote_script(self, script_path, command_args=None, env_vars=None, input_values=None):
        """Execute a Python script within the virtual environment on the remote server.
        
        Args:
            script_path: The path to the script relative to the remote_path
            command_args: Optional string of arguments to pass to the script
            env_vars: Optional dictionary of environment variables to set
            input_values: Optional string of input values to feed to stdin
            
        Returns:
            tuple: (bool, str) where bool indicates success/failure and str contains the output
        """
        # Normalize the script path and ensure it uses Unix-style forward slashes
        norm_script_path = os.path.normpath(script_path).replace("\\", "/")
        remote_script_path = os.path.join(self.remote_path, norm_script_path).replace("\\", "/")
        
        # Build the command to execute the script inside the virtual environment
        venv_python = os.path.join(self.remote_path, ".venv/bin/python").replace("\\", "/")
        
        # Add command arguments if provided
        cmd_suffix = f" {command_args}" if command_args else ""
        
        # Prepare environment variables if provided
        env_prefix = ""
        if env_vars and isinstance(env_vars, dict):
            env_parts = []
            for key, value in env_vars.items():
                env_parts.append(f"{key}={shlex.quote(str(value))}")
            if env_parts:
                env_prefix = " ".join(env_parts) + " "
        
        # Construct the full command
        cmd = f"cd {shlex.quote(self.remote_path)} && {env_prefix}{shlex.quote(venv_python)} {shlex.quote(remote_script_path)}{cmd_suffix}"
        
        print(f"\nExecuting script on {self.remote_host}:")
        print(f"> {norm_script_path}{cmd_suffix}")
        if env_vars:
            print(f"With environment variables: {env_vars}")
        if input_values:
            print(f"With input values provided")
        
        try:
            # Connect to SSH
            ssh = self.connect_ssh()
            
            # Execute the command
            stdin, stdout, stderr = ssh.exec_command(cmd)
            
            # Send input values if provided
            if input_values:
                stdin.write(input_values)
                stdin.flush()
                stdin.channel.shutdown_write()  # Signal that no more input will be sent
            
            # Stream output in real-time
            output = ""
            while not stdout.channel.exit_status_ready():
                if stdout.channel.recv_ready():
                    data = stdout.channel.recv(1024).decode()
                    output += data
                    print(data, end='')
            
            # Get any remaining output
            data = stdout.read().decode()
            if data:
                output += data
                print(data, end='')
            
            # Check for errors
            error_output = stderr.read().decode()
            if error_output:
                print(f"\nErrors encountered while executing script:")
                print(error_output)
                output += "\n" + error_output
            
            # Get exit status
            exit_status = stdout.channel.recv_exit_status()
            success = (exit_status == 0)
            
            if success:
                print(f"\nScript executed successfully on {self.remote_host}")
            else:
                print(f"\nScript execution failed on {self.remote_host} with exit code {exit_status}")
            
            # Close the connection
            ssh.close()
            
            return success, output
            
        except Exception as e:
            print(f"\nError executing script on {self.remote_host}: {str(e)}")
            return False, str(e)


# Sample main function
def main():
    # Configuration for spot-red
    red_config = {
        'remote_host': '192.168.1.110',
        'remote_user': 'spot-red',
        'remote_password': 'srcl2023',
        'remote_path': '/home/spot-red/Documents/ProxiPy_WD'
    }
    
    # Configuration for spot-black
    black_config = {
        'remote_host': '192.168.1.111',
        'remote_user': 'spot-black',
        'remote_password': 'srcl2023',
        'remote_path': '/home/spot-black/Documents/ProxiPy_WD'
    }
    
    # Create transfer instances
    red_transfer = ProjectTransfer(**red_config)
    black_transfer = ProjectTransfer(**black_config)
    
    # Transfer files to spot-red
    print("Starting transfer to spot-red...")
    red_transfer.transfer_files()
    
    # Create or verify virtual environment on spot-red
    red_transfer.create_virtual_environment()
    
    # Transfer files to spot-black
    print("\nStarting transfer to spot-black...")
    black_transfer.transfer_files()
    
    # Create or verify virtual environment on spot-black
    black_transfer.create_virtual_environment()
    
    print("\nAll transfers and virtual environment setups complete!")
    
    # # Ask user if this is an experiment
    # is_experiment = input("\nIs this an experiment? (yes/no): ").lower().strip() in ['yes', 'y', 'true', '1']
    # experiment_value = True if is_experiment else False
    
    # # Execute main.py on both computers
    # print("\n" + "="*50)
    # print("EXECUTING REMOTE SCRIPTS")
    # print("="*50)
    
    # # Run on spot-red
    # print("\nExecuting main.py on spot-red...")
    # red_success, red_output = red_transfer.execute_remote_script(
    #     "main/main.py", 
    #     command_args="--experiment"
    # )
    
    # # Run on spot-black
    # print("\nExecuting main.py on spot-black...")
    # black_success, black_output = black_transfer.execute_remote_script(
    #     "main/main.py", 
    #     command_args="--experiment"
    # )
    
    # # Summary
    # print("\n" + "="*50)
    # print("EXECUTION SUMMARY")
    # print("="*50)
    # print(f"spot-red execution: {'SUCCESS' if red_success else 'FAILED'}")
    # print(f"spot-black execution: {'SUCCESS' if black_success else 'FAILED'}")


if __name__ == "__main__":
    main()