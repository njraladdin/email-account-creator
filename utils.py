import random
import os
import json
from datetime import datetime
from colorama import init, Fore
import yaml
import time
from reboot_router import reboot_router, get_public_ip

# Initialize colorama
init()

def generate_personal_info():
    """Generate random personal information using names from names.txt"""
    try:
        with open('names.txt') as f:
            names = f.read().split('\n')
            names = [name.strip() for name in names if name.strip()]
    except FileNotFoundError:
        raise FileNotFoundError("names.txt file not found in the current directory")
    
    # Get random names from the list
    random_first_name = random.choice(names)
    random_last_name = random.choice(names)
    
    # Generate username with birth year (1950-2007)
    birth_year_for_email = str(random.randint(1950, 2007))
    username = f"{random_first_name.lower()}{random_last_name.lower()}{birth_year_for_email}"
    
    # Rest of the birth date generation for account creation (keeping 1990-1999 for this)
    month_letters = {
        1: 'j',  # January
        2: 'f',  # February
        3: 'm',  # March
        4: 'a',  # April
        5: 'm',  # May
        6: 'j',  # June
        7: 'j',  # July
        8: 'a',  # August
        9: 's',  # September
        10: 'o', # October
        11: 'n', # November
        12: 'd'  # December
    }
    
    birth_day = str(random.randint(1, 28))
    birth_month_num = random.randint(1, 12)
    birth_month = month_letters[birth_month_num]
    birth_year = str(random.randint(1990, 1999))  # This is for account creation
    
    return {
        'username': username,
        'first_name': random_first_name,
        'last_name': random_last_name,
        'birth_day': birth_day,
        'birth_month': birth_month,
        'birth_year': birth_year
    }

def generate_password():
    """Generate random password"""
    def generate_word(length):
        consonants = 'bcdfghjklmnpqrstvwxyz'
        vowels = 'aeiou'
        word = ''
        for i in range(length):
            word += random.choice(consonants if i % 2 == 0 else vowels)
        return word
    
    first_word = generate_word(random.randint(5, 7))
    second_word = generate_word(random.randint(5, 7))
    return f"{first_word}{second_word}{random.randint(0, 9999)}!"

def get_timestamp():
    """Get current timestamp in HH:MM:SS format"""
    return datetime.now().strftime("%H:%M:%S")

def save_account(email, password):
    """Save successful account credentials to file"""
    # Create output directory if it doesn't exist
    if not os.path.exists('output'):
        os.makedirs('output')
        
    timestamp = get_timestamp()
    
    # Log to console with colors - removed success rate
    print(f"{Fore.LIGHTBLACK_EX}[{timestamp}] # {Fore.LIGHTCYAN_EX} Account created {Fore.LIGHTBLACK_EX}[ {email}:{password} ]{Fore.RESET}")
    
    # Save to file with timestamp
    with open("output/Genned.txt", "a") as f:
        f.write(f"[{timestamp}] {email}:{password}\n")

def generate_account_info():
    """Generate complete account information"""
    personal_info = generate_personal_info()
    password = generate_password()

    account_info = {
        'email': f"{personal_info['username']}@outlook.com",
        'password': password,
        'first_name': personal_info['first_name'],
        'last_name': personal_info['last_name'],
        'birth_day': personal_info['birth_day'],
        'birth_month': personal_info['birth_month'], 
        'birth_year': personal_info['birth_year'],
        'date_created': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
    }

    print('Generated account details:')
    print(json.dumps(account_info, indent=2))
    
    return account_info 

def get_config():
    """Load configuration from config.yml with fallback to environment variables"""
    try:
        # Try to load from config.yml
        with open('config.yml', 'r') as f:
            config = yaml.safe_load(f) or {}
            
        # Check for Gemini API key
        if not config.get('gemini_api_key') or config['gemini_api_key'] == "your-api-key-here":
            env_key = os.getenv("GEMINI_API_KEY")
            if env_key:
                config['gemini_api_key'] = env_key
            else:
                raise ValueError("Gemini API key not found in config.yml or environment variables")
        
        # Router settings
        router_config = config.get('router', {})
        if not isinstance(router_config, dict):
            router_config = {}
            
        router_config.update({
            'enabled': os.getenv('ROUTER_ENABLED', str(router_config.get('enabled', True))).lower() == 'true',
            'ip': os.getenv('ROUTER_IP') or router_config.get('ip'),
            'username': os.getenv('ROUTER_USERNAME') or router_config.get('username'),
            'password': os.getenv('ROUTER_PASSWORD') or router_config.get('password'),
            'reboot_command': os.getenv('ROUTER_REBOOT_COMMAND') or router_config.get('reboot_command', 'reboot'),
        })
        config['router'] = router_config
        
        # General settings
        config['concurrent_tasks'] = int(os.getenv('CONCURRENT_TASKS') or config.get('concurrent_tasks', 1))
        config['max_captcha_attempts'] = int(os.getenv('MAX_CAPTCHA_ATTEMPTS') or config.get('max_captcha_attempts', 5))
            
        return config
        
    except FileNotFoundError:
        # If config.yml doesn't exist, try environment variables
        env_key = os.getenv("GEMINI_API_KEY")
        if not env_key:
            raise ValueError("Neither config.yml nor GEMINI_API_KEY environment variable found")
            
        return {
            'gemini_api_key': env_key,
            'concurrent_tasks': int(os.getenv('CONCURRENT_TASKS', '1')),
            'router': {
                'enabled': os.getenv('ROUTER_ENABLED', 'true').lower() == 'true',
                'ip': os.getenv('ROUTER_IP'),
                'username': os.getenv('ROUTER_USERNAME'),
                'password': os.getenv('ROUTER_PASSWORD'),
                'reboot_command': os.getenv('ROUTER_REBOOT_COMMAND', 'reboot'),
            }
        }

def reboot_router_if_allowed() -> bool:
    """
    Reboot router if enabled in config
    Returns: True if reboot was successful or not needed, False if reboot failed
    """
    try:
        config = get_config()
        router_config = config.get('router', {})
        
        if not router_config.get('enabled', False):
            print("Router reboot is disabled in config")
            return True
            
        print("Initiating router reboot for IP rotation...")
        initial_ip = get_public_ip()
        print(f"Current public IP: {initial_ip}")
        
        success, message = reboot_router(
            router_config['ip'],
            router_config['username'],
            router_config['password'],
            router_config['reboot_command']
        )
        
        print(message)
        
        if success:
            print("Waiting for router to reboot and reconnect...")
            time.sleep(60)  # Wait for router reboot
            
            new_ip = get_public_ip()
            print(f"New public IP: {new_ip}")
            
            if initial_ip != new_ip:
                print(f"{Fore.GREEN}IP rotation successful!{Fore.RESET}")
                return True
            else:
                print(f"{Fore.YELLOW}Warning: IP address remained the same{Fore.RESET}")
                return True  # Still return True as the reboot itself was successful
        
        print(f"{Fore.RED}Router reboot failed{Fore.RESET}")
        return False
        
    except Exception as e:
        print(f"{Fore.RED}Error during router reboot: {str(e)}{Fore.RESET}")
        return False 