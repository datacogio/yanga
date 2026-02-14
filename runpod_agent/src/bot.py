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

# ... (ZoomBot Class) ...

    def join_meeting(self, join_url: str, name: str):
        if not self.driver: self.start_browser()
        if not self.driver: return False, "Driver Failed"

        try:
            logger.info(f"Navigating: {join_url}")
            self.speak(f"Navigating to Zoom meeting.")
            
            # Try efficient URL first
            if "/j/" in join_url and "wc" not in join_url:
                mid = join_url.split("/j/")[1].split("?")[0]
                url = f"https://zoom.us/wc/{mid}/join" 
                if "pwd=" in join_url:
                    pwd = join_url.split("pwd=")[1].split("&")[0]
                    url += f"?pwd={pwd}"
                self.driver.get(url)
            else:
                self.driver.get(join_url)
            
            logger.info("Page loaded. Entering Vision Loop...")
            
            # Smart Loop: Retry up to 8 times or until SUCCESS
            for i in range(8):
                logger.info(f"--- Vision Cycle {i+1}/8 ---")
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

    # ... (Rest of ZoomBot methods) ...
