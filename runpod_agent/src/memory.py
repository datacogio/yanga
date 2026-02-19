import json
import os
import uuid
from datetime import datetime
import logging

logger = logging.getLogger("MemoryMgr")

class MemoryManager:
    def __init__(self, base_path="/workspace/memory"):
        self.base_path = base_path
        self.sessions_file = os.path.join(base_path, "sessions.json")
        self.transcripts_dir = os.path.join(base_path, "transcripts")
        self.current_session_id = None
        self.transcript = []
        
        # Ensure directories exist
        try:
            os.makedirs(self.transcripts_dir, exist_ok=True)
            if not os.path.exists(self.sessions_file):
                with open(self.sessions_file, 'w') as f:
                    json.dump([], f)
        except Exception as e:
            logger.error(f"Failed to initialize memory storage: {e}")

    def start_session(self, meeting_url):
        self.current_session_id = str(uuid.uuid4())
        self.transcript = []
        
        session_info = {
            "id": self.current_session_id,
            "url": meeting_url,
            "start_time": datetime.now().isoformat(),
            "end_time": None
        }
        
        self._append_session(session_info)
        logger.info(f"Started session: {self.current_session_id}")
        return self.current_session_id

    def end_session(self):
        if not self.current_session_id:
            return
            
        # Update end time in sessions.json
        self._update_session_end_time(self.current_session_id)
        
        # Save final transcript
        self._save_transcript()
        
        logger.info(f"Ended session: {self.current_session_id}")
        self.current_session_id = None
        self.transcript = []

    def add_entry(self, speaker, text):
        if not self.current_session_id:
            # Optionally auto-start session or just log warning
            # logger.warning("No active session. Transcript entry ignored.")
            return

        entry = {
            "timestamp": datetime.now().isoformat(),
            "speaker": speaker,
            "text": text
        }
        self.transcript.append(entry)
        
        # Persist frequently (or on every message for safety)
        self._save_transcript()

    def get_recent_context(self, limit=10):
        """Returns the last `limit` exchanges as a formatted string."""
        if not self.transcript:
            return ""
            
        recent = self.transcript[-limit:]
        context_str = "\n".join([f"{e['speaker']}: {e['text']}" for e in recent])
        return context_str

    def _save_transcript(self):
        if not self.current_session_id:
            return
        file_path = os.path.join(self.transcripts_dir, f"{self.current_session_id}.json")
        try:
            with open(file_path, 'w') as f:
                json.dump(self.transcript, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save transcript: {e}")

    def _append_session(self, session_info):
        try:
            # Read existing
            sessions = []
            if os.path.exists(self.sessions_file):
                try:
                    with open(self.sessions_file, 'r') as f:
                        sessions = json.load(f)
                except json.JSONDecodeError:
                    sessions = []
            
            sessions.append(session_info)
            
            with open(self.sessions_file, 'w') as f:
                json.dump(sessions, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to append session info: {e}")

    def _update_session_end_time(self, session_id):
        try:
            if not os.path.exists(self.sessions_file):
                return

            with open(self.sessions_file, 'r') as f:
                sessions = json.load(f)
            
            updated = False
            for s in sessions:
                if s['id'] == session_id:
                    s['end_time'] = datetime.now().isoformat()
                    updated = True
                    break
            
            if updated:
                with open(self.sessions_file, 'w') as f:
                    json.dump(sessions, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to update session end time: {e}")
