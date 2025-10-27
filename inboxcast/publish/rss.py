"""RSS feed generation for podcast output."""
from datetime import datetime
from pathlib import Path
import json
from typing import List, Optional
from .episode_history import EpisodeHistoryManager, EpisodeEntry


class RSSGenerator:
    """Generate RSS feed for podcast."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def generate_feed(
        self,
        episode_filename: str = None,
        items: List = None,
        title: str = "InboxCast",
        description: str = "AI-generated newsletter summaries",
        episode_url: str = None,
        file_size: int = None,
        episodes: List[EpisodeEntry] = None
    ) -> str:
        """Generate RSS feed XML.

        Args:
            episode_filename: Legacy parameter for single episode
            items: Legacy parameter for single episode items
            episodes: List of EpisodeEntry objects for multi-episode feed
            Other params: Feed-level metadata
        """

        now = datetime.utcnow()
        pub_date = now.strftime("%a, %d %b %Y %H:%M:%S +0000")

        # Build episode items XML
        if episodes:
            # Multi-episode mode
            items_xml = "\\n".join(self._generate_episode_item_xml(ep) for ep in episodes)
        else:
            # Legacy single episode mode
            if not items:
                items_xml = ""  # No episodes
            else:
                # Calculate total duration (rough estimate)
                total_words = sum(getattr(item, 'word_count', 0) for item in items)
                duration_minutes = total_words / 165  # 165 WPM
                duration_seconds = int(duration_minutes * 60)
                duration_formatted = f"{duration_seconds // 60:02d}:{duration_seconds % 60:02d}"

                # Episode URL - use provided URL or construct from base_url
                if episode_url is None and episode_filename:
                    episode_url = f"{self.base_url}/{episode_filename}"

                items_xml = f'''        <item>
            <title>Episode {now.strftime("%Y-%m-%d")}</title>
            <description>
                Newsletter summary for {now.strftime("%B %d, %Y")}

                Items covered:
                {self._format_item_list(items)}
            </description>
            <pubDate>{pub_date}</pubDate>
            <guid>{episode_url or ''}</guid>
            <enclosure url="{episode_url or ''}" type="audio/mpeg" length="{file_size or 0}"/>
            <itunes:duration>{duration_formatted}</itunes:duration>
            <itunes:summary>AI-generated summaries from tech newsletters</itunes:summary>
        </item>'''

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

{items_xml}
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

    def _generate_episode_item_xml(self, episode: EpisodeEntry) -> str:
        """Generate XML for a single episode item."""
        # Escape XML special characters in description
        description = episode.description.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        return f'''        <item>
            <title>{episode.title}</title>
            <description>{description}</description>
            <pubDate>{episode.pub_date}</pubDate>
            <guid>{episode.guid}</guid>
            <enclosure url="{episode.episode_url}" type="audio/mpeg" length="{episode.file_size}"/>
            <itunes:duration>{episode.duration}</itunes:duration>
            <itunes:summary>AI-generated summaries from tech newsletters</itunes:summary>
        </item>'''
    
    def generate_episode_metadata(self, items: List) -> dict:
        """Generate episode metadata JSON."""
        
        chapters = []
        current_time_ms = 0
        
        for item in items:
            chapters.append({
                "start_ms": current_time_ms,
                "title": getattr(item, 'title', 'Untitled'),
                "key_topics": getattr(item, 'notes', {}).get('key_topics', [])
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
    
    def write_files(self, output_dir: str, episode_filename: str = None, items: List = None,
                   episode_url: str = None, file_size: int = None, use_history: bool = True):
        """Write RSS feed and metadata files.

        Args:
            use_history: If True, generate multi-episode feed from history
        """

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if use_history:
            # Multi-episode mode: load from history
            history_manager = EpisodeHistoryManager(output_dir)
            episodes = history_manager.get_episodes()

            rss_content = self.generate_feed(episodes=episodes)
        else:
            # Legacy single episode mode
            rss_content = self.generate_feed(
                episode_filename, items,
                episode_url=episode_url,
                file_size=file_size
            )

        rss_path = output_path / "feed.xml"
        with open(rss_path, 'w', encoding='utf-8') as f:
            f.write(rss_content)

        # Generate and write metadata for current episode (if provided)
        if items:
            metadata = self.generate_episode_metadata(items)
            if episode_url:
                metadata["episode_url"] = episode_url
            if file_size:
                metadata["file_size_bytes"] = file_size

            metadata_path = output_path / "episode.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)

        print(f"Generated RSS feed: {rss_path}")
        if items:
            print(f"Generated metadata: {output_path / 'episode.json'}")

    def add_episode_to_history(self, output_dir: str, episode_filename: str, items: List,
                             episode_url: str, file_size: int, episode_date: str = None) -> EpisodeEntry:
        """Add a new episode to the history and return the EpisodeEntry."""

        if episode_date is None:
            episode_date = datetime.utcnow().strftime("%Y-%m-%d")

        # Calculate duration
        total_words = sum(getattr(item, 'word_count', 0) for item in items)
        duration_minutes = total_words / 165
        duration_seconds = int(duration_minutes * 60)
        duration_formatted = f"{duration_seconds // 60:02d}:{duration_seconds % 60:02d}"

        # Generate episode description
        description = f"Newsletter summary for {datetime.strptime(episode_date, '%Y-%m-%d').strftime('%B %d, %Y')}\\n\\nItems covered:\\n{self._format_item_list(items)}"

        # Create episode entry
        episode_entry = EpisodeEntry(
            date=episode_date,
            title=f"Episode {episode_date}",
            description=description,
            pub_date=datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000"),
            guid=episode_url,
            episode_url=episode_url,
            file_size=file_size,
            duration=duration_formatted,
            metadata_file=str(Path(output_dir) / f"episode-{episode_date}.json"),
            episode_file=str(Path(output_dir) / episode_filename),
            timestamp=datetime.utcnow().isoformat()
        )

        # Add to history
        history_manager = EpisodeHistoryManager(output_dir)
        history_manager.add_episode(episode_entry)

        return episode_entry