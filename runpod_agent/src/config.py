import json
import os
import logging

logger = logging.getLogger("ConfigMgr")

class ConfigManager:
    def __init__(self, config_path="/workspace/config.json"):
        self.config_path = config_path
        self.config = {
            "tts_provider": "gtts", # default
            "tts_api_url": "http://chatterbox:8000/v1",
            "tts_api_key": "",
            "tts_voice_id": "default",
            "model_vision": "llama3.2-vision",
            "model_chat": "llama3.2-vision"
        }
        self.load_config()

    def load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    saved = json.load(f)
                    self.config.update(saved)
                logger.info("Configuration loaded.")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")

    def save_config(self, new_config):
        try:
            self.config.update(new_config)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info("Configuration saved.")
            return True
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False

    def get(self, key, default=None):
        return self.config.get(key, default)

# Global Instance
config_instance = ConfigManager()
