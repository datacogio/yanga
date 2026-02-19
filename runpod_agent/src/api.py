from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from src.bot import bot_instance
from src.audio import audio_instance
from src.config import config_instance
import requests
import os

app = FastAPI(title="RunPod Zoom Agent")

# Setup Templates
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

class JoinRequest(BaseModel):
    url: str
    name: str = "AI Agent"

class ConfigRequest(BaseModel):
    tts_provider: str
    tts_api_url: str = None
    tts_api_key: str = None
    tts_voice_id: str = None

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# --- Configuration Endpoints ---

@app.get("/config", response_class=HTMLResponse)
async def get_config_page(request: Request):
    """Serves the configuration HTML page."""
    # If the request accepts HTML, return the page
    if "text/html" in request.headers.get("accept", ""):
        return templates.TemplateResponse("config.html", {"request": request})
    # Otherwise return JSON config
    return config_instance.config

@app.post("/config")
def update_config(cfg: ConfigRequest):
    """Updates the agent configuration."""
    new_conf = cfg.dict()
    config_instance.save_config(new_conf)
    # Reload bot config (dynamic update)
    bot_instance.reload_config()
    return {"status": "updated", "config": config_instance.config}

@app.post("/test_tts")
def test_tts():
    """Triggers a TTS test with current settings."""
    bot_instance.speak("This is a test of the text to speech system.")
    return {"status": "playing"}

# --- Core Endpoints ---

@app.post("/join")
def join_meeting(request: JoinRequest):
    success, error_msg = bot_instance.join_meeting(request.url, request.name)
    if success:
        return {"message": "Attempting to join meeting", "url": request.url}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to join meeting: {error_msg}")

@app.post("/leave")
def leave_meeting():
    bot_instance.leave_meeting()
    return {"message": "Left meeting"}

@app.get("/status")
def status():
    return bot_instance.get_status()

@app.get("/audio/status")
def audio_status():
    return audio_instance.check_audio_system()

@app.get("/ollama/check")
def check_ollama():
    """
    Proxy check to see if Ollama is reachable on localhost
    """
    try:
        ollama_host = os.getenv("OLLAMA_HOST", "localhost:11434")
        resp = requests.get(f"http://{ollama_host}/api/tags")
        if resp.status_code == 200:
            return {"status": "ok", "models": resp.json()}
        else:
            return {"status": "error", "code": resp.status_code}
    except Exception as e:
        return {"status": "error", "message": str(e)}
