"""Basic summarization engine for Step 1."""
import re
from html import unescape
from ..types import RawItem, ProcessedItem, Summarizer


class SimpleSummarizer(Summarizer):
    """Basic summarizer using content truncation."""
    
    def __init__(self, max_words: int = 100):
        self.max_words = max_words
    
    def summarize(self, item: RawItem) -> ProcessedItem:
        """Create summary by cleaning and truncating content."""
        
        # Clean HTML and extract text
        cleaned_content = self._clean_html(item.content)
        
        # Create basic script by truncating
        script = self._truncate_to_words(cleaned_content, self.max_words)
        
        # Basic word count
        word_count = len(script.split())
        
        # Basic notes
        notes = {
            "paywalled": self._detect_paywall(item.content),
            "has_numbers": bool(re.search(r'\d+', script)),
            "source": item.source_name
        }
        
        return ProcessedItem(
            title=item.title,
            script=script,
            sources=[item.url],
            notes=notes,
            word_count=word_count
        )
    
    def _clean_html(self, html_content: str) -> str:
        """Basic HTML cleaning."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)
        
        # Decode HTML entities
        text = unescape(text)
        
        # Clean whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _truncate_to_words(self, text: str, max_words: int) -> str:
        """Truncate text to maximum word count."""
        words = text.split()
        if len(words) <= max_words:
            return text
        
        truncated = ' '.join(words[:max_words])
        return truncated + "..."
    
    def _detect_paywall(self, content: str) -> bool:
        """Basic paywall detection."""
        paywall_indicators = [
            "subscribe",
            "subscription",
            "premium",
            "sign in",
            "subscriber-only",
            "behind paywall"
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in paywall_indicators)