"""
Overlay Window - Pure UI layer for Kiro-Mogwai.
NO AI logic, NO Brain imports, ONLY UI components.
"""
import tkinter as tk
from tkinter import scrolledtext


class OverlayWindow:
    """
    Pure UI layer - displays components and handles user interactions.
    Does NOT contain any AI logic or Brain references.
    """
    
    def __init__(self, root):
        self.root = root
        self.root.title("Kiro")
        self.root.geometry("500x400")
        
        # Always on top
        self.root.attributes("-topmost", True)
        
        # Prevent window from being too small
        self.root.minsize(400, 300)
        
        # Bind close button
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Close callback (set by controller)
        self.on_close = None
        
        # Create UI components
        self._create_widgets()
        
        # Callbacks (set by controller)
        self.on_submit = None
        self.on_approve = None
        self.on_cancel = None
        self.on_escape = None
    
    def _create_widgets(self):
        """Create all UI components."""
        # Main container
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Input section
        input_frame = tk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(input_frame, text="Command:", font=("Arial", 10)).pack(anchor=tk.W)
        
        self.input_entry = tk.Entry(input_frame, font=("Arial", 11))
        self.input_entry.pack(fill=tk.X, pady=(5, 0))
        
        # Bind Escape key
        self.input_entry.bind('<Escape>', lambda e: self.on_escape() if self.on_escape else None)
        
        # Status label
        self.status_label = tk.Label(
            main_frame,
            text="Ready",
            font=("Arial", 9),
            fg="gray"
        )
        self.status_label.pack(anchor=tk.W, pady=(5, 10))
        
        # Plan preview section
        preview_frame = tk.Frame(main_frame)
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        tk.Label(preview_frame, text="Plan Preview:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        self.preview_text = scrolledtext.ScrolledText(
            preview_frame,
            height=10,
            font=("Courier", 9),
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # Button section
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        self.approve_button = tk.Button(
            button_frame,
            text="Approve",
            font=("Arial", 10, "bold"),
            bg="#4CAF50",
            fg="white",
            state=tk.DISABLED,
            width=12
        )
        self.approve_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.cancel_button = tk.Button(
            button_frame,
            text="Cancel",
            font=("Arial", 10),
            bg="#f44336",
            fg="white",
            state=tk.DISABLED,
            width=12
        )
        self.cancel_button.pack(side=tk.LEFT)
    
    def get_user_input(self) -> str:
        """Get text from input entry."""
        return self.input_entry.get().strip()
    
    def clear_input(self):
        """Clear input entry."""
        self.input_entry.delete(0, tk.END)
    
    def set_status(self, text: str, color: str = "gray"):
        """Update status label."""
        self.status_label.config(text=text, fg=color)
    
    def show_plan(self, plan_text: str):
        """Display plan in preview area."""
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(1.0, plan_text)
        self.preview_text.config(state=tk.DISABLED)
        
        # Enable buttons
        self.approve_button.config(state=tk.NORMAL)
        self.cancel_button.config(state=tk.NORMAL)
    
    def show_result(self, result_text: str, success: bool = True):
        """Display execution result in preview area."""
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.insert(tk.END, "\n\n" + "="*50 + "\n")
        self.preview_text.insert(tk.END, "EXECUTION RESULT:\n")
        self.preview_text.insert(tk.END, "="*50 + "\n\n")
        self.preview_text.insert(tk.END, result_text)
        self.preview_text.config(state=tk.DISABLED)
        
        # Scroll to bottom
        self.preview_text.see(tk.END)
        
        # Update status
        if success:
            self.set_status("✓ Execution completed", "green")
        else:
            self.set_status("✗ Execution failed", "red")
        
        # Disable buttons after execution
        self.approve_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.DISABLED)
    
    def reset(self):
        """Reset UI to initial state."""
        self.clear_input()
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.config(state=tk.DISABLED)
        self.approve_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.DISABLED)
        self.set_status("Ready", "gray")
        self.enable_input()
    
    def enable_input(self):
        """Enable input entry."""
        self.input_entry.config(state=tk.NORMAL)
    
    def disable_input(self):
        """Disable input entry."""
        self.input_entry.config(state=tk.DISABLED)
    
    def bind_submit(self, callback):
        """Bind Enter key to submit callback."""
        self.input_entry.bind('<Return>', lambda e: callback())
    
    def bind_approve(self, callback):
        """Bind Approve button to callback."""
        self.approve_button.config(command=callback)
    
    def bind_cancel(self, callback):
        """Bind Cancel button to callback."""
        self.cancel_button.config(command=callback)
    
    def bind_escape(self, callback):
        """Bind Escape key to callback."""
        self.on_escape = callback
    
    def bind_close(self, callback):
        """Bind window close to callback."""
        self.on_close = callback
    
    def _on_close(self):
        """Handle window close button."""
        if self.on_close:
            self.on_close()
    
    def show_overlay(self):
        """Show overlay window, center on screen, and focus input."""
        # Center window on screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Show and focus
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.input_entry.focus_set()
        self.set_status("Ready", "gray")
    
    def hide_overlay(self):
        """Hide overlay window and reset UI."""
        self.root.withdraw()
        self.reset()
