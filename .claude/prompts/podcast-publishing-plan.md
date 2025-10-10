# InboxCast Podcast Publishing Implementation Plan

## Phase 1: Azure Blob Storage Integration

1. **Add Azure dependencies** to `pyproject.toml`
   - `azure-storage-blob`
   - `azure-identity` (for authentication)

2. **Create Azure upload module** (`inboxcast/cloud/azure.py`)
   - `AzureBlobUploader` class with upload/delete methods
   - Support for both storage account key and managed identity auth
   - Generate public URLs for uploaded files

3. **Update configuration** (`config.yaml` and `config.py`)
   - Add Azure storage settings (account, container, connection string)
   - Add production base URLs for RSS feeds

## Phase 2: CLI Commands (Simplified Structure)

1. **Keep `run` command unchanged**
   - Only generates files locally (no upload)
   - Current behavior preserved

2. **Create `upload` command** in `cli/main.py`
   - Takes output directory and uploads to Azure
   - `uv run inboxcast upload --output-dir out/`
   - Updates RSS feed with Azure URLs after upload
   - Standalone command for existing output

3. **Create `publish` command** in `cli/main.py`
   - End-to-end: runs pipeline + uploads to Azure
   - `uv run inboxcast publish --config config.yaml --output out/`
   - Combines `run` + `upload` in single command

## Phase 3: Production RSS and Web Server

1. **Update RSSGenerator** (`output/rss.py`)
   - Support for Azure Blob URLs in episode enclosures
   - Production-ready base URLs from config
   - Proper MIME types and file sizes

2. **Create simple FastAPI server** (`server/app.py`)
   - Serve `feed.xml` from output directory
   - Support for health checks
   - CORS headers for podcast clients
   - `uv run inboxcast serve --port 8000 --output-dir out/`

## Phase 4: Deployment Support

1. **Add validation commands**
   - `uv run inboxcast validate-feed` - Test RSS compliance
   - `uv run inboxcast test-upload` - Test Azure connectivity

## CLI Command Summary

- `uv run inboxcast run` - Generate files locally (unchanged)
- `uv run inboxcast upload --output-dir out/` - Upload existing files to Azure
- `uv run inboxcast publish` - Generate + upload in one command
- `uv run inboxcast serve` - Host RSS feed on VPS

This keeps the existing workflow intact while adding cloud publishing capabilities.