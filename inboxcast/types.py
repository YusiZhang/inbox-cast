"""Core data types and contracts for InboxCast pipeline."""
from typing import Protocol, List, Dict, Any, Optional, Literal
from dataclasses import dataclass
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


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


# Audio format types for better type safety
AudioFormat = Literal["mp3", "wav", "pcm", "flac"]
TTSModel = Literal[
    "speech-02-hd", "speech-02-turbo", "speech-01-hd", "speech-01-turbo",
    "speech-01-240228", "speech-01-turbo-240228"
]
Emotion = Literal[
    "happy", "sad", "angry", "fearful", "disgusted", "surprised", "neutral"
]
Language = Literal[
    "en-US", "en-UK", "en-AU", "en-IN", "zh-CN", "zh-HK", "ja-JP", "ko-KR",
    "fr-FR", "de-DE", "es-ES", "pt-PT", "pt-BR", "it-IT", "ar-SA", "ru-RU",
    "tr-TR", "nl-NL", "uk-UA", "vi-VN", "id-ID"
]


class AudioSettings(BaseModel):
    """
    Audio configuration settings for MiniMax TTS output.
    
    Provides comprehensive control over audio quality and format.
    """
    
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )
    
    format: AudioFormat = Field(
        default="mp3",
        description="Audio output format"
    )
    sample_rate: int = Field(
        default=32000,
        description="Audio sample rate in Hz",
        ge=8000,
        le=44100
    )
    bitrate: int = Field(
        default=128000,
        description="Audio bitrate in bps",
        ge=64000,
        le=320000
    )
    channels: int = Field(
        default=1,
        description="Number of audio channels",
        ge=1,
        le=2
    )


class VoiceOverRequest(BaseModel):
    """
    Enhanced Pydantic model for MiniMax TTS API requests.
    
    Supports comprehensive MiniMax AI text-to-speech parameters including
    model selection, emotion control, voice cloning, and advanced audio settings.
    """
    
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )
    
    text: str = Field(
        ...,
        description="Text content to be synthesized",
        min_length=1,
        max_length=200000
    )
    
    # Voice Configuration
    voice_id: str = Field(
        default="female-shaonv",
        description="Voice model ID from available MiniMax voices"
    )
    model: TTSModel = Field(
        default="speech-02-hd",
        description="TTS model to use for synthesis"
    )
    
    # Voice Control Parameters
    speed: float = Field(
        default=1.0,
        description="Speech speed multiplier",
        ge=0.5,
        le=2.0
    )
    vol: float = Field(
        default=1.0,
        description="Volume level",
        ge=0.0,
        le=10.0
    )
    pitch: int = Field(
        default=0,
        description="Pitch adjustment in semitones",
        ge=-12,
        le=12
    )
    
    # Advanced Features
    emotion: Optional[Emotion] = Field(
        default=None,
        description="Emotion to apply to speech (only works with certain models)"
    )
    english_normalization: bool = Field(
        default=False,
        description="Enable improved English number and text normalization"
    )
    language: Optional[Language] = Field(
        default=None,
        description="Target language for synthesis"
    )
    
    # Audio Settings
    audio_settings: AudioSettings = Field(
        default_factory=AudioSettings,
        description="Audio output configuration"
    )
    
    # Streaming and Processing Options
    stream: bool = Field(
        default=False,
        description="Enable streaming response (if supported)"
    )
    long_text_mode: bool = Field(
        default=False,
        description="Enable long text processing for texts over 1000 characters"
    )


class VoiceCloneRequest(BaseModel):
    """
    Request model for MiniMax voice cloning functionality.
    
    Supports creating custom voices from audio samples.
    """
    
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )
    
    audio_data: bytes = Field(
        ...,
        description="Audio sample data for voice cloning (10s-5min, <20MB)"
    )
    audio_format: AudioFormat = Field(
        ...,
        description="Format of the input audio sample"
    )
    voice_name: str = Field(
        ...,
        description="Name for the cloned voice",
        min_length=1,
        max_length=50
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional description of the voice",
        max_length=200
    )


class VoiceInfo(BaseModel):
    """
    Metadata about the voice used for synthesis.
    """
    
    model_config = ConfigDict(extra="ignore")
    
    voice_id: str = Field(..., description="Voice ID that was used")
    voice_name: Optional[str] = Field(default=None, description="Human-readable voice name")
    language: Optional[str] = Field(default=None, description="Voice language")
    gender: Optional[str] = Field(default=None, description="Voice gender")
    age_range: Optional[str] = Field(default=None, description="Apparent age range")
    accent: Optional[str] = Field(default=None, description="Voice accent or region")


class VoiceOverResponse(BaseModel):
    """
    Enhanced Pydantic model for MiniMax TTS API responses.
    
    Provides comprehensive response data including audio content,
    metadata, and detailed error information.
    """
    
    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
    )
    
    # Core Response Data
    success: bool = Field(
        ...,
        description="Whether the TTS request was successful"
    )
    audio_data: Optional[bytes] = Field(
        default=None,
        description="Binary audio data if synthesis succeeded"
    )
    
    # Audio Metadata
    audio_format: Optional[str] = Field(
        default=None,
        description="Actual audio format returned"
    )
    audio_duration: Optional[float] = Field(
        default=None,
        description="Duration of generated audio in seconds",
        ge=0.0
    )
    audio_size: Optional[int] = Field(
        default=None,
        description="Size of audio data in bytes",
        ge=0
    )
    
    # Processing Metadata
    processing_time: Optional[float] = Field(
        default=None,
        description="Time taken for synthesis in seconds",
        ge=0.0
    )
    model_used: Optional[str] = Field(
        default=None,
        description="Actual TTS model that was used"
    )
    
    # Voice Information
    voice_info: Optional[VoiceInfo] = Field(
        default=None,
        description="Metadata about the voice used"
    )
    
    # Error Information
    error_message: Optional[str] = Field(
        default=None,
        description="Detailed error message if synthesis failed"
    )
    error_code: Optional[str] = Field(
        default=None,
        description="Specific error code for programmatic handling"
    )
    
    # Request Tracking
    request_id: Optional[str] = Field(
        default=None,
        description="Unique identifier for this request (for support/debugging)"
    )
    
    # Usage Information
    characters_processed: Optional[int] = Field(
        default=None,
        description="Number of characters that were processed",
        ge=0
    )
    cost_estimate: Optional[float] = Field(
        default=None,
        description="Estimated cost for this synthesis request",
        ge=0.0
    )