"""
Evo-AI Overlay — Main entry point.

Starts the Brain, creates the modern overlay window, registers the global
hotkey (Ctrl+Space), and enters the Tkinter event loop.

Architecture note:
  Brain is initialised once and shared via OverlayController.
  The UI thread never calls Brain directly — all AI work runs in daemon threads
  and posts results back via root.after().
"""
import sys
import os
import tkinter as tk

# Add parent directory so core modules are importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.brain    import Brain
from core.reasoning import Reasoner
from core.executor  import Executor
from core.llm_client import LLMClient
from core.memory    import Memory

from overlay_window import OverlayWindow
from controller     import OverlayController
import hotkey


def main():
    print("Starting Evo-AI Overlay…")

    # ── Core components (unchanged) ───────────────────────────────────────────
    reasoner   = Reasoner(debug=False)
    executor   = Executor(debug=False)
    llm_client = LLMClient(debug=False)
    memory     = Memory(debug=False)

    brain = Brain(
        reasoner=reasoner,
        executor=executor,
        llm_client=llm_client,
        memory=memory,
        debug=False,
    )
    print("Brain ready")

    # ── Tkinter root ──────────────────────────────────────────────────────────
    root = tk.Tk()
    root.withdraw()   # hidden until hotkey

    # ── UI + Controller ───────────────────────────────────────────────────────
    window     = OverlayWindow(root)
    controller = OverlayController(window, brain)

    # ── Global hotkey ─────────────────────────────────────────────────────────
    hotkey.register_hotkey(controller)
    print("Ready — press Ctrl+Space to open")

    try:
        root.mainloop()
    finally:
        hotkey.unregister_all()

    print("Overlay closed")


if __name__ == "__main__":
    main()
