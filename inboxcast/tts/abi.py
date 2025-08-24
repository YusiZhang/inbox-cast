"""TTS Abstract Base Interface."""
from abc import ABC, abstractmethod
from ..types import TTSProvider


class BaseTTSProvider(ABC, TTSProvider):
    """Base TTS provider with common functionality."""
    
    @abstractmethod
    def synthesize(
        self, 
        text: str, 
        voice: str = "default", 
        speed: float = 1.0, 
        sample_rate: int = 44100, 
        format: str = "wav"
    ) -> bytes:
        """Synthesize text to audio bytes."""
        pass
    
    def estimate_duration(self, text: str, speed: float = 1.0) -> float:
        """Estimate duration in seconds based on word count."""
        # Rough estimate: 165 words per minute at speed 1.0
        word_count = len(text.split())
        base_wpm = 165
        actual_wpm = base_wpm * speed
        duration_minutes = word_count / actual_wpm
        return duration_minutes * 60