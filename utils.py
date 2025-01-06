import random
import os
import json
from datetime import datetime
from colorama import init, Fore

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
    """Generate random personal information"""
    def generate_name(length):
        consonants = 'bcdfghjklmnpqrstvwxyz'
        vowels = 'aeiou'
        name = ''
        for i in range(length):
            name += random.choice(consonants if i % 2 == 0 else vowels)
        return name.capitalize()
    
    # Add month letters mapping
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
    
    random_first_name = generate_name(random.randint(5, 7))
    random_last_name = generate_name(random.randint(5, 7))
    username = f"{random_first_name.lower()}{random_last_name.lower()}{random.randint(0, 9999)}"
    birth_day = str(random.randint(1, 28))
    birth_month_num = random.randint(1, 12)
    birth_month = month_letters[birth_month_num]  # Get letter instead of number
    birth_year = str(random.randint(1990, 1999))
    
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

    print('Generated account details (for manual input):')
    print(json.dumps(account_info, indent=2))
    
    return account_info 