"""Utility to parse episode script files."""
import re
from pathlib import Path
from typing import List, Optional
from ..types import PlannedItem


class ScriptParser:
    """Parser for episode_script.txt files."""
    
    def parse_script_file(self, script_path: str) -> List[PlannedItem]:
        """
        Parse episode script file and return PlannedItem objects.
        
        Expected format:
        InboxCast Episode Script - YYYY-MM-DD
        ============================================================
        
        1. Title: Item Title Here
           Words: 50
           Script: The actual script content here...
        
        2. Title: Another Item Title
           Words: 75
           Script: More script content...
        
        Args:
            script_path: Path to episode_script.txt file
            
        Returns:
            List of PlannedItem objects
        """
        path = Path(script_path)
        if not path.exists():
            raise FileNotFoundError(f"Script file not found: {script_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.parse_script_content(content)
    
    def parse_script_content(self, content: str) -> List[PlannedItem]:
        """Parse script content string into PlannedItem objects."""
        items = []
        
        # Split content by item numbers (1., 2., etc.)
        # Use regex to find item boundaries
        item_pattern = r'(\d+)\.\s*Title:\s*(.+?)\n\s*Words:\s*(\d+)\n\s*Script:\s*(.+?)(?=\n\d+\.\s*Title:|\Z)'
        
        matches = re.findall(item_pattern, content, re.DOTALL)
        
        for match in matches:
            item_num, title, words_str, script = match
            
            # Clean up title and script
            title = title.strip()
            script = script.strip()
            word_count = int(words_str.strip())
            
            # Create PlannedItem
            # Note: We don't have sources/notes from script, so use defaults
            planned_item = PlannedItem(
                title=title,
                script=script,
                sources=[],  # Not stored in script format
                notes={},    # Not stored in script format
                word_count=word_count,
                allocated_words=word_count  # Assume word_count == allocated_words
            )
            
            items.append(planned_item)
        
        return items
    
    def find_script_file(self, output_dir: str, script_filename: str = "episode_script.txt") -> Optional[str]:
        """
        Find script file in output directory.
        
        Args:
            output_dir: Output directory path
            script_filename: Script filename (default: episode_script.txt)
            
        Returns:
            Full path to script file if found, None otherwise
        """
        script_path = Path(output_dir) / script_filename
        
        if script_path.exists():
            return str(script_path)
        
        return None