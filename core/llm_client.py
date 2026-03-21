"""
Unified LLM client for local and optional online models.
"""
import os
import json
import requests
from typing import Optional, Dict, Any, Generator
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    def __init__(self, debug: bool = False):
        self.debug = debug
        self.mode = "offline"
        
        # Local settings
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2:latest")
        
        # Online settings
        self.online_api_key = os.getenv("ONLINE_API_KEY", "")
        self.online_base_url = os.getenv("ONLINE_BASE_URL", "")
        self.online_model = os.getenv("ONLINE_MODEL", "")
        
        # Response cache for identical queries
        self._response_cache = {}
        
    def _log(self, message: str):
        if self.debug:
            print(f"[LLM_CLIENT] {message}")
    
    def check_local_available(self) -> bool:
        """Check if local LLM is available."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=3)
            if response.status_code == 200:
                # Check if the specific model exists
                data = response.json()
                models = data.get("models", [])
                model_names = [m.get("name", "") for m in models]
                
                # Check if our model is in the list
                has_model = any(self.ollama_model in name for name in model_names)
                
                if has_model:
                    self._log(f"Local LLM available: {self.ollama_model}")
                    return True
                else:
                    self._log(f"Model {self.ollama_model} not found. Available: {model_names}")
                    return False
            else:
                self._log(f"Ollama responded with status: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            self._log(f"Cannot connect to Ollama at {self.ollama_url}. Is 'ollama serve' running?")
            return False
        except requests.exceptions.Timeout:
            self._log(f"Connection to Ollama timed out. Is 'ollama serve' running?")
            return False
        except Exception as e:
            self._log(f"Error checking Ollama: {e}")
            return False
    
    def generate_local(self, prompt: str, system: str = "", stream: bool = False) -> Optional[str]:
        """Generate response using local Ollama with advanced parameters."""
        try:
            # Check cache for non-streaming requests
            if not stream:
                cache_key = f"{system}:{prompt}"
                if cache_key in self._response_cache:
                    self._log("Cache hit - returning cached response")
                    return self._response_cache[cache_key]
            
            self._log(f"Sending to local model: {self.ollama_model}")
            
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": stream,
                # Optimized parameters for fast, accurate responses
                "options": {
                    "temperature": 0.7,      # Balanced creativity (0.0-1.0)
                    "top_p": 0.9,           # Focused vocabulary
                    "top_k": 40,            # Quality word choices
                    "repeat_penalty": 1.1,  # Prevent repetition
                    "num_predict": 1500,    # Max tokens (reduced for speed)
                    "stop": ["\n\n\n", "User:", "Assistant:"],  # Stop tokens
                }
            }
            
            if system:
                payload["system"] = system
            
            if not stream:
                # Non-streaming mode (original behavior)
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    response_text = result.get("response", "")
                    
                    # Cache the response
                    cache_key = f"{system}:{prompt}"
                    self._response_cache[cache_key] = response_text
                    
                    # Limit cache size
                    if len(self._response_cache) > 50:
                        # Remove oldest entry
                        self._response_cache.pop(next(iter(self._response_cache)))
                    
                    return response_text
                else:
                    self._log(f"Local generation failed: {response.status_code}")
                    return None
            else:
                # Streaming mode - return generator
                return self._stream_local(payload)
                
        except Exception as e:
            self._log(f"Local generation error: {e}")
            return None
    
    def _stream_local(self, payload: dict):
        """Stream response from local Ollama."""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                stream=True,
                timeout=120
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                text = chunk["response"]
                                if text:  # Only yield non-empty chunks
                                    yield text
                            if chunk.get("done", False):
                                break
                        except json.JSONDecodeError as e:
                            self._log(f"JSON decode error: {e}")
                            continue
            else:
                self._log(f"Streaming failed: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            self._log("Connection error during streaming - Ollama may have stopped")
        except Exception as e:
            self._log(f"Streaming error: {e}")
    
    def generate_online(self, prompt: str, system: str = "", stream: bool = False) -> Optional[str]:
        """Generate response using online API."""
        if not self.online_api_key or not self.online_base_url:
            self._log("Online API not configured")
            return None
        
        try:
            self._log(f"Sending to online model: {self.online_model}")
            
            headers = {
                "Authorization": f"Bearer {self.online_api_key}",
                "Content-Type": "application/json"
            }
            
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": self.online_model,
                "messages": messages,
                "stream": stream
            }
            
            if not stream:
                # Non-streaming mode
                response = requests.post(
                    f"{self.online_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    self._log(f"Online generation failed: {response.status_code}")
                    return None
            else:
                # Streaming mode
                return self._stream_online(headers, payload)
                
        except Exception as e:
            self._log(f"Online generation error: {e}")
            return None
    
    def _stream_online(self, headers: dict, payload: dict):
        """Stream response from online API."""
        try:
            response = requests.post(
                f"{self.online_base_url}/chat/completions",
                headers=headers,
                json=payload,
                stream=True,
                timeout=120
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            if data_str.strip() == '[DONE]':
                                break
                            try:
                                chunk = json.loads(data_str)
                                if chunk.get("choices") and len(chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        yield delta["content"]
                            except json.JSONDecodeError:
                                continue
            else:
                self._log(f"Online streaming failed: {response.status_code}")
                yield None
                
        except Exception as e:
            self._log(f"Online streaming error: {e}")
            yield None
    
    def generate(self, prompt: str, system: str = "", force_online: bool = False, stream: bool = False):
        """
        Generate response. Tries local first, falls back to online with permission.
        Returns string for non-streaming, generator for streaming.
        """
        if force_online:
            return self.generate_online(prompt, system, stream=stream)
        
        # Try local first
        if self.check_local_available():
            response = self.generate_local(prompt, system, stream=stream)
            if response:
                return response
        
        # Local failed, offer online
        self._log("Local generation failed or unavailable")
        return None
    
    def generate_local_with_history(self, user_message: str, system: str, 
                                    conversation: list, stream: bool = True):
        """Generate response with conversation history (optimized for chat)."""
        try:
            self._log(f"Generating with history: {len(conversation)} messages")
            
            # Build prompt with conversation context
            prompt_parts = []
            
            # Add recent conversation for context
            if conversation:
                prompt_parts.append("Previous conversation:")
                for msg in conversation[-4:]:  # Last 4 messages for context
                    role = msg["role"].capitalize()
                    content = msg["content"][:200]  # Truncate long messages
                    prompt_parts.append(f"{role}: {content}")
                prompt_parts.append("")
            
            # Add current message
            prompt_parts.append(f"User: {user_message}")
            prompt_parts.append("Assistant:")
            
            full_prompt = "\n".join(prompt_parts)
            
            return self.generate_local(full_prompt, system, stream=stream)
            
        except Exception as e:
            self._log(f"Error generating with history: {e}")
            return None
    
    def generate_online_with_history(self, user_message: str, system: str,
                                     conversation: list, stream: bool = True):
        """Generate response with conversation history for online API."""
        try:
            self._log(f"Generating online with history: {len(conversation)} messages")
            
            headers = {
                "Authorization": f"Bearer {self.online_api_key}",
                "Content-Type": "application/json"
            }
            
            # Build messages array
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            
            # Add conversation history
            messages.extend(conversation[-6:])  # Last 6 messages
            
            # Add current message
            messages.append({"role": "user", "content": user_message})
            
            payload = {
                "model": self.online_model,
                "messages": messages,
                "stream": stream
            }
            
            if not stream:
                response = requests.post(
                    f"{self.online_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    return None
            else:
                return self._stream_online(headers, payload)
                
        except Exception as e:
            self._log(f"Error generating online with history: {e}")
            return None
