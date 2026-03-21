"""
Global hotkey registration for Kiro-Mogwai overlay.
Event-driven, no polling loops.
"""
import keyboard


def register_hotkey(controller):
    """
    Register Ctrl+Space hotkey to toggle overlay.
    Event-driven - no loops.
    """
    keyboard.add_hotkey('ctrl+space', controller.toggle_overlay, suppress=True)


def unregister_all():
    """Unregister all hotkeys on exit."""
    keyboard.unhook_all()
