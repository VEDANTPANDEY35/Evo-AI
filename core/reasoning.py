"""
Planning and self-critique reasoning layer with hybrid intelligence.
"""
from typing import Dict, Any, Optional, List
from .input.input_normalizer import InputNormalizer
from .resolution.target_resolver import TargetResolver


class Reasoner:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.tool_registry = self._build_tool_registry()
        self._normalizer = InputNormalizer()
        self._resolver = TargetResolver(debug=debug)
    
    def _log(self, message: str):
        if self.debug:
            print(f"[REASONING] {message}")
    
    def _build_tool_registry(self) -> Dict[str, Dict[str, Any]]:
        """Build registry of available tools with descriptions."""
        return {
            "get_system_info": {
                "description": "Get hardware and system information (CPU, memory, disk)",
                "keywords": ["system", "hardware", "cpu", "memory", "disk", "specs"],
                "permission": "read_system_info",
                "complexity": "simple"
            },
            "list_directory": {
                "description": "List files and folders in a directory",
                "keywords": ["list", "show", "files", "folder", "directory"],
                "permission": "open_file",
                "complexity": "simple"
            },
            "search_files": {
                "description": "Search for files by name or pattern",
                "keywords": ["find", "locate", "file", "files"],
                "permission": "open_file",
                "complexity": "simple"
            },
            "read_file": {
                "description": "Read contents of a file",
                "keywords": ["read", "open", "show", "cat", "view"],
                "permission": "open_file",
                "complexity": "simple"
            },
            "write_file": {
                "description": "Write or create a file",
                "keywords": ["write", "create", "save"],
                "permission": "write_file",
                "complexity": "simple"
            },
            "delete_file": {
                "description": "Delete a file or folder",
                "keywords": ["delete", "remove", "rm"],
                "permission": "write_file",
                "complexity": "simple"
            },
            "open_application": {
                "description": "Launch an application",
                "keywords": ["open", "launch", "start", "run"],
                "permission": "open_app",
                "complexity": "simple"
            },
            "list_processes": {
                "description": "List running processes",
                "keywords": ["process", "running", "tasks"],
                "permission": "read_system_info",
                "complexity": "simple"
            },
            "kill_process": {
                "description": "Terminate a running process",
                "keywords": ["kill", "stop", "terminate", "close"],
                "permission": "run_code",
                "complexity": "simple"
            },
            "get_clipboard": {
                "description": "Get clipboard contents",
                "keywords": ["clipboard", "paste", "copied"],
                "permission": "read_system_info",
                "complexity": "simple"
            },
            "set_clipboard": {
                "description": "Set clipboard contents",
                "keywords": ["copy", "clipboard"],
                "permission": "write_file",
                "complexity": "simple"
            },
            "screenshot": {
                "description": "Take a screenshot",
                "keywords": ["screenshot", "capture", "screen"],
                "permission": "take_screenshot",
                "complexity": "simple"
            },
            "search_web": {
                "description": "Search the web",
                "keywords": ["google", "web", "online"],
                "permission": "internet_access",
                "complexity": "simple"
            },
            "open_website": {
                "description": "Open a specific website directly in browser",
                "keywords": ["open", "website", "site"],
                "permission": "open_browser",
                "complexity": "simple"
            }
        }
    
    def get_tool_descriptions(self) -> str:
        """Get formatted tool descriptions for LLM."""
        descriptions = []
        for tool_name, tool_info in self.tool_registry.items():
            descriptions.append(f"- {tool_name}: {tool_info['description']}")
        return "\n".join(descriptions)
    
    def analyze_request(self, user_input: str, use_llm: bool = False, llm_client=None) -> Dict[str, Any]:
        """Analyze user request using strict routing hierarchy."""
        # ── Input Normalization (pre-processing) ────────────────────────────
        # Normalize the full input string before any routing decisions.
        # This handles typos ("spotfy" → "spotify") and aliases ("browser" → "chrome")
        # in the target portion of open/launch/start commands.
        normalized_input, was_normalized = self._normalizer.normalize(user_input)
        if was_normalized:
            self._log(f"Input normalized: '{user_input}' → '{normalized_input}'")
        user_lower = normalized_input.lower()
        
        # ========== STRICT ROUTING HIERARCHY ==========
        # Priority 1: Explicit system commands (handled by CLI, but check here for completeness)
        # Priority 2: Process queries
        # Priority 3: System information queries  
        # Priority 4: Direct application/website opening
        # Priority 5: File operations
        # Priority 6: Conversational LLM fallback
        
        # PRIORITY 1: System query lock - NEVER let LLM answer these
        system_keywords = ["cpu", "ram", "memory", "disk", "storage", "process", "running", "hardware"]
        if any(keyword in user_lower for keyword in system_keywords):
            # Determine which system tool to use
            if any(word in user_lower for word in ["process", "running", "task"]):
                self._log("System lock: routing to list_processes")
                return {
                    "intent": "system_lock_processes",
                    "actions": ["list_processes"],
                    "requires_permission": ["read_system_info"],
                    "confidence": "high",
                    "use_llm": False
                }
            else:
                self._log("System lock: routing to get_system_info")
                return {
                    "intent": "system_lock_info",
                    "actions": ["get_system_info"],
                    "requires_permission": ["read_system_info"],
                    "confidence": "high",
                    "use_llm": False
                }
        
        # PRIORITY 2: Process queries (specific patterns)
        process_queries = [
            "what's running", "running processes", "active processes", 
            "what processes", "show processes", "process list",
            "running on my computer", "what's running on", "processes are active",
            "what processes are", "show me processes", "list processes"
        ]
        
        process_patterns = [
            ("what's", "running"), ("what", "processes"), ("show", "processes"),
            ("running", "computer"), ("active", "processes"), ("list", "processes")
        ]
        
        process_match = any(query in user_lower for query in process_queries)
        process_pattern_match = any(all(word in user_lower for word in pattern) for pattern in process_patterns)
        
        if process_match or process_pattern_match:
            self._log("Priority 2: Process query detected")
            return {
                "intent": "proactive_processes",
                "actions": ["list_processes"],
                "requires_permission": ["read_system_info"],
                "confidence": "high",
                "use_llm": False
            }
        
        # PRIORITY 3: System information queries
        system_queries = [
            "system settings", "system configuration", "my system", "computer specs",
            "hardware info", "what can you fetch", "system details", "my computer",
            "system information", "tell me about my system", "show me my system",
            "about my computer", "my system settings", "computer information",
            "what are my system", "show my system", "my computer info"
        ]
        
        system_patterns = [
            ("what are", "my system"), ("tell me about", "my computer"), 
            ("show me", "my system"), ("what can you", "fetch from my system"),
            ("what are", "system settings"), ("my", "computer", "specs")
        ]
        
        system_match = any(query in user_lower for query in system_queries)
        pattern_match = any(all(word in user_lower for word in pattern) for pattern in system_patterns)
        
        conversational_exclusions = ["what can i do", "what games", "recommend", "suggest"]
        is_conversational_question = any(exclusion in user_lower for exclusion in conversational_exclusions)
        
        if (system_match or pattern_match) and not any(proc_word in user_lower for proc_word in ["running", "processes", "active"]) and not is_conversational_question:
            self._log("Priority 3: System info query detected")
            return {
                "intent": "proactive_system_info",
                "actions": ["get_system_info"],
                "requires_permission": ["read_system_info"],
                "confidence": "high",
                "use_llm": False
            }
        
        # PRIORITY 4 & 5: Quick pattern matching (apps, websites, files, greetings)
        quick_analysis = self._quick_pattern_match(user_lower, normalized_input)
        if quick_analysis["confidence"] == "high":
            self._log(f"Priority 4/5: Quick match - {quick_analysis['intent']}")
            return quick_analysis
        
        # PRIORITY 6: Conversational LLM fallback (only if nothing else matched)
        if self._is_conversational(user_lower) and not self._is_system_related(user_lower):
            self._log("Priority 6: Conversational query - routing to LLM")
            return {
                "intent": "conversation",
                "requires_internet": False,
                "requires_permission": [],
                "actions": [],
                "params": {},
                "confidence": "high",
                "use_llm": True
            }
        
        # Enhanced pattern matching for edge cases
        return self._enhanced_pattern_match(user_lower, normalized_input)
    
    def _is_conversational(self, user_lower: str) -> bool:
        """Check if this is a pure conversational query."""
        # Greetings and simple messages
        greetings = [
            "hi", "hello", "hey", "greetings", "good morning", "good afternoon",
            "good evening", "howdy", "sup", "yo", "hiya", "thanks", "thank you",
            "bye", "goodbye", "see you", "later", "ok", "okay", "cool", "nice",
            "awesome", "great", "perfect"
        ]
        
        # Check if it's just a greeting (short message)
        if len(user_lower.split()) <= 3:
            if any(greeting == user_lower.strip() or user_lower.strip().startswith(greeting + " ") for greeting in greetings):
                return True
        
        # Strong conversational indicators
        conversational_patterns = [
            "explain", "what is", "how does", "how do",
            "why", "describe", "can you help", "help me understand",
            "i want to know", "i'm curious", "could you", "would you",
            "please explain", "what's the difference", "compare",
            "teach me", "show me how", "give me an example",
            "what games", "what can i", "what should i", "recommend",
            "suggest", "advice", "opinion", "think about"
        ]
        
        if any(pattern in user_lower for pattern in conversational_patterns):
            return True
        
        # Check for question words at start
        question_starters = ["what", "why", "how", "when", "where", "who", "which"]
        first_word = user_lower.split()[0] if user_lower.split() else ""
        if first_word in question_starters:
            # Make sure it's not a system command
            system_keywords = ["file", "folder", "process", "open", "create", "delete", "kill", "run"]
            if not any(keyword in user_lower for keyword in system_keywords):
                return True
        
        return False
    
    def _is_system_related(self, user_lower: str) -> bool:
        """Check if this query is system-related and should be handled proactively."""
        # Only consider it system-related if it's asking about actual system info
        system_info_patterns = [
            "my system", "system settings", "system configuration", "system information",
            "computer specs", "hardware info", "tell me about my system", 
            "show me my system", "about my computer", "my computer info"
        ]
        
        # Check for specific system info requests, not just any mention of "system"
        return any(pattern in user_lower for pattern in system_info_patterns)
    
    def _quick_pattern_match(self, user_lower: str, user_input: str) -> Dict[str, Any]:
        """Fast pattern matching for common commands."""
        analysis = {
            "intent": "unknown",
            "requires_internet": False,
            "requires_permission": [],
            "actions": [],
            "params": {},
            "confidence": "low",
            "use_llm": False
        }
        
        # Fast-path: Simple greetings (no LLM needed)
        simple_greetings = ["hi", "hello", "hey", "yo", "sup"]
        if user_lower.strip() in simple_greetings:
            analysis.update({
                "intent": "greeting",
                "confidence": "high",
                "use_llm": False
            })
            return analysis
        
        # Fast-path: Thank you (no LLM needed)
        if user_lower.strip() in ["thanks", "thank you", "thx"]:
            analysis.update({
                "intent": "thanks",
                "confidence": "high",
                "use_llm": False
            })
            return analysis
        
        # Self info (questions about Evo-AI itself)
        self_patterns = [
            "how much", "resource", "your resource", "you use", "you take", "you need",
            "about yourself", "about you", "your usage", "your memory"
        ]
        if any(pattern in user_lower for pattern in self_patterns):
            # Check if asking about Evo-AI specifically
            evo_ai_indicators = ["you", "yourself", "Evo-AI", "this", "assistant", "ai"]
            if any(indicator in user_lower for indicator in Evo-AI_indicators):
                analysis.update({
                    "intent": "self_info",
                    "actions": ["get_self_info"],
                    "requires_permission": ["read_system_info"],
                    "confidence": "high"
                })
                return analysis
        
        # List directory
        if user_lower.startswith(("ls", "dir", "list files")):
            analysis.update({
                "intent": "list_directory",
                "actions": ["list_directory"],
                "requires_permission": ["open_file"],
                "confidence": "high"
            })
            return analysis
        
        # SEARCH COLLISION REMOVED - Handle contextually in enhanced matching
        
        # OPEN commands - applications/websites
        # Uses the Resolution Pipeline: InputNormalizer → TargetResolver
        if user_lower.startswith(("open ", "launch ", "start ")):
            for trigger in ["open ", "launch ", "start "]:
                if user_lower.startswith(trigger):
                    raw_target = user_lower[len(trigger):].strip()
                    break

            # Check if it contains "and search" or "then search" (compound handled by planner)
            if "and search" in user_lower or "then search" in user_lower:
                if "and search" in user_lower:
                    query = user_lower.split("and search", 1)[1].strip()
                elif "then search" in user_lower:
                    query = user_lower.split("then search", 1)[1].strip()

                analysis.update({
                    "intent": "search_web",
                    "actions": ["search_web"],
                    "params": {"query": query},
                    "requires_permission": ["open_browser"],
                    "confidence": "high"
                })
            else:
                # ── Resolution Pipeline ──────────────────────────────────────
                # Step 1: Normalize target (typo correction + alias expansion)
                normalized_target, was_changed = self._normalizer.normalize_target(raw_target)
                if was_changed:
                    self._log(f"Normalized '{raw_target}' → '{normalized_target}'")

                # Step 2: Resolve — returns category + confidence, never guesses
                resolution = self._resolver.resolve(normalized_target)
                self._log(f"Resolution: category={resolution.category} confidence={resolution.confidence}")

                if resolution.category == "application":
                    # Use resolved_path (full path from Everything, or exe name from known-apps)
                    app_value = resolution.resolved_path or normalized_target
                    analysis.update({
                        "intent": "open_app",
                        "actions": ["open_application"],
                        "params": {"app_name": app_value},
                        "requires_permission": ["open_app"],
                        "confidence": "high",
                        "resolution": resolution.meta
                    })

                elif resolution.category == "web_search":
                    if resolution.confidence == "high":
                        # High-confidence web_search = known website (e.g. "youtube")
                        # Pass the resolved URL via resolved_path so open_website can use it
                        analysis.update({
                            "intent": "open_website",
                            "actions": ["open_website"],
                            "params": {
                                "site_name": normalized_target,
                                "url": resolution.resolved_path,
                            },
                            "requires_permission": ["open_browser"],
                            "confidence": "high",
                            "resolution": resolution.meta
                        })
                    else:
                        # Low-confidence web_search = app not found locally.
                        # Explicit fallback — NOT silent. Execution layer will
                        # show the user what happened before searching.
                        self._log(f"App not found locally — explicit web_search fallback: '{normalized_target}'")
                        analysis.update({
                            "intent": "search_web",
                            "actions": ["search_web"],
                            "params": {"query": normalized_target},
                            "requires_permission": ["open_browser"],
                            "confidence": "high",
                            "resolution": resolution.meta,
                            "fallback_info": self._resolver.make_fallback_info(normalized_target)
                        })

                else:
                    # Unknown — structured failure, not a raw exception
                    self._log(f"Resolution returned unknown for '{normalized_target}'")
                    analysis.update({
                        "intent": "unknown",
                        "actions": [],
                        "params": {},
                        "requires_permission": [],
                        "confidence": "low",
                        "fallback_info": self._resolver.make_fallback_info(normalized_target)
                    })
                # ── End Resolution Pipeline ──────────────────────────────────

            return analysis
        
        # Screenshot
        if "screenshot" in user_lower or "screen capture" in user_lower:
            analysis.update({
                "intent": "screenshot",
                "actions": ["take_screenshot"],
                "requires_permission": ["take_screenshot"],
                "confidence": "high"
            })
            return analysis
        
        return analysis
    
    def _enhanced_pattern_match(self, user_lower: str, original_input: str) -> Dict[str, Any]:
        """Enhanced pattern matching with scoring and contextual search routing."""
        
        # Check for conversational patterns first
        conversational_patterns = [
            "tell me", "explain", "what is", "how does", "why", "describe",
            "can you", "could you", "would you", "please", "help me understand"
        ]
        
        if any(pattern in user_lower for pattern in conversational_patterns):
            return {
                "intent": "conversation",
                "requires_internet": False,
                "requires_permission": [],
                "actions": [],
                "params": {},
                "confidence": "low",
                "use_llm": True
            }
        
        # Contextual search routing - file vs web
        if "search" in user_lower or "find" in user_lower:
            # File context indicators
            file_indicators = ["file", "files", ".py", ".txt", ".js", ".md", ".json", "folder", "directory"]
            has_file_context = any(indicator in user_lower for indicator in file_indicators)
            
            # Web context indicators
            web_indicators = ["google", "online", "web", "internet"]
            has_web_context = any(indicator in user_lower for indicator in web_indicators)
            
            if has_file_context and not has_web_context:
                # File search wins
                return {
                    "intent": "search_files",
                    "actions": ["search_files"],
                    "requires_permission": ["open_file"],
                    "params": self._extract_params(original_input, "search_files"),
                    "confidence": "high",
                    "use_llm": False
                }
            elif has_web_context or not has_file_context:
                # Web search (default if ambiguous)
                query = user_lower.replace("search", "").replace("find", "").replace("google", "").strip()
                return {
                    "intent": "search_web",
                    "actions": ["search_web"],
                    "requires_permission": ["open_browser"],
                    "params": {"query": query},
                    "confidence": "high",
                    "use_llm": False
                }
        
        scores = {}
        
        # Score each tool based on keyword matches
        for tool_name, tool_info in self.tool_registry.items():
            score = 0
            for keyword in tool_info["keywords"]:
                if keyword in user_lower:
                    score += 1
            if score > 0:
                scores[tool_name] = score
        
        if not scores:
            return {
                "intent": "conversation",
                "requires_internet": False,
                "requires_permission": [],
                "actions": [],
                "params": {},
                "confidence": "low",
                "use_llm": True
            }
        
        # Get best matching tool
        best_tool = max(scores, key=scores.get)
        tool_info = self.tool_registry[best_tool]
        
        # Lower LLM escalation threshold - trust tool if ANY match exists
        if scores[best_tool] == 0:
            return {
                "intent": "conversation",
                "requires_internet": False,
                "requires_permission": [],
                "actions": [],
                "params": {},
                "confidence": "low",
                "use_llm": True
            }
        
        return {
            "intent": best_tool,
            "actions": [best_tool],
            "requires_permission": [tool_info["permission"]],
            "params": self._extract_params(original_input, best_tool),
            "confidence": "medium",
            "use_llm": False
        }
    
    def _llm_analysis(self, user_input: str, llm_client) -> Dict[str, Any]:
        """Use LLM to analyze complex requests with OS awareness."""
        prompt = f"""Analyze this user request and determine what actions to take.

Available tools:
{self.get_tool_descriptions()}

User request: "{user_input}"

Respond in this format:
INTENT: <main intent>
ACTIONS: <comma-separated list of tool names>
PARAMS: <any parameters needed>
REASONING: <brief explanation>"""
        
        system_prompt = "You are analyzing requests for a Windows desktop assistant. You are running on Windows. Never suggest Linux or Unix shell commands. Only choose from the provided tools. If no tool applies, classify as conversation."
        
        response = llm_client.generate(prompt, system=system_prompt)
        
        # Parse LLM response
        return self._parse_llm_response(response, user_input)
    
    def _parse_llm_response(self, response: str, original_input: str) -> Dict[str, Any]:
        """Parse LLM analysis response."""
        if not response:
            return self._enhanced_pattern_match(original_input.lower(), original_input)
        
        lines = response.strip().split('\n')
        intent = "conversation"
        actions = []
        
        for line in lines:
            if line.startswith("INTENT:"):
                intent = line.split(":", 1)[1].strip()
            elif line.startswith("ACTIONS:"):
                actions_str = line.split(":", 1)[1].strip()
                actions = [a.strip() for a in actions_str.split(",") if a.strip()]
        
        # Determine permissions needed
        permissions = []
        for action in actions:
            if action in self.tool_registry:
                permissions.append(self.tool_registry[action]["permission"])
        
        return {
            "intent": intent,
            "actions": actions,
            "requires_permission": list(set(permissions)),
            "params": {},
            "confidence": "high",
            "use_llm": False
        }
    
    def _extract_params(self, user_input: str, tool_name: str) -> Dict[str, Any]:
        """Extract parameters from user input for a specific tool."""
        params = {}
        
        if tool_name == "open_application":
            # Extract app name after "open", "launch", "start"
            for trigger in ["open ", "launch ", "start "]:
                if trigger in user_input.lower():
                    app_name = user_input.lower().split(trigger, 1)[1].strip()
                    # Take only the first word (the actual app/site name)
                    params["app"] = app_name.split()[0] if app_name else ""
                    break
        
        elif tool_name == "open_website":
            # Extract website name after "open", "launch", "start"
            for trigger in ["open ", "launch ", "start "]:
                if trigger in user_input.lower():
                    url = user_input.lower().split(trigger, 1)[1].strip()
                    # Take only the first word (the actual website)
                    url = url.split()[0] if url else ""
                    params["url"] = url
                    break
        
        elif tool_name in ["read_file", "write_file", "delete_file"]:
            # Try to extract file path
            words = user_input.split()
            for word in words:
                if "/" in word or "\\" in word or "." in word:
                    params["path"] = word
                    break
        
        elif tool_name == "list_directory":
            # Extract directory path
            words = user_input.split()
            for word in words:
                if "/" in word or "\\" in word:
                    params["path"] = word
                    break
        
        return params
    
    def plan_execution(self, analysis: Dict[str, Any]) -> list:
        """Create execution plan based on analysis."""
        plan = []
        
        for action in analysis.get("actions", []):
            plan.append({
                "action": action,
                "status": "pending"
            })
        
        self._log(f"Execution plan: {len(plan)} steps")
        return plan
    
    def verify_result(self, result: Any, expected_type: str = "any") -> bool:
        """Verify execution result."""
        if result is None:
            self._log("Verification failed: None result")
            return False
        
        if expected_type == "string" and not isinstance(result, str):
            self._log(f"Verification failed: expected string, got {type(result)}")
            return False
        
        if expected_type == "dict" and not isinstance(result, dict):
            self._log(f"Verification failed: expected dict, got {type(result)}")
            return False
        
        self._log("Verification passed")
        return True
