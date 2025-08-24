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
        wpm: int = 165, 
        sample_rate: int = 44100, 
        format: str = "wav"
    ) -> bytes:
        """Synthesize text to audio bytes."""
        pass
    
    def estimate_duration(self, text: str, wpm: int = 165) -> float:
        """Estimate duration in seconds based on word count and WPM."""
        word_count = len(text.split())
        duration_minutes = word_count / wpm
        return duration_minutes * 60