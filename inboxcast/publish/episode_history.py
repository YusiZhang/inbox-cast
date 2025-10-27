"""Episode history management for multi-episode RSS feeds."""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class EpisodeEntry:
    """Represents a single episode in the history."""
    date: str  # YYYY-MM-DD format
    title: str
    description: str
    pub_date: str  # RFC 2822 format
    guid: str
    episode_url: str
    file_size: int
    duration: str  # MM:SS format
    metadata_file: str
    episode_file: str
    timestamp: str  # ISO format

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'date': self.date,
            'title': self.title,
            'description': self.description,
            'pub_date': self.pub_date,
            'guid': self.guid,
            'episode_url': self.episode_url,
            'file_size': self.file_size,
            'duration': self.duration,
            'metadata_file': self.metadata_file,
            'episode_file': self.episode_file,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EpisodeEntry':
        """Create from dictionary loaded from JSON."""
        return cls(**data)


class EpisodeHistoryManager:
    """Manages episode history with configurable limits."""

    def __init__(self, output_dir: str, max_episodes: int = 5):
        self.output_dir = Path(output_dir)
        self.max_episodes = max_episodes
        self.history_file = self.output_dir / "episodes_history.json"
        self._episodes: List[EpisodeEntry] = []
        self._load_history()

    def _load_history(self):
        """Load existing episode history from disk."""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._episodes = [
                        EpisodeEntry.from_dict(entry)
                        for entry in data.get('episodes', [])
                    ]
                    # Sort by timestamp (newest first)
                    self._episodes.sort(key=lambda x: x.timestamp, reverse=True)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"Warning: Could not load episode history: {e}")
                self._episodes = []

    def _save_history(self):
        """Save episode history to disk."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        data = {
            'max_episodes': self.max_episodes,
            'last_updated': datetime.utcnow().isoformat(),
            'episodes': [ep.to_dict() for ep in self._episodes]
        }

        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_episode(self, episode: EpisodeEntry):
        """Add a new episode to history, maintaining the max limit."""
        # Remove any existing episode with the same date
        self._episodes = [ep for ep in self._episodes if ep.date != episode.date]

        # Add new episode at the beginning
        self._episodes.insert(0, episode)

        # Trim to max episodes
        if len(self._episodes) > self.max_episodes:
            # Clean up old episode files before removing from history
            for old_episode in self._episodes[self.max_episodes:]:
                self._cleanup_episode_files(old_episode)

            self._episodes = self._episodes[:self.max_episodes]

        # Save to disk
        self._save_history()

    def _cleanup_episode_files(self, episode: EpisodeEntry):
        """Clean up files for an episode being removed from history."""
        # Only clean up local files, not cloud files
        for file_path in [episode.metadata_file, episode.episode_file]:
            if file_path and Path(file_path).exists():
                try:
                    Path(file_path).unlink()
                    print(f"Cleaned up old episode file: {file_path}")
                except OSError as e:
                    print(f"Warning: Could not delete {file_path}: {e}")

    def get_episodes(self) -> List[EpisodeEntry]:
        """Get all episodes in history (newest first)."""
        return self._episodes.copy()

    def get_latest_episode(self) -> Optional[EpisodeEntry]:
        """Get the most recent episode."""
        return self._episodes[0] if self._episodes else None

    def episode_exists(self, date: str) -> bool:
        """Check if an episode for the given date already exists."""
        return any(ep.date == date for ep in self._episodes)

    def remove_episode(self, date: str) -> bool:
        """Remove an episode by date. Returns True if removed."""
        original_count = len(self._episodes)
        removed_episodes = [ep for ep in self._episodes if ep.date == date]
        self._episodes = [ep for ep in self._episodes if ep.date != date]

        if len(self._episodes) < original_count:
            # Clean up files for removed episodes
            for episode in removed_episodes:
                self._cleanup_episode_files(episode)

            self._save_history()
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the episode history."""
        return {
            'total_episodes': len(self._episodes),
            'max_episodes': self.max_episodes,
            'oldest_episode': self._episodes[-1].date if self._episodes else None,
            'newest_episode': self._episodes[0].date if self._episodes else None,
            'history_file': str(self.history_file)
        }