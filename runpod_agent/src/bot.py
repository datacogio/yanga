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
        
        # Stability Flags for Docker/RunPod
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--disable-software-rasterizer") # Fix for some headless rendering crashes
        chrome_options.add_argument("--user-data-dir=/tmp/chrome-data") # Isolate user data
        
        # Audio arguments for PulseAudio
        # chrome_options.add_argument("--use-file-for-fake-audio-capture=/dev/null") # Silence input if needed? 
        # Actually we want to capture audio, so we let it use the system default which is PulseAudio in our container
        
        # Stealth / Anti-Bot Flags
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        try:
            # In Docker, we might need to specify the driver path if installed via apt-get
            # However, webdriver-manager is safer for version matching
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Stealth: Execute CDP command to hide webdriver property
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                """
            })
            
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
            
            # Zoom Web Client Logic
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
            
            return True, "Success"
        except Exception as e:
            logger.error(f"Error joining meeting: {e}")
            if self.driver:
                try:
                    self.driver.save_screenshot("/workspace/error.png")
                    with open("/workspace/error.html", "w") as f:
                        f.write(self.driver.page_source)
                    logger.info("Saved debug info to /workspace/error.png and /workspace/error.html")
                except:
                    pass
            return False, str(e)


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
