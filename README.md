# Outlook Account Generator

Automated Outlook account creator using Google's Gemini AI to solve captchas (supports both visual and audio modes).

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/njraladdin/email-account-creator.git
   cd email-account-creator
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure config.yml:
   ```yaml
   # Required settings
   gemini_api_key: "your-api-key-here"  # Get from https://aistudio.google.com/app/apikey
   max_captcha_attempts: 5              # Max retries per captcha

   # Optional: Concurrent browser sessions (default: 1)
   concurrent_tasks: 1                   

   # Optional: Router settings for IP rotation
   # If enabled, router will reboot after each successful account creation
   router:
     enabled: false
     ip: "192.168.0.1"        # Your router's IP address
     username: "router_user"   # Router admin username
     password: "router_pass"   # Router admin password
     reboot_command: "reboot"  # Example: "reboot" or "/ip/system/reboot" or "system restart"
   ```

4. Create names.txt with random names (one per line)

## Usage

The tool can solve Arkose Labs captcha (previously FunCaptcha) using either:

1. Audio Mode (Recommended) - Solves the audio version of the captcha:
   ```
   python email_creator_with_selenium_and_gemini_audio.py
   ```

OR

2. Visual Mode - Solves the visual version of the same captcha:
   ```
   python email_creator_with_selenium_and_gemini_visual.py
   ```

Audio mode is recommended as it typically has higher success rates.

## Output & Results

Successfully created accounts will be automatically saved to `output/Genned.txt`. Each line contains:
```
[HH:MM:SS] email@outlook.com:password
```

Example:
```
[14:22:33] johndoe1995@outlook.com:strongpass123! 
[14:25:47] janesmith2001@outlook.com:securepass456!
```
