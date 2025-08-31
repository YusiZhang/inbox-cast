"""Audio stitching and basic processing."""
import wave
import struct
from typing import List
from pathlib import Path
from io import BytesIO


class SimpleAudioStitcher:
    """Simple audio concatenation without external dependencies."""
    
    def __init__(self, gap_ms: int = 200):
        self.gap_ms = gap_ms
    
    def stitch(self, audio_segments: List[bytes], titles: List[str] = None) -> bytes:
        """Concatenate WAV audio segments with gaps."""
        
        if not audio_segments:
            return b''
        
        # For Step 1, we'll just concatenate the WAV data
        # This is basic but works for our MVP
        combined_samples = []
        sample_rate = 44100
        
        for i, wav_data in enumerate(audio_segments):
            try:
                # Extract samples from WAV data
                samples = self._extract_wav_samples(wav_data)
                combined_samples.extend(samples)
                
                # Add gap (silence) between segments
                if i < len(audio_segments) - 1:
                    gap_samples = int(self.gap_ms * sample_rate / 1000)
                    combined_samples.extend([0] * gap_samples)
                    
            except Exception as e:
                print(f"Warning: Failed to process audio segment {i}: {e}")
                continue
        
        # Create WAV file
        return self._create_wav(combined_samples, sample_rate)
    
    def export_wav(self, wav_data: bytes, output_path: str):
        """Export WAV data to file."""
        try:
            with open(output_path, 'wb') as f:
                f.write(wav_data)
            print(f"Exported WAV: {output_path}")
        except Exception as e:
            print(f"Failed to export WAV: {e}")
            raise
    
    def _extract_wav_samples(self, wav_data: bytes) -> List[int]:
        """Extract 16-bit samples from WAV data."""
        if len(wav_data) < 44:  # Minimum WAV header size
            return []
        
        # Skip WAV header (44 bytes) and read samples
        sample_data = wav_data[44:]
        samples = []
        
        # Read 16-bit samples (2 bytes each)
        for i in range(0, len(sample_data), 2):
            if i + 1 < len(sample_data):
                sample = struct.unpack('<h', sample_data[i:i+2])[0]
                samples.append(sample)
        
        return samples
    
    def _create_wav(self, samples: List[int], sample_rate: int) -> bytes:
        """Create WAV file from samples."""
        num_samples = len(samples)
        data_size = num_samples * 2  # 16-bit samples
        file_size = data_size + 36
        
        # WAV header
        header = b'RIFF'
        header += struct.pack('<I', file_size)
        header += b'WAVE'
        header += b'fmt '
        header += struct.pack('<I', 16)  # fmt chunk size
        header += struct.pack('<H', 1)   # PCM format
        header += struct.pack('<H', 1)   # mono
        header += struct.pack('<I', sample_rate)
        header += struct.pack('<I', sample_rate * 2)  # byte rate
        header += struct.pack('<H', 2)   # block align
        header += struct.pack('<H', 16)  # bits per sample
        header += b'data'
        header += struct.pack('<I', data_size)
        
        # Sample data
        sample_bytes = b''.join(struct.pack('<h', sample) for sample in samples)
        
        return header + sample_bytes


class SimpleEpisodeBuilder:
    """Basic episode builder for Step 1."""
    
    def __init__(self, target_minutes: int = 10):
        self.target_minutes = target_minutes
        self.target_words = target_minutes * 165  # 165 WPM baseline
    
    def fit(self, items: List, target_minutes: int = None) -> List:
        """Simple fitting - just truncate to target word count."""
        if target_minutes:
            self.target_minutes = target_minutes
            self.target_words = target_minutes * 165
        
        # Sort by some criteria (for now, just keep original order)
        sorted_items = items[:]
        
        # Allocate words evenly, up to target
        if not sorted_items:
            return []
        
        # Limit to reasonable number of items for the target duration
        max_items_for_duration = min(len(sorted_items), self.target_minutes * 2) 
        selected_items = sorted_items[:max_items_for_duration]
        
        words_per_item = self.target_words // len(selected_items)
        fitted_items = []
        total_words = 0
        
        for item in selected_items:
            if total_words >= self.target_words:
                break
                
            # Allocate more reasonable word count per item
            remaining_words = self.target_words - total_words
            allocated_words = min(words_per_item, remaining_words, len(item.script.split()))
            
            # Create planned item (for Step 1, we just use the existing item structure)
            fitted_item = type('PlannedItem', (), {
                'title': item.title,
                'script': ' '.join(item.script.split()[:allocated_words]),
                'sources': item.sources,
                'notes': item.notes,
                'word_count': allocated_words,
                'allocated_words': allocated_words
            })()
            
            fitted_items.append(fitted_item)
            total_words += allocated_words
        
        print(f"Episode planning: {len(items)} → {len(fitted_items)} items, {total_words} words")
        return fitted_items


class ProfessionalAudioStitcher:
    """Professional audio stitching with pydub and normalization features."""
    
    def __init__(self, gap_ms: int = 500, fade_ms: int = 50, target_lufs: float = -19.0, output_format: str = "wav"):
        """
        Initialize professional audio stitcher.
        
        Args:
            gap_ms: Gap between segments in milliseconds
            fade_ms: Fade in/out duration in milliseconds
            target_lufs: Target loudness in LUFS (-19.0 is broadcast standard)
            output_format: Output audio format ("wav" or "mp3")
        """
        self.gap_ms = gap_ms
        self.fade_ms = fade_ms
        self.target_lufs = target_lufs
        self.output_format = output_format
        
        # Try importing pydub
        try:
            from pydub import AudioSegment
            from pydub.effects import normalize
            self.AudioSegment = AudioSegment
            self.normalize = normalize
            self.pydub_available = True
        except ImportError:
            print("Warning: pydub not available, falling back to simple stitching")
            self.pydub_available = False
    
    def stitch(self, audio_segments: List[bytes], titles: List[str] = None) -> bytes:
        """
        Concatenate audio segments with professional processing.
        
        If pydub is not available, falls back to simple stitching.
        """
        if not self.pydub_available:
            # Fallback to simple stitcher
            simple_stitcher = SimpleAudioStitcher(gap_ms=self.gap_ms)
            return simple_stitcher.stitch(audio_segments, titles)
        
        if not audio_segments:
            return b''
        
        try:
            return self._stitch_with_pydub(audio_segments, titles)
        except Exception as e:
            print(f"Professional stitching failed: {e}, falling back to simple stitching")
            simple_stitcher = SimpleAudioStitcher(gap_ms=self.gap_ms)
            return simple_stitcher.stitch(audio_segments, titles)
    
    def _stitch_with_pydub(self, audio_segments: List[bytes], titles: List[str] = None) -> bytes:
        """Stitch audio using pydub with professional features."""
        
        combined = None
        
        for i, audio_data in enumerate(audio_segments):
            try:
                # Detect format and load audio
                audio_segment = self._load_audio_segment(audio_data)
                
                if audio_segment is None:
                    print(f"Warning: Failed to load audio segment {i}")
                    continue
                
                # Apply fade in/out
                if self.fade_ms > 0:
                    audio_segment = audio_segment.fade_in(self.fade_ms).fade_out(self.fade_ms)
                
                # Normalize volume
                audio_segment = self.normalize(audio_segment)
                
                if combined is None:
                    combined = audio_segment
                else:
                    # Add gap between segments
                    if self.gap_ms > 0:
                        silence = self.AudioSegment.silent(duration=self.gap_ms)
                        combined = combined + silence + audio_segment
                    else:
                        combined = combined + audio_segment
                        
            except Exception as e:
                print(f"Warning: Failed to process audio segment {i}: {e}")
                continue
        
        if combined is None:
            return b''
        
        # Final normalization and loudness adjustment
        combined = self._apply_broadcast_normalization(combined)
        
        # Export to bytes using configured output format
        return self._export_to_bytes(combined, format=self.output_format)
    
    def _load_audio_segment(self, audio_data: bytes):
        """Load audio data into AudioSegment, detecting format."""
        try:
            # Try MP3 first (MiniMax output)
            return self.AudioSegment.from_mp3(BytesIO(audio_data))
        except:
            try:
                # Try WAV (espeak output)
                return self.AudioSegment.from_wav(BytesIO(audio_data))
            except:
                try:
                    # Try raw format detection
                    return self.AudioSegment.from_file(BytesIO(audio_data))
                except:
                    return None
    
    def _apply_broadcast_normalization(self, audio_segment):
        """
        Apply broadcast-standard loudness normalization.
        
        Note: This is a simplified version. For true -19 LUFS compliance,
        you would need ffmpeg with loudnorm filter or specialized tools.
        """
        # For now, apply basic normalization
        # In a full implementation, you'd use ffmpeg loudnorm or similar
        normalized = self.normalize(audio_segment)
        
        # Apply gentle compression to meet broadcast standards
        # This is a simplified approach - real broadcast processing is more complex
        return normalized
    
    def _export_to_bytes(self, audio_segment, format="wav") -> bytes:
        """Export AudioSegment to bytes."""
        from io import BytesIO
        
        buffer = BytesIO()
        
        # Export with broadcast-quality settings
        export_params = {
            "format": format,
            "parameters": [
                "-ar", "44100",  # 44.1kHz sample rate
                "-ac", "1",      # Mono
                "-sample_fmt", "s16"  # 16-bit
            ]
        }
        
        if format == "mp3":
            export_params["bitrate"] = "128k"
        
        audio_segment.export(buffer, **export_params)
        return buffer.getvalue()
    
    def export_wav(self, wav_data: bytes, output_path: str):
        """Export WAV data to file."""
        try:
            with open(output_path, 'wb') as f:
                f.write(wav_data)
            print(f"Exported professional audio: {output_path}")
        except Exception as e:
            print(f"Failed to export audio: {e}")
            raise
    
    def export_mp3(self, audio_data: bytes, output_path: str, bitrate: str = "128k"):
        """Export audio as MP3 with specified bitrate."""
        if not self.pydub_available:
            raise RuntimeError("pydub not available for MP3 export")
        
        try:
            from io import BytesIO
            
            # Load audio data
            audio_segment = self._load_audio_segment(audio_data)
            if audio_segment is None:
                # Try loading as WAV directly
                audio_segment = self.AudioSegment.from_wav(BytesIO(audio_data))
            
            # Export as MP3
            audio_segment.export(
                output_path, 
                format="mp3", 
                bitrate=bitrate,
                parameters=["-ar", "44100", "-ac", "1"]
            )
            
            print(f"Exported MP3 audio: {output_path}")
            
        except Exception as e:
            print(f"Failed to export MP3: {e}")
            raise