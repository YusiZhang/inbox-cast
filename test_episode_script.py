#!/usr/bin/env python3
"""Test script for the episode script engine with mock data."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from inboxcast.types import PlannedItem
from inboxcast.script.episode_engine import EpisodeScriptEngine

def create_mock_items():
    """Create mock planned items for testing."""
    return [
        PlannedItem(
            title="OpenAI Releases GPT-5 with Revolutionary Capabilities",
            script="OpenAI has unveiled GPT-5, a groundbreaking language model that significantly outperforms its predecessors. This new model demonstrates remarkable improvements in reasoning, coding, and creative tasks. The implications for AI development are substantial, potentially accelerating progress across multiple industries and applications.",
            sources=["https://example.com/gpt5"],
            notes={"source": "OpenAI Blog"},
            word_count=47,
            allocated_words=47
        ),
        PlannedItem(
            title="Google's Gemini Ultra Achieves Human-Level Performance",
            script="Google's latest AI model, Gemini Ultra, has achieved human-level performance on several benchmark tests. The model excels at multimodal tasks, combining text, images, and code understanding. This advancement represents a significant milestone in artificial general intelligence research and development.",
            sources=["https://example.com/gemini"],
            notes={"source": "Google AI Blog"},
            word_count=42,
            allocated_words=42
        ),
        PlannedItem(
            title="AI Safety Research Shows Promising Alignment Breakthrough",
            script="Researchers at Anthropic have published findings on constitutional AI that could solve alignment problems. Their approach uses AI systems to critique and improve their own outputs according to a set of principles. This technique shows promise for creating more reliable and trustworthy AI systems.",
            sources=["https://example.com/safety"],
            notes={"source": "Anthropic Research"},
            word_count=45,
            allocated_words=45
        )
    ]

def test_episode_engine():
    """Test the episode script engine."""
    try:
        # Create mock items
        planned_items = create_mock_items()
        
        # Initialize episode engine
        engine = EpisodeScriptEngine()
        
        print("🧪 Testing Episode Script Engine...")
        print(f"Mock items: {len(planned_items)}")
        
        # Generate episode script
        episode_script = engine.synthesize_episode(
            planned_items, 
            target_minutes=10,
            episode_date="2025-09-05"
        )
        
        print(f"✅ Episode script generated successfully!")
        print(f"📊 Stats:")
        print(f"  - Total words: {episode_script.total_word_count}")
        print(f"  - Estimated duration: {episode_script.estimated_duration_minutes:.1f} minutes")
        print(f"  - Segments: {len(episode_script.segments)}")
        
        # Print the script
        print("\n" + "="*60)
        print("EPISODE SCRIPT PREVIEW")
        print("="*60)
        
        print("\nINTRODUCTION:")
        print(episode_script.introduction)
        
        for i, segment in enumerate(episode_script.segments, 1):
            print(f"\nSEGMENT {i}: {segment.theme_title}")
            print(f"Transition: {segment.transition}")
            print(f"Items: {len(segment.items)}")
            for item in segment.items:
                print(f"  - {item.title}")
        
        print("\nCONCLUSION:")
        print(episode_script.conclusion)
        
        return True
        
    except Exception as e:
        print(f"❌ Episode script engine test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_episode_engine()
    sys.exit(0 if success else 1)