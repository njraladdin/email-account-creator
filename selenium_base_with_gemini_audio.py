from seleniumbase import SB
import time
import json
import random
import os
from dotenv import load_dotenv
from datetime import datetime
import google.generativeai as genai
from typing import List
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from google.ai.generativelanguage_v1beta.types import content
load_dotenv()

MODEL_NAME = "gemini-2.0-flash-exp"

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



def selenium_base_with_gemini():
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
    with SB(uc=True, incognito=True, test=True, locale_code="en" ) as sb:
        try:
            url = "https://signup.live.com/signup?lcid"
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
            screenshot_paths = []  # Initialize array to track screenshots
                
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
                            
                            # Get the instructions text
                            
                            # This is all we need now - the JavaScript interceptors
                            monitor_script = """
                            // Store original fetch
                            const originalFetch = window.fetch;
                            window.fetch = async (...args) => {
                                const url = args[0];
                                console.log('Intercepted fetch request:', url);
                                if(url.includes('audio')) {
                                    window.lastAudioUrl = url;
                                    console.log('Found audio URL:', url);
                                }
                                return originalFetch.apply(window, args);
                            };

                            // Store original XHR
                            const originalXHR = window.XMLHttpRequest;
                            window.XMLHttpRequest = function() {
                                const xhr = new originalXHR();
                                const originalOpen = xhr.open;
                                xhr.open = function(...args) {
                                    const url = args[1];
                                    console.log('Intercepted XHR request:', url);
                                    if(url.includes('audio')) {
                                        window.lastAudioUrl = url;
                                        console.log('Found audio URL:', url);
                                    }
                                    return originalOpen.apply(xhr, args);
                                };
                                return xhr;
                            };
                            """
                            sb.execute_script(monitor_script)
                            
                            # Find and click the Audio button once to start audio challenges
                            print("Looking for Audio challenge button...")
                            audio_button = sb.find_element('[aria-label="Audio"]')
                            if audio_button:
                                print("Found Audio button, clicking to start audio challenges...")
                                audio_button.click()
                                sb.sleep(2)  # Wait for first audio challenge to load
                                
                                # Loop to handle multiple audio challenges
                                while True:
                                    instructions = sb.find_element('#instructions').text
                                    print(f"Captcha Instructions: {instructions}")
                                    
                                    # Check if we captured the audio URL
                                    audio_url = sb.execute_script("return window.lastAudioUrl;")
                                    if audio_url:
                                        print(f"Captured audio URL: {audio_url}")
                                        
                                        # Create event loop for async operations
                                        loop = asyncio.new_event_loop()
                                        asyncio.set_event_loop(loop)
                                        try:
                                            # Download the audio file
                                            audio_path = loop.run_until_complete(download_audio_file(audio_url))
                                            if audio_path:
                                                # Clear the last audio URL after successful download
                                                sb.execute_script("window.lastAudioUrl = null;")
                                                
                                                # Click the play button to simulate human behavior
                                                play_button = sb.find_element('[aria-describedby="instructions"]')
                                                if play_button:
                                                    print("Clicking play button...")
                                                    play_button.click()
                                                    sb.sleep(1)  # Short wait after clicking play
                                                
                                                # Process with Gemini and submit answer
                                                gemini_response = process_audio_with_gemini(audio_path, instructions)
                                                print("Gemini Audio Analysis Result:")
                                                print(gemini_response)
                                                
                                                # Analyze the response to get the option number
                                                option_number = analyze_responses([gemini_response])
                                                print(f"Extracted option number: {option_number}")
                                                
                                                if option_number > 0:
                                                    # Find and fill the answer input
                                                    answer_input = sb.find_element('#answer-input')
                                                    if answer_input:
                                                        print(f"Inputting answer: {option_number}")
                                                        answer_input.clear()
                                                        answer_input.send_keys(str(option_number))
                                                        sb.sleep(1)  # Short wait after input
                                                        
                                                        # Find and click submit button
                                                        submit_button = sb.find_element('button[type="submit"]')
                                                        if submit_button:
                                                            print("Found submit button, clicking...")
                                                            submit_button.click()
                                                            
                                                            # Wait and check for new audio challenge
                                                            sb.sleep(2)
                                                            new_audio_url = sb.execute_script("return window.lastAudioUrl;")
                                                            if not new_audio_url:
                                                                print("No new audio challenge detected, captcha completed!")
                                                                break
                                                            else:
                                                                print("New audio challenge detected, continuing...")
                                                                continue
                                                        else:
                                                            print("Submit button not found")
                                                            break
                                                    else:
                                                        print("Answer input field not found")
                                                        break
                                                else:
                                                    print("Invalid option number received from analysis")
                                                    break
                                            else:
                                                print("Failed to download audio file")
                                                break
                                        finally:
                                            loop.close()
                                    else:
                                        print("No audio URL captured")
                                        break
                            sb.sleep(110000)


            except Exception as e:
                print(f"Error while handling iframes: {str(e)}")
                print("Detailed error:")
                import traceback
                print(traceback.format_exc())

            # print("Continuing with long wait...")
            sb.sleep(31536000)  

            
        except Exception as e:
            print(f'Error during browser setup: {str(e)}')
            # Print more detailed error information
            import traceback
            print(traceback.format_exc())

async def upload_file_async(path: str) -> any:
    """Upload a single file asynchronously"""
    try:
        file = genai.upload_file(path, mime_type="image/png")
        print(f"Successfully uploaded: {path}")
        return file
    except Exception as e:
        print(f"Error uploading file {path}: {str(e)}")
        return None


    
def analyze_responses(responses: List[str]) -> int:
    """
    Analyze Gemini response to extract the solution number
    
    Args:
        responses: List containing a single response text
    
    Returns:
        int: The solution number mentioned in the response
    """
    try:
        # Configure Gemini
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        
        # Create the model with JSON schema
        generation_config = {
            "temperature": 0.5,  # Lower temperature for more deterministic output
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_schema": content.Schema(
                type=content.Type.OBJECT,
                properties={
                    "response": content.Schema(
                        type=content.Type.NUMBER,
                    ),
                },
            ),
            "response_mime_type": "application/json",
        }

        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=generation_config,
        )

        response_text = responses[0]  # Get the single response
        prompt = f"""
        Analyze this response and extract the concluded solution number.
        Only return the final number that represents the solution.
        If no clear number is found, return 0.
        
        Response to analyze:
        {response_text}
        """

        chat_session = model.start_chat()
        response = chat_session.send_message(prompt)
        
        # Parse the JSON response
        try:
            result = json.loads(response.text)
            return int(result.get('response', 0))
        except json.JSONDecodeError:
            print("Error parsing JSON response")
            return 0
            
    except Exception as e:
        print(f"Error analyzing response: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return 0


async def download_audio_file(url: str) -> str:
    """Download audio file from URL and save it locally"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    # Create audio directory if it doesn't exist
                    if not os.path.exists('audio'):
                        os.makedirs('audio')
                    
                    # Save the audio file
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    file_path = f"audio/captcha_{timestamp}.mp3"
                    with open(file_path, 'wb') as f:
                        f.write(await response.read())
                    print(f"Audio file downloaded to: {file_path}")
                    return file_path
                else:
                    print(f"Failed to download audio. Status: {response.status}")
                    return None
    except Exception as e:
        print(f"Error downloading audio: {str(e)}")
        return None

def process_audio_with_gemini(audio_path: str, instructions: str) -> str:
    """
    Upload audio to Gemini AI and get the solution
    
    Args:
        audio_path: Path to the audio file
        instructions: Instructions from the captcha
    """
    print("Initializing Gemini AI processing for audio...")
    
    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        
        # Upload the audio file
        audio_file = genai.upload_file(audio_path, mime_type="audio/mpeg")
        
        # Configure and create the model
        generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
    }

        print("Creating Gemini model...")
        model = genai.GenerativeModel(
            model_name="gemini-exp-1206",
            generation_config=generation_config,
        )

        # Create prompt with instructions
        prompt = f"""listen to this audio challenge carefully, analyze each part, then answer: :

        {instructions}

it's intentionally hidden and tried to be covered by other sounds, 
so try to not be tricked easily. it doesn't have to be exactly it, 
but something very similar (it's obfuscated on purpose) it can be quite subtle as well and very short, so pay attention to that. 
        """

        print("Starting chat session with Gemini...")
        print(prompt)
        chat_session = model.start_chat(
            history=[{
                "role": "user",
                "parts": [audio_file, prompt]
            }]
        )

        print("Sending message to Gemini...")
        response = chat_session.send_message("Please analyze the audio following the provided instructions.")
        
        print("Received response from Gemini:")
        print(response.text)
        
        return response.text

    except Exception as e:
        print(f"Error in Gemini processing: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return f"Error: {str(e)}"

if __name__ == "__main__":
    selenium_base_with_gemini()
    #test_gemini_with_latest_screenshots()


