"""Configuration management for InboxCast."""
import yaml
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class FeedConfig:
    url: str
    weight: float = 1.0


@dataclass  
class VoiceConfig:
    provider: str = "espeak"
    wpm: int = 165
    voice_id: str = "default"


@dataclass
class OutputConfig:
    audio_format: str = "mp3"
    sample_rate: int = 44100
    episode_filename: str = "episode.mp3"
    rss_filename: str = "feed.xml"


@dataclass
class Config:
    rss_feeds: List[FeedConfig]
    voice_settings: VoiceConfig
    output: OutputConfig
    target_duration: int = 10
    dedupe_threshold: float = 0.9

    @classmethod
    def load(cls, config_path: str = "config.yaml") -> "Config":
        """Load configuration from YAML file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        
        # Convert feed configs
        feeds = [FeedConfig(**feed) for feed in data["rss_feeds"]]
        
        # Convert voice config  
        voice = VoiceConfig(**data["voice_settings"])
        
        # Convert output config
        output = OutputConfig(**data["output"])
        
        return cls(
            rss_feeds=feeds,
            target_duration=data["target_duration"],
            dedupe_threshold=data["dedupe_threshold"],
            voice_settings=voice,
            output=output
        )