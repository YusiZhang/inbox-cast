"""Main CLI interface for InboxCast."""
import click
from pathlib import Path
from ..config import Config
from ..sources.rss import MultiRSSSource
from ..dedupe.simple import SimpleDeduplicator  
from ..summarize.engine import SimpleSummarizer
from ..tts.espeak import EspeakProvider, DummyTTSProvider
from ..audio.stitch import SimpleAudioStitcher, SimpleEpisodeBuilder
from ..output.rss import RSSGenerator


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
        source = MultiRSSSource(cfg.rss_feeds)
        raw_items = source.fetch()
        
        if not raw_items:
            click.echo("❌ No items fetched from RSS feeds")
            return
        
        # Step 2: Deduplicate
        click.echo("🔄 Deduplicating content...")
        deduplicator = SimpleDeduplicator()
        unique_items = deduplicator.deduplicate(raw_items)
        
        # Step 3: Summarize
        click.echo("✍️  Summarizing content...")
        summarizer = SimpleSummarizer(max_words=100)
        processed_items = []
        
        for item in unique_items:
            try:
                processed = summarizer.summarize(item)
                processed_items.append(processed)
            except Exception as e:
                click.echo(f"⚠️  Failed to summarize {item.title}: {e}")
        
        if not processed_items:
            click.echo("❌ No items successfully processed")
            return
        
        # Step 4: Plan episode duration
        click.echo("⏱️  Planning episode duration...")
        episode_builder = SimpleEpisodeBuilder(target_minutes)
        planned_items = episode_builder.fit(processed_items, target_minutes)
        
        # Step 5: Generate audio
        click.echo("🗣️  Generating audio...")
        
        # Choose TTS provider based on config
        if cfg.voice_settings.provider == "dummy":
            click.echo("Using dummy TTS provider")
            tts_provider = DummyTTSProvider()
        else:
            # Try espeak first, fallback to dummy
            try:
                tts_provider = EspeakProvider()
            except:
                click.echo("⚠️  Espeak not available, using dummy TTS")
                tts_provider = DummyTTSProvider()
        
        audio_segments = []
        titles = []
        
        for item in planned_items:
            try:
                audio_data = tts_provider.synthesize(
                    item.script,
                    voice=cfg.voice_settings.voice_id,
                    speed=cfg.voice_settings.speed
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
        stitcher = SimpleAudioStitcher(gap_ms=200)
        combined_audio = stitcher.stitch(audio_segments, titles)
        
        # Export to WAV (for Step 1)
        episode_path = output_path / cfg.output.episode_filename.replace('.mp3', '.wav')
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
@click.option('--minutes', '-m', type=int, help='Target duration in minutes')
def plan(config, minutes):
    """Plan episode without generating audio."""
    
    cfg = Config.load(config)
    target_minutes = minutes or cfg.target_duration
    
    # Fetch and process content
    source = MultiRSSSource(cfg.rss_feeds)
    raw_items = source.fetch()
    
    deduplicator = SimpleDeduplicator()
    unique_items = deduplicator.deduplicate(raw_items)
    
    summarizer = SimpleSummarizer()
    processed_items = [summarizer.summarize(item) for item in unique_items]
    
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


if __name__ == '__main__':
    cli()