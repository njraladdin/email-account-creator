from seleniumbase import SB
import time
import json
import random
import os
from dotenv import load_dotenv
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

def add_solution_text(image_path, solution_number):
    """Add solution text to a screenshot with black background at bottom"""
    try:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 120)
        except:
            font = ImageFont.load_default()
            
        text = f"SOLUTION {solution_number}"
        
        # Get text dimensions
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Calculate positions with more bottom padding
        padding_horizontal = 20
        padding_vertical = 40  # Increased vertical padding
        x = (img.width - text_width) // 2
        y = img.height - text_height - (padding_vertical * 1.8)
        
        # Draw black background rectangle with more bottom padding
        background_bbox = [
            x - padding_horizontal,  # left
            y - padding_vertical,    # top
            x + text_width + padding_horizontal,  # right
            y + text_height + padding_vertical    # bottom
        ]
        draw.rectangle(background_bbox, fill="black")
        
        # Draw white text on black background
        draw.text((x, y), text, fill="white", font=font)
        
        img.save(image_path)
        print(f"Added solution text to {image_path}")
        
    except Exception as e:
        print(f"Error adding text to image: {str(e)}")

# Load environment variables
load_dotenv()
TWOCAPTCHA_API_KEY = os.getenv('TWOCAPTCHA_API_KEY')

from twocaptcha import TwoCaptcha

solver = TwoCaptcha(
    TWOCAPTCHA_API_KEY,
    defaultTimeout=500,  # Increase timeout to 4 minutes
    pollingInterval=2
)


def solve_captcha(arkose_blob, url):
    """Solve FunCaptcha using 2captcha service direct API"""
    try:
        print(f"\n[Captcha] Solving FunCaptcha with blob: {arkose_blob}")
        
        # Get your own IP address
        import requests

        # Proxy configuration
        proxy_host = "mobile.free.proxyrack.net"
        proxy_port = "9000"
        proxy_user = "qwerty2950-proxyId-PR6BRYBFFM"
        proxy_pass = "728ec0c31301f4ff1f133e6d494af7df205998b8db2769ae7474f46bfc2d5b5f"
        
        print(f"Using proxy: {proxy_host}:{proxy_port}")
        
        # The blob is already a string, we just need to format it as {"blob": "blob_value"}
        blob_data = f'{{"blob":"{arkose_blob}"}}'
        
        # Create task request
        task_data = {
            "clientKey": TWOCAPTCHA_API_KEY,
            "task": {
                "type": "FunCaptchaTask",
                "websiteURL": url,
                "websitePublicKey": "B7D8911C-5CC8-A9A3-35B0-554ACEE604DA",
                "funcaptchaApiJSSubdomain": "https://iframe.arkoselabs.com",
                "data": blob_data,
                "proxyType": "http",
                "proxyAddress": proxy_host,
                "proxyPort": proxy_port,
                "proxyLogin": proxy_user,
                "proxyPassword": proxy_pass
            }
        }
        print(task_data)

        # Create task
        create_task_response = requests.post('https://api.2captcha.com/createTask', json=task_data)
        create_task_data = create_task_response.json()
        print(f"\n[Captcha] Create task response: {json.dumps(create_task_data)}")

        if create_task_data.get('errorId', 1) != 0:
            raise Exception(f"Failed to create captcha task: {create_task_data.get('errorDescription')}")

        task_id = create_task_data['taskId']
        print(f"\n[Captcha] Got task ID: {task_id}")

        # Poll for result
        max_attempts = 60
        for attempt in range(max_attempts):
            time.sleep(5)  # Wait 5 seconds between checks
            
            result_response = requests.post('https://api.2captcha.com/getTaskResult', json={
                "clientKey": TWOCAPTCHA_API_KEY,
                "taskId": task_id
            })
            result_data = result_response.json()
            print(result_data)
            
            if result_data.get('errorId', 0) != 0:
                print(f"\n[Captcha] Error received: {result_data.get('errorDescription')}")
                return None  # Fail early on error
                
            if result_data.get('status') == 'ready':
                print('\n[Captcha] Solution found!')
                return result_data['solution']['token']
            elif result_data.get('status') != 'processing':
                print(f"\n[Captcha] Unexpected status: {result_data.get('status')}")
                return None  # Fail on unexpected status
            
            print(f"\n[Captcha] Waiting for solution... Attempt {attempt + 1}/{max_attempts}")

        raise Exception('Timeout waiting for captcha solution')

    except Exception as e:
        print(f"\n[Captcha] Error solving captcha: {str(e)}")
        print(f"\n[Captcha] Error type: {type(e)}")
        return None
        

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

# Generate account info first
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
    'date_created': time.strftime('%Y-%m-%dT%H:%M:%SZ')
}

print('Generated account details (for manual input):')
print(json.dumps(account_info, indent=2))
# docs > https://seleniumbase.io/help_docs/uc_mode/#here-are-the-seleniumbase-uc-mode-methods-uc-uctrue
with SB(uc=True, 
        #extension_dir="./nopecha", 
        incognito=True, test=True, locale_code="en" ) as sb:
    try:
        # Navigate to signup page
        url = "https://signup.live.com/signup?lcid"
        # sb.activate_cdp_mode(url)
        sb.activate_cdp_mode(url)
        
        print("Starting signup process...")
        sb.cdp.click("#usernameInput")
        sb.cdp.type("#usernameInput", personal_info['username']+'@hotmail.com')
        sb.cdp.click("#nextButton")

        sb.cdp.click("#Password")
        sb.cdp.type("#Password", password)
        sb.cdp.click('input[type="submit"], button[type="submit"]')

        sb.cdp.click("#firstNameInput")
        sb.cdp.type("#firstNameInput", personal_info['first_name'])
        sb.cdp.click("#lastNameInput")
        sb.cdp.type("#lastNameInput", personal_info['last_name'])
        sb.cdp.click('input[type="submit"], button[type="submit"]')

        sb.cdp.click("#BirthDay")
        sb.cdp.type("#BirthDay", '3')
        sb.cdp.click("#BirthMonth")
        sb.cdp.type("#BirthMonth", 'd')
        sb.cdp.click("#BirthYear")
        sb.cdp.type("#BirthYear", personal_info['birth_year'])
        sb.cdp.click('input[type="submit"], button[type="submit"]')

        # Add debug logging and iframe handling for captcha
        print("Waiting for captcha iframe to load...")
        sb.sleep(5)  # Wait for captcha to fully load
        
        # Create screenshots directory if it doesn't exist
        if not os.path.exists('screenshots'):
            os.makedirs('screenshots')
            
        # Take single screenshot after captcha loads
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        print("Taking screenshot of captcha page...")
        sb.save_screenshot(f"screenshots/captcha_{timestamp}.png")
        try:
            print("Attempting to switch to enforcement frame...")
            with sb.frame_switch("#enforcementFrame"):
                print("Successfully switched to enforcement frame")
                
                print("Attempting to switch to arkose iframe...")
                with sb.frame_switch("#arkose > div > iframe"):
                    print("Successfully switched to arkose iframe")
                    
                    # Switch to game-core-frame
                    print("Attempting to switch to game-core-frame...")
                    with sb.frame_switch("#game-core-frame"):
                        print("Successfully switched to game-core-frame")
                        
                        # Find and click the Next button using data-theme attribute
                        print("Looking for Next button...")
                        next_button = sb.find_element('[data-theme="home.verifyButton"]')
                        if next_button:
                            print("Found Next button, clicking...")
                            next_button.click()
                            sb.sleep(2)  # Wait for images to load

                            sb.cdp.evaluate("window.devicePixelRatio = 2.4")
                            sb.cdp.evaluate("document.body.style.zoom = '240%'")

                            # Get total number of images from aria-label
                            img_element = sb.find_element('img[aria-live="assertive"]')
                            aria_label = img_element.get_attribute('aria-label')
                            total_images = int(aria_label.split('of')[1].strip().rstrip('.'))
                            print(f"Total number of images detected: {total_images}")
                            
                            # Capture all images
                            for i in range(total_images):
                                # Find current image and scroll it into view
                                current_img = sb.find_element('.match-game.box.screen > div > h2')
                                sb.execute_script("arguments[0].scrollIntoView(true);", current_img)
                                sb.sleep(1)  # Wait for scroll to complete
                                
                                # Take screenshot and add solution text
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                screenshot_path = f"screenshots/captcha_image_{i+1}_{timestamp}.png"
                                sb.save_screenshot(screenshot_path)
                                add_solution_text(screenshot_path, i+1)
                                
                                # Click next if not the last image
                                if i < total_images - 1:
                                    next_image_button = sb.find_element('a[aria-label="Navigate to next image"]')
                                    if next_image_button:
                                        print(f"Clicking to see image {i+2} of {total_images}...")
                                        next_image_button.click()
                                        sb.sleep(1)  # Wait for next image to load
                                    else:
                                        print("Next image button not found")
                                        break
                        else:
                            print("Next button not found")
                    
                    # Find and log all input elements first
                    print("Searching for input elements...")
                    input_elements = sb.find_elements("input")
                    print(f"Found {len(input_elements)} input elements:")
                    token_value = None
                    
                    for i, element in enumerate(input_elements):
                        element_type = element.get_attribute("type")
                        element_id = element.get_attribute("id")
                        element_class = element.get_attribute("class")
                        print(f"Input {i+1}:")
                        print(f"  - Type: {element_type}")
                        print(f"  - ID: {element_id}")
                        print(f"  - Class: {element_class}")
                        
                        # Check if this is the verification token
                        if element_id == "verification-token":
                            token_value = element.get_attribute("value")
                            print(f"Found verification token: {token_value[:50]}...") # Print first 50 chars
                    
                    print("Exiting arkose iframe...")
            print("Exiting enforcement frame...")
            
            # Now solve the captcha with the extracted token
            if token_value:
                print("Attempting to solve captcha...")
                sb.sleep(2)
                current_url = sb.cdp.get_current_url()  # Get current URL before solving
                solved_token = solve_captcha(token_value, current_url)
                if solved_token:
                    print("Successfully solved captcha!")
                    print(f"Solved token: {solved_token[:50]}...") # Print first 50 chars
                else:
                    print("Failed to solve captcha")
            
        except Exception as e:
            print(f"Error while handling iframes: {str(e)}")
            print("Detailed error:")
            import traceback
            print(traceback.format_exc())

        # print("Continuing with long wait...")
        # sb.sleep(31536000)  # Your original long wait

        # # Fill username with anti-detection measures
        # sb.uc_click('#usernameInput', reconnect_time=2)
        # sb.type("#usernameInput", personal_info['username']+'@hotmail.com')
        # sb.reconnect(0.1)  # Small delay before clicking
        # sb.uc_click('#nextButton', reconnect_time=2)
        
        # # Wait for password field to be present and visible
        # sb.wait_for_element_present("#Password", timeout=10)
        # sb.wait_for_element_visible("#Password", timeout=10)
        # sb.sleep(2)  # Additional small delay
        
        # # Fill password
        # sb.type("#Password", password)  # Note: using password instead of personal_info['password']
        # sb.reconnect(0.1)  # Small delay before clicking
        # sb.uc_click('input[type="submit"], button[type="submit"]', reconnect_time=2)
        
        print("Password entered - waiting for manual completion...")
        sb.sleep(31536000)  # Wait for a year
        
        # # Fill name fields
        # sb.type("#firstNameInput", ACCOUNT_INFO['first_name'])
        # sb.type("#lastNameInput", ACCOUNT_INFO['last_name'])
        # sb.click('input[type="submit"], button[type="submit"]')
        
        # # Fill birth date
        # sb.select_option_by_value("#BirthDay", ACCOUNT_INFO['birth_day'])
        # sb.select_option_by_value("#BirthMonth", ACCOUNT_INFO['birth_month'])
        # sb.type("#BirthYear", ACCOUNT_INFO['birth_year'])
        # sb.click('input[type="submit"], button[type="submit"]')
        
        # # Stop here as we've reached the captcha
        # print("Reached captcha - waiting indefinitely...")
        
        # # Save account details
        # account_info = {
        #     'email': ACCOUNT_INFO['username'] + '@outlook.com',
        #     'password': ACCOUNT_INFO['password'],
        #     'first_name': ACCOUNT_INFO['first_name'],
        #     'last_name': ACCOUNT_INFO['last_name'],
        #     'date_created': time.strftime('%Y-%m-%dT%H:%M:%SZ')
        # }
        
        # print('Account details:')
        # print(json.dumps(account_info, indent=2))
        
    except Exception as e:
        print(f'Error during browser setup: {str(e)}')
        # Print more detailed error information
        import traceback
        print(traceback.format_exc())