"""FastAPI server for hosting RSS feeds and podcast metadata."""
import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import json


def create_app(output_dir: str = "out") -> FastAPI:
    """Create and configure FastAPI app."""

    app = FastAPI(
        title="InboxCast RSS Server",
        description="Hosts RSS feeds and podcast metadata for InboxCast",
        version="1.0.0"
    )

    # Add CORS middleware for podcast clients
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    output_path = Path(output_dir).resolve()

    @app.get("/")
    async def root():
        """Root endpoint with basic info."""
        return {
            "name": "InboxCast RSS Server",
            "version": "1.0.0",
            "endpoints": {
                "rss_feed": "/feed.xml",
                "episode_metadata": "/episode.json",
                "health": "/health"
            }
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        feed_exists = (output_path / "feed.xml").exists()
        episode_exists = (output_path / "episode.json").exists()

        return {
            "status": "healthy",
            "output_dir": str(output_path),
            "files": {
                "feed.xml": feed_exists,
                "episode.json": episode_exists
            }
        }

    @app.get("/feed.xml")
    async def get_rss_feed():
        """Serve the RSS feed XML file."""
        feed_path = output_path / "feed.xml"

        if not feed_path.exists():
            raise HTTPException(
                status_code=404,
                detail="RSS feed not found. Run 'inboxcast run' or 'inboxcast publish' first."
            )

        return FileResponse(
            path=str(feed_path),
            media_type="application/rss+xml",
            headers={
                "Cache-Control": "public, max-age=300",  # 5 minutes cache
                "Content-Type": "application/rss+xml; charset=utf-8"
            }
        )
    
    @app.head("/feed.xml")
    async def feed_head():
        # return headers only; FastAPI will omit body for HEAD
        return Response(headers={"Content-Type": "application/rss+xml"})

    @app.get("/episode.json")
    async def get_episode_metadata():
        """Serve episode metadata as JSON."""
        metadata_path = output_path / "episode.json"

        if not metadata_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Episode metadata not found. Run 'inboxcast run' or 'inboxcast publish' first."
            )

        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            return metadata
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=500,
                detail="Invalid episode metadata file"
            )

    @app.get("/episode/{filename}")
    async def get_episode_file(filename: str):
        """Serve episode audio files (if stored locally)."""
        # Security: only allow certain file extensions
        allowed_extensions = {'.mp3', '.wav', '.m4a', '.ogg'}
        file_path = output_path / filename

        if file_path.suffix.lower() not in allowed_extensions:
            raise HTTPException(status_code=400, detail="Invalid file type")

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Episode file not found")

        # Determine media type
        media_types = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.m4a': 'audio/mp4',
            '.ogg': 'audio/ogg'
        }
        media_type = media_types.get(file_path.suffix.lower(), 'audio/mpeg')

        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            headers={
                "Cache-Control": "public, max-age=86400",  # 24 hours cache
                "Accept-Ranges": "bytes"
            }
        )

    @app.get("/stats")
    async def get_stats():
        """Get basic statistics about the podcast."""
        try:
            metadata_path = output_path / "episode.json"
            if not metadata_path.exists():
                raise HTTPException(status_code=404, detail="No episode data found")

            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            return {
                "episode_date": metadata.get("episode_date"),
                "total_items": metadata.get("total_items", 0),
                "estimated_duration_ms": metadata.get("estimated_duration_ms", 0),
                "sources": metadata.get("sources", []),
                "chapters": len(metadata.get("chapters", []))
            }
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Invalid metadata")

    return app


# Create app instance for uvicorn
app = create_app(os.getenv("INBOXCAST_OUTPUT_DIR", "out"))