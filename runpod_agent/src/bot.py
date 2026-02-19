import logging
import asyncio
import base64
import requests
import json
import time
import os
from gtts import gTTS
import speech_recognition as sr
import threading
from src.memory import MemoryManager

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ZoomBot")

OLLAMA_URL = "http://localhost:11434/api/generate"
VISION_MODEL = "llama3.2-vision"
CHAT_MODEL = "llama3.2-vision" # Using same model for chat logic

class VisionHelper:
    @staticmethod
    def decide_action(driver, name, join_url):
        """
        Sends current screenshot to Vision model and gets the next action instruction.
        Returns: Tuple(ACTION_TYPE, REASONING, SPEAK_TEXT)
        """
        try:
            screenshot_b64 = driver.get_screenshot_as_base64()
            
            prompt = f"""
            Identify the current state of this Zoom Meeting Join flow.
            Goal: Join the meeting with name '{name}'.
            URL: {join_url}
            
            Based on the screenshot, choose the single best ACTION from this list:
            1. CLICK_LAUNCH (If you see 'Launch Meeting' button or 'Open Zoom Meetings' dialog)
            2. ENTER_NAME (If you see an input field for 'Your Name' and a 'Join' button)
            3. CLICK_JOIN_AUDIO (If you see 'Join Audio', 'Join by Computer', or a microphone with a red slash)
            4. SOLVE_CAPTCHA (If you see a CAPTCHA or 'I am not a robot')
            5. MEETING_ENDED (If you see 'The meeting has ended', 'Host has ended the meeting', or 'Thank you for attending')
            6. END_SUCCESS (Only if you see the meeting interface AND the microphone is Unmuted/Green/Active. If audio popup is visible, choose CLICK_JOIN_AUDIO)
            
            Format: Check the image carefully. Return a JSON object:
            {{ 
                "action": "ACTION_NAME", 
                "reasoning": "Brief explanation of what you see",
                "speak": "A short, natural sentence announcing what you are doing (e.g., 'I am joining audio now.')"
            }}
            """

            payload = {
                "model": VISION_MODEL,
                "prompt": prompt,
                "stream": False,
                "images": [screenshot_b64],
                "format": "json" 
            }
            
            # logger.info("Thinking... (Sending screenshot to Vision Model)")
            response = requests.post(OLLAMA_URL, json=payload, timeout=45)
            
            if response.status_code == 200:
                result_text = response.json().get("response", "").strip()
                # logger.info(f"Model Response: {result_text}")
                try:
                    data = json.loads(result_text)
                    return (
                        data.get("action", "WAIT"), 
                        data.get("reasoning", "No reasoning provided"),
                        data.get("speak", "Processing...")
                    )
                except:
                    # Fallback if model outputs plain text
                    speak_fallback = "I am unsure, waiting."
                    if "LAUNCH" in result_text.upper(): return "CLICK_LAUNCH", result_text, "I see the launch button."
                    if "NAME" in result_text.upper(): return "ENTER_NAME", result_text, "I am entering the name."
                    if "AUDIO" in result_text.upper(): return "CLICK_JOIN_AUDIO", result_text, "Joining audio."
                    if "CAPTCHA" in result_text.upper(): return "SOLVE_CAPTCHA", result_text, "There is a CAPTCHA."
                    if "ENDED" in result_text.upper(): return "MEETING_ENDED", result_text, "The meeting has ended."
                    return "WAIT", result_text, speak_fallback
            else:
                logger.error(f"Ollama Error: {response.text}")
                return "WAIT", "Model Error", "I encountered an error."
        except Exception as e:
            logger.error(f"Vision Decision Failed: {e}")
            return "WAIT", str(e), "System failure."

class ZoomBot:
    def __init__(self):
        self.driver = None
        self.status = "IDLE"
        self.recognizer = sr.Recognizer()
        self.is_listening = False
        # Use default mic (which start.sh sets to SpeakerSink.monitor)
        self.mic_index = None 
        self.memory = MemoryManager() 

    def start_browser(self):
        """Initializes the Selenium Chrome Driver with Audio support."""
        logger.info("Starting Chrome Browser...")
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--use-fake-ui-for-media-stream") # Auto-allow mic/cam
        options.add_argument("--window-size=1280,720")
        
        # Audio Flags
        options.add_argument("--autoplay-policy=no-user-gesture-required")
        
        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            self.status = "BROWSER_READY"
            logger.info("Chrome Started Successfully.")
        except Exception as e:
            logger.error(f"Failed to start Chrome: {e}")
            self.status = "ERROR"

    def speak(self, text):
        """Uses gTTS to generate speech and plays it via mpg123 into MicSink."""
        try:
            logger.info(f"Speaking: {text}")
            tts = gTTS(text=text, lang='en')
            tts.save("/tmp/speech.mp3")
            # Play to MicSink so Zoom hears it
            os.system("PULSE_SINK=MicSink mpg123 -q /tmp/speech.mp3") 
        except Exception as e:
            logger.error(f"TTS Error: {e}")

    def listen(self):
        """Listens for audio input via PulseAudio Default Source (Force SpeakerSink.monitor)."""
        try:
            # Force PyAudio to use SpeakerSink.monitor as 'default'
            original_source = os.environ.get("PULSE_SOURCE")
            os.environ["PULSE_SOURCE"] = "SpeakerSink.monitor"
            
            try:
                # Re-initialize recognizer to pick up new env var? 
                # Actually, sr.Microphone() creates PyAudio instance on enter.
                with sr.Microphone() as source:
                    logger.info("Listening to SpeakerSink.monitor...")
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    logger.info(f"Energy Threshold: {self.recognizer.energy_threshold}")
                    
                    try:
                        audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=15)
                        logger.info(f"Audio captured! Size: {len(audio.get_raw_data())} bytes")
                    except sr.WaitTimeoutError:
                        logger.warning("Listening timed out (No speech detected).")
                        return None
            finally:
                # Restore environment
                if original_source:
                    os.environ["PULSE_SOURCE"] = original_source
                else:
                    del os.environ["PULSE_SOURCE"]

            try:
                # Using Google STT for lightweight speed 
                text = self.recognizer.recognize_google(audio)
                logger.info(f"Heard: {text}")
                self.memory.add_entry("User", text)
                return text
            except sr.UnknownValueError:
                logger.info("STT: Could not understand audio (Unintelligible).")
                return None
            except sr.RequestError as e:
                logger.error(f"STT Service Error: {e}")
                return None
        except Exception as e:
            logger.error(f"Mic Error: {e}")
            return None

    def start_conversation_loop(self):
        """Main listening loop once in the meeting."""
        self.is_listening = True
        logger.info("--- Starting Conversation Loop ---")
        self.speak("I am now listening.")
        
        while self.is_listening:
            # 1. Listen
            user_input = self.listen()
            
            if user_input:
                # 2. Think (LLM)
                response_text = self.ask_llm(user_input)
                
                # 3. Speak
                if response_text:
                    self.speak(response_text)
            
            # Check if meeting ended (Quick vision check logic or status check)
            if self.status != "IN_MEETING":
                break
        
        logger.info("Conversation Loop Ended.")

    def ask_llm(self, text):
        """Sends text to Ollama for a chat response."""
        context = self.memory.get_recent_context(limit=10)
        
        prompt = f"""You are a helpful AI assistant in a Zoom meeting.
        
CONTEXT (Recent Conversation):
{context}

CURRENT INPUT: {text}

RESPONSE (Brief and natural):"""

        payload = {
            "model": CHAT_MODEL,
            "prompt": prompt,
            "stream": False
        }
        try:
            resp = requests.post(OLLAMA_URL, json=payload, timeout=20)
            if resp.status_code == 200:
                response = resp.json().get("response", "").strip()
                self.memory.add_entry("Agent", response)
                return response
        except Exception as e:
            logger.error(f"LLM Error: {e}")
        return "I didn't quite catch that."

    def check_meeting_status_via_dom(self):
        """
        Checks DOM for indicators that we are successfully IN the meeting.
        This overrides the Vision Model if it's hallucinating.
        """
        try:
            # 1. Check for 'Leave' or 'End' button
            leave_btn = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Leave') or contains(@aria-label, 'Leave')]")
            if leave_btn: return "IN_MEETING"
            
            # 2. Check for 'Mute' / 'Unmute' button
            mute_btn = self.driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'mute') or contains(@aria-label, 'unmute')]")
            if mute_btn: return "IN_MEETING"
            
            # 3. Check for 'Chat' or 'Participants'
            footer_btns = self.driver.find_elements(By.CLASS_NAME, "footer-button__button")
            if len(footer_btns) > 2: return "IN_MEETING"
            
            return None
        except:
            return None

    def join_meeting(self, join_url: str, name: str):
        if not self.driver: self.start_browser()
        if not self.driver: return False, "Driver Failed"

        try:
            logger.info(f"Navigating: {join_url}")
            self.memory.start_session(join_url)
            self.speak(f"Navigating to Zoom meeting.")
            
            # Try efficient URL first
            if "/j/" in join_url and "wc" not in join_url:
                try:
                    mid = join_url.split("/j/")[1].split("?")[0]
                    url = f"https://zoom.us/wc/{mid}/join" 
                    if "pwd=" in join_url:
                        pwd = join_url.split("pwd=")[1].split("&")[0]
                        url += f"?pwd={pwd}"
                    self.driver.get(url)
                except:
                    self.driver.get(join_url)
            else:
                self.driver.get(join_url)
            
            logger.info("Page loaded. Entering Vision Loop...")
            
            # Smart Loop: Retry up to 15 times
            success = False
            for i in range(15):
                logger.info(f"--- Vision Cycle {i+1}/15 ---")
                
                # FAST PATH: Check DOM first!
                dom_status = self.check_meeting_status_via_dom()
                if dom_status == "IN_MEETING":
                    logger.info("DOM CHECK: Successfully detected meeting interface!")
                    action = "END_SUCCESS"
                    reasoning = "DOM elements found (Leave/Mute buttons)"
                    speech = None # Wait for explicit hello
                else:
                    # SLOW PATH: Vision Model
                    action, reasoning, speech = VisionHelper.decide_action(self.driver, name, join_url)
                
                logger.info(f"DECISION: {action} | REASON: {reasoning}")
                
                if speech: self.speak(speech)
                
                if action == "CLICK_LAUNCH":
                    self.perform_click_launch()
                elif action == "ENTER_NAME":
                    if self.perform_enter_name(name):
                        pass 
                elif action == "CLICK_JOIN_AUDIO":
                    self.perform_join_audio()
                elif action == "SOLVE_CAPTCHA":
                    logger.warning("CAPTCHA Detected! Attempting to wait/retry instead of quitting.")
                    time.sleep(5)
                elif action == "MEETING_ENDED":
                    self.speak("The meeting has ended. Goodbye.")
                    self.leave_meeting()
                    return True, "Meeting Ended"
                elif action == "END_SUCCESS":
                    self.speak("Hello everyone, I have joined the meeting.")
                    self.status = "IN_MEETING"
                    success = True
                    break # Exit Vision Loop, Enter Chat Loop
                elif action == "WAIT":
                    pass
                
                time.sleep(3)

            if success:
                # Start Conversation Thread (Non-blocking)
                threading.Thread(target=self.start_conversation_loop, daemon=True).start()
                return True, "Joined & Listening"
            else:
                return False, "Timed out trying to join."

        except Exception as e:
            logger.error(f"Error: {e}")
            self.speak("I encountered an error joining the meeting.")
            return False, str(e)
            
    def perform_join_audio(self):
        logger.info("Executing CLICK_JOIN_AUDIO...")
        try:
            self.driver.execute_script("""
                // 1. Check for 'Join Audio by Computer' (Blue Button)
                var buttons = document.querySelectorAll('button');
                for (var i = 0; i < buttons.length; i++) {
                    var text = buttons[i].innerText.toLowerCase();
                    if (text.includes('join audio by computer') || text.includes('join audio')) {
                        buttons[i].click();
                        console.log('Clicked Join Audio');
                        return;
                    }
                }
                
                // 2. Check for Unmute Icon (if muted)
                var muteBtn = document.querySelector('button[aria-label="unmute"]'); 
                if (muteBtn) {
                     muteBtn.click();
                     console.log('Clicked Unmute');
                }
            """)
        except Exception as e:
            logger.error(f"Join Audio Failed: {e}")

    def perform_click_launch(self):
        logger.info("Executing CLICK_LAUNCH...")
        try:
            self.driver.execute_script("""
                var buttons = document.querySelectorAll('a, button');
                for (var i = 0; i < buttons.length; i++) {
                    if (buttons[i].innerText.includes('Launch Meeting') || buttons[i].innerText.includes('Join from Your Browser')) {
                         buttons[i].click();
                         return;
                    }
                }
            """)
        except Exception as e:
            logger.error(f"Click Launch Failed: {e}")

    def perform_enter_name(self, name):
        logger.info(f"Executing ENTER_NAME: {name}...")
        try:
            # Locate Input Field
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="text"]'))
            )
            input_field = self.driver.find_element(By.CSS_SELECTOR, 'input[type="text"]')
            
            # Clear and Send Keys (Simulates real typing)
            input_field.clear()
            input_field.send_keys(name)
            time.sleep(1) 
            
            # Locate and Click Join Button
            join_btn = self.driver.find_element(By.CSS_SELECTOR, 'button.preview-join-button')
            # Check if enabled
            if join_btn.is_enabled():
                join_btn.click()
                logger.info("Clicked Join Button")
                return True
            else:
                logger.warning("Join Button is still disabled!")
                return False
                
        except Exception as e:
            logger.error(f"Enter Name Failed: {e}")
            return False

    def leave_meeting(self):
        self.is_listening = False # Stop loop
        self.memory.end_session()
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.status = "IDLE"
            logger.info("Browser Closed.")

    def get_status(self):
        return {"status": self.status, "listening": self.is_listening}

# Instantiate Global Bot
bot_instance = ZoomBot()
