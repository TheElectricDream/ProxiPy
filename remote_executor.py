#!/usr/bin/env python3
import os
import sys
import argparse
import paramiko
import tarfile
import tempfile
from concurrent.futures import ThreadPoolExecutor

class RemoteExecutor:
    def __init__(self, hosts, username, key_path=None, password=None, port=22):
        """
        Initialize the remote executor with connection details
        
        Args:
            hosts (list): List of hostnames or IPs to connect to
            username (str): SSH username
            key_path (str, optional): Path to SSH private key
            password (str, optional): SSH password (if not using key)
            port (int): SSH port number
        """
        self.hosts = hosts
        self.username = username
        self.key_path = key_path
        self.password = password
        self.port = port
        
    def _create_tarball(self, project_dir):
        """Create a temporary tarball of the project directory"""
        temp_dir = tempfile.gettempdir()
        tarball_path = os.path.join(temp_dir, "project.tar.gz")
        
        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(project_dir, arcname=os.path.basename(project_dir))
            
        return tarball_path
    
    def _get_ssh_client(self, host):
        """Create and return a configured SSH client"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        connect_kwargs = {
            'hostname': host,
            'username': self.username,
            'port': self.port
        }
        
        if self.key_path:
            connect_kwargs['key_filename'] = self.key_path
        elif self.password:
            connect_kwargs['password'] = self.password
        
        client.connect(**connect_kwargs)
        return client
    
    def _deploy_and_execute(self, host, project_dir, tarball_path, remote_dir="~/remote_project", 
                          command="python main.py", extra_args=None):
        """Deploy and execute the project on a single remote host"""
        try:
            print(f"Connecting to {host}...")
            client = self._get_ssh_client(host)
            sftp = client.open_sftp()
            
            # Create remote directory if it doesn't exist
            stdin, stdout, stderr = client.exec_command(f"mkdir -p {remote_dir}")
            stdout.channel.recv_exit_status()
            
            # Upload the tarball
            remote_tarball = f"{remote_dir}/project.tar.gz"
            print(f"Uploading project to {host}...")
            sftp.put(tarball_path, remote_tarball)
            
            # Extract on remote host
            print(f"Extracting project on {host}...")
            extract_cmd = f"cd {remote_dir} && tar -xzf project.tar.gz"
            stdin, stdout, stderr = client.exec_command(extract_cmd)
            stdout.channel.recv_exit_status()
            
            # Run the project
            project_name = os.path.basename(project_dir)
            run_cmd = f"cd {remote_dir}/{project_name} && {command}"
            if extra_args:
                run_cmd += f" {extra_args}"
                
            print(f"Running project on {host}...")
            stdin, stdout, stderr = client.exec_command(run_cmd)
            
            # Print output in real-time
            while not stdout.channel.exit_status_ready():
                if stdout.channel.recv_ready():
                    output = stdout.channel.recv(1024).decode('utf-8')
                    print(f"{host} output: {output}", end='')
            
            # Get any remaining output
            output = stdout.read().decode('utf-8')
            if output:
                print(f"{host} output: {output}")
                
            # Check for errors
            errors = stderr.read().decode('utf-8')
            if errors:
                print(f"{host} errors: {errors}")
                
            exit_status = stdout.channel.recv_exit_status()
            print(f"Execution on {host} completed with status {exit_status}")
            
            sftp.close()
            client.close()
            return host, exit_status == 0
            
        except Exception as e:
            print(f"Error on {host}: {str(e)}")
            return host, False
    
    def deploy_and_execute(self, project_dir, remote_dir="~/remote_project", 
                          command="python main.py", extra_args=None, max_workers=None):
        """
        Deploy project to all hosts and execute the given command
        
        Args:
            project_dir (str): Local project directory path
            remote_dir (str): Remote directory to deploy to
            command (str): Command to execute (default: "python main.py")
            extra_args (str): Extra arguments to pass to the command
            max_workers (int): Maximum number of concurrent deployments
        
        Returns:
            dict: Results of execution for each host
        """
        # Create tarball of project
        tarball_path = self._create_tarball(project_dir)
        results = {}
        
        # Deploy and execute on each host in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for host in self.hosts:
                future = executor.submit(
                    self._deploy_and_execute, 
                    host, 
                    project_dir,
                    tarball_path,
                    remote_dir,
                    command,
                    extra_args
                )
                futures.append(future)
            
            # Collect results
            for future in futures:
                host, success = future.result()
                results[host] = success
        
        # Clean up
        os.remove(tarball_path)
        return results


def main():
    parser = argparse.ArgumentParser(description='Deploy and execute Python projects on remote hosts')
    parser.add_argument('project_dir', help='Path to the project directory')
    parser.add_argument('--hosts', required=True, nargs='+', help='Remote hosts to deploy to')
    parser.add_argument('--username', required=True, help='SSH username')
    parser.add_argument('--key', help='Path to SSH private key')
    parser.add_argument('--password', help='SSH password (not recommended, use key authentication)')
    parser.add_argument('--port', type=int, default=22, help='SSH port (default: 22)')
    parser.add_argument('--remote-dir', default='~/remote_project', help='Remote directory to deploy to')
    parser.add_argument('--command', default='python main.py', help='Command to execute')
    parser.add_argument('--args', help='Extra arguments to pass to the command')
    
    args = parser.parse_args()
    
    if not args.key and not args.password:
        parser.error("Either --key or --password must be provided")
    
    executor = RemoteExecutor(
        hosts=args.hosts,
        username=args.username,
        key_path=args.key,
        password=args.password,
        port=args.port
    )
    
    results = executor.deploy_and_execute(
        project_dir=args.project_dir,
        remote_dir=args.remote_dir,
        command=args.command,
        extra_args=args.args
    )
    
    # Print summary
    print("\nExecution summary:")
    for host, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        print(f"{host}: {status}")
    
    # Exit with error if any host failed
    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()