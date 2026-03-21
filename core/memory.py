"""
Local chat and persona memory management.
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Any


class Memory:
    def __init__(self, config_dir: str = "config", logs_dir: str = "logs", debug: bool = False):
        self.config_dir = config_dir
        self.logs_dir = logs_dir
        self.debug = debug
        self.chat_history: List[Dict[str, str]] = []
        self.personality = self._load_personality()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        os.makedirs(logs_dir, exist_ok=True)
        
        # Don't show "history restored" message - just load silently
        self._log(f"Session ID: {self.session_id}")
    
    def _log(self, message: str):
        if self.debug:
            print(f"[MEMORY] {message}")
    
    def _load_personality(self) -> Dict[str, Any]:
        """Load personality configuration."""
        personality_path = os.path.join(self.config_dir, "personality.json")
        try:
            if os.path.exists(personality_path):
                with open(personality_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self._log(f"Error loading personality: {e}")
        
        return {
            "name": "Kiro-Mogwai",
            "identity": "I am your local assistant.",
            "principles": []
        }
    
    def get_system_prompt(self) -> str:
        """Generate system prompt optimized for fast, accurate responses."""
        return """You are Kiro, a helpful desktop AI assistant with access to system tools.

Core Principles:
- Be concise and direct - avoid unnecessary explanations
- When a task can be done with tools, suggest using them
- Provide accurate information - if unsure, say so
- Keep responses short unless detail is requested
- Use simple language and clear structure

Tool Usage:
- You can execute system commands, open applications, search files
- When user asks to do something actionable, use tools when possible
- Explain what you're doing briefly

Response Format:
- Start with direct answer
- Use bullet points for lists (dashes, not asterisks)
- Keep paragraphs short (2-3 sentences max)
- No markdown bold/italic symbols

Examples:
User: "open chrome"
You: [Execute tool, confirm action]

User: "what is python?"
You: Python is a programming language known for simplicity and readability. It's widely used for web development, data science, and automation.

Be helpful, accurate, and efficient."""
    
    def get_conversation_for_llm(self, max_messages: int = 6) -> List[Dict[str, str]]:
        """Get recent conversation formatted for LLM (limited for speed)."""
        # Only keep last N messages to avoid slowdown
        recent = self.chat_history[-max_messages:] if self.chat_history else []
        
        conversation = []
        for msg in recent:
            # Truncate very long messages to save tokens
            content = msg["content"]
            if len(content) > 500:
                content = content[:500] + "..."
            
            conversation.append({
                "role": msg["role"],
                "content": content
            })
        
        return conversation
        
        return conversation
    
    def add_message(self, role: str, content: str):
        """Add message to chat history."""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.chat_history.append(message)
        self._log(f"Added {role} message")
    
    def get_context(self, max_messages: int = 10) -> str:
        """Get recent chat context."""
        recent = self.chat_history[-max_messages:]
        context = []
        for msg in recent:
            context.append(f"{msg['role']}: {msg['content']}")
        return "\n".join(context)
    
    def save_session(self):
        """Save current session to log file."""
        log_file = os.path.join(self.logs_dir, f"session_{self.session_id}.txt")
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"Session: {self.session_id}\n")
                f.write(f"Started: {datetime.now().isoformat()}\n")
                f.write("=" * 50 + "\n\n")
                
                for msg in self.chat_history:
                    f.write(f"[{msg['timestamp']}] {msg['role'].upper()}\n")
                    f.write(f"{msg['content']}\n\n")
            
            self._log(f"Session saved to {log_file}")
        except Exception as e:
            self._log(f"Error saving session: {e}")
    
    def clear_history(self):
        """Clear chat history."""
        self.chat_history = []
        self._log("Chat history cleared")
