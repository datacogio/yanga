import os
import logging
import asyncio
from playwright.async_api import async_playwright, Page, BrowserContext
from playwright_stealth import stealth_async

logger = logging.getLogger("BrowserTool")

class BrowserTool:
    def __init__(self, headless: bool = False, user_data_dir: str = "/app/browser_data"):
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.playwright = None
        self.context = None
        self.page = None
        self._lock = asyncio.Lock()

    async def start(self):
        async with self._lock:
            if self.context:
                return

            self.playwright = await async_playwright().start()
            
            # Use launch_persistent_context for keeping cookies/login state
            # Args for stealth and docker environment
            args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage", # Crucial for Docker
                "--disable-gpu" if self.headless else "",
            ]
            
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=self.headless,
                args=[a for a in args if a],
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
            )
            
            # Create a new page or get existing one
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = await self.context.new_page()

            # Apply stealth
            await stealth_async(self.page) 
            # Note: manually applying some stealth scripts if package missing
            await self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            logger.info("Browser started with persistent context.")

    async def navigate(self, url: str):
        if not self.page:
            await self.start()
        logger.info(f"Navigating to {url}")
        await self.page.goto(url, wait_until="domcontentloaded")
        return f"Navigated to {url}"

    async def click(self, selector: str):
        if not self.page:
            await self.start()
        logger.info(f"Clicking {selector}")
        await self.page.click(selector)
        return f"Clicked {selector}"

    async def type(self, selector: str, text: str):
        if not self.page:
            await self.start()
        logger.info(f"Typing into {selector}")
        await self.page.type(selector, text, delay=50) # Human-like delay
        return f"Typed text into {selector}"

    async def read_screen(self):
        if not self.page:
            await self.start()
        content = await self.page.evaluate("document.body.innerText")
        return content

    async def screenshot(self, path: str = "screenshot.png"):
        if not self.page:
            await self.start()
        await self.page.screenshot(path=path)
        return f"Screenshot saved to {path}"

    async def stop(self):
        if self.context:
            await self.context.close()
            self.context = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
