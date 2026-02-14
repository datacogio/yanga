import yaml
import os
from pathlib import Path
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_anthropic import ChatAnthropic # Optional if needed
import logging

logger = logging.getLogger("ModelManager")

class ModelManager:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.provider = self.config.get("llm", {}).get("provider", "ollama")
        
    def _load_config(self, path: str) -> dict:
        try:
            # Look in current dir or parent dir
            p = Path(path)
            if not p.exists():
                p = Path("/app") / path # Docker path fallback
            
            if p.exists():
                with open(p, "r") as f:
                    return yaml.safe_load(f)
            else:
                logger.warning(f"Config file {path} not found. Using defaults.")
                return {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    def get_llm(self):
        llm_config = self.config.get("llm", {})
        
        if self.provider == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", llm_config.get("base_url", "http://localhost:11434"))
            model = llm_config.get("model", "deepseek-r1:1.5b")
            logger.info(f"Initializing Ollama LLM: {model} at {base_url}")
            return ChatOllama(
                base_url=base_url,
                model=model,
                temperature=0.7
            )
            
        elif self.provider == "google":
            model = llm_config.get("model", "gemini-1.5-pro")
            api_key = os.getenv("GOOGLE_API_KEY")
            logger.info(f"Initializing Google LLM: {model}")
            return ChatGoogleGenerativeAI(
                model=model,
                google_api_key=api_key
            )
            
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
