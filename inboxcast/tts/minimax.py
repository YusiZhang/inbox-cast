"""MiniMax AI service for text-to-speech voice-over generation."""
import os
import time
import requests
from typing import Optional
from ..types import VoiceOverRequest, VoiceOverResponse
from .abi import BaseTTSProvider


class MiniMaxProvider(BaseTTSProvider):
    """MiniMax TTS provider with retry logic and fallback."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        group_id: Optional[str] = None,
        base_url: Optional[str] = None,
        max_retries: int = 1,
        retry_delay: float = 1.0,
    ):
        """
        Initialize MiniMax service.

        Args:
            api_key: MiniMax API key. If not provided, will try to read from environment
            group_id: MiniMax Group ID. If not provided, will try to read from environment
            base_url: Base URL for MiniMax API. Defaults to official API endpoint
            max_retries: Maximum number of retry attempts for failed requests
            retry_delay: Base delay between retries (exponential backoff)
        """
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY")
        self.group_id = group_id or os.getenv("MINIMAX_GROUP_ID")
        self.base_url = base_url or "https://api.minimax.io/v1/t2a_v2"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.session = requests.Session()

        if self.api_key and self.group_id:
            self.session.headers.update(
                {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            )
            self.session.params.update({"GroupId": self.group_id})

    def synthesize(
        self, 
        text: str, 
        voice: str = "female-shaonv", 
        wpm: int = 165, 
        sample_rate: int = 44100, 
        format: str = "wav",
        speed: Optional[float] = None,
        vol: Optional[float] = None,
        pitch: Optional[int] = None
    ) -> bytes:
        """Synthesize text to audio bytes using MiniMax API."""
        
        # Create request object with optional parameters
        from ..types import AudioSettings
        
        audio_settings = AudioSettings(
            format="mp3" if format == "wav" else format,  # Convert wav to mp3 for compatibility
            sample_rate=sample_rate if sample_rate <= 44100 else 32000,
            channels=1
        )
        
        request = VoiceOverRequest(
            text=text,
            voice_id=voice,
            speed=speed if speed is not None else self._wpm_to_speed(wpm),
            vol=vol if vol is not None else 1.0,
            pitch=pitch if pitch is not None else 0,
            audio_settings=audio_settings
        )
        
        # Generate voice-over
        response = self.generate_voice_over(request)
        
        if response.success and response.audio_data:
            return response.audio_data
        else:
            print(f"MiniMax TTS failed: {response.error_message}")
            return b''

    def generate_voice_over(self, request: VoiceOverRequest) -> VoiceOverResponse:
        """
        Generate voice-over audio from text using MiniMax AI with retry logic.

        Args:
            request: VoiceOverRequest containing text and voice parameters

        Returns:
            VoiceOverResponse with audio data or error information
        """
        if not self.api_key or not self.group_id:
            return VoiceOverResponse(
                success=False,
                error_message="MiniMax API key or Group ID not provided. Set MINIMAX_API_KEY and MINIMAX_GROUP_ID environment variables.",
            )

        # Retry logic with exponential backoff
        for attempt in range(self.max_retries + 1):
            try:
                response = self._make_api_request(request)
                if response.success:
                    return response
                
                # If not successful and we have retries left, continue
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    print(f"MiniMax request failed (attempt {attempt + 1}), retrying in {delay}s: {response.error_message}")
                    time.sleep(delay)
                else:
                    return response
                    
            except Exception as e:
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    print(f"MiniMax request error (attempt {attempt + 1}), retrying in {delay}s: {str(e)}")
                    time.sleep(delay)
                else:
                    return VoiceOverResponse(success=False, error_message=f"Max retries exceeded: {str(e)}")
        
        return VoiceOverResponse(success=False, error_message="Unexpected error in retry logic")

    def _make_api_request(self, request: VoiceOverRequest) -> VoiceOverResponse:
        """Make a single API request to MiniMax."""
        
        # Prepare request payload for MiniMax API
        voice_setting = {
            "voice_id": request.voice_id,
            "speed": request.speed,
            "vol": request.vol,
            "pitch": request.pitch,
        }
        
        # Add emotion if specified and supported by model
        if hasattr(request, 'emotion') and request.emotion:
            if request.model in ["speech-02-hd", "speech-02-turbo", "speech-01-turbo", "speech-01-hd"]:
                voice_setting["emotion"] = request.emotion
        
        # Add english normalization if specified
        if hasattr(request, 'english_normalization') and request.english_normalization:
            voice_setting["english_normalization"] = request.english_normalization
        
        payload = {
            "model": request.model,
            "text": request.text,
            "stream": request.stream if hasattr(request, 'stream') else False,
            "voice_setting": voice_setting,
            "audio_setting": {
                "sample_rate": request.audio_settings.sample_rate,
                "bitrate": request.audio_settings.bitrate,
                "format": request.audio_settings.format,
                "channel": request.audio_settings.channels,
            },
        }

        # Make API request with timeout
        response = self.session.post(self.base_url, json=payload, timeout=60)

        if response.status_code == 200:
            response_data = response.json()

            if response_data.get("base_resp", {}).get("status_code") == 0:
                audio_hex = response_data.get("data", {}).get("audio")
                if audio_hex:
                    audio_bytes = bytes.fromhex(audio_hex)
                    
                    # Extract additional response metadata
                    extra_info = response_data.get("extra_info", {})
                    
                    return VoiceOverResponse(
                        success=True,
                        audio_data=audio_bytes,
                        audio_format=extra_info.get("audio_format", request.audio_settings.format),
                        audio_duration=extra_info.get("audio_length", 0.0) / 1000.0,  # Convert ms to seconds
                        audio_size=len(audio_bytes),
                        processing_time=extra_info.get("processing_time"),
                        model_used=payload["model"],
                        characters_processed=len(request.text),
                        request_id=response_data.get("request_id"),
                    )
                else:
                    return VoiceOverResponse(
                        success=False,
                        error_message="No audio data in MiniMax API response",
                    )
            else:
                error_msg = response_data.get("base_resp", {}).get(
                    "status_msg", "Unknown API error"
                )
                return VoiceOverResponse(success=False, error_message=error_msg)
        else:
            error_msg = f"API request failed with status {response.status_code}: {response.text}"
            try:
                error_data = response.json()
                if "message" in error_data:
                    error_msg = error_data["message"]
            except Exception:
                pass

            return VoiceOverResponse(success=False, error_message=error_msg)

    def _wpm_to_speed(self, wpm: int) -> float:
        """Convert words per minute to MiniMax speed parameter."""
        # MiniMax speed: 0.5-2.0, where 1.0 is normal speed
        # Assume baseline WPM is 165, adjust proportionally
        baseline_wpm = 165
        speed = wpm / baseline_wpm
        return max(0.5, min(2.0, speed))  # Clamp to valid range

    def test_connection(self) -> bool:
        """
        Test connection to MiniMax API.

        Returns:
            bool: True if API is accessible, False otherwise
        """
        if not self.api_key:
            return False

        try:
            # Use a minimal test request
            test_request = VoiceOverRequest(text="Test")
            response = self.generate_voice_over(test_request)
            return response.success

        except Exception:
            return False

    def save_audio_to_file(self, response: VoiceOverResponse, file_path: str) -> bool:
        """
        Save audio data from VoiceOverResponse to a file.

        Args:
            response: VoiceOverResponse containing audio data
            file_path: Path where to save the audio file

        Returns:
            bool: True if file was saved successfully, False otherwise
        """
        if not response.success:
            return False

        try:
            if response.audio_data:
                # Save direct audio data
                with open(file_path, "wb") as f:
                    f.write(response.audio_data)
                return True
            return False

        except Exception:
            return False