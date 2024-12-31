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
class Encryptor:
    def __init__(self):
        self._cipher = js_compile(open("cipher_value.js").read())

    def encrypt_value(self, password, num, key) -> str:
        return self._cipher.call("encrypt", password, num, key)

def make_first_request():
    """Make the initial request to signup.live.com"""
    try:
        # Create TLS session
        session = tls_client.Session(
            client_identifier="chrome126",
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        }

        # Make request
        resp1 = session.get(
            "https://signup.live.com/signup", 
            headers=headers
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        }

        # Add cookies from first request
        cookies = {
            "amsc": first_request_data["cookies"].get("amsc"),
        }

        # Make second request
        resp2 = session.get(
            href_value,
            headers=headers,
            cookies=cookies
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        }

        # Add cookies from previous requests
        cookies = {
            "amsc": first_result["cookies"].get("amsc"),
        }

        # Make third request
        resp3 = session.get(
            f"https://signup.live.com/signup?lic=1&uaid={uaid}",
            headers=headers,
            cookies=cookies
        )

        
        # Save JS content for debugging
        debug_dir = "debug"
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
            
        with open(os.path.join(debug_dir, "resp3_content.html"), "w", encoding="utf-8") as f:
            f.write(resp3.text)

        # List all script tags
        soup = BeautifulSoup(resp3.text, "html.parser")
        script_tags = soup.find_all("script")
        
        print("\n[Debug] Found script tags:")
        for i, script in enumerate(script_tags):
            src = script.get("src", "inline script")
            print(f"{i+1}. {src}")
            if "inline script" in src and script.string:
                print(f"   Content preview: {script.string[:100]}...")

        # Extract and fetch the external JS bundle
        soup = BeautifulSoup(resp3.text, "html.parser")
        js_bundle = soup.find("script", {"class": "error-handling-tag"})
        
        # if js_bundle and js_bundle.get("src"):
        #     bundle_url = js_bundle["src"]
        #     print(f"\n[Debug] Found JS bundle URL: {bundle_url}")
            
        #     bundle_headers = {
        #         "Accept": "*/*",
        #         "Accept-Encoding": "gzip, deflate, br, zstd",
        #         "Accept-Language": "en-US,en;q=0.9",
        #         "Connection": "keep-alive",
        #         "Referer": "https://signup.live.com/",
        #         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        #     }

        #     bundle_resp = session.get(bundle_url, headers=bundle_headers)
            
        #     # Save bundle content
        #     with open(os.path.join(debug_dir, "resp3_bundle.js"), "w", encoding="utf-8") as f:
        #         f.write(bundle_resp.text)
        #     print("\n[Debug] Saved JS bundle to debug/resp3_bundle.js")

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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        }

        # Add cookies from previous requests
        cookies = {
            "amsc": first_result["cookies"].get("amsc"),
        }

        # Make fourth request
        resp4 = session.get(
            fptLink1,
            headers=headers,
            cookies=cookies
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        }

        cookies = {
            "amsc": first_result["cookies"].get("amsc"),
            "MUID": fourth_result["cookies"].get("MUID"),
            "fptctx2": fourth_result["cookies"].get("fptctx2"),
        }

        print("\n[Request 5] Making request with:")
        print(f"URL: {url}")
        print(f"Cookies being sent: {cookies}")

        resp5 = session.get(url, headers=headers, cookies=cookies)
        
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
        print("\n[Debug] Found Script Content:")
        print(script_content)
        
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
        print("\n[Debug] Found encoded id:")
        print(f"Raw encoded value: {encoded_id}")
        
        # Split and convert each octal value
        octal_parts = [x for x in encoded_id.split('\\') if x]
        print(f"Octal parts: {octal_parts}")
        
        try:
            real_muid = ''.join(chr(int(x, 8)) for x in octal_parts)
            print(f"\n[Debug] Conversion steps:")
            for part in octal_parts:
                print(f"Converting {part} -> {chr(int(part, 8))}")
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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        }

        print("\n[Request 6] Making request with:")
        print(f"Data: {data}")
        print(f"Cookies: {cookies}")

        # Make the request
        resp6 = session.post(
            "https://signup.live.com/API/CheckAvailableSigninNames",
            headers=headers,
            json=data,
            cookies=cookies
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

def make_seventh_request(first_result, third_result, fourth_result, fifth_result, sixth_result, email, password):
    """Make the seventh request to attempt account creation (pre-CAPTCHA)"""
    try:
        session = sixth_result["session"]
        
        # Get current UTC timestamp in required format
        current_time = datetime.utcnow()
        formatted_time = current_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # Prepare request data - now without encryption
        data = {
            "RequestTimeStamp": formatted_time,
            "MemberName": email,
            "Password": password,  # Send password directly
            "CheckAvailStateMap": [f"{email}:false"],
            "FirstName": "justmanooo",
            "LastName": "exploited7",
            "BirthDate": "17:11:1999",
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
            "uaid": third_result.get("uaid"),
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
            "uaid": third_result.get("uaid"),
            "uiflvr": "1001",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "x-ms-apiTransport": "xhr",
            "x-ms-apiVersion": "2",
        }

        # Make the request
        resp7 = session.post(
            "https://signup.live.com/API/CreateAccount?lic=1",
            headers=headers,
            json=data
        )

        # Parse response
        response_data = resp7.json()

        if "error" in response_data:
            error_data = response_data["error"]
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

            print("\n[Request 7] Successfully got CAPTCHA challenge")
            return result

        print("\n[Request 7] Failed - Unexpected response format")
        return None

    except Exception as e:
        print(f"\n[Request 7] Failed with exception: {str(e)}")
        return None

def main():
    # Generate random email
    email = f"dododod1231@outlook.com"
    
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

    # Make seventh request
    seventh_result = make_seventh_request(first_result, third_result, fourth_result, fifth_result, sixth_result, email, "@izlamihhz2z")
    if not seventh_result:
        print("\nFailed to complete seventh request")
        return

    print("\nAll requests completed successfully!")

if __name__ == "__main__":
    main()
