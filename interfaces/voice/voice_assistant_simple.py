"""
Simple Voice Assistant - Alternative implementation without PyAudio.
Uses Windows Speech API (SAPI) for both recognition and synthesis.
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

# Check platform
if sys.platform != 'win32':
    print("⚠️  This simple voice assistant only works on Windows.")
    print("   For cross-platform support, use voice_assistant.py with PyAudio.")
    sys.exit(1)

# Windows-only voice libraries (no PyAudio needed!)
try:
    import win32com.client
    import pythoncom
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    print("⚠️  Windows COM libraries not installed!")
    print("   Install with: pip install pywin32")


class SimpleVoiceAssistant:
    """
    Simple voice interface for Windows using SAPI.
    Architecture: Voice (I/O) → Brain (logic) → Core
    No PyAudio required!
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug
        
        if not VOICE_AVAILABLE:
            raise RuntimeError("Windows COM libraries not available. Install: pip install pywin32")
        
        # Initialize COM for this thread
        pythoncom.CoInitialize()
        
        # Initialize Windows SAPI components (I/O only)
        self.speaker = win32com.client.Dispatch("SAPI.SpVoice")
        self.recognizer = win32com.client.Dispatch("SAPI.SpSharedRecognizer")
        self.context = self.recognizer.CreateRecoContext()
        
        # Configure voice
        self._configure_voice()
        
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
        self.last_recognition = ""
        
        print("✓ Voice assistant ready (Windows SAPI)")
    
    def _configure_voice(self):
        """Configure text-to-speech voice."""
        # Get available voices
        voices = self.speaker.GetVoices()
        
        # Try to use a female voice if available
        for i in range(voices.Count):
            voice = voices.Item(i)
            if 'female' in voice.GetDescription().lower() or 'zira' in voice.GetDescription().lower():
                self.speaker.Voice = voice
                break
        
        # Set speech rate (-10 to 10, default 0)
        self.speaker.Rate = 1  # Slightly faster
        
        # Set volume (0 to 100)
        self.speaker.Volume = 90
    
    def _log(self, message: str):
        if self.debug:
            print(f"[VOICE] {message}")
    
    def listen_once(self) -> str:
        """
        Listen for a single voice command using Windows Speech Recognition.
        Returns: text string or empty string on failure.
        """
        try:
            print("\n🎤 Listening... (speak now)")
            
            # Create grammar for dictation (free-form speech)
            grammar = self.context.CreateGrammar()
            grammar.DictationSetState(1)  # Enable dictation
            
            # Wait for recognition event
            import time
            timeout = 10  # 10 second timeout
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                # Process Windows messages
                pythoncom.PumpWaitingMessages()
                
                # Check for recognition
                if hasattr(self.context, 'Recognition'):
                    result = self.context.Recognition
                    if result:
                        text = result.PhraseInfo.GetText()
                        self._log(f"Recognized: {text}")
                        return text.strip()
                
                time.sleep(0.1)
            
            print("⏱️  No speech detected (timeout)")
            return ""
            
        except Exception as e:
            self._log(f"Listen error: {e}")
            print(f"❌ Error: {e}")
            return ""
    
    def listen_simple(self) -> str:
        """
        Simple text input fallback when speech recognition fails.
        """
        try:
            text = input("\n💬 Type your message (or 'speak' to try voice): ").strip()
            if text.lower() == 'speak':
                return self.listen_once()
            return text
        except (EOFError, KeyboardInterrupt):
            return "exit"
    
    def speak(self, text: str):
        """
        Convert text to speech and speak it.
        """
        if not text:
            return
        
        try:
            print(f"\n🔊 Kiro: {text}\n")
            self.speaker.Speak(text)
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
        print("🎤 Kiro Simple Voice Assistant (Windows)")
        print("="*50)
        
        if not self.brain.local_available:
            print("\n⚠️  Warning: Ollama not running!")
            print("   Voice assistant will have limited capabilities.")
            print("   Start Ollama with: ollama serve\n")
        else:
            print(f"\n✓ Connected to {self.llm.ollama_model}")
        
        print("\nVoice Commands:")
        print("  - Say 'exit', 'quit', or 'goodbye' to stop")
        print("  - Type your message if voice recognition fails")
        print("  - Type 'speak' to try voice recognition")
        print("\nReady! Start speaking or typing...\n")
        
        # Welcome message
        self.speak("Hello! I'm Kiro, your voice assistant. How can I help you?")
        
        # Main loop
        while self.running:
            try:
                # Listen for voice input (I/O)
                # Using simple text input as fallback
                text = self.listen_simple()
                
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
        
        # Cleanup COM
        pythoncom.CoUninitialize()


def main():
    """Entry point for simple voice assistant."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Kiro Simple Voice Assistant (Windows)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    try:
        assistant = SimpleVoiceAssistant(debug=args.debug)
        assistant.run()
    except RuntimeError as e:
        print(f"\n❌ {e}")
        print("\nInstallation instructions:")
        print("  pip install pywin32")
        sys.exit(1)


if __name__ == "__main__":
    main()
