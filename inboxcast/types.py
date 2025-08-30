"""Core data types and contracts for InboxCast pipeline."""
from typing import Protocol, List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RawItem:
    """Raw item from RSS source."""
    title: str
    url: str
    content: str
    published: Optional[datetime] = None
    source_name: str = ""


@dataclass 
class ProcessedItem:
    """Item after summarization and processing."""
    title: str
    script: str
    sources: List[str]
    notes: Dict[str, Any]
    word_count: int = 0


@dataclass
class PlannedItem:
    """Item with duration planning applied."""
    title: str
    script: str
    sources: List[str]
    notes: Dict[str, Any]
    word_count: int
    allocated_words: int


class Source(Protocol):
    """RSS source fetcher contract."""
    
    def fetch(self) -> List[RawItem]:
        """Fetch raw items from source."""
        ...


class Summarizer(Protocol):
    """Content summarizer contract."""
    
    def summarize(self, item: RawItem) -> ProcessedItem:
        """Summarize item with policy guards."""
        ...


class TTSProvider(Protocol):
    """Text-to-speech provider contract."""
    
    def synthesize(
        self, 
        text: str, 
        voice: str = "default", 
        wpm: int = 165, 
        sample_rate: int = 44100, 
        format: str = "wav"
    ) -> bytes:
        """Synthesize text to audio bytes."""
        ...


class EpisodeBuilder(Protocol):
    """Episode duration planner contract."""
    
    def fit(self, items: List[ProcessedItem], target_minutes: int) -> List[PlannedItem]:
        """Fit items to target duration with word budgeting."""
        ...


# MiniMax TTS Models
@dataclass
class VoiceOverRequest:
    """Request model for MiniMax TTS API."""
    text: str
    voice_id: str = "female-shaonv"
    speed: float = 1.0
    vol: float = 1.0
    pitch: int = 0


@dataclass
class VoiceOverResponse:
    """Response model from MiniMax TTS API."""
    success: bool
    audio_data: Optional[bytes] = None
    audio_format: str = "mp3"
    error_message: Optional[str] = None