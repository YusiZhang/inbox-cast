"""Configuration management for InboxCast."""
import os
import yaml
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# Disable tokenizers parallelism to avoid warning in forked processes
os.environ["TOKENIZERS_PARALLELISM"] = "false"


def load_dotenv_files():
    """
    Load environment variables from .env files in order of precedence:
    1. Current working directory/.env
    2. User home directory/.env
    
    Uses override=False to respect precedence (higher priority files won't be overwritten).
    """
    cwd_env = Path.cwd() / ".env"
    home_env = Path.home() / ".env"
    
    # Load in reverse order of precedence so higher priority files override lower ones
    if home_env.exists():
        load_dotenv(home_env, override=False)
    
    if cwd_env.exists():
        load_dotenv(cwd_env, override=False)


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
class PolicyChecksConfig:
    """Configuration for policy compliance checks."""
    # Pre-LLM checks (applied before OpenAI call)
    paywall_detection: bool = True
    min_content_length: bool = True
    content_quality_check: bool = True
    url_allowlist_check: bool = False
    
    # Post-LLM checks (applied after OpenAI call)  
    max_word_count: bool = True
    quote_length_check: bool = True
    derivative_language_check: bool = True
    transformative_analysis_check: bool = True


@dataclass
class ProcessingConfig:
    """Configuration for content processing pipeline."""
    # Summarization
    summarizer: str = "simple"  # "simple" or "openai"
    max_words: int = 50
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.3
    
    # Deduplication  
    deduplicator: str = "simple"  # "simple" or "semantic"
    similarity_threshold: float = 0.85
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_cache_days: int = 7
    
    # Content cleaning
    use_readability: bool = True
    fetch_full_content: bool = True
    content_timeout: int = 10
    
    # Policy guards
    max_quote_words: int = 30
    
    # Policy checks configuration
    policy_checks: PolicyChecksConfig = None


@dataclass
class Config:
    rss_feeds: List[FeedConfig]
    voice_settings: VoiceConfig
    output: OutputConfig
    processing: ProcessingConfig
    target_duration: int = 10
    max_rss_items: int = 20  # Maximum items to fetch per RSS feed
    dedupe_threshold: float = 0.9  # Legacy field for backward compatibility

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
        
        # Convert processing config (with defaults for backward compatibility)
        processing_data = data.get("processing", {})
        
        # Handle policy checks configuration
        policy_checks_data = processing_data.get("policy_checks", {})
        policy_checks = PolicyChecksConfig(**policy_checks_data) if policy_checks_data else PolicyChecksConfig()
        processing_data["policy_checks"] = policy_checks
        
        processing = ProcessingConfig(**processing_data)
        
        return cls(
            rss_feeds=feeds,
            target_duration=data["target_duration"],
            max_rss_items=data.get("max_rss_items", 20),
            dedupe_threshold=data.get("dedupe_threshold", 0.9),
            voice_settings=voice,
            output=output,
            processing=processing
        )