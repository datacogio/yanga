from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.bot import bot_instance
from src.audio import audio_instance
import requests
import os

app = FastAPI(title="RunPod Zoom Agent")

class JoinRequest(BaseModel):
    url: str
    name: str = "AI Agent"

@app.get("/health")
def health_check():
    return {"status": "healthy"}

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
