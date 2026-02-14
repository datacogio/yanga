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
    def analyze_page(driver, prompt="Describe the main button or action on this page."):
        """
        Takes a screenshot, sends it to Ollama Vision, and returns the analysis.
        """
        try:
            # 1. Capture Screenshot as Base64
            screenshot_b64 = driver.get_screenshot_as_base64()
            
            # 2. Construct Payload
            payload = {
                "model": VISION_MODEL,
                "prompt": prompt,
                "stream": False,
                "images": [screenshot_b64]
            }
            
            # 3. Send to Ollama
            logger.info("Sending screenshot to Vision Model...")
            response = requests.post(OLLAMA_URL, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json().get("response", "").strip()
                logger.info(f"Vision Analysis: {result}")
                return result
            else:
                logger.error(f"Ollama Error: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Vision Helper Failed: {e}")
            return None

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
            
            # Smart URL Handling (Force Web Client if possible)
            if "/j/" in join_url:
                mid = join_url.split("/j/")[1].split("?")[0]
                url = f"https://zoom.us/wc/{mid}/join" # Try direct WC link first
                if "pwd=" in join_url:
                    pwd = join_url.split("pwd=")[1].split("&")[0]
                    url += f"?pwd={pwd}"
                self.driver.get(url)
            else:
                 self.driver.get(join_url)
            
            logger.info("Page loaded. Checking State...")
            time.sleep(5) # Wait for redirects/rendering
            
            # --- VISION LOGIC START ---
            # 1. Check for "Launch Meeting" Landing Page
            if "launch" in self.driver.current_url or "postattendee" in self.driver.current_url:
                logger.info("Detected Launch/Post-Attendee Page. Attempting Smart Click...")
                
                # Heuristic First: Try to find hidden 'Join from Browser' link
                try:
                    logger.info("Looking for 'Join from Your Browser' link...")
                    # It's usually hidden or small text
                    links = self.driver.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        if "browser" in link.text.lower() or "join" in link.text.lower():
                            logger.info(f"Clicking link: {link.text}")
                            link.click()
                            time.sleep(5)
                            break
                except:
                    pass

                # Fallback to Vision if still stuck
                # But for now, we assume the direct link usually works or we need to click "Launch Meeting"
                try:
                    launch_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CLASS_NAME, "launch-meeting-btn"))
                    )
                    launch_btn.click()
                except:
                    pass
            
            # 2. Check for "Name Input" (Success State)
            logger.info("Checking for Name Input...")
            try:
                inp = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "inputname")))
                inp.clear()
                inp.send_keys(name)
                
                btn = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "joinBtn")))
                btn.click()
                logger.info("Clicked Join.")
                return True, "Joining..."
            except:
                # If we are here, we are stuck. Time for Vision Analysis.
                logger.warning("Input not found. Invoking Vision Agent...")
                
                analysis = VisionHelper.analyze_page(self.driver, 
                    "Is there a CAPTCHA on this page? Answer YES or NO. Is there a 'Launch Meeting' button? Answer YES or NO.")
                
                if analysis and "CAPTCHA" in analysis.upper() and "YES" in analysis.upper():
                     logger.warning("VISION REPORT: CAPTCHA DETECTED! User intervention required.")
                     return True, "Blocked by CAPTCHA (Check VNC)"
                
                if analysis and "LAUNCH MEETING" in analysis.upper():
                    logger.info("VISION REPORT: Launch Meeting button detected. Trying to click center...")
                    # TODO: Implement precise coordinate clicking in future
                    return True, "Stuck on Launch Page (Check VNC)"
                
                return True, "Check VNC (Unknown State)"

        except Exception as e:
            logger.error(f"Error: {e}")
            return False, str(e)

    def leave_meeting(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.running = False

    def get_status(self):
        return {"running": self.running}

bot_instance = ZoomBot()
