# InboxCast Publishing Guide

This guide covers the new podcast publishing features for distributing your InboxCast episodes via Apple Podcasts and other podcast platforms.

## Overview

InboxCast now supports:
- **Azure Blob Storage** for reliable audio file hosting
- **Production RSS feeds** with proper file sizes and HTTPS URLs
- **Web server** for hosting RSS feeds on your VPS
- **Apple Podcasts** distribution via `podcast.yusizhang.com/feed.xml`

## Quick Start

### 1. Configure Azure Storage

Set up Azure Blob Storage and get your connection string:

```bash
# Option 1: Environment variable (recommended)
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=..."

# Option 2: Add to config-publish.yaml
publishing:
  azure:
    connection_string: "DefaultEndpointsProtocol=https;AccountName=..."
    container_name: "podcast-files"
```

### 2. Generate and Publish Episodes

```bash
# Generate episode locally only
uv run inboxcast run --config config-publish.yaml --output out/

# Upload existing episode to Azure
uv run inboxcast upload --config config-publish.yaml --output-dir out/

# Generate + upload in one command
uv run inboxcast publish --config config-publish.yaml --output out/
```

### 3. Host RSS Feed on VPS

```bash
# Start web server (for VPS deployment)
uv run inboxcast serve --output-dir out/ --port 8000 --host 0.0.0.0

# RSS feed will be available at:
# http://your-vps:8000/feed.xml
```

## CLI Commands

### `uv run inboxcast run`
- Generates episode files locally (unchanged behavior)
- Creates MP3, RSS feed, metadata, and script files
- No upload functionality

### `uv run inboxcast upload --output-dir out/`
- Uploads existing episode to Azure Blob Storage
- Updates RSS feed with Azure URLs and proper file sizes
- Requires Azure configuration

### `uv run inboxcast publish`
- End-to-end workflow: generate + upload
- Runs complete pipeline then uploads to Azure
- Updates RSS with production URLs

### `uv run inboxcast serve --port 8000`
- Starts FastAPI web server for RSS hosting
- Serves feed.xml, health checks, and episode metadata
- For VPS deployment with CloudFlare routing

### `uv run inboxcast validate-feed`
- Validates RSS feed compliance
- Tests Azure connectivity
- Checks for Apple Podcasts requirements (HTTPS)

### `uv run inboxcast test-upload`
- Tests Azure Blob Storage connectivity
- Lists existing files in container
- No file uploads performed

## Configuration

Add publishing settings to your config file:

```yaml
publishing:
  rss_base_url: "https://podcast.yusizhang.com"
  azure:
    connection_string: ""  # or set AZURE_STORAGE_CONNECTION_STRING
    container_name: "podcast-files"
    base_url: ""  # optional CDN domain
```

## Architecture

- **Audio files**: Hosted on Azure Blob Storage with date-based paths
  - `https://{storage}.blob.core.windows.net/podcast-files/2025-01-08/episode.mp3`
- **RSS feed**: Served from your VPS at `podcast.yusizhang.com/feed.xml`
- **RSS content**: Points to Azure URLs for reliable audio delivery

## Apple Podcasts Submission

1. Ensure RSS feed is available at: `https://podcast.yusizhang.com/feed.xml`
2. Validate feed with: `uv run inboxcast validate-feed`
3. Submit RSS URL to Apple Podcasts Connect
4. All URLs must use HTTPS (Azure Blob Storage provides this automatically)

## Deployment on VPS

1. Install InboxCast on your VPS
2. Configure CloudFlare DNS: `podcast.yusizhang.com` → your VPS IP
3. Run web server: `uv run inboxcast serve --port 8000`
4. Configure reverse proxy (nginx) for HTTPS if needed

## Example Workflow

```bash
# Daily publishing workflow
uv run inboxcast publish --config config-publish.yaml --output out/

# On VPS (runs continuously)
uv run inboxcast serve --output-dir out/ --port 8000
```

This setup provides reliable podcast hosting with Azure's global CDN and your own RSS feed control.