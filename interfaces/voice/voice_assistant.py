"""
Voice Assistant - Voice I/O layer for Kiro-Mogwai.
Handles speech-to-text, text-to-speech, and microphone input.
NO reasoning, NO tools, NO memory - ONLY I/O.
"""
import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.brain import Brain
from core.reasoning import Reasoner
from core.executor import Executor
from core.llm_client import LLMClient
from core.memory import Memory

# Voice libraries (simple, offline-capable)
try:
    import speech_recognition as sr
    import pyttsx3
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    print("⚠️  Voice libraries not installed!")
    print("   Install with: pip install SpeechRecognition pyttsx3 pyaudio")


class VoiceAssistant:
    """
    Voice interface for Kiro-Mogwai.
    Architecture: Voice (I/O) → Brain (logic) → Core
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        
        if not VOICE_AVAILABLE:
            raise RuntimeError("Voice libraries not available. Install: pip install SpeechRecognition pyttsx3 pyaudio")
        
        # Initialize voice components (I/O only)
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.tts_engine = pyttsx3.init()
        
        # Configure TTS for natural speech
        self._configure_tts()
        
        # Initialize brain (pure logic)
        self.llm = LLMClient(debug=debug)
        self.memory = Memory(debug=debug)
        self.reasoner = Reasoner(debug=debug)
        self.executor = Executor(debug=debug)
        
        self.brain = Brain(
            reasoner=self.reasoner,
            executor=self.executor,
            llm_client=self.llm,
            memory=self.memory,
            debug=debug
        )
        
        self.running = True
        
        # Adjust for ambient noise on startup
        print("🎤 Calibrating microphone for ambient noise...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        print("✓ Microphone ready")
    
    def _configure_tts(self):
        """Configure text-to-speech engine."""
        # Set voice properties
        voices = self.tts_engine.getProperty('voices')
        
        # Try to use a female voice if available (more pleasant)
        for voice in voices:
            if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                self.tts_engine.setProperty('voice', voice.id)
                break
        
        # Set speech rate (words per minute)
        self.tts_engine.setProperty('rate', 175)  # Slightly faster than default
        
        # Set volume (0.0 to 1.0)
        self.tts_engine.setProperty('volume', 0.9)
    
    def _log(self, message: str):
        if self.debug:
            print(f"[VOICE] {message}")
    
    def listen(self) -> str:
        """
        Listen to microphone and convert speech to text.
        Returns: text string or empty string on failure.
        """
        try:
            with self.microphone as source:
                print("\n🎤 Listening...")
                
                # Listen with timeout
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
                print("🔄 Processing speech...")
                
                # Convert speech to text (offline first, then online)
                try:
                    # Try offline recognition first (faster, no internet)
                    text = self.recognizer.recognize_sphinx(audio)
                    self._log("Used offline speech recognition")
                except (sr.UnknownValueError, sr.RequestError):
                    # Fallback to Google (requires internet)
                    try:
                        text = self.recognizer.recognize_google(audio)
                        self._log("Used Google speech recognition")
                    except sr.UnknownValueError:
                        print("❌ Could not understand audio")
                        return ""
                    except sr.RequestError as e:
                        print(f"❌ Speech recognition error: {e}")
                        return ""
                
                return text.strip()
                
        except sr.WaitTimeoutError:
            print("⏱️  No speech detected (timeout)")
            return ""
        except Exception as e:
            self._log(f"Listen error: {e}")
            print(f"❌ Error: {e}")
            return ""
    
    def speak(self, text: str):
        """
        Convert text to speech and speak it.
        """
        if not text:
            return
        
        try:
            print(f"\n🔊 Kiro: {text}\n")
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            self._log(f"Speak error: {e}")
            print(f"❌ TTS error: {e}")
    
    def process_voice_input(self, text: str):
        """
        Process voice input through brain and speak response.
        This is the main I/O orchestration method.
        """
        if not text:
            return
        
        print(f"💭 You said: {text}")
        
        # Check for exit commands
        if text.lower() in ['exit', 'quit', 'goodbye', 'bye', 'stop']:
            self.speak("Goodbye! Have a great day.")
            self.memory.save_session()
            self.running = False
            return
        
        # Call brain (pure logic, no I/O)
        response = self.brain.process(text)
        
        # Speak the response
        self.speak(response)
    
    def run(self):
        """
        Main voice interaction loop.
        Architecture: Listen → Brain.process() → Speak → Loop
        """
        print("\n" + "="*50)
        print("🎤 Kiro Voice Assistant")
        print("="*50)
        
        if not self.brain.local_available:
            print("\n⚠️  Warning: Ollama not running!")
            print("   Voice assistant will have limited capabilities.")
            print("   Start Ollama with: ollama serve\n")
        else:
            print(f"\n✓ Connected to {self.llm.ollama_model}")
        
        print("\nVoice Commands:")
        print("  - Say 'exit', 'quit', or 'goodbye' to stop")
        print("  - Speak naturally for questions and commands")
        print("\nReady! Start speaking...\n")
        
        # Welcome message
        self.speak("Hello! I'm Kiro, your voice assistant. How can I help you?")
        
        # Main loop
        while self.running:
            try:
                # Listen for voice input (I/O)
                text = self.listen()
                
                if text:
                    # Process through brain and speak response (I/O)
                    self.process_voice_input(text)
                
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted by user")
                self.speak("Goodbye!")
                self.memory.save_session()
                break
            except Exception as e:
                self._log(f"Loop error: {e}")
                print(f"❌ Error: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()


def main():
    """Entry point for voice assistant."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Kiro Voice Assistant")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    try:
        assistant = VoiceAssistant(debug=args.debug)
        assistant.run()
    except RuntimeError as e:
        print(f"\n❌ {e}")
        print("\nInstallation instructions:")
        print("  pip install SpeechRecognition pyttsx3 pyaudio")
        print("\nNote: pyaudio may require additional setup on some systems.")
        sys.exit(1)


if __name__ == "__main__":
    main()
