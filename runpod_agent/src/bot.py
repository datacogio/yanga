import logging
import asyncio
import base64
import requests
import json
import time

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
        Returns: Tuple(ACTION_TYPE, REASONING)
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
            3. SOLVE_CAPTCHA (If you see a CAPTCHA or 'I am not a robot')
            4. WAIT (If the page is loading or blank)
            5. SUCCESS (If you see the meeting interface with microphone/video icons)
            
            Format: Check the image carefully. Return a JSON object:
            {{ "action": "ACTION_NAME", "reasoning": "Brief explanation of what you see" }}
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
                    return data.get("action", "WAIT"), data.get("reasoning", "No reasoning provided")
                except:
                    # Fallback if model outputs plain text
                    if "LAUNCH" in result_text.upper(): return "CLICK_LAUNCH", result_text
                    if "NAME" in result_text.upper(): return "ENTER_NAME", result_text
                    if "CAPTCHA" in result_text.upper(): return "SOLVE_CAPTCHA", result_text
                    return "WAIT", result_text
            else:
                logger.error(f"Ollama Error: {response.text}")
                return "WAIT", "Model Error"
        except Exception as e:
            logger.error(f"Vision Decision Failed: {e}")
            return "WAIT", str(e)

class ZoomBot:
    def __init__(self):
        self.driver = None
        self.running = False

    def start_browser(self):
        logger.info("Starting Chrome HEADED (Xvfb)...")
        opts = Options()
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--use-fake-ui-for-media-stream")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--disable-extensions")
        opts.add_argument("--disable-setuid-sandbox")
        opts.add_argument("--disable-infobars")
        opts.add_argument("--user-data-dir=/tmp/vision-session") 
        opts.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=opts)
            self.running = True
            logger.info("Browser started.")
        except Exception as e:
            logger.error(f"Failed: {e}")
            self.running = False

    def join_meeting(self, join_url: str, name: str):
        if not self.driver: self.start_browser()
        if not self.driver: return False, "Driver Failed"

        try:
            logger.info(f"Navigating: {join_url}")
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
            
            # Smart Loop: Retry up to 5 times or until SUCCESS
            for i in range(5):
                logger.info(f"--- Vision Cycle {i+1}/5 ---")
                time.sleep(3) # Wait for render
                
                action, reasoning = VisionHelper.decide_action(self.driver, name, join_url)
                logger.info(f"DECISION: {action} | REASON: {reasoning}")
                
                if action == "CLICK_LAUNCH":
                    self.perform_click_launch()
                elif action == "ENTER_NAME":
                    if self.perform_enter_name(name):
                        return True, "Joining (Name Entered)"
                elif action == "SOLVE_CAPTCHA":
                    return True, "Blocked by CAPTCHA (Check VNC)"
                elif action == "SUCCESS":
                    return True, "Already in Meeting"
                elif action == "WAIT":
                    logger.info("Waiting for page change...")
                    continue
                
                time.sleep(2)

            return True, "Loop Finished (Check VNC)"

        except Exception as e:
            logger.error(f"Error: {e}")
            return False, str(e)

    def perform_click_launch(self):
        logger.info("Executing CLICK_LAUNCH...")
        try:
            # Try JS Click on common buttons
            self.driver.execute_script("""
                var buttons = document.querySelectorAll('button, a');
                for (var i = 0; i < buttons.length; i++) {
                    var text = buttons[i].innerText.toLowerCase();
                    if (text.includes('launch meeting') || text.includes('join from your browser')) {
                        buttons[i].click();
                        return;
                    }
                }
            """)
            # Backup: Class name
            try:
                self.driver.find_element(By.CLASS_NAME, "launch-meeting-btn").click()
            except: pass
        except Exception as e:
            logger.error(f"Click Launch Failed: {e}")

    def perform_enter_name(self, name):
        logger.info(f"Executing ENTER_NAME with '{name}'...")
        try:
            # Try specific ID first
            try:
                inp = self.driver.find_element(By.ID, "inputname")
                inp.clear()
                inp.send_keys(name)
            except:
                # Fallback: Find visible text input
                inputs = self.driver.find_elements(By.TAG_NAME, "input")
                for i in inputs:
                    if i.is_displayed() and i.get_attribute("type") in ["text"]:
                        i.clear()
                        i.send_keys(name)
                        break
            
            # Click Join
            try:
                self.driver.find_element(By.ID, "joinBtn").click()
            except:
                # Fallback: Find button with "Join" text
                self.driver.execute_script("""
                    var buttons = document.querySelectorAll('button');
                    for (var i = 0; i < buttons.length; i++) {
                        if (buttons[i].innerText.toLowerCase() === 'join') {
                            buttons[i].click();
                            return;
                        }
                    }
                """)
            return True
        except Exception as e:
            logger.error(f"Enter Name Failed: {e}")
            return False

    def leave_meeting(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.running = False

    def get_status(self):
        return {"running": self.running}

bot_instance = ZoomBot()
