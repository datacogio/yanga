import os
from celery import Celery
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AgentWorker")

# Redis Config
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery('agent_worker', broker=REDIS_URL, backend=REDIS_URL)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

@app.task
def long_wait_task(seconds: int):
    """Example task: Wait for X seconds (e.g., check email later)"""
    logger.info(f"Waiting for {seconds} seconds...")
    time.sleep(seconds)
    logger.info("Wait complete.")
    return f"Waited {seconds} seconds"

@app.task
def process_data(data: dict):
    """Example CPU bound task"""
    logger.info(f"Processing data: {data}")
    # Simulate work
    time.sleep(1)
    return {"status": "processed", "result": "ok"}
