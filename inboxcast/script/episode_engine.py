"""Episode-level script synthesis engine for cohesive podcast generation."""
import json
import os
from typing import List, Dict, Any, Optional
from openai import OpenAI
from ..types import PlannedItem, EpisodeScript, EpisodeSegment
from ..config import load_dotenv_files


class EpisodeScriptEngine:
    """
    Synthesizes individual newsletter summaries into cohesive episode scripts.
    
    Takes segmented content (already processed by OpenAISummarizer) and creates
    professional podcast episodes with introductions, transitions, and conclusions.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,  # Higher creativity for episode flow
        max_intro_words: int = 65,
        max_outro_words: int = 80,
        max_transition_words: int = 30
    ):
        """Initialize episode script engine with OpenAI client."""
        load_dotenv_files()
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required for episode script generation")
            
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.temperature = temperature
        self.max_intro_words = max_intro_words
        self.max_outro_words = max_outro_words
        self.max_transition_words = max_transition_words
    
    def synthesize_episode(
        self,
        planned_items: List[PlannedItem],
        target_minutes: int,
        episode_date: str = None
    ) -> EpisodeScript:
        """
        Synthesize individual items into cohesive episode script.
        
        Args:
            planned_items: List of newsletter items already processed and planned
            target_minutes: Target episode duration in minutes
            episode_date: Date for episode (for personalized intro)
            
        Returns:
            Structured episode script with intro, segments, transitions, outro
        """
        if not planned_items:
            raise ValueError("Cannot create episode from empty items list")
        
        # Step 1: Analyze content themes and group related items
        segments = self._create_thematic_segments(planned_items)
        
        # Step 2: Generate episode introduction
        introduction = self._generate_introduction(segments, target_minutes, episode_date)
        
        # Step 3: Generate transitions for each segment
        self._generate_segment_transitions(segments)
        
        # Step 4: Generate episode conclusion
        conclusion = self._generate_conclusion(segments, target_minutes)
        
        # Step 5: Calculate final word counts and duration
        total_words = (
            len(introduction.split()) +
            sum(seg.word_count for seg in segments) +
            len(conclusion.split())
        )
        
        estimated_duration = total_words / 165  # 165 WPM speaking rate
        
        return EpisodeScript(
            introduction=introduction,
            segments=segments,
            conclusion=conclusion,
            total_word_count=total_words,
            estimated_duration_minutes=estimated_duration,
            metadata={
                "target_minutes": target_minutes,
                "item_count": len(planned_items),
                "segment_count": len(segments),
                "generation_model": self.model,
                "episode_date": episode_date
            }
        )
    
    def _create_thematic_segments(self, planned_items: List[PlannedItem]) -> List[EpisodeSegment]:
        """Group related items into thematic segments."""
        
        # For now, implement simple semantic grouping
        # In future: could use embedding similarity or topic modeling
        segments = []
        
        # Analyze item topics and group similar ones
        item_groups = self._group_items_by_theme(planned_items)
        
        for theme, items in item_groups:
            segment_word_count = sum(item.word_count for item in items)
            
            segment = EpisodeSegment(
                theme_title=theme,
                transition="",  # Will be generated later
                items=items,
                word_count=segment_word_count
            )
            segments.append(segment)
        
        return segments
    
    def _group_items_by_theme(self, items: List[PlannedItem]) -> List[tuple]:
        """Simple thematic grouping based on content analysis."""
        
        # Use OpenAI to analyze themes and group items
        try:
            # Create item summaries for analysis
            item_summaries = []
            for i, item in enumerate(items):
                item_summaries.append({
                    "id": i,
                    "title": item.title,
                    "script_preview": item.script[:100] + "..." if len(item.script) > 100 else item.script
                })
            
            # Generate thematic analysis
            analysis_prompt = self._build_theme_analysis_prompt(item_summaries)
            
            response = self.client.responses.create(
                model=self.model,
                instructions="You are an expert podcast producer who groups newsletter content into thematic segments for better narrative flow.",
                input=analysis_prompt,
                temperature=0.3,  # Lower temperature for consistent grouping
                max_output_tokens=300,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "episode_segments",
                        "description": "Thematic grouping of newsletter items",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "segments": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "theme": {"type": "string"},
                                            "item_ids": {
                                                "type": "array",
                                                "items": {"type": "integer"}
                                            }
                                        },
                                        "required": ["theme", "item_ids"],
                                        "additionalProperties": False
                                    }
                                }
                            },
                            "required": ["segments"],
                            "additionalProperties": False
                        }
                    }
                }
            )
            
            result = json.loads(response.output_text)
            
            # Convert analysis result to grouped items
            groups = []
            for segment_data in result.get("segments", []):
                theme = segment_data["theme"]
                item_ids = segment_data["item_ids"]
                segment_items = [items[i] for i in item_ids if i < len(items)]
                if segment_items:  # Only add non-empty groups
                    groups.append((theme, segment_items))
            
            # If no groups created or all items missed, create single segment
            if not groups:
                groups = [("Today's AI Updates", items)]
                
            return groups
            
        except Exception as e:
            print(f"Theme analysis failed, using single segment: {e}")
            # Fallback: single segment with all items
            return [("Today's AI Updates", items)]
    
    def _generate_introduction(
        self, 
        segments: List[EpisodeSegment], 
        target_minutes: int,
        episode_date: str = None
    ) -> str:
        """Generate engaging episode introduction."""
        
        intro_prompt = self._build_introduction_prompt(segments, target_minutes, episode_date)
        
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=f"Generate a {self.max_intro_words}-word professional, concise podcast introduction. Be direct and informative. Avoid marketing language, enthusiasm, or filler phrases.",
                input=intro_prompt,
                temperature=self.temperature,
                max_output_tokens=150,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "episode_intro",
                        "description": "Podcast episode introduction",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "introduction": {"type": "string"}
                            },
                            "required": ["introduction"],
                            "additionalProperties": False
                        }
                    }
                }
            )
            
            result = json.loads(response.output_text)
            return result.get("introduction", "Welcome to today's InboxCast episode.")
            
        except Exception as e:
            print(f"Introduction generation failed: {e}")
            # Fallback introduction
            topics = ", ".join([seg.theme_title.lower() for seg in segments])
            return f"Welcome to InboxCast. Today we're covering {len(segments)} key topics including {topics}. Let's dive in."
    
    def _generate_segment_transitions(self, segments: List[EpisodeSegment]) -> None:
        """Generate natural transitions between segments (modifies segments in place)."""
        
        for i, segment in enumerate(segments):
            if i == 0:
                # First segment - transition from intro
                segment.transition = self._generate_intro_transition(segment)
            else:
                # Subsequent segments - transition from previous
                segment.transition = self._generate_inter_segment_transition(
                    segments[i-1], segment
                )
    
    def _generate_intro_transition(self, first_segment: EpisodeSegment) -> str:
        """Generate transition from introduction to first segment."""
        
        transition_prompt = f"""Create a natural transition from the episode introduction to the first segment about "{first_segment.theme_title}".
        
First segment preview:
{first_segment.items[0].title if first_segment.items else "AI updates"}

Generate a brief, conversational transition (max {self.max_transition_words} words) that flows naturally."""
        
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=f"Generate a brief {self.max_transition_words}-word transition that sounds natural in podcast flow.",
                input=transition_prompt,
                temperature=self.temperature,
                max_output_tokens=50,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "segment_transition",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "transition": {"type": "string"}
                            },
                            "required": ["transition"],
                            "additionalProperties": False
                        }
                    }
                }
            )
            
            result = json.loads(response.output_text)
            return result.get("transition", f"Let's start with {first_segment.theme_title.lower()}.")
            
        except Exception as e:
            print(f"Transition generation failed: {e}")
            return f"Let's start with {first_segment.theme_title.lower()}."
    
    def _generate_inter_segment_transition(
        self, 
        prev_segment: EpisodeSegment, 
        current_segment: EpisodeSegment
    ) -> str:
        """Generate transition between two segments."""
        
        transition_prompt = f"""Create a natural transition in a podcast from one topic to another.

Previous segment: "{prev_segment.theme_title}"
Last item was: {prev_segment.items[-1].title if prev_segment.items else ""}

Current segment: "{current_segment.theme_title}" 
First item: {current_segment.items[0].title if current_segment.items else ""}

Generate a brief, conversational transition (max {self.max_transition_words} words) that naturally bridges these topics."""
        
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=f"Generate a natural {self.max_transition_words}-word transition between podcast segments.",
                input=transition_prompt,
                temperature=self.temperature,
                max_output_tokens=50,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "segment_transition",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "transition": {"type": "string"}
                            },
                            "required": ["transition"],
                            "additionalProperties": False
                        }
                    }
                }
            )
            
            result = json.loads(response.output_text)
            return result.get("transition", f"Moving on to {current_segment.theme_title.lower()}.")
            
        except Exception as e:
            print(f"Transition generation failed: {e}")
            return f"Moving on to {current_segment.theme_title.lower()}."
    
    def _generate_conclusion(self, segments: List[EpisodeSegment], target_minutes: int) -> str:
        """Generate episode conclusion with key takeaways."""
        
        conclusion_prompt = self._build_conclusion_prompt(segments, target_minutes)
        
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=f"Generate a {self.max_outro_words}-word podcast conclusion that wraps up the episode with key takeaways.",
                input=conclusion_prompt,
                temperature=self.temperature,
                max_output_tokens=120,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "episode_conclusion",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "conclusion": {"type": "string"}
                            },
                            "required": ["conclusion"],
                            "additionalProperties": False
                        }
                    }
                }
            )
            
            result = json.loads(response.output_text)
            return result.get("conclusion", "That wraps up today's InboxCast episode. Thanks for listening.")
            
        except Exception as e:
            print(f"Conclusion generation failed: {e}")
            return "That wraps up today's InboxCast episode. Stay curious, and we'll see you next time."
    
    def _build_theme_analysis_prompt(self, item_summaries: List[Dict]) -> str:
        """Build prompt for thematic analysis of items."""
        
        items_text = "\n".join([
            f"{item['id']}. {item['title']}\n   Preview: {item['script_preview']}"
            for item in item_summaries
        ])
        
        return f"""Analyze these newsletter items and group them into 2-4 thematic segments for a podcast episode:

Items:
{items_text}

Create thematic segments that:
- Group related/similar topics together
- Create natural narrative flow
- Have descriptive theme names (e.g., "AI Safety Developments", "New Model Releases", "Industry News")
- Include all items (no item should be left out)

Return the grouping as JSON with segment themes and corresponding item IDs."""
    
    def _build_introduction_prompt(
        self, 
        segments: List[EpisodeSegment], 
        target_minutes: int, 
        episode_date: str = None
    ) -> str:
        """Build prompt for episode introduction generation."""
        
        topics = [seg.theme_title for seg in segments]
        date_text = f" for {episode_date}" if episode_date else ""
        
        return f"""Create a professional, concise podcast introduction{date_text} for an AI newsletter summary episode.

Episode details:
- Target duration: {target_minutes} minutes
- Topics covered: {', '.join(topics)}
- Number of segments: {len(segments)}

The introduction should:
- Be direct and informative (NPR-style)
- Briefly state what topics will be covered
- Sound natural when spoken aloud
- Be exactly {self.max_intro_words} words or less
- Welcome listeners to "InboxCast"
- Avoid enthusiasm, marketing language, or filler phrases (no "thrilled", "grab a beverage", "settle in", etc.)

Create a professional, matter-of-fact introduction that gets straight to the content."""
    
    def _build_conclusion_prompt(self, segments: List[EpisodeSegment], target_minutes: int) -> str:
        """Build prompt for episode conclusion generation."""
        
        topics = [seg.theme_title for seg in segments]
        
        return f"""Create a podcast conclusion that wraps up an AI newsletter summary episode.

Topics we covered:
{', '.join(topics)}

The conclusion should:
- Briefly recap the key themes (don't repeat details)
- Thank listeners for their time
- Sound natural and warm when spoken
- Be exactly {self.max_outro_words} words or less
- End on an engaging note that encourages return listening

Create a professional, friendly conclusion for "InboxCast"."""