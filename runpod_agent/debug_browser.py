from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import logging
import sys

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DebugBrowser")

def test_browser():
    logger.info("Initializing Chrome Options...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--use-fake-ui-for-media-stream")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--remote-debugging-port=9222")

    try:
        logger.info("Installing/Finding ChromeDriver...")
        executable_path = ChromeDriverManager().install()
        logger.info(f"ChromeDriver found at: {executable_path}")
        
        service = Service(executable_path)
        
        logger.info("Starting WebDriver...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        logger.info("Browser started successfully!")
        
        # Test 1: Simple Navigation
        logger.info("Test 1: Navigating to example.com...")
        driver.get("http://example.com")
        logger.info(f"Page Title: {driver.title}")
        driver.save_screenshot("debug_example.png")
        logger.info("Saved debug_example.png")
        
        # Test 2: Zoom Navigation
        logger.info("Test 2: Navigating to Zoom Web Client...")
        zoom_url = "https://zoom.us/wc/join"
        driver.get(zoom_url)
        logger.info(f"Page Title: {driver.title}")
        driver.save_screenshot("debug_zoom.png")
        logger.info("Saved debug_zoom.png")
        
        logger.info("Attempting to quit...")
        driver.quit()
        logger.info("Browser quit successfully.")
        return True
    except Exception as e:
        logger.error(f"CRITICAL FAILURE: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_browser()
    if not success:
        sys.exit(1)
