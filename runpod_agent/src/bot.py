import logging
import asyncio
import base64
import requests
import json
import time
import os
from gtts import gTTS

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ZoomBot")

OLLAMA_URL = "http://localhost:11434/api/generate"
VISION_MODEL = "llama3.2-vision"

class VisionHelper:
    @staticmethod
    def decide_action(driver, name, join_url):
        """
        Sends current screenshot to Vision model and gets the next action instruction.
        Returns: Tuple(ACTION_TYPE, REASONING, SPEAK_TEXT)
        """
        try:
            screenshot_b64 = driver.get_screenshot_as_base64()
            
            prompt = f"""
            Identify the current state of this Zoom Meeting Join flow.
            Goal: Join the meeting with name '{name}'.
            URL: {join_url}
            
            Based on the screenshot, choose the single best ACTION from this list:
            1. CLICK_LAUNCH (If you see 'Launch Meeting' button or 'Open Zoom Meetings' dialog)
            2. ENTER_NAME (If you see an input field for 'Your Name' and a 'Join' button)
            3. CLICK_JOIN_AUDIO (If you see 'Join Audio', 'Join by Computer', or a microphone with a red slash)
            4. SOLVE_CAPTCHA (If you see a CAPTCHA or 'I am not a robot')
            5. END_SUCCESS (Only if you see the meeting interface AND the microphone is Unmuted/Green)
            
            Format: Check the image carefully. Return a JSON object:
            {{ 
                "action": "ACTION_NAME", 
                "reasoning": "Brief explanation of what you see",
                "speak": "A short, natural sentence announcing what you are doing (e.g., 'I am joining audio now.')"
            }}
            """

            payload = {
                "model": VISION_MODEL,
                "prompt": prompt,
                "stream": False,
                "images": [screenshot_b64],
                "format": "json" 
            }
            
            logger.info("Thinking... (Sending screenshot to Vision Model)")
            response = requests.post(OLLAMA_URL, json=payload, timeout=45)
            
            if response.status_code == 200:
                result_text = response.json().get("response", "").strip()
                logger.info(f"Model Response: {result_text}")
                try:
                    data = json.loads(result_text)
                    return (
                        data.get("action", "WAIT"), 
                        data.get("reasoning", "No reasoning provided"),
                        data.get("speak", "Processing...")
                    )
                except:
                    # Fallback if model outputs plain text
                    speak_fallback = "I am unsure, waiting."
                    if "LAUNCH" in result_text.upper(): return "CLICK_LAUNCH", result_text, "I see the launch button."
                    if "NAME" in result_text.upper(): return "ENTER_NAME", result_text, "I am entering the name."
                    if "AUDIO" in result_text.upper(): return "CLICK_JOIN_AUDIO", result_text, "Joining audio."
                    if "CAPTCHA" in result_text.upper(): return "SOLVE_CAPTCHA", result_text, "There is a CAPTCHA."
                    return "WAIT", result_text, speak_fallback
            else:
                logger.error(f"Ollama Error: {response.text}")
                return "WAIT", "Model Error", "I encountered an error."
        except Exception as e:
            logger.error(f"Vision Decision Failed: {e}")
            return "WAIT", str(e), "System failure."

class ZoomBot:
    def __init__(self):
        self.driver = None
        self.status = "IDLE"

    def start_browser(self):
        """Initializes the Selenium Chrome Driver with Audio support."""
        logger.info("Starting Chrome Browser...")
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--use-fake-ui-for-media-stream") # Auto-allow mic/cam
        options.add_argument("--window-size=1280,720")
        
        # Audio Flags
        options.add_argument("--autoplay-policy=no-user-gesture-required")
        
        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            self.status = "BROWSER_READY"
            logger.info("Chrome Started Successfully.")
        except Exception as e:
            logger.error(f"Failed to start Chrome: {e}")
            self.status = "ERROR"

    def speak(self, text):
        """Uses gTTS to generate speech and plays it via mpg123 into the Virtual Mic."""
        try:
            logger.info(f"Speaking: {text}")
            tts = gTTS(text=text, lang='en')
            # Save to shared volume or tmp
            tts.save("/tmp/speech.mp3")
            # Play using mpg123 to default sink (which loops to VirtualMic)
            os.system("mpg123 /tmp/speech.mp3")
        except Exception as e:
            logger.error(f"TTS Error: {e}")

    def join_meeting(self, join_url: str, name: str):
        if not self.driver: self.start_browser()
        if not self.driver: return False, "Driver Failed"

        try:
            logger.info(f"Navigating: {join_url}")
            self.speak(f"Navigating to Zoom meeting.")
            
            # Try efficient URL first
            if "/j/" in join_url and "wc" not in join_url:
                try:
                    mid = join_url.split("/j/")[1].split("?")[0]
                    url = f"https://zoom.us/wc/{mid}/join" 
                    if "pwd=" in join_url:
                        pwd = join_url.split("pwd=")[1].split("&")[0]
                        url += f"?pwd={pwd}"
                    self.driver.get(url)
                except:
                    self.driver.get(join_url)
            else:
                self.driver.get(join_url)
            
            logger.info("Page loaded. Entering Vision Loop...")
            
            # Smart Loop: Retry up to 8 times or until SUCCESS
            for i in range(12):
                logger.info(f"--- Vision Cycle {i+1}/12 ---")
                time.sleep(3) # Wait for render
                
                action, reasoning, speech = VisionHelper.decide_action(self.driver, name, join_url)
                logger.info(f"DECISION: {action} | REASON: {reasoning}")
                
                # Speak the model's thought process
                if speech: self.speak(speech)
                
                if action == "CLICK_LAUNCH":
                    self.perform_click_launch()
                elif action == "ENTER_NAME":
                    if self.perform_enter_name(name):
                        self.speak("I have entering the name.")
                elif action == "CLICK_JOIN_AUDIO":
                    self.perform_join_audio()
                elif action == "SOLVE_CAPTCHA":
                    self.speak("I see a CAPTCHA. Please help me.")
                    return True, "Blocked by CAPTCHA (Check VNC)"
                elif action == "END_SUCCESS":
                    self.speak("I am in the meeting and audio is active.")
                    return True, "Success (In Meeting)"
                elif action == "WAIT":
                    logger.info("Waiting for page change...")
                    continue
                
                time.sleep(2)

            return True, "Loop Finished (Check VNC)"

        except Exception as e:
            logger.error(f"Error: {e}")
            self.speak("I encountered an error joining the meeting.")
            return False, str(e)
            
    def perform_join_audio(self):
        logger.info("Executing CLICK_JOIN_AUDIO...")
        try:
            self.driver.execute_script("""
                // 1. Check for 'Join Audio by Computer' (Blue Button)
                var buttons = document.querySelectorAll('button');
                for (var i = 0; i < buttons.length; i++) {
                    var text = buttons[i].innerText.toLowerCase();
                    if (text.includes('join audio by computer') || text.includes('join audio')) {
                        buttons[i].click();
                        console.log('Clicked Join Audio');
                        return;
                    }
                }
                
                // 2. Check for Unmute Icon (if muted)
                var muteBtn = document.querySelector('button[aria-label="unmute"]'); 
                if (muteBtn) {
                     muteBtn.click();
                     console.log('Clicked Unmute');
                }
            """)
        except Exception as e:
            logger.error(f"Join Audio Failed: {e}")

    def perform_click_launch(self):
        logger.info("Executing CLICK_LAUNCH...")
        try:
            self.driver.execute_script("""
                var buttons = document.querySelectorAll('a, button');
                for (var i = 0; i < buttons.length; i++) {
                    if (buttons[i].innerText.includes('Launch Meeting') || buttons[i].innerText.includes('Join from Your Browser')) {
                         buttons[i].click();
                         return;
                    }
                }
            """)
        except Exception as e:
            logger.error(f"Click Launch Failed: {e}")

    def perform_enter_name(self, name):
        logger.info(f"Executing ENTER_NAME: {name}...")
        try:
            # Locate Input Field
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="text"]'))
            )
            input_field = self.driver.find_element(By.CSS_SELECTOR, 'input[type="text"]')
            
            # Clear and Send Keys (Simulates real typing to trigger React/Vue events)
            input_field.clear()
            input_field.send_keys(name)
            time.sleep(1) # Let UI update
            
            # Locate and Click Join Button
            join_btn = self.driver.find_element(By.CSS_SELECTOR, 'button.preview-join-button')
            # Check if enabled
            if join_btn.is_enabled():
                join_btn.click()
                logger.info("Clicked Join Button")
                return True
            else:
                logger.warning("Join Button is still disabled!")
                return False
                
        except Exception as e:
            logger.error(f"Enter Name Failed: {e}")
            return False

    def leave_meeting(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.status = "IDLE"
            logger.info("Browser Closed.")

    def get_status(self):
        return {"status": self.status}

# Instantiate Global Bot
bot_instance = ZoomBot()
