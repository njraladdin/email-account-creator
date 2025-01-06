"""
Original script request flow:

1. resp1: GET https://signup.live.com/signup
   Requirements: None
   - Gets initial redirect URL and cookies (amsc)
   - Used for: href_value and amsc cookie for resp2

2. resp2: GET {href_value from resp1}
   Requirements: 
   - amsc cookie from resp1
   - href_value from resp1
   - Gets uaid cookie
   - Used for: uaid cookie for resp3

3. resp3: GET https://signup.live.com/signup?lic=1&uaid={uaid}
   Requirements:
   - amsc cookie
   - uaid from resp2
   - Gets updated amsc cookie and JS content
   - Extracts: api_canary, fid, SKI, hpgid, i_ui_flavor, scenario_id, key, random_num, fptLink1

4. resp4: GET {fptLink1} (to fpt.live.com)
   Requirements:
   - All previous cookies
   - fptLink1 from resp3
   - Gets MUID and fptctx2 cookies
   - Extracts: txnId, ticks, rid, authKey, cid
   - Used for: Fraud prevention validation

5. resp5: GET https://fpt2.microsoft.com/Clear.HTML
   Requirements:
   - Previous cookies
   - txnId, rid, ticks, authKey, cid from resp4
   - Gets real MUID cookie
   - Used for: Final fraud prevention validation

6. resp6: POST https://signup.live.com/API/CheckAvailableSigninNames
   Requirements:
   - All cookies (amsc, MUID, fptctx2)
   - api_canary from resp3
   - Checks email availability
   - Gets: new apiCanary and telemetryContext
   - Used for: Headers in resp7

7. resp7: POST https://signup.live.com/API/CreateAccount
   Requirements:
   - All previous cookies and tokens
   - Latest apiCanary and telemetryContext
   - Encrypted password (using key, random_num from resp3)
   - First attempt at account creation
   - Gets: RiskAssessmentDetails and arkoseBlob for CAPTCHA

[After CAPTCHA solve]
8. Final POST to /API/CreateAccount
   Requirements:
   - All previous tokens/cookies
   - Solved CAPTCHA token
   - RiskAssessmentDetails from resp7
   - Creates the account
"""
from execjs import compile as js_compile

from bs4 import BeautifulSoup
import tls_client
import re
import os
import base64
import time
import json
from datetime import datetime

from twocaptcha import TwoCaptcha
import os
from dotenv import load_dotenv
import threading
from concurrent.futures import ThreadPoolExecutor

# Load environment variables from .env file
load_dotenv()

# Get 2captcha API key from environment variables and set longer timeout (240 seconds = 4 minutes)
solver = TwoCaptcha(
    os.getenv('2CAPTCHA_API_KEY'),
    defaultTimeout=500,  # Increase timeout to 4 minutes
    pollingInterval=5
)
print(os.getenv('2CAPTCHA_API_KEY'))

# At the top with other constants
USE_PROXY = True  # Change this to True to enable proxy

PROXY = {
    "host": "mobile.free.proxyrack.net",
    "port": "9000",
    "username": "qwerty2950-proxyId-PR6BRYBFFM",
    "password": "728ec0c31301f4ff1f133e6d494af7df205998b8db2769ae7474f46bfc2d5b5f"
}
print(PROXY)
def get_proxy_url():
    if not USE_PROXY:
        return None
    if PROXY.get("username") and PROXY.get("password"):
        return f"http://{PROXY['username']}:{PROXY['password']}@{PROXY['host']}:{PROXY['port']}"
    return f"http://{PROXY['host']}:{PROXY['port']}"

class Encryptor:
    def __init__(self):
        self._cipher = js_compile(open("cipher_value.js").read())

    def encrypt_value(self, password, num, key) -> str:
        return self._cipher.call("encrypt", password, num, key)
def solve_captcha(arkose_blob):
    """Solve FunCaptcha using 2captcha service"""
    try:
        print(f"\n[Captcha] Solving FunCaptcha with blob: {arkose_blob}")
        
        # Format proxy in URI format: login:password@IP_address:PORT
        proxy_config = {
            'type': 'HTTP',
            'uri': f"{PROXY['username']}:{PROXY['password']}@{PROXY['host']}:{PROXY['port']}"
        }
        
        print(f"\n[Debug] Using proxy config: {proxy_config}")  # Debug line
        
        # Properly format the data parameter as a JSON string
        data_str = json.dumps({"blob": arkose_blob})
        
        result = solver.funcaptcha(
            sitekey='B7D8911C-5CC8-A9A3-35B0-554ACEE604DA',
            url='https://signup.live.com',
            surl='https://iframe.arkoselabs.com',
            data=data_str,
            proxy=proxy_config,  # Using ProxyRack proxy in URI format
            userAgent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        )
        
        print(f"\n[Captcha] Raw result: {result}")  # Add debug logging
        
        if result and isinstance(result, dict) and 'code' in result:
            print("\n[Captcha] Successfully solved captcha")
            return result['code']
        elif result and isinstance(result, str):
            print("\n[Captcha] Got string result")
            return result
            
        print("\n[Captcha] Failed to get valid response from 2captcha")
        return None

    except Exception as e:
        print(f"\n[Captcha] Error solving captcha: {str(e)}")
        print(f"\n[Captcha] Error type: {type(e)}")
        return None
    
def make_first_request():
    """Make the initial request to signup.live.com"""
    try:
        # Create TLS session
        session = tls_client.Session(
             client_identifier="firefox_120",
            random_tls_extension_order=True
         
        )

        # Headers for initial request
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Host": "signup.live.com",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }

        # Make request with proxy
        resp1 = session.get(
            "https://signup.live.com/signup", 
            headers=headers,
            proxy=get_proxy_url()
        )

        # Parse response
        soup = BeautifulSoup(resp1.text, "html.parser")
        link_tag = soup.find("a")
        
        if link_tag:
            href_value = link_tag.get("href")
            cookies = resp1.cookies
            print("\n[Request 1] Initial signup page request successful")
            return {
                "href": href_value,
                "cookies": cookies,
                "session": session
            }
        return None

    except Exception as e:
        print(f"\n[Request 1] Failed: {str(e)}")
        return None

def make_second_request(first_request_data):
    """Make the second request using href from first request"""
    try:
        session = first_request_data["session"]
        href_value = first_request_data["href"]
        
        # Update headers for second request
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Host": "login.live.com",  # Changed host for second request
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }

        # Add cookies from first request
        cookies = {
            "amsc": first_request_data["cookies"].get("amsc"),
        }

        # Make second request
        resp2 = session.get(
            href_value,
            headers=headers,
            cookies=cookies,
            proxy=get_proxy_url()
        )

        if resp2.cookies.get("uaid"):
            print("\n[Request 2] Successfully got uaid cookie")
            return {
                "uaid": resp2.cookies.get("uaid"),
                "cookies": resp2.cookies,
                "session": session
            }
        return None

    except Exception as e:
        print(f"\n[Request 2] Failed: {str(e)}")
        return None

def make_third_request(first_result, second_result):
    """Make the third request to get JS content and values"""
    try:
        session = second_result["session"]
        uaid = second_result["uaid"]
        
        # Update headers for third request
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Host": "signup.live.com",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }

        # Add cookies from previous requests
        cookies = {
            "amsc": first_result["cookies"].get("amsc"),
        }

        # Make third request
        resp3 = session.get(
            f"https://signup.live.com/signup?lic=1&uaid={uaid}",
            headers=headers,
            cookies=cookies,
            proxy=get_proxy_url()
        )

        # Save JS content for debugging
        debug_dir = "debug"
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
            
        with open(os.path.join(debug_dir, "resp3_content.html"), "w", encoding="utf-8") as f:
            f.write(resp3.text)

        # Continue with original value extraction...
        js_content = resp3.text
        values = {}
        
        # Extract api_canary
        api_canary_match = re.search(r'"apiCanary"\s*:\s*"([^"]+)"', js_content)
        if api_canary_match:
            values["api_canary"] = api_canary_match.group(1)

        # Extract fid (sHipFid)
        fid_match = re.search(r'"sHipFid"\s*:\s*"([^"]+)"', js_content)
        if fid_match:
            values["fid"] = fid_match.group(1)

        # Extract SKI
        ski_match = re.search(r'"SKI"\s*:\s*"([^"]+)"', js_content)
        if ski_match:
            values["ski"] = ski_match.group(1)

        # Extract hpgid
        hpgid_match = re.search(r'"hpgid"\s*:\s*(\d+)', js_content)
        if hpgid_match:
            values["hpgid"] = hpgid_match.group(1)

        # Extract i_ui_flavor
        i_ui_flavor_match = re.search(r'"iUiFlavor":\s*(\d+)', js_content)
        if i_ui_flavor_match:
            values["i_ui_flavor"] = i_ui_flavor_match.group(1)
        else:
            i_ui_flavor_match = re.search(r'"uiflvr":\s*(\d+)', js_content)
            if i_ui_flavor_match:
                values["i_ui_flavor"] = i_ui_flavor_match.group(1)

        # Extract scenario_id
        scenario_id_match = re.search(r'"iScenarioId"\s*:\s*(\d+)', js_content)
        if scenario_id_match:
            values["scenario_id"] = scenario_id_match.group(1)
        else:
            scenario_id_match = re.search(r'"scid"\s*:\s*(\d+)', js_content)
            if scenario_id_match:
                values["scenario_id"] = scenario_id_match.group(1)

        # Extract key and random_num
        key_match = re.search(r'var\s+Key\s*=\s*"([^"]+)"', js_content)
        random_num_match = re.search(r'var\s+randomNum\s*=\s*"([^"]+)"', js_content)
        
        if key_match:
            values["key"] = key_match.group(1)
        if random_num_match:
            values["random_num"] = random_num_match.group(1)
        else:
            print("Failed to extract random_num")
            # return None  # Return None if random_num is not found, matching original

        # Extract fptLink1
        fpt_link_match = re.search(r'https://fpt\.live\.com/\?[^"\']+', js_content)
        if fpt_link_match:
            values["fptLink1"] = fpt_link_match.group(0)

        if values and resp3.cookies.get("amsc"):
            print("\n[Request 3] Successfully got JS content and values")
            return {
                "values": values,
                "cookies": resp3.cookies,
                "session": session
            }
        return None

    except Exception as e:
        print(f"\n[Request 3] Failed: {str(e)}")
        return None

def make_fourth_request(first_result, third_result):
    """Make the fourth request to fpt.live.com for fraud prevention"""
    try:
        session = third_result["session"]
        fptLink1 = third_result["values"]["fptLink1"]
        
        # Update headers for fourth request
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Host": "fpt.live.com",
            "Referer": "https://signup.live.com/",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }

        # Add cookies from previous requests
        cookies = {
            "amsc": first_result["cookies"].get("amsc"),
        }

        # Make fourth request
        resp4 = session.get(
            fptLink1,
            headers=headers,
            cookies=cookies,
            proxy=get_proxy_url()
        )

        # Save response content for debugging
        debug_dir = "debug"
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
            
        with open(os.path.join(debug_dir, "resp4_content.html"), "w", encoding="utf-8") as f:
            f.write(resp4.text)
        print("\n[Debug] Saved resp4 content to debug/resp4_content.html")

        # Parse response to extract values
        soup = BeautifulSoup(resp4.text, "html.parser")
        script_content = None
        for script in soup.find_all("script"):
            if script.string and "txnId" in script.string:
                script_content = script.string
                break

        values = {}
        if script_content:
            # Extract all required values using regex
            txnId_match = re.search(r"txnId\s*=\s*'([^']+)'", script_content)
            ticks_match = re.search(r"ticks\s*=\s*'([^']+)'", script_content)
            rid_match = re.search(r"rid\s*=\s*'([^']+)'", script_content)
            authKey_match = re.search(r"authKey\s*=\s*'([^']+)'", script_content)
            cid_match = re.search(r"cid\s*=\s*'([^']+)'", script_content)

            if txnId_match:
                values["txnId"] = txnId_match.group(1)
            if ticks_match:
                values["ticks"] = ticks_match.group(1)
            if rid_match:
                values["rid"] = rid_match.group(1)
            if authKey_match:
                values["authKey"] = authKey_match.group(1)
            if cid_match:
                values["cid"] = cid_match.group(1)

        # Check if we got the required cookies and values
        if values and resp4.cookies.get("MUID") and resp4.cookies.get("fptctx2"):
            print("\n[Request 4] Successfully got fraud prevention values and cookies")
            return {
                "values": values,
                "cookies": resp4.cookies,
                "session": session
            }
        return None

    except Exception as e:
        print(f"\n[Request 4] Failed: {str(e)}")
        return None

def make_fifth_request(first_result, fourth_result):
    """Make the fifth request to fpt2.microsoft.com for final fraud prevention validation"""
    try:
        session = fourth_result["session"]
        values = fourth_result["values"]
        
        # First request to Clear.HTML
        url = (f"https://fpt2.microsoft.com/Clear.HTML?"
               f"ctx=Ls1.0&wl=False"
               f"&session_id={values['txnId']}"
               f"&id={values['rid']}"
               f"&w={values['ticks']}"
               f"&tkt={values['authKey']}"
               f"&CustomerId={values['cid']}")
        
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Host": "fpt2.microsoft.com",
            "Referer": "https://fpt.live.com/",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }

        cookies = {
            "amsc": first_result["cookies"].get("amsc"),
            "MUID": fourth_result["cookies"].get("MUID"),
            "fptctx2": fourth_result["cookies"].get("fptctx2"),
        }

        print("\n[Request 5] Making request with:")
        print(f"URL: {url}")
        print(f"Cookies being sent: {cookies}")

        resp5 = session.get(
            url,
            headers=headers,
            cookies=cookies,
            proxy=get_proxy_url()
        )
        
        # Save response content for debugging
        debug_dir = "debug"
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
            
        with open(os.path.join(debug_dir, "resp5_content.html"), "w", encoding="utf-8") as f:
            f.write(resp5.text)
        print(f"\n[Debug] Saved resp5 content to debug/resp5_content.html")
        print(f"[Debug] Response status code: {resp5.status_code}")
        # Check response status and cookies
        if resp5.status_code != 200:
            print(f"\n[Request 5] Failed - Bad status code: {resp5.status_code}")        
        # Step 1: First extract the entire script content
        script_match = re.search(r'<script>(.*?)</script>', resp5.text, re.DOTALL)
        if not script_match:
            print("\n[Request 5] Failed - Could not find script tag")
            print("[Debug] Full Response Content:")
            print(resp5.text)
            return None
            
        script_content = script_match.group(1)

        # Step 2: Look for the variables declared at the end
        # This pattern matches the block of variable declarations after the BaseStamp function
        vars_match = re.search(r'var\s+sid\s*=\s*"([^"]+)",\s*cid\s*=\s*"([^"]+)",\s*id\s*=\s*"([^"]+)"', script_content)
        if not vars_match:
            print("\n[Request 5] Failed - Could not find variable declarations")
            print("[Debug] Available variable declarations:")
            var_declarations = re.findall(r'var\s+(\w+)\s*=', script_content)
            print(f"Found variables: {var_declarations}")
            return None
            
        # Get the id value directly from the vars_match
        encoded_id = vars_match.group(3)  # Third capture group contains the id value
        print(f"Raw encoded value: {encoded_id}")
        
        # Split and convert each octal value
        octal_parts = [x for x in encoded_id.split('\\') if x]
        
        try:
            real_muid = ''.join(chr(int(x, 8)) for x in octal_parts)
            # print(f"\n[Debug] Conversion steps:")
            # for part in octal_parts:
            #     print(f"Converting {part} -> {chr(int(part, 8))}")
        except ValueError as ve:
            print(f"\n[Debug] Failed to convert octal values: {str(ve)}")
            return None
        
        print(f"\n[Request 5] Successfully got real MUID: {real_muid}")
        
        return {
            "real_muid": real_muid,
            "cookies": resp5.cookies,
            "session": session
        }

    except Exception as e:
        print(f"\n[Request 5] Failed with exception: {str(e)}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")
        return None

def make_sixth_request(first_result, third_result, fourth_result, fifth_result, email):
    """Make the sixth request to check email availability"""
    try:
        session = fifth_result["session"]
        uaid = third_result.get("uaid")
        
        # Prepare request data
        data = {
            "signInName": email,
            "uaid": uaid,
            "includeSuggestions": True,
            "uiflvr": 1001,
            "scid": 100118,
            "hpgid": 200639,
        }

        # Set up cookies
        cookies = {
            "amsc": first_result["cookies"].get("amsc"),
            "ai_session": generate_ai_session(),
            "MUID": fourth_result["cookies"].get("MUID"),
            "fptctx2": fourth_result["cookies"].get("fptctx2"),
        }

        # Get canary value from third request
        api_canary = third_result["values"].get("api_canary")
        if not api_canary:
            print("\n[Request 6] Failed - No API canary found")
            return None

        decoded_canary = decode_url(api_canary)

        # Set up headers
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "canary": decoded_canary,
            "Connection": "keep-alive",
            "Content-Type": "application/json; charset=utf-8",
            "correlationId": uaid,
            "Host": "signup.live.com",
            "hpgact": "0",
            "hpgid": "200639",
            "Origin": "https://signup.live.com",
            "Referer": f"https://signup.live.com/signup?lic=1&uaid={uaid}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }

        print("\n[Request 6] Making request with:")
        print(f"Data: {data}")
        print(f"Cookies: {cookies}")

        # Make the request
        resp6 = session.post(
            "https://signup.live.com/API/CheckAvailableSigninNames",
            headers=headers,
            json=data,
            proxy=get_proxy_url()
        )

        if resp6.status_code != 200:
            print(f"\n[Request 6] Failed - Bad status code: {resp6.status_code}")
            return None

        # Parse response
        response_data = resp6.json()
        if not response_data:
            print("\n[Request 6] Failed - Empty response")
            return None

        print(f"\n[Request 6] Response: {response_data}")

        # Extract required values
        api_canary = response_data.get("apiCanary")
        telemetry_context = response_data.get("telemetryContext")

        if not api_canary or not telemetry_context:
            print("\n[Request 6] Failed - Missing required response values")
            return None

        return {
            "api_canary": api_canary,
            "telemetry_context": telemetry_context,
            "cookies": resp6.cookies,
            "session": session
        }

    except Exception as e:
        print(f"\n[Request 6] Failed with exception: {str(e)}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")
        return None

def generate_ai_session():
    """Generate AI session ID"""
    session_id = base64.urlsafe_b64encode(os.urandom(16)).decode("utf-8").rstrip("=")
    timestamp = str(int(time.time() * 1000))
    return f"{session_id}|{timestamp}|{timestamp}"

def decode_url(encoded_string):
    """Decode URL encoded string"""
    return re.sub(
        r"\\u([0-9a-fA-F]{4})", 
        lambda m: chr(int(m.group(1), 16)), 
        encoded_string
    )



def make_seventh_request(first_result,second_result, third_result, fourth_result, fifth_result, sixth_result, email, password):
    """Make the seventh request to attempt account creation (pre-CAPTCHA)"""
    try:
        session = sixth_result["session"]
        
        # Get current UTC timestamp in required format
        current_time = datetime.utcnow()
        formatted_time = current_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # Prepare initial request data
        data = {
            "RequestTimeStamp": formatted_time,
            "MemberName": email,
            "Password": password,
            "CheckAvailStateMap": [f"{email}:false"],
            "FirstName": "Aladdin",
            "LastName": "Najjar",
            "BirthDate": "16:10:2001",
            "Country": "TN",
            "IsOptOutEmailDefault": False,
            "IsOptOutEmailShown": True,
            "IsOptOutEmail": False,
            "LW": True,
            "SiteId": "68692",
            "IsRDM": 0,
            "WReply": None,
            "ReturnUrl": None,
            "SignupReturnUrl": None,
            "uiflvr": 1001,
            "uaid": second_result.get("uaid"),
            "SuggestedAccountType": "EASI",
            "scid": 100118,
            "hpgid": 200650,
            "MemberNameChangeCount": 1,
            "MemberNameAvailableCount": 1,
            "MemberNameUnavailableCount": 0
        }

        # Set up headers
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "canary": sixth_result["api_canary"],
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Cookie": (f'amsc={first_result["cookies"].get("amsc")}; '
                      f'MUID={fourth_result["cookies"].get("MUID")}; '
                      f'fptctx2={fourth_result["cookies"].get("fptctx2")}; '
                      f'ai_session={generate_ai_session()}'),
            "Host": "signup.live.com",
            "hpgid": "200650",
            "Origin": "https://signup.live.com",
            "Referer": "https://signup.live.com/?lic=1",
            "scid": "100118",
            "tcxt": sixth_result["telemetry_context"],
            "uaid": second_result.get("uaid"),
            "uiflvr": "1001",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "x-ms-apiTransport": "xhr",
            "x-ms-apiVersion": "2",
        }

        # Make initial request to get arkose blob
        resp7 = session.post(
            "https://signup.live.com/API/CreateAccount?lic=1",
            headers=headers,
            json=data,
            proxy=get_proxy_url()
        )

        # Parse response to get arkose blob
        resp_data = resp7.json()
        print(f"Response: {resp_data}")
        if "error" in resp_data:
            error_data = resp_data["error"]
            result = {
                "session": session,
                "cookies": resp7.cookies,
                "telemetry_context": error_data.get("telemetryContext")
            }

            # Extract additional data if available
            if "data" in error_data:
                data = json.loads(error_data["data"])
                result.update({
                    "risk_assessment_details": data.get("riskAssessmentDetails"),
                    "rep_map_request_identifier_details": data.get("repMapRequestIdentifierDetails"),
                    "dfp_request_id": data.get("dfpRequestId"),
                    "arkose_blob": data.get("arkoseBlob")
                })

                if "arkoseBlob" in data:
                    arkose_blob = data["arkoseBlob"]
                    print("\n[Request 7] Successfully got CAPTCHA challenge")
                    print("\n[Request 7] Got arkose blob, solving captcha...")
                    
                    # Solve the captcha
                    captcha_token = solve_captcha(arkose_blob)
                    print('request 7: ', captcha_token)
                    if not captcha_token:
                        print("\n[Request 7] Failed to solve captcha")
                        return None
                    print(f"\n[Captcha] Solved captcha: {captcha_token}")
                    # Add solved captcha token to result
                    result["captcha_token"] = captcha_token
                    print('request 7: ', result)
                    return result

            print("\n[Request 7] Failed - No arkose blob in response")
            return result

        print("\n[Request 7] Failed - Unexpected response format")
        return None

    except Exception as e:
        print(f"\n[Request 7] Failed with exception: {str(e)}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")
        return None

def make_final_request(first_result, third_result, fourth_result, fifth_result, sixth_result, seventh_result, email, password):
    """Make the final request to create the account after CAPTCHA is solved"""
    try:
        session = seventh_result["session"]
        
        # Get CAPTCHA solution and risk assessment details
        captcha_token = seventh_result.get("captcha_token")
        
        print("\n[Final Request Debug] Initial values:")
        print(f"CAPTCHA token: {captcha_token[:50]}...") # Print first 50 chars
        print(f"Risk Assessment Details: {seventh_result.get('risk_assessment_details')}")
        
        if not captcha_token:
            print("\n[Final Request] No CAPTCHA token available")
            return None
            
        # First, we need to report the client event for loading enforcement
        timestamp = str(int(time.time() * 1000))
        load_enforcement_data = {
            "pageApiId": 201040,
            "clientDetails": [],
            "country": "TN",
            "userAction": "Action_LoadEnforcement,Action_ClientSideTelemetry",
            "source": "UserAction",
            "clientTelemetryData": {
                "category": "UserAction",
                "pageName": "201040",
                "eventInfo": {
                    "timestamp": timestamp,
                    "enforcementSessionToken": None,
                    "appVersion": None,
                    "networkType": None,
                },
            },
            "cxhFunctionRes": None,
            "netId": None,
            "uiflvr": 1001,
            "uaid": third_result.get("uaid"),
            "scid": 100118,
            "hpgid": 201040,
        }

        # Headers for the load enforcement request
        report_headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "canary": seventh_result.get("api_canary"),
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Cookie": (f'amsc={first_result["cookies"].get("amsc")}; '
                      f'MUID={fourth_result["cookies"].get("MUID")}; '
                      f'fptctx2={fourth_result["cookies"].get("fptctx2")}; '
                      f'clrc={{"19861":["d7PFy/1V","+VC+x0R6","FutSZdvn"]}}; '
                      f'ai_session={generate_ai_session()}'),
            "Host": "signup.live.com",
            "tcxt": seventh_result.get("telemetry_context"),
            "uaid": third_result.get("uaid"),
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        }

        # Add debug logging for load enforcement request
        print("\n[Final Request Debug] Load Enforcement Request:")
        print(f"URL: https://signup.live.com/API/ReportClientEvent?lic=1")
        print(f"Headers: {json.dumps(report_headers, indent=2)}")
        print(f"Data: {json.dumps(load_enforcement_data, indent=2)}")
        
        # Make the load enforcement request
        load_resp = session.post(
            "https://signup.live.com/API/ReportClientEvent?lic=1",
            headers=report_headers,
            json=load_enforcement_data,
            proxy=get_proxy_url()
        )
        
        print(f"\n[Final Request Debug] Load Enforcement Response:")
        print(f"Status Code: {load_resp.status_code}")
        print(f"Response: {load_resp.text}")
        
        if load_resp.status_code != 200:
            print("\n[Final Request] Load enforcement request failed")
            return None

        load_resp_data = load_resp.json()
        api_canary = load_resp_data.get("apiCanary")
        telemetry_context = load_resp_data.get("telemetryContext")

        # Now report the completion of enforcement
        complete_enforcement_data = {
            "pageApiId": 201040,
            "clientDetails": [],
            "country": "TN",
            "userAction": "Action_CompleteEnforcement,Action_ClientSideTelemetry",
            "source": "UserAction",
            "clientTelemetryData": {
                "category": "UserAction",
                "pageName": "201040",
                "eventInfo": {
                    "timestamp": timestamp,
                    "enforcementSessionToken": seventh_result.get("captcha_token"),
                    "appVersion": None,
                    "networkType": None,
                },
            },
            "cxhFunctionRes": None,
            "netId": None,
            "uiflvr": 1001,
            "uaid": third_result.get("uaid"),
            "scid": 100118,
            "hpgid": 201040,
        }

        # Update headers with new values
        report_headers.update({
            "canary": api_canary,
            "tcxt": telemetry_context
        })

        # Add debug logging for complete enforcement request
        print("\n[Final Request Debug] Complete Enforcement Request:")
        print(f"Headers: {json.dumps(report_headers, indent=2)}")
        print(f"Data: {json.dumps(complete_enforcement_data, indent=2)}")
        
        # Make the complete enforcement request
        complete_resp = session.post(
            "https://signup.live.com/API/ReportClientEvent?lic=1",
            headers=report_headers,
            json=complete_enforcement_data,
            proxy=get_proxy_url()
        )

        if complete_resp.status_code != 200:
            print("\n[Final Request] Complete enforcement request failed")
            return None

        complete_resp_data = complete_resp.json()
        api_canary = complete_resp_data.get("apiCanary")
        telemetry_context = complete_resp_data.get("telemetryContext")
        print(f"\n[Final Request Debug] Complete Enforcement Response:")
        print(f"Status Code: {complete_resp.status_code}")
        print(f"Response: {complete_resp.text}")
        # Now proceed with the final account creation request
        # Get current UTC timestamp
        current_time = datetime.utcnow()
        formatted_time = current_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # Get required values from previous requests
        key = third_result["values"].get("key")
        random_num = third_result["values"].get("random_num")
        ski = third_result["values"].get("ski")
        fid = third_result["values"].get("fid")
        
        # Encrypt password
        encryptor = Encryptor()
        encrypted_value = encryptor.encrypt_value(password, random_num, key)

        # Prepare final request data
        final_data = {
            "RequestTimeStamp": formatted_time,
            "MemberName": email,
            "CheckAvailStateMap": [f"{email}:undefined"],
            "EvictionWarningShown": [],
            "UpgradeFlowToken": {},
            "FirstName": "Aladdin",
            "LastName": "Najjar",
            "Password": password,
            "MemberNameChangeCount": 1,
            "MemberNameAvailableCount": 1,
            "MemberNameUnavailableCount": 0,
            "CipherValue": encrypted_value,
            "SKI": ski,
            "BirthDate": "17:11:1999",
            "IsUserConsentedToChinaPIPL": False,
            "Country": "TN",
            "IsOptOutEmailDefault": True,
            "VerificationCode": None,
            "IsOptOutEmailShown": 1,
            "IsOptOutEmail": True,
            "VerificationCodeSlt": None,
            "PrefillMemberNamePassed": True,
            "LW": 1,
            "SiteId": "68692",
            "IsRDM": False,
            "WReply": None,
            "ReturnUrl": None,
            "SignupReturnUrl": None,
            "uiflvr": 1001,
            "uaid": third_result.get("uaid"),
            "SuggestedAccountType": "EASI",
            "HFId": fid,
            "HType": "enforcement",
            "HSol": seventh_result.get("captcha_token"),
            "HPId": "B7D8911C-5CC8-A9A3-35B0-554ACEE604DA",
            "scid": 100118,
            "hpgid": 200639,
        }

        # Add risk assessment details if available
        if seventh_result.get("risk_assessment_details"):
            final_data["RiskAssessmentDetails"] = seventh_result["risk_assessment_details"]

        # Update headers for final request
        final_headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "canary": api_canary,
            "Connection": "keep-alive",
            "Content-Type": "application/json",
            "Cookie": (f'amsc={first_result["cookies"].get("amsc")}; '
                      f'MicrosoftApplicationsTelemetryDeviceId=dfa874b8-9e17-4654-bb56-42187176e7ad; '
                      f'MUID={fourth_result["cookies"].get("MUID")}; '
                      f'fptctx2={fourth_result["cookies"].get("fptctx2")}; '
                      f'clrc={{"19861":["d7PFy/1V","+VC+x0R6","FutSZdvn"]}}; '
                      f'ai_session={generate_ai_session()}'),
            "Host": "signup.live.com",
            "hpgid": "200639",
            "Origin": "https://signup.live.com",
            "Referer": "https://signup.live.com/?lic=1",
            "scid": "100118",
            "tcxt": telemetry_context,
            "uaid": third_result.get("uaid"),
            "uiflvr": "1001",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "x-ms-apiTransport": "xhr",
            "x-ms-apiVersion": "2",
        }

        # Add debug logging for final request
        print("\n[Final Request Debug] Final Account Creation Request:")
        print(f"Headers: {json.dumps(final_headers, indent=2)}")
        print(f"Data: {json.dumps(final_data, indent=2)}")
        
        # Make final account creation request
        final_resp = session.post(
            "https://signup.live.com/API/CreateAccount?lic=1",
            headers=final_headers,
            json=final_data,
            proxy=get_proxy_url()
        )

        print(f"\n[Final Request Debug] Final Response:")
        print(f"Status Code: {final_resp.status_code}")
        print(f"Response: {final_resp.text}")

        if final_resp.status_code == 200:
            print(f"\n[Final Request] Successfully created account: {email}")
            with open("output/created_accounts.txt", "a") as f:
                f.write(f"{email}:{password}\n")
            return {
                "success": True,
                "email": email,
                "password": password
            }
        else:
            print(f"\n[Final Request] Failed with status code: {final_resp.status_code}")
            print(f"Response: {final_resp.text}")
            return None

    except Exception as e:
        print(f"\n[Final Request] Failed with exception: {str(e)}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        print(f"Full traceback:\n{traceback.format_exc()}")
        return None

def generate_random_email():
    """Generate a random email address with @outlook.com"""
    import random, string
    return f"aladynjr228046455" + "@outlook.com"

def generate_random_password():
    """Generate a random strong password"""
    import random, string
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=12))

def email_account_creator(thread_id=None):
    """
    Creates a single email account. Can be run in parallel.
    
    Args:
        thread_id: Optional identifier for the thread running this function
    
    Returns:
        dict: Account credentials if successful, None if failed
        {
            'email': email address,
            'password': password
        }
    """
    # Generate random email and password
    email = generate_random_email()
    password = generate_random_password()
    
    print(f"\n[Thread {thread_id}] Attempting to create account with:")
    print(f"Email: {email}")
    print(f"Password: {password}")
    
    # Make first request
    first_result = make_first_request()
    if not first_result:
        print("\nFailed to complete first request")
        return

    print(f"\n[Request 1] Redirect URL: {first_result['href']}")
    print(f"[Request 1] Cookies: {dict(first_result['cookies'])}")

    # Make second request
    second_result = make_second_request(first_result)
    if not second_result:
        print("\nFailed to complete second request")
        return

    print(f"\n[Request 2] UAID: {second_result['uaid']}")
    print(f"[Request 2] Cookies: {dict(second_result['cookies'])}")

    # Make third request
    third_result = make_third_request(first_result, second_result)
    if not third_result:
        print("\nFailed to complete third request")
        return

    print(f"\n[Request 3] Extracted values: {third_result['values']}")
    print(f"[Request 3] Cookies: {dict(third_result['cookies'])}")

    # Make fourth request
    fourth_result = make_fourth_request(first_result, third_result)
    if not fourth_result:
        print("\nFailed to complete fourth request")
        return

    print(f"\n[Request 4] Extracted values: {fourth_result['values']}")
    print(f"[Request 4] Cookies: {dict(fourth_result['cookies'])}")

    # Make fifth request
    fifth_result = make_fifth_request(first_result, fourth_result)
    if not fifth_result:
        print("\nFailed to complete fifth request")
        return

    # Make sixth request
    sixth_result = make_sixth_request(first_result, third_result, fourth_result, fifth_result, email)
    if not sixth_result:
        print("\nFailed to complete sixth request")
        return

    # Make seventh request (CAPTCHA)
    seventh_result = make_seventh_request(first_result,second_result, third_result, fourth_result, fifth_result, sixth_result, email, password)
    if not seventh_result:
        print("\nFailed to complete seventh request")
        return

    # Make final request
    final_result = make_final_request(first_result, third_result, fourth_result, fifth_result, sixth_result, seventh_result, email, password)
    if final_result and final_result["success"]:
        print(f"\n[Thread {thread_id}] Successfully created account: {final_result['email']}:{final_result['password']}")
        return {
            'email': final_result['email'],
            'password': final_result['password']
        }
    else:
        print(f"\n[Thread {thread_id}] Failed to create account")
        return None

def main():
    # Number of concurrent threads to run
    num_threads = 3
    
    # Create a thread pool
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Submit tasks to the thread pool
        futures = []
        for i in range(num_threads):
            future = executor.submit(email_account_creator, i+1)  # Pass thread ID
            futures.append(future)
        
        # Wait for all tasks to complete and collect results
        results = []
        for future in futures:
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                print(f"Thread failed with error: {str(e)}")
        
        # Print summary
        print("\n=== Account Creation Summary ===")
        print(f"Total attempts: {num_threads}")
        print(f"Successful accounts: {len(results)}")
        print("\nCreated accounts:")
        for account in results:
            print(f"Email: {account['email']}, Password: {account['password']}")

if __name__ == "__main__":
    start_time = time.time()
    main()
    elapsed_time = time.time() - start_time
    print(f"\nTotal execution time: {elapsed_time:.2f} seconds") 


