import paramiko
import time
import requests
from typing import Tuple
from dotenv import load_dotenv
import os
import yaml

# Load environment variables
load_dotenv()

def get_router_config() -> dict:
    """Load router configuration from config.yml with fallback to environment variables"""
    try:
        # Try to load from config.yml
        with open('config.yml', 'r') as f:
            config = yaml.safe_load(f)
            
        router_config = config.get('router', {})
        
        # If any required values are missing in config.yml, try env vars
        if not all([router_config.get(key) for key in ['ip', 'username', 'password']]):
            router_config = {
                'ip': os.getenv('ROUTER_IP') or router_config.get('ip'),
                'username': os.getenv('ROUTER_USERNAME') or router_config.get('username'),
                'password': os.getenv('ROUTER_PASSWORD') or router_config.get('password'),
                'reboot_command': os.getenv('ROUTER_REBOOT_COMMAND') or router_config.get('reboot_command', 'reboot')
            }
            
        # Verify all required values are present
        if not all([router_config.get(key) for key in ['ip', 'username', 'password', 'reboot_command']]):
            raise ValueError("Router configuration incomplete. Check config.yml or .env file")
            
        return router_config
        
    except FileNotFoundError:
        # If config.yml doesn't exist, try environment variables
        router_config = {
            'ip': os.getenv('ROUTER_IP'),
            'username': os.getenv('ROUTER_USERNAME'),
            'password': os.getenv('ROUTER_PASSWORD'),
            'reboot_command': os.getenv('ROUTER_REBOOT_COMMAND', 'reboot')
        }
        
        if not all([router_config.get(key) for key in ['ip', 'username', 'password']]):
            raise ValueError("Router configuration not found in environment variables")
            
        return router_config

def get_public_ip() -> str:
    """Get the current public IP address using ipify API"""
    try:
        response = requests.get('https://api.ipify.org?format=json')
        return response.json()['ip']
    except Exception as e:
        print(f"Error getting public IP: {e}")
        return None

def reboot_router(host: str, username: str, password: str, command: str) -> Tuple[bool, str]:
    """
    Reboot the router using SSH and return status and error message if any
    """
    try:
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect to router
        print(f"Connecting to {host}...")
        ssh.connect(host, username=username, password=password)
        
        # Execute reboot command
        print(f"Executing reboot command: {command}")
        stdin, stdout, stderr = ssh.exec_command(command)
        
        # Close SSH connection
        ssh.close()
        
        return True, "Router reboot command executed successfully"
        
    except Exception as e:
        return False, f"Error rebooting router: {e}"

def main():
    # Get router configuration
    try:
        router_config = get_router_config()
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return
    
    # Get initial IP
    print("Getting initial public IP...")
    initial_ip = get_public_ip()
    print(f"Initial public IP: {initial_ip}")
    
    # Reboot router
    success, message = reboot_router(
        router_config['ip'],
        router_config['username'],
        router_config['password'],
        router_config['reboot_command']
    )
    
    print(message)
    
    if success:
        # Wait for router to reboot and reconnect
        print("Waiting for router to reboot (60 seconds)...")
        time.sleep(60)
        
        # Check new IP
        print("Getting new public IP...")
        new_ip = get_public_ip()
        print(f"New public IP: {new_ip}")
        
        if initial_ip != new_ip:
            print("IP address successfully changed!")
        else:
            print("Warning: IP address remained the same")
    else:
        print("Failed to reboot router")

if __name__ == "__main__":
    main()
