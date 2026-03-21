"""
Strict action parser for tool-calling format.
Supports two formats:
1. ACTION block: [ACTION: tool=name args={"key":"value"}]
2. JSON object: {"tool":"name", "args":{"key":"value"}}
"""
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ParsedAction:
    """Parsed action from LLM output."""
    tool: str
    args: Dict[str, Any]
    raw_text: str
    format_type: str  # "action_block" or "json"


class ActionParser:
    """Parser for extracting tool calls from LLM output."""
    
    # Grammar patterns
    ACTION_BLOCK_PATTERN = r'\[ACTION:\s*tool=(\w+)\s+args=(\{[^}]+\})\s*\]'
    JSON_CODE_BLOCK_PATTERN = r'```json\s*(\{[^`]+\})\s*```'
    JSON_INLINE_PATTERN = r'\{[\s\n]*"tool"[\s\n]*:[\s\n]*"(\w+)"[^}]+\}'
    
    def __init__(self, debug: bool = False):
        self.debug = debug
    
    def _log(self, message: str):
        if self.debug:
            print(f"[ACTION_PARSER] {message}")
    
    def parse(self, text: str) -> List[ParsedAction]:
        """
        Parse LLM output and extract all valid actions.
        Returns list of ParsedAction objects.
        """
        actions = []
        
        # Try ACTION block format first
        actions.extend(self._parse_action_blocks(text))
        
        # Try JSON format
        actions.extend(self._parse_json_actions(text))
        
        self._log(f"Parsed {len(actions)} actions from text")
        return actions
    
    def _parse_action_blocks(self, text: str) -> List[ParsedAction]:
        """Parse ACTION block format: [ACTION: tool=name args={...}]"""
        actions = []
        
        matches = re.finditer(self.ACTION_BLOCK_PATTERN, text, re.IGNORECASE)
        for match in matches:
            try:
                tool_name = match.group(1)
                args_str = match.group(2)
                
                # Parse args JSON
                args = json.loads(args_str)
                
                action = ParsedAction(
                    tool=tool_name,
                    args=args,
                    raw_text=match.group(0),
                    format_type="action_block"
                )
                actions.append(action)
                self._log(f"Parsed ACTION block: {tool_name}")
                
            except json.JSONDecodeError as e:
                self._log(f"Invalid JSON in ACTION block: {e}")
            except Exception as e:
                self._log(f"Error parsing ACTION block: {e}")
        
        return actions
    
    def _parse_json_actions(self, text: str) -> List[ParsedAction]:
        """Parse JSON format: {"tool":"name", "args":{...}}"""
        actions = []
        
        # Try code block format first
        code_blocks = re.finditer(self.JSON_CODE_BLOCK_PATTERN, text, re.DOTALL)
        for match in code_blocks:
            try:
                json_str = match.group(1)
                data = json.loads(json_str)
                
                if self._is_valid_action_json(data):
                    action = ParsedAction(
                        tool=data["tool"],
                        args=data.get("args", {}),
                        raw_text=match.group(0),
                        format_type="json"
                    )
                    actions.append(action)
                    self._log(f"Parsed JSON action: {data['tool']}")
                    
            except json.JSONDecodeError as e:
                self._log(f"Invalid JSON in code block: {e}")
            except Exception as e:
                self._log(f"Error parsing JSON code block: {e}")
        
        # Try inline JSON format
        if not actions:
            inline_matches = re.finditer(self.JSON_INLINE_PATTERN, text, re.DOTALL)
            for match in inline_matches:
                try:
                    json_str = match.group(0)
                    data = json.loads(json_str)
                    
                    if self._is_valid_action_json(data):
                        action = ParsedAction(
                            tool=data["tool"],
                            args=data.get("args", {}),
                            raw_text=json_str,
                            format_type="json"
                        )
                        actions.append(action)
                        self._log(f"Parsed inline JSON action: {data['tool']}")
                        
                except json.JSONDecodeError as e:
                    self._log(f"Invalid inline JSON: {e}")
                except Exception as e:
                    self._log(f"Error parsing inline JSON: {e}")
        
        return actions
    
    def _is_valid_action_json(self, data: Any) -> bool:
        """Validate that JSON object is a valid action."""
        if not isinstance(data, dict):
            return False
        
        if "tool" not in data:
            return False
        
        if not isinstance(data["tool"], str):
            return False
        
        if "args" in data and not isinstance(data["args"], dict):
            return False
        
        return True
    
    def parse_llm_response(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse LLM response and return actions in executor-compatible format.
        Returns list of dicts with 'action' and 'params' keys.
        """
        parsed_actions = self.parse(text)
        
        # Convert to executor format
        executor_actions = []
        for action in parsed_actions:
            executor_actions.append({
                "action": action.tool,
                "params": action.args
            })
        
        return executor_actions
    
    def extract_human_response(self, text: str, actions: List[ParsedAction]) -> str:
        """
        Extract human-readable response by removing action blocks.
        """
        clean_text = text
        
        # Remove all action blocks
        for action in actions:
            clean_text = clean_text.replace(action.raw_text, "")
        
        # Clean up extra whitespace
        clean_text = re.sub(r'\n\s*\n\s*\n', '\n\n', clean_text)
        clean_text = clean_text.strip()
        
        return clean_text
    
    def validate_action_format(self, text: str) -> Tuple[bool, str]:
        """
        Validate that text contains properly formatted actions.
        Returns (is_valid, error_message)
        """
        # Check for malformed ACTION blocks
        malformed_actions = re.findall(r'\[ACTION[^\]]*(?:\]|$)', text, re.IGNORECASE)
        for ma in malformed_actions:
            if not re.match(self.ACTION_BLOCK_PATTERN, ma, re.IGNORECASE):
                return False, f"Malformed ACTION block: {ma}"
        
        # Check for JSON objects that look like actions but are invalid
        potential_jsons = re.findall(r'\{[^}]*"tool"[^}]*\}', text, re.DOTALL)
        for pj in potential_jsons:
            try:
                data = json.loads(pj)
                if not self._is_valid_action_json(data):
                    return False, f"Invalid action JSON structure: {pj}"
            except json.JSONDecodeError:
                return False, f"Malformed JSON: {pj}"
        
        return True, ""


def create_action_example(tool: str, args: Dict[str, Any], format: str = "action_block") -> str:
    """
    Create example action in specified format.
    Useful for few-shot prompting.
    """
    if format == "action_block":
        args_json = json.dumps(args)
        return f"[ACTION: tool={tool} args={args_json}]"
    
    elif format == "json":
        action_obj = {"tool": tool, "args": args}
        return f"```json\n{json.dumps(action_obj, indent=2)}\n```"
    
    else:
        raise ValueError(f"Unknown format: {format}")


# Example usage and tests
if __name__ == "__main__":
    parser = ActionParser(debug=True)
    
    # Test ACTION block format
    text1 = """
    I'll help you create that file.
    [ACTION: tool=create_file args={"path":"test.py","content":"print('hello')"}]
    The file has been created successfully.
    """
    
    actions1 = parser.parse(text1)
    print(f"Test 1: Found {len(actions1)} actions")
    
    # Test JSON format
    text2 = """
    Let me search for that.
    ```json
    {
      "tool": "search_files",
      "args": {
        "pattern": "*.py",
        "directory": "~/Documents"
      }
    }
    ```
    """
    
    actions2 = parser.parse(text2)
    print(f"Test 2: Found {len(actions2)} actions")
    
    # Test extraction
    human_text = parser.extract_human_response(text1, actions1)
    print(f"Human response: {human_text}")
