# InboxCast

AI newsletter summarization to private audio podcasts. Converts user-forwarded AI newsletters into commute-sized audio episodes via semantic deduplication, transformative summarization, and private RSS delivery.

## Installation

### Dependencies

**System Requirements:**
- Python 3.8+
- `espeak` for text-to-speech synthesis
- `ffmpeg` for mp3 audio format support

**Install espeak,ffmpeg:**
```bash
# macOS
brew install espeak
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install espeak
sudo apt-get install ffmpeg

```

**Install Python dependencies:**
```bash
uv sync
```

## Usage

```bash
# Run with default config
inboxcast run

# Use custom config
inboxcast run --config your-config.yaml
```

## Configuration

The system uses `espeak` for TTS by default. If espeak is not available, it falls back to a dummy provider that generates silence.

To explicitly use dummy mode, set in your config.yaml:
```yaml
voice_settings:
  provider: "dummy"
```

## Target Users
Busy software engineers/PMs tracking AI developments

## Core Value
Turn newsletter firehose into hands-free, commute-length audio with legal-first architecture