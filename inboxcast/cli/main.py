"""Main CLI interface for InboxCast."""
import click
from pathlib import Path
from datetime import datetime
from ..config import Config
from ..sources.rss import MultiRSSSource
from ..dedupe.simple import SimpleDeduplicator
from ..dedupe.semantic import SemanticDeduplicator
from ..summarize.engine import SimpleSummarizer
from ..summarize.openai_engine import OpenAISummarizer
from ..tts.espeak import EspeakProvider, DummyTTSProvider
from ..tts.minimax import MiniMaxProvider
from ..audio.stitch import SimpleAudioStitcher, ProfessionalAudioStitcher, SimpleEpisodeBuilder
from ..output.rss import RSSGenerator
from ..utils.script_parser import ScriptParser
from ..script.episode_engine import EpisodeScriptEngine
from ..cloud.azure import AzureBlobUploader

from ..config import load_dotenv_files
# Load environment variables from .env files
load_dotenv_files()


def _run_pipeline(cfg: Config, output_path: Path, target_minutes: int):
    """
    Run the complete InboxCast pipeline to generate episode files.

    Returns:
        tuple: (episode_path, planned_items, script_path) or (None, None, None) if failed
    """

    # Step 1: Fetch RSS content
    click.echo("📡 Fetching RSS feeds...")
    source = MultiRSSSource(cfg.rss_feeds, cfg.max_rss_items)
    raw_items = source.fetch()

    if not raw_items:
        click.echo("❌ No items fetched from RSS feeds")
        return None, None, None

    # Step 2: Deduplicate
    click.echo("🔄 Deduplicating content...")
    if cfg.processing.deduplicator == "semantic":
        cache_dir = output_path / "cache"
        deduplicator = SemanticDeduplicator(
            model_name=cfg.processing.embedding_model,
            similarity_threshold=cfg.processing.similarity_threshold,
            cache_dir=str(cache_dir),
            cache_days=cfg.processing.embedding_cache_days
        )
    else:
        deduplicator = SimpleDeduplicator()

    unique_items = deduplicator.deduplicate(raw_items)

    # Step 3: Summarize
    click.echo("✍️  Summarizing content...")
    if cfg.processing.summarizer == "openai":
        try:
            summarizer = OpenAISummarizer(
                model=cfg.processing.openai_model,
                max_words=cfg.processing.max_words,
                max_quote_words=cfg.processing.max_quote_words,
                temperature=cfg.processing.openai_temperature,
                use_content_cleaning=cfg.processing.use_readability,
                policy_checks=cfg.processing.policy_checks
            )
            click.echo(f"Using OpenAI summarizer ({cfg.processing.openai_model})")
        except Exception as e:
            click.echo(f"⚠️  OpenAI setup failed: {e}")
            click.echo("Falling back to simple summarizer")
            summarizer = SimpleSummarizer(max_words=cfg.processing.max_words)
    else:
        summarizer = SimpleSummarizer(max_words=cfg.processing.max_words)

    processed_items = []
    skipped_count = 0

    for item in unique_items:
        try:
            processed = summarizer.summarize(item)
            # Skip items that were filtered out by policy guards
            if processed.word_count > 0:  # Non-empty script means not skipped
                processed_items.append(processed)
            else:
                skipped_count += 1
                click.echo(f"⚠️  Skipped '{item.title}': {processed.notes.get('skip_reason', 'unknown')}")
        except Exception as e:
            click.echo(f"⚠️  Failed to summarize {item.title}: {e}")
            skipped_count += 1

    if not processed_items:
        click.echo("❌ No items successfully processed")
        return None, None, None

    if skipped_count > 0:
        click.echo(f"📋 Processed {len(processed_items)} items, skipped {skipped_count}")

    # Step 4: Plan episode duration
    click.echo("⏱️  Planning episode duration...")
    episode_builder = SimpleEpisodeBuilder(target_minutes)
    planned_items = episode_builder.fit(processed_items, target_minutes)

    # Step 4.5: Generate cohesive episode script
    click.echo("📝 Generating cohesive episode script...")
    episode_script = None
    try:
        episode_engine = EpisodeScriptEngine(
            model=cfg.processing.openai_model if hasattr(cfg.processing, 'openai_model') else "gpt-4o-mini"
        )

        episode_date = datetime.now().strftime('%Y-%m-%d')
        episode_script = episode_engine.synthesize_episode(
            planned_items,
            target_minutes,
            episode_date
        )

        # Write enhanced episode script
        script_path = output_path / "episode_script.txt"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(f"InboxCast Episode Script - {episode_date}\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Target Duration: {target_minutes} minutes\n")
            f.write(f"Estimated Duration: {episode_script.estimated_duration_minutes:.1f} minutes\n")
            f.write(f"Total Words: {episode_script.total_word_count}\n")
            f.write("=" * 60 + "\n\n")

            # Write introduction
            f.write("INTRODUCTION:\n")
            f.write(f"{episode_script.introduction}\n\n")

            # Write each segment
            for i, segment in enumerate(episode_script.segments, 1):
                f.write(f"SEGMENT {i}: {segment.theme_title}\n")
                f.write(f"Transition: {segment.transition}\n")
                f.write(f"Words: {segment.word_count}\n\n")

                for j, item in enumerate(segment.items, 1):
                    f.write(f"  {i}.{j} {item.title}\n")
                    f.write(f"      Script: {item.script}\n\n")

            # Write conclusion
            f.write("CONCLUSION:\n")
            f.write(f"{episode_script.conclusion}\n")

        click.echo(f"✅ Generated cohesive episode ({episode_script.estimated_duration_minutes:.1f} min, {episode_script.total_word_count} words)")

    except Exception as e:
        click.echo(f"⚠️  Episode script synthesis failed: {e}")
        click.echo("Falling back to simple script generation...")

        # Fallback to simple script generation
        script_path = output_path / "episode_script.txt"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(f"InboxCast Episode Script - {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write("=" * 60 + "\n\n")
            for i, item in enumerate(planned_items, 1):
                f.write(f"{i}. Title: {item.title}\n")
                f.write(f"   Words: {item.word_count}\n")
                f.write(f"   Script: {item.script}\n\n")

        # Set episode_script to None so we know to use simple approach for TTS
        episode_script = None

    # Step 5: Generate audio
    click.echo("🗣️  Generating audio...")

    # Choose TTS provider based on config with fallback chain: MiniMax → espeak → dummy
    tts_provider = None

    if cfg.voice_settings.provider == "minimax":
        try:
            tts_provider = MiniMaxProvider()
            if tts_provider.test_connection():
                click.echo("✅ Using MiniMax TTS provider")
            else:
                click.echo("⚠️  MiniMax connection failed, falling back to espeak")
                tts_provider = None
        except Exception as e:
            click.echo(f"⚠️  MiniMax setup failed: {e}, falling back to espeak")

    if not tts_provider:
        if cfg.voice_settings.provider == "dummy":
            click.echo("Using dummy TTS provider")
            tts_provider = DummyTTSProvider()
        else:
            # Try espeak, fallback to dummy
            try:
                tts_provider = EspeakProvider()
                click.echo("✅ Using espeak TTS provider")
            except:
                click.echo("⚠️  Espeak not available, using dummy TTS")
                tts_provider = DummyTTSProvider()

    audio_segments = []
    titles = []

    # Generate audio based on whether we have episode script or fallback to simple
    if episode_script is not None:
        # Use structured episode script for TTS
        click.echo(f"🎯 Generating cohesive episode audio ({len(episode_script.segments)} segments)")

        # Generate introduction audio
        try:
            if isinstance(tts_provider, MiniMaxProvider):
                intro_audio = tts_provider.synthesize(
                    episode_script.introduction,
                    voice=cfg.voice_settings.voice_id,
                    wpm=cfg.voice_settings.wpm,
                    speed=cfg.voice_settings.speed,
                    vol=cfg.voice_settings.vol,
                    pitch=cfg.voice_settings.pitch
                )
            else:
                intro_audio = tts_provider.synthesize(
                    episode_script.introduction,
                    voice=cfg.voice_settings.voice_id,
                    wpm=cfg.voice_settings.wpm
                )
            if intro_audio:
                audio_segments.append(intro_audio)
                titles.append("Introduction")
        except Exception as e:
            click.echo(f"⚠️  TTS failed for introduction: {e}")

        # Generate audio for each segment
        for segment in episode_script.segments:
            # Generate transition audio
            if segment.transition.strip():
                try:
                    if isinstance(tts_provider, MiniMaxProvider):
                        transition_audio = tts_provider.synthesize(
                            segment.transition,
                            voice=cfg.voice_settings.voice_id,
                            wpm=cfg.voice_settings.wpm,
                            speed=cfg.voice_settings.speed,
                            vol=cfg.voice_settings.vol,
                            pitch=cfg.voice_settings.pitch
                        )
                    else:
                        transition_audio = tts_provider.synthesize(
                            segment.transition,
                            voice=cfg.voice_settings.voice_id,
                            wpm=cfg.voice_settings.wpm
                        )
                    if transition_audio:
                        audio_segments.append(transition_audio)
                        titles.append(f"Transition: {segment.theme_title}")
                except Exception as e:
                    click.echo(f"⚠️  TTS failed for {segment.theme_title} transition: {e}")

            # Generate audio for each item in segment
            for item in segment.items:
                try:
                    if isinstance(tts_provider, MiniMaxProvider):
                        item_audio = tts_provider.synthesize(
                            item.script,
                            voice=cfg.voice_settings.voice_id,
                            wpm=cfg.voice_settings.wpm,
                            speed=cfg.voice_settings.speed,
                            vol=cfg.voice_settings.vol,
                            pitch=cfg.voice_settings.pitch
                        )
                    else:
                        item_audio = tts_provider.synthesize(
                            item.script,
                            voice=cfg.voice_settings.voice_id,
                            wpm=cfg.voice_settings.wpm
                        )
                    if item_audio:
                        audio_segments.append(item_audio)
                        titles.append(item.title)
                except Exception as e:
                    click.echo(f"⚠️  TTS failed for {item.title}: {e}")

        # Generate conclusion audio
        try:
            if isinstance(tts_provider, MiniMaxProvider):
                conclusion_audio = tts_provider.synthesize(
                    episode_script.conclusion,
                    voice=cfg.voice_settings.voice_id,
                    wpm=cfg.voice_settings.wpm,
                    speed=cfg.voice_settings.speed,
                    vol=cfg.voice_settings.vol,
                    pitch=cfg.voice_settings.pitch
                )
            else:
                conclusion_audio = tts_provider.synthesize(
                    episode_script.conclusion,
                    voice=cfg.voice_settings.voice_id,
                    wpm=cfg.voice_settings.wpm
                )
            if conclusion_audio:
                audio_segments.append(conclusion_audio)
                titles.append("Conclusion")
        except Exception as e:
            click.echo(f"⚠️  TTS failed for conclusion: {e}")

    else:
        # Fallback: Use simple item-by-item approach
        click.echo(f"🔄 Generating simple episode audio ({len(planned_items)} items)")
        for item in planned_items:
            try:
                # Pass MiniMax-specific parameters if using MiniMax provider
                if isinstance(tts_provider, MiniMaxProvider):
                    audio_data = tts_provider.synthesize(
                        item.script,
                        voice=cfg.voice_settings.voice_id,
                        wpm=cfg.voice_settings.wpm,
                        speed=cfg.voice_settings.speed,
                        vol=cfg.voice_settings.vol,
                        pitch=cfg.voice_settings.pitch
                    )
                else:
                    audio_data = tts_provider.synthesize(
                        item.script,
                        voice=cfg.voice_settings.voice_id,
                        wpm=cfg.voice_settings.wpm
                    )
                if audio_data:
                    audio_segments.append(audio_data)
                    titles.append(item.title)
            except Exception as e:
                click.echo(f"⚠️  TTS failed for {item.title}: {e}")

    if not audio_segments:
        click.echo("❌ No audio generated")
        return None, None, None

    # Step 6: Stitch audio
    click.echo("🎵 Stitching audio segments...")
    if cfg.audio.use_professional_stitcher:
        stitcher = ProfessionalAudioStitcher(
            gap_ms=cfg.audio.gap_ms,
            fade_ms=cfg.audio.fade_ms,
            target_lufs=cfg.audio.target_lufs,
            output_format=cfg.output.audio_format
        )
    else:
        stitcher = SimpleAudioStitcher(gap_ms=cfg.audio.gap_ms)

    combined_audio = stitcher.stitch(audio_segments, titles)

    # Export audio in configured format
    episode_path = output_path / cfg.output.episode_filename

    if cfg.output.audio_format.lower() == "mp3" and hasattr(stitcher, 'export_mp3'):
        try:
            stitcher.export_mp3(combined_audio, str(episode_path), bitrate=cfg.output.bitrate)
        except Exception as e:
            click.echo(f"⚠️  MP3 export failed: {e}, falling back to WAV")
            episode_path = episode_path.with_suffix('.wav')
            stitcher.export_wav(combined_audio, str(episode_path))
    else:
        # Default to WAV export
        if episode_path.suffix.lower() != '.wav':
            episode_path = episode_path.with_suffix('.wav')
        stitcher.export_wav(combined_audio, str(episode_path))

    # Step 7: Generate RSS feed
    click.echo("📻 Generating RSS feed...")
    rss_generator = RSSGenerator()
    rss_generator.write_files(str(output_path), cfg.output.episode_filename, planned_items)

    return episode_path, planned_items, script_path


@click.group()
def cli():
    """InboxCast - AI newsletter summarization to private audio podcasts."""
    pass


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Configuration file')
@click.option('--output', '-o', default='out', help='Output directory')
@click.option('--minutes', '-m', type=int, help='Target duration in minutes')
def run(config, output, minutes):
    """Run the complete pipeline to generate an episode."""

    try:
        # Load configuration
        cfg = Config.load(config)
        target_minutes = minutes or cfg.target_duration

        click.echo(f"🎙️  Starting InboxCast pipeline (target: {target_minutes} minutes)")

        # Create output directory
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)

        # Run the complete pipeline
        episode_path, planned_items, script_path = _run_pipeline(cfg, output_path, target_minutes)

        if episode_path is None:
            return  # Pipeline failed, error already logged

        # Summary
        total_items = len(planned_items)
        total_words = sum(item.word_count for item in planned_items)

        click.echo("✅ Pipeline completed!")
        click.echo(f"   📊 {total_items} items, {total_words} words")
        click.echo(f"   🎧 Episode: {episode_path}")
        click.echo(f"   📡 RSS feed: {output_path / 'feed.xml'}")
        click.echo(f"   📋 Metadata: {output_path / 'episode.json'}")
        click.echo(f"   📝 Script: {script_path}")

    except Exception as e:
        click.echo(f"❌ Pipeline failed: {e}")
        raise


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Configuration file')
@click.option('--output-dir', '-o', default='out', help='Output directory to upload')
def upload(config, output_dir):
    """Upload existing episode files to Azure Blob Storage."""

    try:
        # Load configuration
        cfg = Config.load(config)
        output_path = Path(output_dir)

        if not output_path.exists():
            click.echo(f"❌ Output directory not found: {output_dir}")
            return

        # Check for Azure configuration
        if not cfg.publishing.azure.connection_string:
            click.echo("❌ Azure connection string not configured")
            click.echo("   Please set azure.connection_string in config.yaml or AZURE_STORAGE_CONNECTION_STRING environment variable")
            return

        click.echo(f"☁️  Uploading files from {output_dir} to Azure...")

        # Initialize Azure uploader
        uploader = AzureBlobUploader(
            connection_string=cfg.publishing.azure.connection_string,
            container_name=cfg.publishing.azure.container_name
        )

        # Test connection
        if not uploader.test_connection():
            click.echo("❌ Failed to connect to Azure Blob Storage")
            return

        click.echo("✅ Connected to Azure Blob Storage")

        # Find episode file
        episode_file = output_path / cfg.output.episode_filename
        if not episode_file.exists():
            click.echo(f"❌ Episode file not found: {episode_file}")
            return

        # Upload episode file
        click.echo(f"📤 Uploading {episode_file.name}...")
        episode_url = uploader.upload_file(str(episode_file))
        click.echo(f"✅ Uploaded episode: {episode_url}")

        # Get file size for RSS
        blob_name = f"{datetime.now().strftime('%Y-%m-%d')}/{episode_file.name}"
        file_size = uploader.get_file_size(blob_name)

        # Update RSS feed with Azure URL
        click.echo("📻 Updating RSS feed with Azure URLs...")

        # Load existing metadata
        metadata_file = output_path / "episode.json"
        if metadata_file.exists():
            import json
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            # Use existing items from metadata for RSS generation
            from ..types import ProcessedItem
            items = []
            for chapter in metadata.get('chapters', []):
                item = ProcessedItem(
                    title=chapter.get('title', 'Untitled'),
                    url='',
                    script='',
                    word_count=0,
                    summary='',
                    sources=[],
                    notes={}
                )
                items.append(item)
        else:
            click.echo("⚠️  No metadata file found, creating minimal RSS")
            items = []

        # Generate RSS with Azure URLs
        rss_generator = RSSGenerator(base_url=cfg.publishing.rss_base_url)
        rss_generator.write_files(
            str(output_path),
            cfg.output.episode_filename,
            items,
            episode_url=episode_url,
            file_size=file_size
        )

        click.echo("✅ Upload completed!")
        click.echo(f"   📊 Episode URL: {episode_url}")
        click.echo(f"   📡 RSS feed: {output_path / 'feed.xml'}")
        if file_size:
            click.echo(f"   📏 File size: {file_size:,} bytes")

    except Exception as e:
        click.echo(f"❌ Upload failed: {e}")
        raise


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Configuration file')
@click.option('--output', '-o', default='out', help='Output directory')
@click.option('--minutes', '-m', type=int, help='Target duration in minutes')
def publish(config, output, minutes):
    """Run the complete pipeline and upload to Azure Blob Storage."""

    try:
        # Load configuration
        cfg = Config.load(config)

        # Check for Azure configuration
        if not cfg.publishing.azure.connection_string:
            click.echo("❌ Azure connection string not configured")
            click.echo("   Please set azure.connection_string in config.yaml or AZURE_STORAGE_CONNECTION_STRING environment variable")
            return

        click.echo("🚀 Starting publish pipeline (generate + upload)...")

        target_minutes = minutes or cfg.target_duration

        click.echo(f"🎙️  Starting InboxCast pipeline (target: {target_minutes} minutes)")

        # Create output directory
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)

        # Run the complete pipeline to generate all files
        episode_path, planned_items, script_path = _run_pipeline(cfg, output_path, target_minutes)

        if episode_path is None:
            return  # Pipeline failed, error already logged

        # After successful generation, upload to Azure
        click.echo("☁️  Uploading to Azure Blob Storage...")

        # Initialize Azure uploader
        uploader = AzureBlobUploader(
            connection_string=cfg.publishing.azure.connection_string,
            container_name=cfg.publishing.azure.container_name
        )

        # Test connection
        if not uploader.test_connection():
            click.echo("❌ Failed to connect to Azure Blob Storage")
            return

        click.echo("✅ Connected to Azure Blob Storage")

        # Upload episode file
        click.echo(f"📤 Uploading {episode_path.name}...")
        episode_url = uploader.upload_file(str(episode_path))
        click.echo(f"✅ Uploaded episode: {episode_url}")

        # Get file size for RSS
        blob_name = f"{datetime.now().strftime('%Y-%m-%d')}/{episode_path.name}"
        file_size = uploader.get_file_size(blob_name)

        # Generate RSS with Azure URLs
        click.echo("📻 Updating RSS feed with Azure URLs...")
        rss_generator = RSSGenerator(base_url=cfg.publishing.rss_base_url)
        rss_generator.write_files(
            str(output_path),
            cfg.output.episode_filename,
            planned_items,
            episode_url=episode_url,
            file_size=file_size
        )

        # Summary
        total_items = len(planned_items)
        total_words = sum(item.word_count for item in planned_items)

        click.echo("✅ Publish completed!")
        click.echo(f"   📊 {total_items} items, {total_words} words published")
        click.echo(f"   🎧 Episode URL: {episode_url}")
        click.echo(f"   📡 RSS feed: {output_path / 'feed.xml'}")
        click.echo(f"   📋 Metadata: {output_path / 'episode.json'}")
        click.echo(f"   📝 Script: {script_path}")
        if file_size:
            click.echo(f"   📏 File size: {file_size:,} bytes")

    except Exception as e:
        click.echo(f"❌ Publish failed: {e}")
        raise


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Configuration file')
def fetch(config):
    """Fetch and display RSS items."""
    
    cfg = Config.load(config)
    source = MultiRSSSource(cfg.rss_feeds)
    items = source.fetch()
    
    deduplicator = SimpleDeduplicator()
    unique_items = deduplicator.deduplicate(items)
    
    click.echo(f"\\nFetched {len(unique_items)} unique items:\\n")
    
    for i, item in enumerate(unique_items, 1):
        click.echo(f"{i}. {item.title}")
        click.echo(f"   Source: {item.source_name}")
        click.echo(f"   URL: {item.url}")
        click.echo(f"   Content: {item.content[:100]}...")
        click.echo()


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Configuration file') 
def validate(config):
    """Validate configuration file and show settings."""
    try:
        cfg = Config.load(config)
        click.echo(f"✅ Configuration valid: {config}")
        click.echo(f"   📡 RSS feeds: {len(cfg.rss_feeds)}")
        click.echo(f"   🔄 Deduplicator: {cfg.processing.deduplicator}")
        click.echo(f"   ✍️  Summarizer: {cfg.processing.summarizer}")
        click.echo(f"   ⏱️  Target duration: {cfg.target_duration} minutes")
        
        # Check OpenAI setup if using OpenAI
        if cfg.processing.summarizer == "openai":
            import os
            from ..config import load_dotenv_files
            
            # Load environment variables from .env files
            load_dotenv_files()
            
            if not os.getenv("OPENAI_API_KEY"):
                click.echo("⚠️  OPENAI_API_KEY not set in environment")
            else:
                click.echo("✅ OpenAI API key found")
        
    except Exception as e:
        click.echo(f"❌ Configuration error: {e}")
        return 1


@cli.command() 
@click.option('--config', '-c', default='config.yaml', help='Configuration file')
@click.option('--minutes', '-m', type=int, help='Target duration in minutes')
def plan(config, minutes):
    """Plan episode without generating audio."""
    
    cfg = Config.load(config)
    target_minutes = minutes or cfg.target_duration
    
    # Fetch and process content
    source = MultiRSSSource(feed_configs=cfg.rss_feeds, 
                            max_items_per_feed=cfg.max_rss_items)
    raw_items = source.fetch()
    
    # Use configured deduplicator
    if cfg.processing.deduplicator == "semantic":
        cache_dir = Path("out") / "cache"
        deduplicator = SemanticDeduplicator(
            model_name=cfg.processing.embedding_model,
            similarity_threshold=cfg.processing.similarity_threshold,
            cache_dir=str(cache_dir),
            cache_days=cfg.processing.embedding_cache_days
        )
    else:
        deduplicator = SimpleDeduplicator()
    
    unique_items = deduplicator.deduplicate(raw_items)
    
    # Use configured summarizer
    if cfg.processing.summarizer == "openai":
        try:
            summarizer = OpenAISummarizer(
                model=cfg.processing.openai_model,
                max_words=cfg.processing.max_words,
                max_quote_words=cfg.processing.max_quote_words,
                temperature=cfg.processing.openai_temperature,
                use_content_cleaning=cfg.processing.use_readability
            )
        except Exception as e:
            click.echo(f"⚠️  OpenAI setup failed: {e}")
            click.echo("Falling back to simple summarizer")
            summarizer = SimpleSummarizer(max_words=cfg.processing.max_words)
    else:
        summarizer = SimpleSummarizer(max_words=cfg.processing.max_words)
    
    processed_items = []
    for item in unique_items:
        try:
            processed = summarizer.summarize(item)
            if processed.word_count > 0:  # Skip filtered items
                processed_items.append(processed)
        except Exception as e:
            click.echo(f"⚠️  Failed to summarize {item.title}: {e}")
    
    # Plan episode
    episode_builder = SimpleEpisodeBuilder(target_minutes)
    planned_items = episode_builder.fit(processed_items, target_minutes)
    
    # Display plan
    click.echo(f"\\n📋 Episode Plan ({target_minutes} minutes target):\\n")
    
    total_words = 0
    for i, item in enumerate(planned_items, 1):
        click.echo(f"{i}. {item.title}")
        click.echo(f"   Words: {item.word_count}")
        click.echo(f"   Script: {item.script[:100]}...")
        click.echo()
        total_words += item.word_count
    
    estimated_minutes = total_words / 165
    click.echo(f"📊 Total: {len(planned_items)} items, {total_words} words")
    click.echo(f"⏱️  Estimated duration: {estimated_minutes:.1f} minutes")
    
    # Save full script to file for inspection
    script_path = Path("out") / "episode_script.txt"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(f"InboxCast Episode Script - {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write("=" * 60 + "\n\n")
        for i, item in enumerate(planned_items, 1):
            f.write(f"{i}. {item.title}\n")
            f.write(f"   Words: {item.word_count}\n")
            f.write(f"   Script: {item.script}\n\n")
    click.echo(f"📝 Full script saved to: {script_path}")


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Configuration file')
@click.option('--output', '-o', default='out', help='Output directory')
@click.option('--script-path', '-s', help='Path to episode script file (overrides config-based path)')
@click.option('--provider', '-p', help='TTS provider override (minimax, espeak, dummy)')
def tts(config, output, script_path, provider):
    """Generate audio from saved episode script without running LLM pipeline."""
    
    try:
        # Load configuration
        cfg = Config.load(config)
        output_path = Path(output)
        
        click.echo("🗣️  Running TTS-only pipeline...")
        
        # Find script file
        if script_path:
            script_file = script_path
        else:
            # Look for script in output directory
            parser = ScriptParser()
            script_file = parser.find_script_file(str(output_path))
            
        if not script_file:
            click.echo("❌ No script file found. Run 'inboxcast run' first or specify --script-path")
            return
            
        click.echo(f"📖 Reading script from: {script_file}")
        
        # Parse script file
        parser = ScriptParser()
        planned_items = parser.parse_script_file(script_file)
        
        if not planned_items:
            click.echo("❌ No items found in script file")
            return
            
        click.echo(f"📋 Found {len(planned_items)} items in script")
        
        # Create output directory
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Choose TTS provider
        tts_provider = None
        provider_name = provider or cfg.voice_settings.provider
        
        if provider_name == "minimax":
            try:
                tts_provider = MiniMaxProvider()
                if not tts_provider.test_connection():
                    click.echo("⚠️  MiniMax connection failed, falling back to espeak")
                    tts_provider = None
                else:
                    click.echo("✅ Using MiniMax TTS provider")
            except Exception as e:
                click.echo(f"⚠️  MiniMax setup failed: {e}, falling back to espeak")
        
        if not tts_provider:
            if provider_name == "dummy" or (not provider_name and cfg.voice_settings.provider == "dummy"):
                click.echo("Using dummy TTS provider")
                tts_provider = DummyTTSProvider()
            else:
                # Try espeak, fallback to dummy
                try:
                    tts_provider = EspeakProvider()
                    click.echo("✅ Using espeak TTS provider")
                except:
                    click.echo("⚠️  Espeak not available, using dummy TTS")
                    tts_provider = DummyTTSProvider()
        
        # Generate audio for each item
        audio_segments = []
        titles = []
        
        for i, item in enumerate(planned_items, 1):
            click.echo(f"🔊 Processing item {i}/{len(planned_items)}: {item.title[:50]}...")
            
            try:
                # Pass MiniMax-specific parameters if using MiniMax provider
                if isinstance(tts_provider, MiniMaxProvider):
                    audio_data = tts_provider.synthesize(
                        item.script,
                        voice=cfg.voice_settings.voice_id,
                        wpm=cfg.voice_settings.wpm,
                        speed=cfg.voice_settings.speed,
                        vol=cfg.voice_settings.vol,
                        pitch=cfg.voice_settings.pitch
                    )
                else:
                    audio_data = tts_provider.synthesize(
                        item.script,
                        voice=cfg.voice_settings.voice_id,
                        wpm=cfg.voice_settings.wpm
                    )
                if audio_data:
                    audio_segments.append(audio_data)
                    titles.append(item.title)
                    click.echo(f"✅ Generated audio for: {item.title[:50]}...")
                else:
                    click.echo(f"⚠️  No audio generated for: {item.title[:50]}...")
            except Exception as e:
                click.echo(f"⚠️  TTS failed for {item.title[:50]}...: {e}")
        
        if not audio_segments:
            click.echo("❌ No audio generated")
            return
        
        # Stitch audio segments
        click.echo("🎵 Stitching audio segments...")
        if cfg.audio.use_professional_stitcher:
            stitcher = ProfessionalAudioStitcher(
                gap_ms=cfg.audio.gap_ms,
                fade_ms=cfg.audio.fade_ms,
                target_lufs=cfg.audio.target_lufs,
                output_format=cfg.output.audio_format
            )
        else:
            stitcher = SimpleAudioStitcher(gap_ms=cfg.audio.gap_ms)
        
        combined_audio = stitcher.stitch(audio_segments, titles)
        
        # Export audio in configured format
        episode_path = output_path / cfg.output.episode_filename
        
        if cfg.output.audio_format.lower() == "mp3" and hasattr(stitcher, 'export_mp3'):
            try:
                stitcher.export_mp3(combined_audio, str(episode_path), bitrate=cfg.output.bitrate)
            except Exception as e:
                click.echo(f"⚠️  MP3 export failed: {e}, falling back to WAV")
                episode_path = episode_path.with_suffix('.wav')
                stitcher.export_wav(combined_audio, str(episode_path))
        else:
            # Default to WAV export
            if episode_path.suffix.lower() != '.wav':
                episode_path = episode_path.with_suffix('.wav')
            stitcher.export_wav(combined_audio, str(episode_path))
        
        # Generate RSS feed using existing planned items
        click.echo("📻 Generating RSS feed...")
        rss_generator = RSSGenerator()
        rss_generator.write_files(str(output_path), cfg.output.episode_filename, planned_items)
        
        # Summary
        total_items = len(audio_segments)
        total_words = sum(item.word_count for item in planned_items[:total_items])
        
        click.echo("✅ TTS pipeline completed!")
        click.echo(f"   📊 {total_items} items, {total_words} words")
        click.echo(f"   🎧 Episode: {episode_path}")
        click.echo(f"   📡 RSS feed: {output_path / 'feed.xml'}")
        click.echo(f"   📋 Metadata: {output_path / 'episode.json'}")
        
    except Exception as e:
        click.echo(f"❌ TTS pipeline failed: {e}")
        raise


@cli.command()
@click.option('--output-dir', '-o', default='out', help='Output directory containing RSS feed')
@click.option('--port', '-p', default=8000, help='Port to run the server on')
@click.option('--host', default='0.0.0.0', help='Host to bind the server to')
def serve(output_dir, port, host):
    """Start web server to host RSS feed."""

    try:
        import uvicorn
        from ..server.app import create_app
    except ImportError:
        click.echo("❌ FastAPI/uvicorn not installed. Install with: uv add fastapi uvicorn")
        return

    output_path = Path(output_dir)
    if not output_path.exists():
        click.echo(f"❌ Output directory not found: {output_dir}")
        return

    # Check if feed exists
    feed_path = output_path / "feed.xml"
    if not feed_path.exists():
        click.echo(f"⚠️  RSS feed not found at {feed_path}")
        click.echo("   Run 'inboxcast run' or 'inboxcast publish' first to generate content")
        click.echo("   Server will start anyway for health checks")

    click.echo(f"🌐 Starting RSS server...")
    click.echo(f"   📁 Serving from: {output_path.resolve()}")
    click.echo(f"   🌍 URL: http://{host}:{port}")
    click.echo(f"   📡 RSS feed: http://{host}:{port}/feed.xml")
    click.echo(f"   ❤️  Health check: http://{host}:{port}/health")
    click.echo("")
    click.echo("Press Ctrl+C to stop the server")

    # Create app with the specified output directory
    app = create_app(str(output_path))

    # Set environment variable for the app
    import os
    os.environ["INBOXCAST_OUTPUT_DIR"] = str(output_path)

    # Run server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Configuration file')
@click.option('--output-dir', '-o', default='out', help='Output directory to validate')
def validate_feed(config, output_dir):
    """Validate RSS feed compliance and Azure connectivity."""

    try:
        # Load configuration
        cfg = Config.load(config)
        output_path = Path(output_dir)

        click.echo("🔍 Validating RSS feed and configuration...")

        # Check output directory
        if not output_path.exists():
            click.echo(f"❌ Output directory not found: {output_dir}")
            return

        # Check RSS feed
        feed_path = output_path / "feed.xml"
        if not feed_path.exists():
            click.echo(f"❌ RSS feed not found: {feed_path}")
            click.echo("   Run 'inboxcast run' first to generate feed")
            return

        click.echo(f"✅ RSS feed found: {feed_path}")

        # Basic RSS validation
        try:
            with open(feed_path, 'r', encoding='utf-8') as f:
                rss_content = f.read()

            # Check for required RSS elements
            required_elements = ['<rss', '<channel>', '<title>', '<description>', '<item>', '<enclosure']
            missing_elements = [elem for elem in required_elements if elem not in rss_content]

            if missing_elements:
                click.echo(f"⚠️  RSS validation warnings: Missing elements: {missing_elements}")
            else:
                click.echo("✅ RSS feed structure looks valid")

            # Check for HTTPS URLs (required by Apple Podcasts)
            if 'http://' in rss_content and 'https://' not in rss_content:
                click.echo("⚠️  RSS feed contains HTTP URLs - Apple Podcasts requires HTTPS")

        except Exception as e:
            click.echo(f"❌ RSS validation failed: {e}")

        # Check episode metadata
        metadata_path = output_path / "episode.json"
        if metadata_path.exists():
            click.echo(f"✅ Episode metadata found: {metadata_path}")
        else:
            click.echo(f"⚠️  Episode metadata not found: {metadata_path}")

        # Check Azure configuration if provided
        if cfg.publishing.azure.connection_string:
            click.echo("🔍 Testing Azure connectivity...")
            try:
                uploader = AzureBlobUploader(
                    connection_string=cfg.publishing.azure.connection_string,
                    container_name=cfg.publishing.azure.container_name
                )
                if uploader.test_connection():
                    click.echo("✅ Azure Blob Storage connection successful")
                else:
                    click.echo("❌ Azure Blob Storage connection failed")
            except Exception as e:
                click.echo(f"❌ Azure test failed: {e}")
        else:
            click.echo("⚠️  Azure configuration not found - upload commands will not work")

        click.echo("🎉 Validation completed!")

    except Exception as e:
        click.echo(f"❌ Validation failed: {e}")
        raise


@cli.command()
@click.option('--config', '-c', default='config.yaml', help='Configuration file')
def test_upload(config):
    """Test Azure Blob Storage connectivity without uploading files."""

    try:
        # Load configuration
        cfg = Config.load(config)

        # Check for Azure configuration
        if not cfg.publishing.azure.connection_string:
            click.echo("❌ Azure connection string not configured")
            click.echo("   Please set azure.connection_string in config.yaml or AZURE_STORAGE_CONNECTION_STRING environment variable")
            return

        click.echo("🔍 Testing Azure Blob Storage connectivity...")

        # Initialize Azure uploader
        uploader = AzureBlobUploader(
            connection_string=cfg.publishing.azure.connection_string,
            container_name=cfg.publishing.azure.container_name
        )

        # Test connection
        if uploader.test_connection():
            click.echo("✅ Azure Blob Storage connection successful")

            # List existing blobs as additional test
            blobs = uploader.list_blobs()
            if blobs:
                click.echo(f"📁 Found {len(blobs)} existing files in container:")
                for blob in blobs[:5]:  # Show first 5
                    click.echo(f"   - {blob}")
                if len(blobs) > 5:
                    click.echo(f"   ... and {len(blobs) - 5} more files")
            else:
                click.echo("📁 Container is empty")

            click.echo(f"🏷️  Container: {cfg.publishing.azure.container_name}")
            click.echo("🎉 Upload connectivity test passed!")
        else:
            click.echo("❌ Azure Blob Storage connection failed")
            click.echo("   Check your connection string and container name")

    except Exception as e:
        click.echo(f"❌ Upload test failed: {e}")
        raise


if __name__ == '__main__':
    cli()