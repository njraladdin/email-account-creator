# Outlook Account Generator

Automated Outlook account creator using Google's Gemini AI to solve captchas (supports both visual and audio modes).

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Configure config.yml:
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

3. Create names.txt with random names (one per line)

## Usage

The tool offers two modes for solving Outlook's captcha:

1. Visual Mode - Uses Gemini AI to analyze captcha images:
   ```
   python email_creator_with_selenium_and_gemini_visual.py
   ```

2. Audio Mode - Uses Gemini AI to solve audio captchas (useful if visual fails):
   ```
   python email_creator_with_selenium_and_gemini_audio.py
   ```

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
