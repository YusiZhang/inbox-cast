"""Audio stitching and basic processing."""
import wave
import struct
from typing import List
from pathlib import Path


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
        max_items_for_duration = min(len(sorted_items), self.target_minutes * 2)  # ~30 seconds per item
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