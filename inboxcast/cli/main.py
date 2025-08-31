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

from ..config import load_dotenv_files
# Load environment variables from .env files
load_dotenv_files()

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
        
        # Step 1: Fetch RSS content
        click.echo("📡 Fetching RSS feeds...")
        source = MultiRSSSource(cfg.rss_feeds, cfg.max_rss_items)
        raw_items = source.fetch()
        
        if not raw_items:
            click.echo("❌ No items fetched from RSS feeds")
            return
        
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
            return
        
        if skipped_count > 0:
            click.echo(f"📋 Processed {len(processed_items)} items, skipped {skipped_count}")
        
        # Step 4: Plan episode duration
        click.echo("⏱️  Planning episode duration...")
        episode_builder = SimpleEpisodeBuilder(target_minutes)
        planned_items = episode_builder.fit(processed_items, target_minutes)
        
        # Step 4.5: Generate episode script (early so TTS command can use it)
        click.echo("📝 Generating episode script...")
        script_path = output_path / "episode_script.txt"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(f"InboxCast Episode Script - {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write("=" * 60 + "\n\n")
            for i, item in enumerate(planned_items, 1):
                f.write(f"{i}. Title: {item.title}\n")
                f.write(f"   Words: {item.word_count}\n")
                f.write(f"   Script: {item.script}\n\n")
        
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
            return
        
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
    source = MultiRSSSource(cfg.rss_feeds)
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


if __name__ == '__main__':
    cli()