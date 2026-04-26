"""
System utilities for local operations - Enhanced toolkit.
"""
import os
import platform
import subprocess
import psutil
import glob
import shutil
from typing import Dict, Any, Optional, List


class SystemTools:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.platform = platform.system()
        self._init_adapter()
        self._register_all_tools()
    
    def _init_adapter(self):
        """Initialize OS-specific adapter."""
        from .os_adapter import WindowsAdapter, MacOSAdapter, LinuxAdapter
        
        if self.platform == "Windows":
            self.adapter = WindowsAdapter(debug=self.debug)
        elif self.platform == "Darwin":
            self.adapter = MacOSAdapter(debug=self.debug)
        else:
            self.adapter = LinuxAdapter(debug=self.debug)
    
    def _log(self, message: str):
        if self.debug:
            print(f"[TOOLS] {message}")
    
    def _register_all_tools(self):
        """Register all tools in the global registry."""
        from .tool_registry import get_registry, ToolMetadata, ToolParameter, RiskLevel
        
        registry = get_registry(debug=self.debug)
        
        # System info tool
        registry.register_tool(ToolMetadata(
            name="get_system_info",
            description="Get hardware and system information (CPU, memory, disk)",
            function=self.get_system_info,
            parameters=[],
            risk_level=RiskLevel.SAFE,
            permissions_required=["read_system_info"],
            os_support=["windows", "linux", "darwin"],
            category="system"
        ))
        
        # File operations
        registry.register_tool(ToolMetadata(
            name="list_directory",
            description="List files and folders in a directory",
            function=self.list_directory,
            parameters=[
                ToolParameter(name="path", type="path", required=False, default=".")
            ],
            risk_level=RiskLevel.SAFE,
            permissions_required=["open_file"],
            os_support=["windows", "linux", "darwin"],
            category="file"
        ))
        
        registry.register_tool(ToolMetadata(
            name="read_file",
            description="Read contents of a file",
            function=self.read_file,
            parameters=[
                ToolParameter(name="path", type="path", required=True)
            ],
            risk_level=RiskLevel.SAFE,
            permissions_required=["open_file"],
            os_support=["windows", "linux", "darwin"],
            category="file"
        ))
        
        registry.register_tool(ToolMetadata(
            name="write_file",
            description="Write content to a file",
            function=self.write_file,
            parameters=[
                ToolParameter(name="path", type="path", required=True),
                ToolParameter(name="content", type="string", required=True)
            ],
            risk_level=RiskLevel.MEDIUM,
            permissions_required=["write_file"],
            os_support=["windows", "linux", "darwin"],
            category="file"
        ))
        
        registry.register_tool(ToolMetadata(
            name="create_file",
            description="Create a new file with content",
            function=self.create_file,
            parameters=[
                ToolParameter(name="path", type="path", required=True),
                ToolParameter(name="content", type="string", required=True)
            ],
            risk_level=RiskLevel.MEDIUM,
            permissions_required=["write_file"],
            os_support=["windows", "linux", "darwin"],
            category="file"
        ))
        
        registry.register_tool(ToolMetadata(
            name="search_files",
            description="Search for files matching a pattern",
            function=self.search_files,
            parameters=[
                ToolParameter(name="pattern", type="string", required=True),
                ToolParameter(name="directory", type="path", required=False, default=".")
            ],
            risk_level=RiskLevel.SAFE,
            permissions_required=["open_file"],
            os_support=["windows", "linux", "darwin"],
            category="file"
        ))
        
        # Process management
        registry.register_tool(ToolMetadata(
            name="list_processes",
            description="List running processes",
            function=self.list_processes,
            parameters=[],
            risk_level=RiskLevel.SAFE,
            permissions_required=["read_system_info"],
            os_support=["windows", "linux", "darwin"],
            category="process"
        ))
        
        registry.register_tool(ToolMetadata(
            name="kill_process",
            description="Terminate a running process",
            function=self.kill_process,
            parameters=[
                ToolParameter(name="pid", type="integer", required=False),
                ToolParameter(name="name", type="string", required=False)
            ],
            risk_level=RiskLevel.HIGH,
            permissions_required=["run_command"],
            os_support=["windows", "linux", "darwin"],
            category="process"
        ))
        
        # Application control
        registry.register_tool(ToolMetadata(
            name="open_application",
            description="Launch an application",
            function=self.open_application,
            parameters=[
                ToolParameter(name="app_name", type="string", required=True)
            ],
            risk_level=RiskLevel.LOW,
            permissions_required=["open_app"],
            os_support=["windows", "linux", "darwin"],
            category="app"
        ))
        
        # Network info
        registry.register_tool(ToolMetadata(
            name="get_network_info",
            description="Get network information",
            function=self.get_network_info,
            parameters=[],
            risk_level=RiskLevel.SAFE,
            permissions_required=["read_system_info"],
            os_support=["windows", "linux", "darwin"],
            category="system"
        ))
        
        registry.register_tool(ToolMetadata(
            name="search_web",
            description="Search for something on the web (opens browser and searches)",
            function=self.search_web,
            parameters=[
                ToolParameter(name="query", type="string", required=True),
                ToolParameter(name="engine", type="string", required=False, default="google")
            ],
            risk_level=RiskLevel.SAFE,
            permissions_required=["open_browser"],
            os_support=["windows", "linux", "darwin"],
            category="browser"
        ))
        
        # Open specific websites
        registry.register_tool(ToolMetadata(
            name="open_website",
            description="Open a specific website directly in the browser",
            function=self.open_website,
            parameters=[
                ToolParameter(name="site_name", type="string", required=True),
                ToolParameter(name="url", type="string", required=False, default=None)
            ],
            risk_level=RiskLevel.SAFE,
            permissions_required=["open_browser"],
            os_support=["windows", "linux", "darwin"],
            category="browser"
        ))
        
        # Self-awareness
        registry.register_tool(ToolMetadata(
            name="get_self_info",
            description="Get information about Evo-AI's own resource usage and status",
            function=self.get_self_info,
            parameters=[],
            risk_level=RiskLevel.SAFE,
            permissions_required=["read_system_info"],
            os_support=["windows", "linux", "darwin"],
            category="system"
        ))
        
        # Clipboard operations
        registry.register_tool(ToolMetadata(
            name="get_clipboard",
            description="Get clipboard contents",
            function=self.get_clipboard,
            parameters=[],
            risk_level=RiskLevel.SAFE,
            permissions_required=["read_system_info"],
            os_support=["windows", "linux", "darwin"],
            category="system"
        ))
        
        registry.register_tool(ToolMetadata(
            name="set_clipboard",
            description="Set clipboard contents",
            function=self.set_clipboard,
            parameters=[
                ToolParameter(name="text", type="string", required=True)
            ],
            risk_level=RiskLevel.SAFE,
            permissions_required=["write_file"],
            os_support=["windows", "linux", "darwin"],
            category="system"
        ))
        
        # Screenshot
        registry.register_tool(ToolMetadata(
            name="take_screenshot",
            description="Take a screenshot",
            function=self.take_screenshot,
            parameters=[
                ToolParameter(name="filename", type="string", required=False, default=None)
            ],
            risk_level=RiskLevel.SAFE,
            permissions_required=["take_screenshot"],
            os_support=["windows", "linux", "darwin"],
            category="system"
        ))
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information."""
        try:
            info = self.adapter.get_system_info()
            
            # Add disk info for all partitions
            if "error" not in info:
                info["disk_usage"] = {}
                for partition in psutil.disk_partitions():
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        info["disk_usage"][partition.mountpoint] = {
                            "total_gb": round(usage.total / (1024**3), 2),
                            "used_gb": round(usage.used / (1024**3), 2),
                            "free_gb": round(usage.free / (1024**3), 2),
                            "percent": usage.percent
                        }
                    except:
                        pass
            
            self._log("System info retrieved")
            return info
            
        except Exception as e:
            self._log(f"Error getting system info: {e}")
            return {"error": str(e)}
    
    def get_self_info(self) -> Dict[str, Any]:
        """Get information about Evo-AI's own resource usage."""
        try:
            import os
            
            info = {
                "name": "Evo-AI",
                "version": "1.0.0",
                "status": "running",
                "processes": {}
            }
            
            # Find Evo-AI process (current)
            current_pid = os.getpid()
            current_proc = psutil.Process(current_pid)
            info["processes"]["Evo-AI"] = {
                "pid": current_pid,
                "memory_mb": round(current_proc.memory_info().rss / (1024**2), 1),
                "cpu_percent": current_proc.cpu_percent(interval=0.1)
            }
            
            # Find Ollama processes
            ollama_procs = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                try:
                    if 'ollama' in proc.info['name'].lower():
                        ollama_procs.append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "memory_mb": round(proc.info['memory_info'].rss / (1024**2), 1),
                            "cpu_percent": proc.info['cpu_percent']
                        })
                except:
                    pass
            
            if ollama_procs:
                info["processes"]["ollama"] = ollama_procs
                total_ollama_mem = sum(p["memory_mb"] for p in ollama_procs)
                info["total_memory_mb"] = round(info["processes"]["Evo-AI"]["memory_mb"] + total_ollama_mem, 1)
            else:
                info["processes"]["ollama"] = "not running"
                info["total_memory_mb"] = info["processes"]["Evo-AI"]["memory_mb"]
            
            # Disk usage
            Evo_AI_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            Evo_AI_size = 0
            for root, dirs, files in os.walk(Evo-AI_dir):
                if 'venv' in root or '__pycache__' in root or '.git' in root:
                    continue
                for file in files:
                    try:
                        Evo_AI_size += os.path.getsize(os.path.join(root, file))
                    except:
                        pass
            info["disk_usage_mb"] = round(Evo-AI_size / (1024**2), 2)
            
            # Model info
            ollama_dir = os.path.expanduser("~/.ollama/models")
            if os.path.exists(ollama_dir):
                model_size = 0
                for root, dirs, files in os.walk(ollama_dir):
                    for file in files:
                        try:
                            model_size += os.path.getsize(os.path.join(root, file))
                        except:
                            pass
                info["model_disk_usage_gb"] = round(model_size / (1024**3), 2)
            
            self._log("Self info retrieved")
            return info
            
        except Exception as e:
            self._log(f"Error getting self info: {e}")
            return {"error": str(e)}
    
    def format_self_info(self, info: Dict[str, Any]) -> str:
        """Format self info for display."""
        if "error" in info:
            return f"Error: {info['error']}"
        
        output = []
        output.append(f"🤖 {info['name']} v{info['version']}")
        output.append(f"Status: {info['status']}")
        output.append("")
        
        output.append("💾 Memory Usage:")
        output.append(f"  Evo-AI: {info['processes']['Evo-AI']['memory_mb']} MB")
        
        if isinstance(info['processes']['ollama'], list):
            for proc in info['processes']['ollama']:
                output.append(f"  Ollama ({proc['name']}): {proc['memory_mb']} MB")
            output.append(f"  Total: {info['total_memory_mb']} MB")
        else:
            output.append(f"  Ollama: Not running")
        
        output.append("")
        output.append("💿 Disk Usage:")
        output.append(f"  Evo-AI code: {info['disk_usage_mb']} MB")
        if "model_disk_usage_gb" in info:
            output.append(f"  AI models: {info['model_disk_usage_gb']} GB")
        
        output.append("")
        output.append("📊 Performance:")
        output.append(f"  Lightweight: Evo-AI uses minimal resources")
        output.append(f"  Efficient: Only active when generating responses")
        output.append(f"  Scalable: Adapts to your hardware")
        
        return "\n".join(output)
    
    def format_system_info(self, info: Dict[str, Any]) -> str:
        """Format system info for display."""
        if "error" in info:
            return f"Error: {info['error']}"
        
        output = []
        output.append(f"OS: {info.get('os')} {info.get('os_version', info.get('os_release', ''))}")
        output.append(f"Architecture: {info.get('architecture')}")
        output.append(f"Processor: {info.get('processor')}")
        
        # Handle both old and new field names
        cpu_count = info.get('cpu_count') or info.get('cpu_cores') or info.get('cpu_threads')
        if cpu_count:
            output.append(f"CPU Cores: {cpu_count}")
        
        # CPU usage might not always be available
        if 'cpu_percent' in info:
            output.append(f"CPU Usage: {info['cpu_percent']}%")
        
        # Memory info
        mem_avail = info.get('memory_available_gb')
        mem_total = info.get('memory_total_gb')
        mem_percent = info.get('memory_percent') or info.get('memory_used_percent')
        
        if mem_avail and mem_total:
            output.append(f"Memory: {mem_avail}GB / {mem_total}GB available ({mem_percent}% used)")
        
        if info.get("disk_usage"):
            output.append("\nDisk Usage:")
            for mount, usage in info["disk_usage"].items():
                output.append(f"  {mount}: {usage['free_gb']}GB / {usage['total_gb']}GB free ({usage['percent']}% used)")
        
        return "\n".join(output)
    
    def open_application(self, app_name: str) -> str:
        """Open an application using the resolution pipeline.

        Uses resolved_path from the resolver when available (full path from
        Everything CLI, or exe name from known-apps list).
        Does NOT silently fall back to web search — that decision belongs
        to the execution layer after user confirmation.
        """
        try:
            self._log(f"Opening application: {app_name}")

            from .resolution.target_resolver import TargetResolver
            resolution = TargetResolver(debug=self.debug).resolve(app_name.lower().strip())

            if resolution.category == "web_search" and resolution.confidence == "high":
                # Resolver says this is a known website (e.g. "teams", "outlook")
                return self.open_website(app_name, url=resolution.resolved_path)

            if resolution.category != "application":
                # Not found locally — return a clear failure message.
                # The execution layer (brain/executor) decides whether to search.
                return f"✗ Application '{app_name}' not found on this system"

            resolved = resolution.resolved_path or app_name

            # Special handling for browsers — use BrowserAutomation path lookup
            browser_names = {"brave", "chrome", "firefox", "edge"}
            base_name = resolved.lower().removesuffix(".exe")
            if base_name in browser_names:
                from .browser_automation import BrowserAutomation
                browser_auto = BrowserAutomation(debug=self.debug)
                browser_path = None
                for path in browser_auto.BROWSER_PATHS.get(self.platform, []):
                    if base_name in path.lower() and os.path.exists(path):
                        browser_path = path
                        break
                if browser_path:
                    subprocess.Popen([browser_path])
                    return f"✓ Opened {app_name.title()}"
                return f"✗ {app_name.title()} not found on your system"

            # Full absolute path from Everything CLI — launch directly
            if os.path.isabs(resolved) and os.path.isfile(resolved):
                subprocess.Popen([resolved])
                return f"✓ Opened {app_name}"

            # Executable name — let the OS adapter resolve via PATH/registry
            success = self.adapter.open_application(resolved)
            return f"✓ Opened {app_name}" if success else f"✗ Could not open {app_name}"

        except Exception as e:
            self._log(f"Error opening application: {e}")
            return f"✗ Error opening {app_name}: {e}"
    
    def read_file(self, file_path: str) -> Optional[str]:
        """Read a local file."""
        try:
            self._log(f"Reading file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self._log(f"Error reading file: {e}")
            return None
    
    def write_file(self, file_path: str, content: str) -> bool:
        """Write to a local file."""
        try:
            self._log(f"Writing file: {file_path}")
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            self._log(f"Error writing file: {e}")
            return False
    
    def create_file(self, path: str, content: str) -> str:
        """Create a new file with content."""
        try:
            self._log(f"Creating file: {path}")
            # Ensure directory exists
            dir_path = os.path.dirname(path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            # Create file with content
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"✓ Created file: {path}"
        except Exception as e:
            self._log(f"Error creating file: {e}")
            return f"✗ Error creating file: {e}"
    
    def list_directory(self, dir_path: str = ".") -> Optional[list]:
        """List directory contents."""
        try:
            self._log(f"Listing directory: {dir_path}")
            return os.listdir(dir_path)
        except Exception as e:
            self._log(f"Error listing directory: {e}")
            return None

    
    def search_files(self, pattern: str, directory: str = ".", recursive: bool = True) -> List[str]:
        """Search for files matching a pattern."""
        try:
            self._log(f"Searching for: {pattern} in {directory}")
            
            if recursive:
                search_pattern = os.path.join(directory, "**", pattern)
                results = glob.glob(search_pattern, recursive=True)
            else:
                search_pattern = os.path.join(directory, pattern)
                results = glob.glob(search_pattern)
            
            return results[:100]  # Limit to 100 results
            
        except Exception as e:
            self._log(f"Error searching files: {e}")
            return []
    
    def delete_file(self, path: str) -> bool:
        """Delete a file or directory."""
        try:
            self._log(f"Deleting: {path}")
            
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
            else:
                return False
            
            return True
            
        except Exception as e:
            self._log(f"Error deleting: {e}")
            return False
    
    def copy_file(self, src: str, dst: str) -> bool:
        """Copy a file or directory."""
        try:
            self._log(f"Copying {src} to {dst}")
            
            if os.path.isfile(src):
                shutil.copy2(src, dst)
            elif os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                return False
            
            return True
            
        except Exception as e:
            self._log(f"Error copying: {e}")
            return False
    
    def move_file(self, src: str, dst: str) -> bool:
        """Move a file or directory."""
        try:
            self._log(f"Moving {src} to {dst}")
            shutil.move(src, dst)
            return True
            
        except Exception as e:
            self._log(f"Error moving: {e}")
            return False
    
    def list_processes(self) -> List[Dict[str, Any]]:
        """List all running processes."""
        try:
            self._log("Listing processes")
            processes = self.adapter.list_processes()
            return sorted(processes, key=lambda x: x.get('memory', 0), reverse=True)[:50]
        except Exception as e:
            self._log(f"Error listing processes: {e}")
            return []
    
    def format_processes(self, processes: List[Dict[str, Any]]) -> str:
        """Format process list for display."""
        if not processes:
            return "No processes found"
        
        output = ["PID\tNAME\t\t\tCPU%\tMEM%"]
        output.append("-" * 60)
        
        for proc in processes[:20]:  # Show top 20
            name = proc['name'][:20].ljust(20)
            output.append(f"{proc['pid']}\t{name}\t{proc['cpu']:.1f}\t{proc['memory']:.1f}")
        
        return "\n".join(output)
    
    def kill_process(self, pid: int = None, name: str = None) -> bool:
        """Kill a process by PID or name."""
        try:
            self._log(f"Killing process PID: {pid}" if pid else f"Killing process: {name}")
            return self.adapter.kill_process(pid=pid, name=name)
        except Exception as e:
            self._log(f"Error killing process: {e}")
            return False
    
    def get_clipboard(self) -> Optional[str]:
        """Get clipboard contents."""
        try:
            return self.adapter.get_clipboard()
        except Exception as e:
            self._log(f"Error getting clipboard: {e}")
            return None
    
    def set_clipboard(self, text: str) -> bool:
        """Set clipboard contents."""
        try:
            return self.adapter.set_clipboard(text)
        except Exception as e:
            self._log(f"Error setting clipboard: {e}")
            return False
    
    def take_screenshot(self, filename: str = None) -> Optional[str]:
        """Take a screenshot."""
        try:
            return self.adapter.take_screenshot(filename)
        except Exception as e:
            self._log(f"Error taking screenshot: {e}")
            return None
    
    def get_network_info(self) -> Dict[str, Any]:
        """Get network information."""
        try:
            info = {
                "interfaces": {},
                "connections": len(psutil.net_connections())
            }
            
            for interface, addrs in psutil.net_if_addrs().items():
                info["interfaces"][interface] = []
                for addr in addrs:
                    info["interfaces"][interface].append({
                        "family": str(addr.family),
                        "address": addr.address
                    })
            
            return info
            
        except Exception as e:
            self._log(f"Error getting network info: {e}")
            return {"error": str(e)}
    
    def format_network_info(self, info: Dict[str, Any]) -> str:
        """Format network info for display."""
        if "error" in info:
            return f"Error: {info['error']}"
        
        output = [f"Active connections: {info['connections']}\n"]
        output.append("Network Interfaces:")
        
        for interface, addrs in info["interfaces"].items():
            output.append(f"\n{interface}:")
            for addr in addrs:
                output.append(f"  {addr['address']}")
        
        return "\n".join(output)
    
    def run_command(self, command: str, shell: bool = True) -> Dict[str, Any]:
        """Run a shell command and return output."""
        try:
            self._log(f"Running command: {command}")
            
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            self._log(f"Error running command: {e}")
            return {"success": False, "error": str(e)}
    

    def search_web(self, query: str, engine: str = "google") -> str:
        """Search for something on the web."""
        try:
            from .browser_automation import BrowserAutomation
            browser = BrowserAutomation(debug=self.debug)
            
            success, message = browser.search(query, engine)
            if success:
                return f"✓ Searching for '{query}' on {engine}"
            else:
                return f"✗ Error: {message}"
        except Exception as e:
            self._log(f"Error searching web: {e}")
            return f"✗ Error searching web: {e}"
    
    def open_website(self, site_name: str, url: str = None) -> str:
        """Open a specific website in the browser.

        If a pre-resolved URL is provided (from the resolver), use it directly.
        Otherwise, ask the resolver. Never guesses URLs.
        """
        try:
            from .browser_automation import BrowserAutomation
            browser = BrowserAutomation(debug=self.debug)

            # Use pre-resolved URL if the caller already has it
            if url and url.startswith("http"):
                success, message = browser.open_url(url)
                if success:
                    return f"✓ Opened {site_name} ({url})"
                return f"✗ Error opening {site_name}: {message}"

            # Otherwise ask the resolver
            from .resolution.target_resolver import TargetResolver
            resolution = TargetResolver(debug=self.debug).resolve(site_name.lower().strip())

            if resolution.category == "web_search" and resolution.resolved_path:
                # Known website — resolved_path holds the canonical URL
                success, message = browser.open_url(resolution.resolved_path)
                if success:
                    return f"✓ Opened {site_name} ({resolution.resolved_path})"
                return f"✗ Error opening {site_name}: {message}"

            # Not a known website — search for it instead of guessing
            self._log(f"Unknown site '{site_name}' — falling back to web search")
            return self.search_web(site_name)

        except Exception as e:
            self._log(f"Error opening website: {e}")
            return f"✗ Error opening website: {e}"
