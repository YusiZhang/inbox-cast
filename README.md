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

### Basic Pipeline (Local Generation)

```bash
# Run with default config
inboxcast run

# Use custom config
inboxcast run --config your-config.yaml

# Specify target duration
inboxcast run --config config.yaml --minutes 15
```

### Publishing Commands (Azure + RSS Hosting)

```bash
# Generate and upload to Azure in one command
inboxcast publish --config config-publish.yaml

# Upload existing files to Azure
inboxcast upload --config config-publish.yaml --output-dir out/

# Host RSS feed on web server (for VPS deployment)
inboxcast serve --output-dir out/ --port 8000
```

### Running FastAPI Server as Background Service (VPS Deployment)

For production deployment on a VPS, use systemd to run the FastAPI server as a persistent background service:

```bash
# Copy the service file to systemd directory
sudo cp inboxcast.service /etc/systemd/system/

# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable inboxcast

# Start the service now
sudo systemctl start inboxcast

# Check the status
sudo systemctl status inboxcast
```

**Service Management Commands:**
```bash
# Stop the server
sudo systemctl stop inboxcast

# Restart the server
sudo systemctl restart inboxcast

# View logs
sudo journalctl -u inboxcast -f
```

The service configuration file (`inboxcast.service`) is included in the repository and will automatically restart the server if it crashes.

### Validation and Testing

```bash
# Validate RSS feed and test Azure connectivity
inboxcast validate-feed --config config-publish.yaml

# Test Azure Blob Storage connection
inboxcast test-upload --config config-publish.yaml

# Plan episode without generating audio
inboxcast plan --config config.yaml --minutes 10

# Generate audio from existing script
inboxcast tts --config config.yaml --output out/
```

## Configuration

### Basic Configuration

The system uses `espeak` for TTS by default. If espeak is not available, it falls back to a dummy provider that generates silence.

To explicitly use dummy mode, set in your config.yaml:
```yaml
voice_settings:
  provider: "dummy"
```

### Publishing Configuration (Azure + RSS)

For podcast publishing, create a `config-publish.yaml` with Azure settings:

```yaml
publishing:
  rss_base_url: "https://podcast.yourdomain.com"
  azure:
    container_name: "podcast-files"
    # Set connection string via environment variable:
    # export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;..."

voice_settings:
  provider: "minimax"  # Better quality TTS
  voice_id: "English_captivating_female1"
  speed: 0.9

output:
  audio_format: "mp3"
  episode_filename: "episode.mp3"
```

**Required for publishing:**
- Azure Blob Storage account and connection string
- Domain for RSS hosting (e.g., `podcast.yourdomain.com`)
- MiniMax API key for high-quality TTS (optional)

## Target Users
Busy software engineers/PMs tracking AI developments

## Core Value
Turn newsletter firehose into hands-free, commute-length audio with legal-first architecture