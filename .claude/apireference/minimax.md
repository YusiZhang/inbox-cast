Here is a reference minimax REST API implementation in python

```
"""
MiniMax AI service for text-to-speech voice-over generation.
"""

import os

import requests

from models import VoiceOverRequest, VoiceOverResponse


class MiniMaxService:
    """Service class for MiniMax AI text-to-speech integration."""

    def __init__(
        self,
        api_key: str | None = None,
        group_id: str | None = None,
        base_url: str | None = None,
    ):
        """
        Initialize MiniMax service.

        Args:
            api_key: MiniMax API key. If not provided, will try to read from environment
            group_id: MiniMax Group ID. If not provided, will try to read from environment
            base_url: Base URL for MiniMax API. Defaults to official API endpoint
        """
        self.api_key = api_key or os.getenv("MINIMAX_API_KEY")
        self.group_id = group_id or os.getenv("MINIMAX_GROUP_ID")
        self.base_url = base_url or "https://api.minimax.io/v1/t2a_v2"
        self.session = requests.Session()

        if self.api_key and self.group_id:
            self.session.headers.update(
                {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            )
            self.session.params.update({"GroupId": self.group_id})

    def generate_voice_over(self, request: VoiceOverRequest) -> VoiceOverResponse:
        """
        Generate voice-over audio from text using MiniMax AI.

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

        try:
            # Prepare request payload for MiniMax API
            payload = {
                "model": "speech-02-turbo",
                "text": request.text,
                "stream": False,
                "voice_setting": {
                    "voice_id": request.voice_id,
                    "speed": request.speed,
                    "vol": request.vol,
                    "pitch": request.pitch,
                },
                "audio_setting": {
                    "sample_rate": 32000,
                    "bitrate": 128000,
                    "format": "mp3",
                    "channel": 1,
                },
            }

            # Make API request
            response = self.session.post(self.base_url, json=payload, timeout=30)

            if response.status_code == 200:
                response_data = response.json()

                if response_data.get("base_resp", {}).get("status_code") == 0:
                    audio_hex = response_data.get("data", {}).get("audio")
                    if audio_hex:
                        audio_bytes = bytes.fromhex(audio_hex)
                        return VoiceOverResponse(
                            success=True,
                            audio_data=audio_bytes,
                            audio_format=response_data.get("extra_info", {}).get(
                                "audio_format", "mp3"
                            ),
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

        except requests.exceptions.Timeout:
            return VoiceOverResponse(
                success=False,
                error_message="Request timeout. MiniMax API did not respond within 30 seconds.",
            )
        except requests.exceptions.ConnectionError:
            return VoiceOverResponse(
                success=False, error_message="Connection error. Could not reach MiniMax API."
            )
        except Exception as e:
            return VoiceOverResponse(success=False, error_message=f"Unexpected error: {str(e)}")

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

```