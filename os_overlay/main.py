"""
Evo-AI Windows Overlay - Main Entry Point
Minimal Tkinter-based overlay prototype.
"""
import sys
import os
import tkinter as tk

# Add parent directory to path to import core modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.brain import Brain
from core.reasoning import Reasoner
from core.executor import Executor
from core.llm_client import LLMClient
from core.memory import Memory

from overlay_window import OverlayWindow
from controller import OverlayController
import hotkey


def main():
    """
    Initialize Brain and start Tkinter overlay.
    """
    print("Initializing Evo-AI Overlay...")
    
    # Initialize core components (unchanged)
    reasoner = Reasoner(debug=False)
    executor = Executor(debug=False)
    llm_client = LLMClient(debug=False)
    memory = Memory(debug=False)
    
    # Initialize Brain (unchanged)
    brain = Brain(
        reasoner=reasoner,
        executor=executor,
        llm_client=llm_client,
        memory=memory,
        debug=False
    )
    
    print("Brain initialized successfully")
    
    # Create Tkinter root
    root = tk.Tk()
    
    # Start hidden
    root.withdraw()
    
    # Create UI window
    window = OverlayWindow(root)
    
    # Create controller (connects UI to Brain)
    controller = OverlayController(window, brain)
    
    # Register global hotkey (Ctrl+Space)
    hotkey.register_hotkey(controller)
    
    print("Overlay ready - Press Ctrl+Space to show")
    
    try:
        # Start Tkinter main loop
        root.mainloop()
    finally:
        # Cleanup hotkeys on exit
        hotkey.unregister_all()
    
    print("Overlay closed")


if __name__ == "__main__":
    main()
