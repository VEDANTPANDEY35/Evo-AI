"""
Evo-AI CLI - Main entry point with rich terminal UI
"""

import sys
import os
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.brain import Brain
from core.llm_client import LLMClient
from core.memory import Memory
from core.reasoning import Reasoner
from core.executor import Executor

# Rich terminal imports
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.spinner import Spinner
from rich.live import Live

# Initialize rich console
console = Console()


class EvoAI:
    def __init__(self, debug: bool = False):
        self.debug = debug
        
        # Initialize core components
        self.llm = LLMClient(debug=debug)
        self.memory = Memory(debug=debug)
        self.reasoner = Reasoner(debug=debug)
        self.executor = Executor(debug=debug)
        
        # Initialize brain (pure logic layer)
        self.brain = Brain(
            reasoner=self.reasoner,
            executor=self.executor,
            llm_client=self.llm,
            memory=self.memory,
            debug=debug
        )
        
        self.running = True
        self.local_available = self.brain.local_available
    
    def print_welcome(self):
        """Print welcome message with rich formatting."""
        console.clear()
        
        # Welcome panel
        welcome_text = Text()
        welcome_text.append("🧩 Evo-AI\n", style="bold cyan")
        welcome_text.append("Your AI Desktop Assistant\n\n", style="dim")
        
        # Status
        if self.local_available:
            welcome_text.append("✅ ", style="green")
            welcome_text.append(f"Connected to {self.llm.ollama_model}\n", style="green")
        else:
            welcome_text.append("⚠️  ", style="yellow")
            welcome_text.append("Ollama not running\n", style="yellow")
            welcome_text.append("   Start it: ", style="dim")
            welcome_text.append("ollama serve\n", style="cyan")
        
        welcome_text.append("\nType ", style="dim")
        welcome_text.append("help", style="bold")
        welcome_text.append(" for commands, ", style="dim")
        welcome_text.append("exit", style="bold")
        welcome_text.append(" to quit", style="dim")
        
        console.print(Panel(welcome_text, border_style="cyan", padding=(1, 2)))
    
    def handle_command(self, user_input: str) -> bool:
        """Handle special commands. Returns True if command was handled."""
        cmd = user_input.lower().strip()
        
        if cmd in ['exit', 'quit', 'bye']:
            print("\n👋 Goodbye!")
            self.memory.save_session()
            self.running = False
            return True
        
        if cmd == 'help':
            console.print("\n[bold cyan]Commands:[/bold cyan]")
            console.print("  help          - Show this help")
            console.print("  clear         - Clear chat history")
            console.print("  save          - Save current session")
            console.print("  status        - Show system status")
            console.print("  exit / quit   - Exit Evo-AI")
            
            console.print("\n[bold cyan]Quick Commands:[/bold cyan]")
            console.print("  system info         - Show hardware specs")
            console.print("  open notepad        - Launch application")
            console.print("  list files          - List current directory")
            console.print("  running processes   - Show active processes")
            
            console.print("\n[bold cyan]Natural Language:[/bold cyan]")
            console.print('  "tell me about python"')
            console.print('  "explain how neural networks work"')
            console.print('  "find all python files in Documents"')
            console.print('  "what processes are using the most memory?"')
            console.print()
            return True
        
        if cmd == 'clear':
            self.memory.clear_history()
            print("✓ Chat history cleared")
            return True
        
        if cmd == 'save':
            self.memory.save_session()
            print("✓ Session saved")
            return True
        
        if cmd == 'status':
            print(f"\nLocal LLM: {'✓ Available' if self.local_available else '✗ Not available'}")
            print(f"Online API: {'✓ Configured' if self.llm.online_api_key else '✗ Not configured'}")
            print(f"Session ID: {self.memory.session_id}")
            print(f"Messages: {len(self.memory.chat_history)}")
            return True
        
        if cmd == 'history':
            if not self.executor.execution_history:
                print("\nNo execution history yet")
            else:
                print("\nRecent Executions:")
                for i, exec_record in enumerate(self.executor.execution_history[-10:], 1):
                    status = "✓" if exec_record["success"] else "✗"
                    print(f"{i}. {status} {exec_record['action']} - {exec_record['result'][:50]}")
            return True
        
        return False
    
    def process_request(self, user_input: str):
        """Process user request with execution gating and user confirmation."""
        # STEP 1: Generate plan (no execution)
        thinking_spinner = Spinner("dots", text="[dim]Analyzing request...[/dim]")
        
        with Live(thinking_spinner, console=console, refresh_per_second=10):
            plan = self.brain.generate_plan(user_input)
        
        # STEP 2: Display plan preview for non-conversational requests
        if not plan.is_conversational and plan.steps:
            console.print("\n[bold yellow]📋 Execution Plan:[/bold yellow]")
            console.print(f"  Steps: {len(plan.steps)}")
            console.print(f"  Risk Level: {plan.risk_level.upper()}")
            console.print(f"  Confidence: {plan.confidence:.0%}")
            
            if plan.permissions_required:
                console.print(f"  Permissions: {', '.join(plan.permissions_required)}")
            
            console.print("\n[bold yellow]Steps to execute:[/bold yellow]")
            for i, step in enumerate(plan.steps, 1):
                actions = step.get("actions", [])
                console.print(f"  {i}. {', '.join(actions)}")
            
            # STEP 3: Ask for confirmation
            console.print()
            confirmation = console.input("[bold yellow]Execute this plan? (y/n):[/bold yellow] ").strip().lower()
            
            if confirmation not in ['y', 'yes']:
                console.print("\n[dim]⚠️  Execution cancelled by user.[/dim]\n")
                return
        
        # STEP 4: Execute plan
        executing_spinner = Spinner("dots", text="[dim]Executing...[/dim]")
        
        with Live(executing_spinner, console=console, refresh_per_second=10):
            result = self.brain.execute_plan(plan)
        
        # STEP 5: Display result
        console.print("\n[bold cyan]Assistant:[/bold cyan]\n")
        
        if result.success:
            self._stream_display(result.message)
        else:
            console.print(f"[bold red]{result.message}[/bold red]")
        
        console.print("\n")
    
    def _stream_display(self, text: str):
        """Display text with streaming effect (ChatGPT-style)."""
        import time
        
        for char in text:
            console.print(char, end='', style="white")
            time.sleep(0.01)  # 10ms delay per character
    
    def run(self):
        """Main interaction loop with rich UI."""
        self.print_welcome()
        
        while self.running:
            try:
                # Simple input with rich formatting
                console.print()
                user_input = console.input("[bold green]You:[/bold green] ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if self.handle_command(user_input):
                    continue
                
                # Process request
                self.process_request(user_input)
                
            except KeyboardInterrupt:
                console.print("\n\n[bold cyan]👋 Goodbye![/bold cyan]")
                self.memory.save_session()
                break
            except EOFError:
                console.print("\n\n[bold cyan]👋 Goodbye![/bold cyan]")
                self.memory.save_session()
                break
            except Exception as e:
                console.print(f"\n[bold red]⚠️  Error:[/bold red] {e}\n")
                if self.debug:
                    import traceback
                    traceback.print_exc()


def main():
    print("Evo-AI Version 9 🚀", flush=true)
    parser = argparse.ArgumentParser(description="Evo-AI - Your local AI companion")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()
    
    evo_ai = EvoAI(debug=args.debug)
    evo_ai.run()


if __name__ == "__main__":
    main()

def run_ai(user_input: str):
    """
    API-safe wrapper for EvoAI.
    No interactive input, no confirmation, always returns response.
    """
    try:
        if not user_input:
            return "No input provided"

        evo_ai = EvoAI(debug=False)

        # Generate plan
        plan = evo_ai.brain.generate_plan(user_input)

        # 🚨 IMPORTANT: Skip confirmation (API cannot handle input())
        # Direct execution
        result = evo_ai.brain.execute_plan(plan)

        # Return safe response
        if hasattr(result, "success") and result.success:
    base_response = result.message if hasattr(result, "message") else str(result)
    return f"🔥 Version 9 CLI Response:\n{base_response}"
else:
    return result.message if hasattr(result, "message") else "Execution failed"

    except Exception as e:
        return f"Error: {str(e)}"
