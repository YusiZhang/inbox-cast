"""RSS feed generation for podcast output."""
from datetime import datetime
from pathlib import Path
import json
from typing import List


class RSSGenerator:
    """Generate RSS feed for podcast."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def generate_feed(
        self, 
        episode_filename: str,
        items: List,
        title: str = "InboxCast",
        description: str = "AI-generated newsletter summaries"
    ) -> str:
        """Generate RSS feed XML."""
        
        now = datetime.utcnow()
        pub_date = now.strftime("%a, %d %b %Y %H:%M:%S +0000")
        
        # Calculate total duration (rough estimate)
        total_words = sum(getattr(item, 'word_count', 0) for item in items)
        duration_minutes = total_words / 165  # 165 WPM
        duration_seconds = int(duration_minutes * 60)
        duration_formatted = f"{duration_seconds // 60:02d}:{duration_seconds % 60:02d}"
        
        # Episode URL
        episode_url = f"{self.base_url}/{episode_filename}"
        
        rss_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
    <channel>
        <title>{title}</title>
        <description>{description}</description>
        <link>{self.base_url}</link>
        <language>en-us</language>
        <pubDate>{pub_date}</pubDate>
        <lastBuildDate>{pub_date}</lastBuildDate>
        <generator>InboxCast</generator>
        
        <itunes:author>InboxCast</itunes:author>
        <itunes:summary>{description}</itunes:summary>
        <itunes:category text="Technology"/>
        <itunes:explicit>false</itunes:explicit>
        
        <item>
            <title>Episode {now.strftime("%Y-%m-%d")}</title>
            <description>
                Newsletter summary for {now.strftime("%B %d, %Y")}
                
                Items covered:
                {self._format_item_list(items)}
            </description>
            <pubDate>{pub_date}</pubDate>
            <guid>{episode_url}</guid>
            <enclosure url="{episode_url}" type="audio/mpeg" length="0"/>
            <itunes:duration>{duration_formatted}</itunes:duration>
            <itunes:summary>AI-generated summaries from tech newsletters</itunes:summary>
        </item>
    </channel>
</rss>'''
        
        return rss_xml
    
    def _format_item_list(self, items: List) -> str:
        """Format items for RSS description."""
        formatted_items = []
        for i, item in enumerate(items, 1):
            title = getattr(item, 'title', 'Untitled')
            formatted_items.append(f"{i}. {title}")
        
        return "\\n".join(formatted_items)
    
    def generate_episode_metadata(self, items: List, episode_path: str) -> dict:
        """Generate episode metadata JSON."""
        
        chapters = []
        current_time_ms = 0
        
        for item in items:
            chapters.append({
                "start_ms": current_time_ms,
                "title": getattr(item, 'title', 'Untitled')
            })
            
            # Estimate duration for this item (rough)
            word_count = getattr(item, 'word_count', 0)
            duration_ms = int((word_count / 165) * 60 * 1000)  # 165 WPM to ms
            current_time_ms += duration_ms + 200  # Add gap
        
        metadata = {
            "episode_date": datetime.utcnow().isoformat(),
            "total_items": len(items),
            "estimated_duration_ms": current_time_ms,
            "chapters": chapters,
            "sources": list(set(
                source 
                for item in items 
                for source in getattr(item, 'sources', [])
            ))
        }
        
        return metadata
    
    def write_files(self, output_dir: str, episode_filename: str, items: List):
        """Write RSS feed and metadata files."""
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate and write RSS feed
        rss_content = self.generate_feed(episode_filename, items)
        rss_path = output_path / "feed.xml"
        with open(rss_path, 'w', encoding='utf-8') as f:
            f.write(rss_content)
        
        # Generate and write metadata
        metadata = self.generate_episode_metadata(items, episode_filename)
        metadata_path = output_path / "episode.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"Generated RSS feed: {rss_path}")
        print(f"Generated metadata: {metadata_path}")