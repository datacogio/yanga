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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ZoomBot")

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
        opts.add_argument("--user-data-dir=/tmp/headed-session") 
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
            
            if "/j/" in join_url:
                mid = join_url.split("/j/")[1].split("?")[0]
                url = f"https://zoom.us/wc/{mid}/join"
                if "pwd=" in join_url:
                    pwd = join_url.split("pwd=")[1].split("&")[0]
                    url += f"?pwd={pwd}"
                self.driver.get(url)
            else:
                 self.driver.get(join_url)
            
            logger.info("Page loaded. Waiting for input...")
            try:
                inp = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "inputname")))
                inp.clear()
                inp.send_keys(name)
                
                btn = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "joinBtn")))
                btn.click()
                logger.info("Clicked Join.")
                return True, "Joining..."
            except:
                logger.warning("Input not found. CHECK VNC!")
                return True, "Check VNC"

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
