"""Simple deduplication by URL for Step 1."""
from typing import List, Set
from urllib.parse import urlparse, parse_qs
from ..types import RawItem


class SimpleDeduplicator:
    """Dummy deduplication by URL normalization."""
    
    def __init__(self):
        self.seen_urls: Set[str] = set()
    
    def deduplicate(self, items: List[RawItem]) -> List[RawItem]:
        """Remove duplicates by normalized URL."""
        unique_items = []
        
        for item in items:
            normalized_url = self._normalize_url(item.url)
            
            if normalized_url not in self.seen_urls:
                self.seen_urls.add(normalized_url)
                unique_items.append(item)
            else:
                print(f"Skipping duplicate: {item.title}")
        
        print(f"Dedupe: {len(items)} → {len(unique_items)} items")
        return unique_items
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL by removing query params and fragments."""
        try:
            parsed = urlparse(url)
            # Remove query params and fragment
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            return normalized.lower().rstrip('/')
        except:
            return url.lower()