from seleniumbase import SB
import time
import json
import random
import os
from dotenv import load_dotenv
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
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

def add_solution_text(image_path, solution_number):
    """Add solution text to a screenshot with black background at bottom"""
    try:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("arial.ttf", 120)
        except:
            font = ImageFont.load_default()
            
        text = f"ATTEMPT {solution_number}"
        
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
                                    screenshot_paths.append(screenshot_path)  # Track the screenshot path
                                    
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

                            # Process images with Gemini while still in the correct iframe context
                            print("All screenshots captured, processing with Gemini AI...")
                            print(screenshot_paths)
                            if screenshot_paths:
                                try:
                                    gemini_response = process_images_with_gemini(screenshot_paths)
                                    print("Gemini Analysis Result:")
                                    print(gemini_response)
                                    
                                    # Analyze the response to get the solution number
                                    solution_number = analyze_responses([gemini_response])
                                    print(f"Determined solution number: {solution_number}")
                                    
                                    if solution_number > 0:
                                        # Go back to first image
                                        first_image_button = sb.find_element('a[aria-label="Navigate to next image"]')
                                        if first_image_button:
                                            first_image_button.click()
                                            sb.sleep(1)
                                        
                                        # Click right button (solution_number - 1) times to reach the correct image
                                        for _ in range(solution_number - 1):
                                            next_image_button = sb.find_element('a[aria-label="Navigate to next image"]')
                                            if next_image_button:
                                                next_image_button.click()
                                                sb.sleep(0.5)
                                        
                                        # Find and click the submit button
                                        print("Looking for submit button...")
                                        submit_button = sb.find_element("button")
                                        if submit_button:
                                            print("Found submit button, clicking...")
                                            submit_button.click()
                                            sb.sleep(2)  # Wait for submission
                                        else:
                                            print("Submit button not found")
                                    else:
                                        print("Invalid solution number received from analysis")
                                        
                                except Exception as e:
                                    print(f"Error processing images with Gemini: {str(e)}")
                                    import traceback
                                    print(traceback.format_exc())

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

def process_images_with_gemini(screenshot_paths: List[str]) -> str:
    """
    Upload screenshots to Gemini AI and get the solution
    
    Args:
        screenshot_paths: List of paths to screenshot images
    """
    print("Initializing Gemini AI processing...")
    
    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        
        # Create event loop and run concurrent uploads
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Create tasks for all uploads
        tasks = [upload_file_async(path) for path in screenshot_paths]
        
        # Run all uploads concurrently and wait for results
        uploaded_files = loop.run_until_complete(asyncio.gather(*tasks))
        uploaded_files = [f for f in uploaded_files if f is not None]
        
        if not uploaded_files:
            raise Exception("No files were successfully uploaded")

        # Configure and create the model
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
            "response_mime_type": "text/plain",
        }

        print("Creating Gemini model...")
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            generation_config=generation_config,
        )

        # Create prompt
        prompt = """You are a multimodal AI specialized in solving visual captcha challenges. 
You are given a series of images and you need to determine the correct attempt.
WHICH ATTEMPT IS THE CORRECT ONE? each object should face the same direction as the pointing hand. the front of the object should face the same direction as teh hand is pointing
the correct one should be looking the same way as the hand. if the hand is poitning to the right, the front of the object should be also pointing to the right. from the POV if both the object and the hand are in front of you
they should also have the same angle, starting from 12 oclock. 

your final answer should be the correct ATTEMPT number.
        """

        print("Starting chat session with Gemini...")
        chat_session = model.start_chat(
            history=[{
                "role": "user",
                "parts": uploaded_files + [prompt]
            }]
        )

        print("Sending message to Gemini...")
        response = chat_session.send_message("Please analyze the images and determine the correct solution.")
        
        print("Received response from Gemini:")
        print(response.text)
        
        return response.text

    except Exception as e:
        print(f"Error in Gemini processing: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return f"Error: {str(e)}"
    finally:
        if 'loop' in locals():
            loop.close()
    
def analyze_responses(responses: List[str]) -> int:
    """
    Analyze multiple Gemini responses to find the most frequently mentioned solution number
    
    Args:
        responses: List of text responses from previous Gemini calls
    
    Returns:
        int: The solution number that appears most frequently
    """
    try:
        # Configure Gemini
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        
        # Create the model with JSON schema
        generation_config = {
            "temperature": 1,
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

        # Format the responses for analysis
        formatted_responses = "\n\nResponses from previous analysis:\n"
        for i, resp in enumerate(responses, 1):
            formatted_responses += f"\nResponse {i}:\n{resp}\n"

        prompt = f"""
        Analyze these responses and return the correct attempt number that was mentioned more than once in each response.
        Only return the attempt number that appears the most in each response analysis. 
        If no attempt number is mentioned more than once, return 0.
        
        {formatted_responses}
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
        print(f"Error analyzing responses: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return 0

# Update test_gemini_with_latest_screenshots to use the new function
def test_gemini_with_latest_screenshots():
    """Test function to process 6 screenshots with overlapping requests to Gemini"""
    try:
        if not os.path.exists('screenshots'):
            print("Screenshots directory not found!")
            return
            
        screenshot_files = [f for f in os.listdir('screenshots') if f.endswith('.png')]
        if not screenshot_files:
            print("No screenshots found!")
            return
            
        # Sort by creation time and get last 6
        screenshot_files.sort(key=lambda x: os.path.getctime(os.path.join('screenshots', x)), reverse=True)
        latest_screenshots = screenshot_files[:6]  # Get 6 most recent screenshots
        screenshot_paths = [os.path.join('screenshots', f) for f in latest_screenshots]
        
        if len(screenshot_paths) < 6:
            print(f"Not enough screenshots found. Need 6, but only found {len(screenshot_paths)}")
            return

        # Create the overlapping groups as per the strategy
        groups = [
            screenshot_paths[0:4],     # A,B,C,D
            screenshot_paths[2:6],     # C,D,E,F
            screenshot_paths[0:2] + screenshot_paths[4:6]  # A,B,E,F
        ]

        print("Processing images with overlapping strategy...")
        all_responses = []
        
        for i, group in enumerate(groups, 1):
            print(f"\nProcessing Request {i} with images:")
            for path in group:
                print(f"- {path}")
            
            response = process_images_with_gemini(group)
            print(f"\nGemini Response for Request {i}:")
            print(response)
            all_responses.append(response)

        print("\nAll Responses Summary:")
        for i, response in enumerate(all_responses, 1):
            print(f"\nRequest {i} Response:")
            print(response)
        
        # Add analysis of responses
        final_solution = analyze_responses(all_responses)
        print(f"\nFinal Solution (most frequent answer): {final_solution}")
        
    except Exception as e:
        print(f"Error in test function: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    selenium_base_with_gemini()
    #test_gemini_with_latest_screenshots()


