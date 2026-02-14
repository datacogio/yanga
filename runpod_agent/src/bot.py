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
        logger.info("Starting Chrome Browser...")
        chrome_options = Options()
        chrome_options.add_argument("--headless=new") # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--use-fake-ui-for-media-stream") # Allow cam/mic permissions automatically
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Audio arguments for PulseAudio
        # chrome_options.add_argument("--use-file-for-fake-audio-capture=/dev/null") # Silence input if needed? 
        # Actually we want to capture audio, so we let it use the system default which is PulseAudio in our container
        
        try:
            # In Docker, we might need to specify the driver path if installed via apt-get
            # However, webdriver-manager is safer for version matching
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
        
        try:
            logger.info(f"Navigating to meeting: {join_url}")
            self.driver.get(join_url)
            
            # Zoom Web Client Logic (Simplified)
            # 1. Dismiss cookie banners or popups if any (omitted for brevity)
            
            # 2. Handle "Launch Meeting" page -> "Join from your browser"
            # This is tricky as Zoom changes selectors often.
            # Strategy: detecting if we are on the launcher page and clicking "Join from browser"
            
            # Note: A robust implementation would need complex selectors. 
            # This is a placeholder for the logic to reach the "Join" button.
            
            # Bypass system dialog prompt is tricky in Headless. 
            # Ideally use the direct web client link if possible: `https://zoom.us/wc/{meeting_id}/join`
            
            if "/j/" in join_url:
                meeting_id = join_url.split("/j/")[1].split("?")[0]
                web_client_url = f"https://zoom.us/wc/{meeting_id}/join"
                logger.info(f"Redirecting to Web Client URL: {web_client_url}")
                self.driver.get(web_client_url)
            
            # Wait for input name field
            name_input = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "inputname"))
            )
            name_input.clear()
            name_input.send_keys(name)
            
            # Click Join
            join_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "joinBtn"))
            )
            join_btn.click()
            
            logger.info("Clicked Join button. Waiting for meeting connection...")
            
            # Wait for "Join Audio" prompt
            # ...
            
            return True
        except Exception as e:
            logger.error(f"Error joining meeting: {e}")
            return False

    def leave_meeting(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed.")
            except Exception as e:
                logger.error(f"Error closing browser: {e}")
            finally:
                self.driver = None
                self.running = False

    def get_status(self):
        return {"running": self.running, "title": self.driver.title if self.driver else None}

bot_instance = ZoomBot()
