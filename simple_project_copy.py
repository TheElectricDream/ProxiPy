import os
import paramiko
import shlex
from scp import SCPClient

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
    
    def transfer_files(self):
        """Transfer files to the remote server.
        
        Returns:
            int: The number of files transferred
        """
        # Set up SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect using password or SSH key
        if self.ssh_key_path:
            ssh.connect(self.remote_host, username=self.remote_user, key_filename=self.ssh_key_path)
        else:
            ssh.connect(self.remote_host, username=self.remote_user, password=self.remote_password)
        
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


# Sample main function
def main():
    # Configuration for spot-red
    red_config = {
        'remote_host': '192.168.1.110',
        'remote_user': 'spot-red',
        'remote_password': 'srcl2023',
        'remote_path': '/home/spot-red/Documents/TMP'
    }
    
    # Configuration for spot-black
    black_config = {
        'remote_host': '192.168.1.111',
        'remote_user': 'spot-black',
        'remote_password': 'srcl2023',
        'remote_path': '/home/spot-black/Documents/TMP'
    }
    
    # Create transfer instances
    red_transfer = ProjectTransfer(**red_config)
    black_transfer = ProjectTransfer(**black_config)
    
    # Add any additional file types to exclude if needed
    # red_transfer.add_excluded_extension('.data')
    # black_transfer.add_excluded_extension('.data')
    
    # Transfer files
    print("Starting transfer to spot-red...")
    red_transfer.transfer_files()
    
    print("\nStarting transfer to spot-black...")
    black_transfer.transfer_files()
    
    print("\nAll transfers complete!")


if __name__ == "__main__":
    main()