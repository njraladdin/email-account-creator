import random
import os
import json
from datetime import datetime
from colorama import init, Fore
import yaml

# Initialize colorama
init()

# Global tracking variables
ATTEMPTS = 0
GENNED = 0

def update_stats(success=False):
    """Update global statistics"""
    global ATTEMPTS, GENNED
    ATTEMPTS += 1
    if success:
        GENNED += 1

def get_success_percentage():
    """Calculate success percentage"""
    if ATTEMPTS == 0:
        return 0
    return (GENNED / ATTEMPTS) * 100

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
    success_rate = get_success_percentage()
    
    # Log to console with colors
    print(f"{Fore.LIGHTBLACK_EX}[{timestamp}] # {Fore.LIGHTCYAN_EX} Account created {Fore.LIGHTBLACK_EX}[ {email}:{password} ] {Fore.YELLOW}({success_rate:.1f}% Success){Fore.RESET}")
    
    # Save to file with timestamp
    with open("output/Genned.txt", "a") as f:
        f.write(f"[{timestamp}] {email}:{password} ({success_rate:.1f}% Success)\n")

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
            config = yaml.safe_load(f)
            
        # If gemini_api_key is not in config or is the default value, try env var
        if not config.get('gemini_api_key') or config['gemini_api_key'] == "your-api-key-here":
            env_key = os.getenv("GEMINI_API_KEY")
            if env_key:
                config['gemini_api_key'] = env_key
            else:
                raise ValueError("Gemini API key not found in config.yml or environment variables")
                
        # Ensure concurrent_tasks exists with default value
        if 'concurrent_tasks' not in config:
            config['concurrent_tasks'] = 1
            
        return config
        
    except FileNotFoundError:
        # If config.yml doesn't exist, try environment variables
        env_key = os.getenv("GEMINI_API_KEY")
        if not env_key:
            raise ValueError("Neither config.yml nor GEMINI_API_KEY environment variable found")
            
        return {
            'gemini_api_key': env_key,
            'concurrent_tasks': 1
        } 