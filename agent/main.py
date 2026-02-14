import asyncio
import logging
import signal
import sys
from agent.model_manager import ModelManager
from agent.memory_manager import MemoryManager
from agent.browser_tool import BrowserTool

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SensoryAgent")

class SensoryAgent:
    def __init__(self):
        self.model_manager = ModelManager()
        self.memory_manager = MemoryManager()
        self.browser_tool = BrowserTool(headless=False) # Helper for visualization
        self.llm = self.model_manager.get_llm()
        self.running = True

    async def start(self):
        logger.info("Sensory Agent Starting...")
        
        # Initialize browser
        await self.browser_tool.start()
        
        logger.info("Agent is ready. Entering main loop...")
        
        try:
            while self.running:
                # Placeholder loop: In a real scenario, this would poll a queue or listen for input
                logger.info("Agent heartbeat...")
                
                # Example: Check memory
                # memories = self.memory_manager.recall("Who am I?")
                
                await asyncio.sleep(10)
        except asyncio.CancelledError:
            logger.info("Agent task cancelled.")
        finally:
            await self.shutdown()

    async def shutdown(self):
        logger.info("Shutting down agent...")
        await self.browser_tool.stop()
        logger.info("Shutdown complete.")

def handle_exit(sig, frame):
    logger.info("Received exit signal.")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    agent = SensoryAgent()
    asyncio.run(agent.start())
