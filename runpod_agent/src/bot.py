import logging
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ZoomBot")

class ZoomBot:
    def __init__(self):
        self.driver = None
        self.running = False

    def start_browser(self):
        logger.info("Starting Chrome Browser (HEADED MODE via Xvfb)...")
        chrome_options = Options()
        # Headless DISABLED -> We are using Xvfb
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--use-fake-ui-for-media-stream")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Stability Flags
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--user-data-dir=/tmp/headed-session") 

        # Add User Agent
        chrome_options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.running = True
            logger.info("Browser started successfully.")
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            self.running = False

    def join_meeting(self, join_url: str, name: str):
        if not self.driver:
            self.start_browser()
        
        if not self.driver:
            return False, "Failed to start browser (driver is None)"

        try:
            logger.info(f"Navigating to meeting: {join_url}")
            
            if "/j/" in join_url:
                meeting_id = join_url.split("/j/")[1].split("?")[0]
                web_client_url = f"https://zoom.us/wc/{meeting_id}/join"
                if "pwd=" in join_url:
                    pwd = join_url.split("pwd=")[1].split("&")[0]
                    web_client_url += f"?pwd={pwd}"
                
                logger.info(f"Redirecting to Web Client URL: {web_client_url}")
                self.driver.get(web_client_url)
            else:
                 self.driver.get(join_url)
            
            logger.info("Page loaded. Checking for inputs...")
            
            try:
                name_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "inputname"))
                )
                name_input.clear()
                name_input.send_keys(name)
                
                join_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.ID, "joinBtn"))
                )
                join_btn.click()
                logger.info("Clicked Join. Success expected.")
                return True, "Attempting to Join"
            except:
                logger.warning("Could not find Name Input. Possible CAPTCHA or Launch Meeting page.")
                return True, "Check VNC for Interaction"

        except Exception as e:
            logger.error(f"Error joining meeting: {e}")
            return False, str(e)

    def leave_meeting(self):
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.running = False

    def get_status(self):
        return {"running": self.running}

bot_instance = ZoomBot()
