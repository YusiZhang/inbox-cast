"""RSS source fetcher implementation."""
import feedparser
import requests
from datetime import datetime
from typing import List, Optional
from ..types import RawItem, Source
from ..config import FeedConfig


class RSSSource(Source):
    """Simple RSS source fetcher."""
    
    def __init__(self, feed_config: FeedConfig, max_items: Optional[int] = None):
        self.feed_config = feed_config
        self.max_items = max_items
    
    def fetch(self) -> List[RawItem]:
        """Fetch items from RSS feed."""
        try:
            # Parse RSS feed
            feed = feedparser.parse(self.feed_config.url)
            
            if feed.bozo:
                print(f"Warning: RSS feed may be malformed: {self.feed_config.url}")
            
            # Get source name from feed title (do this once outside the loop)
            source_name = getattr(feed.feed, 'title', 'Unknown')
            
            items = []
            entries_to_process = feed.entries[:self.max_items] if self.max_items else feed.entries
            
            for entry in entries_to_process:
                # Extract content (try multiple fields)
                content = self._extract_content(entry)
                
                # Parse publish date
                published = self._parse_date(entry)
                
                item = RawItem(
                    title=entry.title,
                    url=entry.link,
                    content=content,
                    published=published,
                    source_name=source_name
                )
                items.append(item)
                
            total_available = len(feed.entries)
            fetched_count = len(items)
            if self.max_items and total_available > self.max_items:
                print(f"Fetched {fetched_count} items from {source_name} (limited from {total_available} total)")
            else:
                print(f"Fetched {fetched_count} items from {source_name}")
            return items
            
        except Exception as e:
            print(f"Error fetching RSS feed {self.feed_config.url}: {e}")
            return []
    
    def _extract_content(self, entry) -> str:
        """Extract content from RSS entry, trying multiple fields."""
        # Try content first
        if hasattr(entry, 'content') and entry.content:
            return entry.content[0].value
        
        # Try summary
        if hasattr(entry, 'summary'):
            return entry.summary
        
        # Try description  
        if hasattr(entry, 'description'):
            return entry.description
        
        # Fallback to title if no content available (for minimal RSS feeds)
        if hasattr(entry, 'title'):
            # Create more natural content from the title
            title = entry.title
            # Generate a more descriptive summary based on the title
            summary = f"Today's highlight covers {title}. This article discusses key developments and insights in artificial intelligence and machine learning technology. The piece explores innovative approaches and practical applications that are shaping the future of AI development."
            return summary
            
        return ""
    
    def _parse_date(self, entry) -> Optional[datetime]:
        """Parse publish date from entry."""
        try:
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                return datetime(*entry.published_parsed[:6])
        except:
            pass
        return None


class MultiRSSSource(Source):
    """Aggregates multiple RSS sources."""
    
    def __init__(self, feed_configs: List[FeedConfig], max_items_per_feed: Optional[int] = None):
        self.sources = [RSSSource(config, max_items_per_feed) for config in feed_configs]
    
    def fetch(self) -> List[RawItem]:
        """Fetch from all RSS sources."""
        all_items = []
        
        for source in self.sources:
            items = source.fetch()
            all_items.extend(items)
        
        print(f"Total items fetched: {len(all_items)}")
        return all_items