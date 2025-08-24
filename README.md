# InboxCast

AI newsletter summarization to private audio podcasts. Converts user-forwarded AI newsletters into commute-sized audio episodes via semantic deduplication, transformative summarization, and private RSS delivery.

## Installation

### Dependencies

**System Requirements:**
- Python 3.8+
- `espeak` for text-to-speech synthesis

**Install espeak:**
```bash
# macOS
brew install espeak

# Ubuntu/Debian
sudo apt-get install espeak

# Other systems
# See: http://espeak.sourceforge.net/download.html
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