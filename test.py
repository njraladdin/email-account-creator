from DrissionPage import Chromium, ChromiumOptions
import time
import random
import os
import json
from dotenv import load_dotenv
from twocaptcha import TwoCaptcha
import sys
from pathlib import Path

# Load environment variables
load_dotenv()
TWOCAPTCHA_API_KEY = os.getenv('TWOCAPTCHA_API_KEY')

# Configuration Constants
CHROME_PATHS = {
    'win32': "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    'linux': "/usr/bin/google-chrome"
}

BROWSER_CLEANUP_DELAY = 0.4  # seconds to wait after browser closes

def get_chrome_options():
    """Create and configure ChromiumOptions"""
    co = ChromiumOptions()
    
    # Set Chrome executable path based on platform
    chrome_path = CHROME_PATHS.get(sys.platform)
    if chrome_path and os.path.exists(chrome_path):
        co.set_browser_path(chrome_path)
    
    # Create chrome-user-data directory if it doesn't exist
    user_data_dir = Path('chrome-user-data')
    user_data_dir.mkdir(exist_ok=True)
    
    # Set user data directory
    co.set_user_data_path(str(user_data_dir))
    
    # Add Chrome flags
    chrome_flags = [
        '--no-sandbox',
        '--disable-gpu',
        '--enable-webgl',
        '--window-size=1920,1080',
        '--disable-dev-shm-usage',
        '--disable-setuid-sandbox',
        '--no-first-run',
        '--no-default-browser-check',
        '--password-store=basic',
        '--disable-blink-features=AutomationControlled',
        '--disable-features=IsolateOrigins,site-per-process',
        '--lang=en',
        '--disable-web-security',
        '--flag-switches-begin --disable-site-isolation-trials --flag-switches-end'
    ]
    
    for flag in chrome_flags:
        co.set_argument(flag)
    
    return co

def generate_personal_info():
    """Generate random personal information"""
    def generate_name(length):
        consonants = 'bcdfghjklmnpqrstvwxyz'
        vowels = 'aeiou'
        name = ''
        for i in range(length):
            name += random.choice(consonants if i % 2 == 0 else vowels)
        return name.capitalize()
    
    random_first_name = generate_name(random.randint(5, 7))
    random_last_name = generate_name(random.randint(5, 7))
    username = f"{random_first_name.lower()}{random_last_name.lower()}{random.randint(0, 9999)}"
    birth_day = str(random.randint(1, 28))
    birth_month = str(random.randint(1, 12))
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

async def solve_2captcha(sitekey, page_url, user_agent):
    """Solve captcha using 2captcha service"""
    try:
        solver = TwoCaptcha(TWOCAPTCHA_API_KEY)
        print('Initiating 2captcha solve request...')
        
        result = solver.recaptcha(
            sitekey=sitekey,
            url=page_url,
            invisible=False,
            user_agent=user_agent
        )
        
        if result and 'code' in result:
            print('Successfully received token from 2captcha')
            return result['code']
        
        print('Failed to get token from 2captcha')
        return None
        
    except Exception as e:
        print(f'Error in solve_2captcha: {str(e)}')
        return None

async def create_outlook_account(headless=False):
    """Create a new Outlook account"""
    chrome_options = get_chrome_options()
    browser = None
    
    try:
        browser = Chromium(chrome_options)
        page = browser.new_tab()
        
        print('Navigating to Outlook signup...')
        page.get('https://outlook.live.com/owa/?nlp=1&signup=1')
        
        # Generate account info
        personal_info = generate_personal_info()
        password = generate_password()
        
        # Fill username
        print('Starting signup process...')
        username_input = page.ele('#usernameInput')
        username_input.input(personal_info['username'])
        next_button = page.ele('input[type="submit"], button[type="submit"]')
        next_button.click() if next_button else None
        
        # Fill password
        password_input = page.ele('#Password', timeout=10)
        password_input.input(password)
        next_button = page.ele('input[type="submit"], button[type="submit"]')
        next_button.click() if next_button else None
        
        # Fill name fields
        first_name_input = page.ele('#firstNameInput', timeout=10)
        first_name_input.input(personal_info['first_name'])
        
        last_name_input = page.ele('#lastNameInput')
        last_name_input.input(personal_info['last_name'])
        next_button = page.ele('input[type="submit"], button[type="submit"]')
        next_button.click() if next_button else None
        
        # Fill birth date
        page.ele('#BirthDay', timeout=10).select(personal_info['birth_day'])
        page.ele('#BirthMonth').select(personal_info['birth_month'])
        birth_year_input = page.ele('#BirthYear')
        birth_year_input.input(personal_info['birth_year'])
        next_button = page.ele('input[type="submit"], button[type="submit"]')
        next_button.click() if next_button else None
        
        # Get email address
        email = page.ele('#userDisplayName', timeout=10).text
        print(f'Created account: {email}')
        
        # Save account details
        account_info = {
            'email': email,
            'password': password,
            'first_name': personal_info['first_name'],
            'last_name': personal_info['last_name'],
            'date_created': time.strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        
        # Keep browser open briefly to verify
        time.sleep(3)
        
        return account_info
        
    except Exception as e:
        print(f'Error in create_outlook_account: {str(e)}')
        return None
        
    finally:
        if browser:
            print('Cleaning up browser...')
            browser.quit()
            time.sleep(BROWSER_CLEANUP_DELAY)

if __name__ == '__main__':
    import asyncio
    account_info = asyncio.run(create_outlook_account(headless=False))
    if account_info:
        print('Account created successfully:')
        print(json.dumps(account_info, indent=2))
    else:
        print('Failed to create account')
