"""
Adaptive learning layer for Tier-1 and Tier-2 pattern matching.
Learns from successful matches and improves over time.
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict


class LearningLayer:
    """Learns and adapts pattern matching from user interactions."""
    
    def __init__(self, patterns_file: str = "config/learned_patterns.json", debug: bool = False):
        self.patterns_file = patterns_file
        self.debug = debug
        self.patterns = self._load_patterns()
        self.session_matches = []  # Track matches in current session
    
    def _log(self, message: str):
        if self.debug:
            print(f"[LEARNING] {message}")
    
    def _load_patterns(self) -> Dict[str, Any]:
        """Load learned patterns from file."""
        try:
            if os.path.exists(self.patterns_file):
                with open(self.patterns_file, 'r') as f:
                    data = json.load(f)
                    self._log(f"Loaded {len(data.get('patterns', []))} learned patterns")
                    return data
        except Exception as e:
            self._log(f"Error loading patterns: {e}")
        
        return {
            "version": "1.0",
            "patterns": [],
            "tool_frequencies": {},
            "phrase_mappings": {}
        }
    
    def save_patterns(self):
        """Save learned patterns to file."""
        try:
            os.makedirs(os.path.dirname(self.patterns_file), exist_ok=True)
            with open(self.patterns_file, 'w') as f:
                json.dump(self.patterns, f, indent=2)
            self._log(f"Saved {len(self.patterns['patterns'])} patterns")
        except Exception as e:
            self._log(f"Error saving patterns: {e}")
    
    def record_successful_match(self, user_input: str, tool: str, 
                               params: Dict[str, Any], confidence: str):
        """
        Record a successful pattern match for learning.
        
        Args:
            user_input: Original user input
            tool: Tool that was matched
            params: Parameters extracted
            confidence: Confidence level of match
        """
        # Normalize input
        normalized_input = user_input.lower().strip()
        
        # Create pattern entry
        pattern_entry = {
            "input": normalized_input,
            "tool": tool,
            "params": params,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
            "success_count": 1
        }
        
        # Check if similar pattern exists
        existing_pattern = self._find_similar_pattern(normalized_input, tool)
        
        if existing_pattern:
            # Increment success count
            existing_pattern["success_count"] += 1
            existing_pattern["last_used"] = datetime.now().isoformat()
            self._log(f"Updated existing pattern: {tool} (count: {existing_pattern['success_count']})")
        else:
            # Add new pattern
            self.patterns["patterns"].append(pattern_entry)
            self._log(f"Learned new pattern: {normalized_input} -> {tool}")
        
        # Update tool frequency
        if tool not in self.patterns["tool_frequencies"]:
            self.patterns["tool_frequencies"][tool] = 0
        self.patterns["tool_frequencies"][tool] += 1
        
        # Update phrase mappings (for quick lookup)
        key_phrases = self._extract_key_phrases(normalized_input)
        for phrase in key_phrases:
            if phrase not in self.patterns["phrase_mappings"]:
                self.patterns["phrase_mappings"][phrase] = []
            
            if tool not in self.patterns["phrase_mappings"][phrase]:
                self.patterns["phrase_mappings"][phrase].append(tool)
        
        # Track in session
        self.session_matches.append(pattern_entry)
        
        # Auto-save periodically
        if len(self.session_matches) % 10 == 0:
            self.save_patterns()
    
    def _find_similar_pattern(self, input_text: str, tool: str) -> Optional[Dict[str, Any]]:
        """Find existing similar pattern."""
        for pattern in self.patterns["patterns"]:
            if pattern["tool"] == tool and self._similarity(pattern["input"], input_text) > 0.8:
                return pattern
        return None
    
    def _similarity(self, text1: str, text2: str) -> float:
        """Calculate simple similarity score between two texts."""
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from text for indexing."""
        # Simple extraction - can be enhanced with NLP
        words = text.split()
        phrases = []
        
        # Single words
        phrases.extend([w for w in words if len(w) > 3])
        
        # Bigrams
        for i in range(len(words) - 1):
            phrases.append(f"{words[i]} {words[i+1]}")
        
        return phrases[:10]  # Limit to top 10
    
    def suggest_tool(self, user_input: str) -> Optional[tuple[str, float]]:
        """
        Suggest a tool based on learned patterns.
        
        Returns:
            (tool_name, confidence_score) or None
        """
        normalized_input = user_input.lower().strip()
        
        # Check for exact or near-exact matches
        best_match = None
        best_score = 0.0
        
        for pattern in self.patterns["patterns"]:
            similarity = self._similarity(pattern["input"], normalized_input)
            
            # Weight by success count
            weighted_score = similarity * (1 + 0.1 * min(pattern["success_count"], 10))
            
            if weighted_score > best_score:
                best_score = weighted_score
                best_match = pattern["tool"]
        
        if best_score > 0.6:  # Threshold for suggestion
            self._log(f"Suggested tool: {best_match} (score: {best_score:.2f})")
            return best_match, best_score
        
        # Check phrase mappings
        key_phrases = self._extract_key_phrases(normalized_input)
        tool_votes = defaultdict(int)
        
        for phrase in key_phrases:
            if phrase in self.patterns["phrase_mappings"]:
                for tool in self.patterns["phrase_mappings"][phrase]:
                    tool_votes[tool] += 1
        
        if tool_votes:
            best_tool = max(tool_votes, key=tool_votes.get)
            confidence = tool_votes[best_tool] / len(key_phrases)
            
            if confidence > 0.3:
                self._log(f"Phrase-based suggestion: {best_tool} (confidence: {confidence:.2f})")
                return best_tool, confidence
        
        return None
    
    def get_popular_tools(self, limit: int = 10) -> List[tuple[str, int]]:
        """Get most frequently used tools."""
        sorted_tools = sorted(
            self.patterns["tool_frequencies"].items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_tools[:limit]
    
    def get_pattern_stats(self) -> Dict[str, Any]:
        """Get statistics about learned patterns."""
        return {
            "total_patterns": len(self.patterns["patterns"]),
            "total_tools": len(self.patterns["tool_frequencies"]),
            "total_phrases": len(self.patterns["phrase_mappings"]),
            "session_matches": len(self.session_matches),
            "popular_tools": self.get_popular_tools(5)
        }
    
    def prune_patterns(self, min_success_count: int = 2, max_age_days: int = 90):
        """
        Prune low-quality or old patterns.
        
        Args:
            min_success_count: Minimum success count to keep
            max_age_days: Maximum age in days
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        original_count = len(self.patterns["patterns"])
        
        # Filter patterns
        self.patterns["patterns"] = [
            p for p in self.patterns["patterns"]
            if p["success_count"] >= min_success_count or
               datetime.fromisoformat(p["timestamp"]) > cutoff_date
        ]
        
        pruned_count = original_count - len(self.patterns["patterns"])
        self._log(f"Pruned {pruned_count} patterns")
        
        # Rebuild phrase mappings
        self._rebuild_phrase_mappings()
        
        self.save_patterns()
    
    def _rebuild_phrase_mappings(self):
        """Rebuild phrase mappings from current patterns."""
        self.patterns["phrase_mappings"] = {}
        
        for pattern in self.patterns["patterns"]:
            key_phrases = self._extract_key_phrases(pattern["input"])
            for phrase in key_phrases:
                if phrase not in self.patterns["phrase_mappings"]:
                    self.patterns["phrase_mappings"][phrase] = []
                
                if pattern["tool"] not in self.patterns["phrase_mappings"][phrase]:
                    self.patterns["phrase_mappings"][phrase].append(pattern["tool"])
    
    def export_patterns(self, output_file: str):
        """Export patterns to human-readable format."""
        try:
            with open(output_file, 'w') as f:
                f.write("LEARNED PATTERNS\n")
                f.write("=" * 60 + "\n\n")
                
                # Group by tool
                by_tool = defaultdict(list)
                for pattern in self.patterns["patterns"]:
                    by_tool[pattern["tool"]].append(pattern)
                
                for tool, patterns in sorted(by_tool.items()):
                    f.write(f"\n{tool}:\n")
                    f.write("-" * 40 + "\n")
                    
                    for p in sorted(patterns, key=lambda x: x["success_count"], reverse=True):
                        f.write(f"  '{p['input']}' (used {p['success_count']} times)\n")
                
                f.write(f"\n\nTOOL FREQUENCIES:\n")
                f.write("=" * 60 + "\n")
                for tool, count in self.get_popular_tools():
                    f.write(f"  {tool}: {count}\n")
            
            self._log(f"Patterns exported to {output_file}")
            
        except Exception as e:
            self._log(f"Error exporting patterns: {e}")
    
    def clear_patterns(self):
        """Clear all learned patterns (use with caution)."""
        self.patterns = {
            "version": "1.0",
            "patterns": [],
            "tool_frequencies": {},
            "phrase_mappings": {}
        }
        self.session_matches = []
        self.save_patterns()
        self._log("All patterns cleared")
