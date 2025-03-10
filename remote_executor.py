#!/usr/bin/env python3
"""
remote_executor.py - A CLI tool to copy files to a remote computer, 
execute a script, and retrieve generated data.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Copy files to a remote server, execute main.py, and retrieve data files."
    )
    
    parser.add_argument(
        "-H", "--host", 
        required=True,
        help="Remote host address (IP or hostname)"
    )
    
    parser.add_argument(
        "-u", "--user", 
        default=os.environ.get("USER", "user"),
        help="Username for SSH connection (default: current user)"
    )
    
    parser.add_argument(
        "-i", "--identity", 
        help="Path to SSH identity file (private key)"
    )
    
    parser.add_argument(
        "-p", "--port", 
        type=int, 
        default=22,
        help="SSH port (default: 22)"
    )
    
    parser.add_argument(
        "-d", "--directory", 
        default=os.getcwd(),
        help="Local directory to sync (default: current directory)"
    )
    
    return parser.parse_args()

def get_ssh_command(args, command=None):
    """Build SSH command with appropriate options"""
    ssh_cmd = ["ssh"]
    
    if args.identity:
        ssh_cmd.extend(["-i", args.identity])
    
    ssh_cmd.extend(["-p", str(args.port), f"{args.user}@{args.host}"])
    
    if command:
        ssh_cmd.append(command)
    
    return ssh_cmd

def run_command(command, check=True):
    """Run command and return result, optionally checking for errors"""
    try:
        result = subprocess.run(
            command,
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {' '.join(command)}")
        print(f"Exit code: {e.returncode}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        sys.exit(1)

def ensure_remote_directory(args):
    """Ensure the destination directory exists on the remote host"""
    remote_dir = "~/Documents"
    command = f"mkdir -p {remote_dir}"
    run_command(get_ssh_command(args, command))
    print(f"✅ Ensured remote directory exists: {remote_dir}")

def rsync_files_to_remote(args, exclude_data=True):
    """Copy files to remote host using rsync, optionally excluding data directory"""
    local_dir = args.directory.rstrip("/") + "/"
    remote_path = f"{args.user}@{args.host}:~/Documents/"
    
    # Build proper SSH command for rsync
    ssh_cmd = "ssh"
    if args.identity:
        ssh_cmd += f" -i {args.identity}"
    ssh_cmd += f" -p {args.port}"
    
    rsync_cmd = ["rsync", "-avz", "--progress"]
    
    # Exclude hidden files and optionally data directory
    rsync_cmd.append("--exclude=.*")
    if exclude_data:
        rsync_cmd.append("--exclude=data/")
    
    # Add SSH options correctly
    rsync_cmd.extend(["-e", ssh_cmd])
    
    rsync_cmd.extend([local_dir, remote_path])
    
    print(f"📤 Copying files to {remote_path}...")
    print(f"Running command: {' '.join(rsync_cmd)}")
    run_command(rsync_cmd)
    print("✅ Files copied successfully!")

def execute_remote_script(args):
    """Execute main.py on the remote host and stream output"""
    print("\n🚀 Executing main.py on remote host...")
    command = f"cd ~/Documents && python3 main.py"
    
    # Use subprocess.Popen to stream output in real-time
    process = subprocess.Popen(
        get_ssh_command(args, command),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Print output as it comes
    for line in process.stdout:
        print(line, end="")
    
    exit_code = process.wait()
    if exit_code != 0:
        print(f"⚠️ Remote script exited with non-zero code: {exit_code}")
        return False
    
    print("✅ Remote script execution completed successfully!")
    return True

def rsync_data_back(args):
    """Copy data directory from remote host back to local machine"""
    print("\n📥 Copying data directory from remote host...")
    local_data_dir = Path(args.directory) / "data"
    if not local_data_dir.exists():
        os.makedirs(local_data_dir, exist_ok=True)
    
    remote_data_path = f"{args.user}@{args.host}:~/Documents/data/"
    local_data_path = str(local_data_dir) + "/"
    
    # Build proper SSH command for rsync
    ssh_cmd = "ssh"
    if args.identity:
        ssh_cmd += f" -i {args.identity}"
    ssh_cmd += f" -p {args.port}"
    
    rsync_cmd = ["rsync", "-avz", "--progress", "-e", ssh_cmd, remote_data_path, local_data_path]
    
    print(f"Running command: {' '.join(rsync_cmd)}")
    run_command(rsync_cmd)
    print("✅ Data directory copied successfully!")

def main():
    args = parse_arguments()
    
    print(f"🔄 Remote Executor starting...")
    print(f"📡 Target: {args.user}@{args.host}:{args.port}")
    
    # Check if we can connect to the remote host
    print("🔍 Testing SSH connection...")
    test_result = run_command(get_ssh_command(args, "echo Connection successful"), check=False)
    if test_result.returncode != 0:
        print("❌ Failed to connect to remote host!")
        print(f"Error: {test_result.stderr}")
        sys.exit(1)
    print("✅ SSH connection successful!")
    
    # Ensure remote directory exists
    ensure_remote_directory(args)
    
    # Copy files (excluding data directory)
    rsync_files_to_remote(args, exclude_data=True)
    
    # Execute the main.py script on the remote host
    success = execute_remote_script(args)
    
    # Copy data directory back if execution was successful
    if success:
        rsync_data_back(args)
    
    print("\n🎉 Remote Executor completed!")

if __name__ == "__main__":
    main()