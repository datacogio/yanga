import os
import logging
import requests
from gtts import gTTS
from src.config import config_instance

logger = logging.getLogger("TTSMgr")

class TTSManager:
    def __init__(self):
        pass

    def speak(self, text, output_file="/tmp/speech.mp3"):
        provider = config_instance.get("tts_provider", "gtts")
        
        try:
            if provider == "openai":
                return self._speak_openai(text, output_file)
            else:
                return self._speak_gtts(text, output_file)
        except Exception as e:
            logger.error(f"TTS Failed ({provider}): {e}")
            # Fallback to gTTS if primary fails
            logger.info("Falling back to gTTS...")
            return self._speak_gtts(text, output_file)

    def _speak_gtts(self, text, output_file):
        """Standard Google Translate TTS (Free, Robotic)"""
        tts = gTTS(text=text, lang='en')
        tts.save(output_file)
        return True

    def _speak_openai(self, text, output_file):
        """OpenAI-Compatible API (Chatterbox, OpenAI, etc.)"""
        api_url = config_instance.get("tts_api_url")
        api_key = config_instance.get("tts_api_key", "sk-dummy")
        voice_id = config_instance.get("tts_voice_id", "alloy")
        
        # Ensure we hit the speech endpoint
        if not api_url.endswith("/audio/speech"):
            if not api_url.endswith("/v1"):
                api_url = f"{api_url}/v1"
            api_url = f"{api_url}/audio/speech"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "tts-1", # Standard OpenAI model name
            "input": text,
            "voice": voice_id
        }
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            with open(output_file, "wb") as f:
                f.write(response.content)
            return True
        else:
            raise Exception(f"API Error {response.status_code}: {response.text}")

# Global Instance
tts_instance = TTSManager()
