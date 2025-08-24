"""Espeak TTS provider implementation."""
import subprocess
import tempfile
import os
from pathlib import Path
from .abi import BaseTTSProvider


class EspeakProvider(BaseTTSProvider):
    """Espeak TTS provider for fallback."""
    
    def __init__(self):
        self.check_espeak_available()
    
    def check_espeak_available(self):
        """Check if espeak is available on the system."""
        try:
            subprocess.run(['espeak', '--version'], 
                         capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Warning: espeak not found. Install with: brew install espeak (macOS)")
    
    def synthesize(
        self, 
        text: str, 
        voice: str = "default", 
        wpm: int = 165, 
        sample_rate: int = 44100, 
        format: str = "wav"
    ) -> bytes:
        """Synthesize text using espeak."""
        
        # Create temporary file for output
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            # Use WPM directly for espeak speed
            espeak_speed = wpm
            
            # Build espeak command
            cmd = [
                'espeak',
                '-s', str(espeak_speed),  # Speed in words per minute
                '-w', temp_path,          # Write to WAV file
                text
            ]
            
            # Add voice if not default
            if voice != "default":
                cmd.extend(['-v', voice])
            
            # Run espeak
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"Espeak failed: {result.stderr}")
            
            # Read the generated audio file
            with open(temp_path, 'rb') as f:
                audio_data = f.read()
            
            return audio_data
            
        except Exception as e:
            print(f"Espeak synthesis failed: {e}")
            # Return empty bytes on failure
            return b''
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class DummyTTSProvider(BaseTTSProvider):
    """Dummy TTS that generates silence for testing."""
    
    def synthesize(
        self, 
        text: str, 
        voice: str = "default", 
        wpm: int = 165, 
        sample_rate: int = 44100, 
        format: str = "wav"
    ) -> bytes:
        """Generate silence based on estimated duration."""
        
        # Estimate duration and generate silence
        duration = self.estimate_duration(text, wpm)
        num_samples = int(duration * sample_rate)
        
        # WAV header for 16-bit mono
        wav_header = self._create_wav_header(num_samples, sample_rate)
        
        # Silent audio data (16-bit zeros)
        silence_data = b'\x00\x00' * num_samples
        
        return wav_header + silence_data
    
    def _create_wav_header(self, num_samples: int, sample_rate: int) -> bytes:
        """Create WAV header for silent audio."""
        # Minimal WAV header (44 bytes)
        data_size = num_samples * 2  # 16-bit samples
        file_size = data_size + 36
        
        header = b'RIFF'
        header += file_size.to_bytes(4, 'little')
        header += b'WAVE'
        header += b'fmt '
        header += (16).to_bytes(4, 'little')  # fmt chunk size
        header += (1).to_bytes(2, 'little')   # PCM format
        header += (1).to_bytes(2, 'little')   # mono
        header += sample_rate.to_bytes(4, 'little')
        header += (sample_rate * 2).to_bytes(4, 'little')  # byte rate
        header += (2).to_bytes(2, 'little')   # block align
        header += (16).to_bytes(2, 'little')  # bits per sample
        header += b'data'
        header += data_size.to_bytes(4, 'little')
        
        return header