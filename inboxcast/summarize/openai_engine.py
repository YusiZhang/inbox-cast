"""OpenAI-powered summarization with structured JSON output."""
import json
import os
import re
from typing import Dict, Any, Optional
from openai import OpenAI
from ..types import RawItem, ProcessedItem, Summarizer
from ..clean.readability import ReadabilityContentCleaner
from ..config import load_dotenv_files


class OpenAISummarizer(Summarizer):
    """
    OpenAI-powered summarizer with policy guards and structured output.
    
    Generates high-quality summaries with legal compliance checks,
    including quote detection and paywall awareness.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        max_words: int = 50,
        max_quote_words: int = 30,
        temperature: float = 0.3,
        use_content_cleaning: bool = True
    ):
        """
        Initialize OpenAI summarizer.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: OpenAI model to use
            max_words: Maximum words in output script
            max_quote_words: Maximum words allowed in direct quotes
            temperature: Generation temperature (0.0-1.0)
            use_content_cleaning: Whether to use readability cleaning
        """
        # Load environment variables from .env files
        load_dotenv_files()
        
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY env var or pass api_key parameter")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.max_words = max_words
        self.max_quote_words = max_quote_words
        self.temperature = temperature
        
        # Initialize content cleaner if enabled
        self.content_cleaner = ReadabilityContentCleaner() if use_content_cleaning else None
        
        # System prompt for summarization
        self.system_prompt = self._build_system_prompt()
    
    def summarize(self, item: RawItem) -> ProcessedItem:
        """Summarize item with OpenAI and apply policy guards."""
        try:
            # Clean content if enabled
            if self.content_cleaner:
                cleaned_content = self.content_cleaner.extract_content(item.content, item.url)
                paywall_detected = self.content_cleaner.detect_paywall(item.content, item.url)
            else:
                cleaned_content = self._basic_clean(item.content)
                paywall_detected = self._basic_paywall_detection(item.content)
            
            # Skip if paywalled
            if paywall_detected:
                return self._create_skipped_item(item, "paywall_detected")
            
            # Skip if content too short
            if len(cleaned_content.split()) < 20:
                return self._create_skipped_item(item, "insufficient_content")
            
            # Generate summary with OpenAI
            summary_result = self._generate_summary(item.title, cleaned_content)
            
            if not summary_result:
                return self._create_skipped_item(item, "summarization_failed")
            
            # Apply policy guards
            policy_result = self._apply_policy_guards(summary_result)
            
            if not policy_result['passed']:
                return self._create_skipped_item(item, f"policy_violation: {policy_result['reason']}")
            
            # Create processed item
            return ProcessedItem(
                title=item.title,
                script=summary_result['script'],
                sources=[item.url],
                notes={
                    "source": item.source_name,
                    "summary_method": "openai",
                    "model": self.model,
                    "original_length": len(cleaned_content.split()),
                    "paywalled": paywall_detected,
                    "policy_checks": policy_result,
                    "key_topics": summary_result.get('key_topics', []),
                    "summary_type": summary_result.get('type', 'unknown')
                },
                word_count=len(summary_result['script'].split())
            )
            
        except Exception as e:
            print(f"Summarization failed for '{item.title}': {e}")
            return self._create_skipped_item(item, f"error: {str(e)}")
    
    def _generate_summary(self, title: str, content: str) -> Optional[Dict[str, Any]]:
        """Generate summary using OpenAI API."""
        try:
            # Prepare user prompt
            user_prompt = self._build_user_prompt(title, content)
            
            # Call OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=200,  # Conservative limit for summaries
                response_format={"type": "json_object"}
            )
            
            # Parse JSON response
            result = json.loads(response.choices[0].message.content)
            
            # Validate required fields
            if not all(key in result for key in ['script', 'type', 'key_topics']):
                print("OpenAI response missing required fields")
                return None
            
            return result
            
        except Exception as e:
            print(f"OpenAI API call failed: {e}")
            return None
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for OpenAI."""
        return f"""You are an expert podcast script writer specializing in AI newsletter summaries.

Your task is to create engaging, conversational scripts for audio consumption that:
- Are exactly {self.max_words} words or fewer
- Sound natural when spoken aloud
- Capture the key insights without direct quotes longer than {self.max_quote_words} words
- Are legally compliant (transformative, not derivative)
- Focus on "why this matters" rather than just "what happened"

CRITICAL LEGAL REQUIREMENTS:
- NO direct quotes longer than {self.max_quote_words} words
- Must be transformative commentary, not mere copying
- Focus on analysis and implications, not verbatim content
- When referencing specific claims, paraphrase rather than quote

Output format must be valid JSON with these fields:
- "script": The podcast script text ({self.max_words} words max)
- "type": Content type ("news", "research", "opinion", "tutorial", etc.)  
- "key_topics": Array of 2-4 key topics covered

The script should be written in a conversational, engaging style suitable for audio."""
    
    def _build_user_prompt(self, title: str, content: str) -> str:
        """Build user prompt with article content."""
        # Truncate content if too long (to stay within token limits)
        max_content_length = 2000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        return f"""Article Title: {title}

Article Content:
{content}

Create a {self.max_words}-word podcast script that transforms this content into engaging audio commentary. Focus on insights and implications rather than direct quotes."""
    
    def _apply_policy_guards(self, summary_result: Dict[str, Any]) -> Dict[str, Any]:
        """Apply legal and policy compliance checks."""
        script = summary_result['script']
        violations = []
        
        # Check word count
        word_count = len(script.split())
        if word_count > self.max_words:
            violations.append(f"exceeds_word_limit: {word_count} > {self.max_words}")
        
        # Check for long quotes (heuristic: text in quotes)
        quotes = re.findall(r'"([^"]{10,})"', script)
        for quote in quotes:
            quote_words = len(quote.split())
            if quote_words > self.max_quote_words:
                violations.append(f"quote_too_long: {quote_words} words")
        
        # Check for copy-paste indicators
        if any(phrase in script.lower() for phrase in [
            "according to the article",
            "the article states",
            "as mentioned in the piece",
            "the author writes"
        ]):
            violations.append("derivative_language_detected")
        
        # Check for transformative content
        transformative_indicators = [
            "this means",
            "the implications",
            "why this matters",
            "looking ahead",
            "the key insight"
        ]
        
        has_transformative = any(phrase in script.lower() for phrase in transformative_indicators)
        if not has_transformative:
            violations.append("lacks_transformative_analysis")
        
        return {
            'passed': len(violations) == 0,
            'violations': violations,
            'reason': '; '.join(violations) if violations else None,
            'word_count': word_count,
            'quotes_found': len(quotes)
        }
    
    def _basic_clean(self, content: str) -> str:
        """Basic HTML cleaning fallback."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', content)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _basic_paywall_detection(self, content: str) -> bool:
        """Basic paywall detection."""
        indicators = ["subscribe", "subscription", "premium", "sign in", "paywall"]
        return any(indicator in content.lower() for indicator in indicators)
    
    def _create_skipped_item(self, item: RawItem, reason: str) -> ProcessedItem:
        """Create a processed item for skipped content."""
        return ProcessedItem(
            title=item.title,
            script="",  # Empty script for skipped items
            sources=[item.url],
            notes={
                "source": item.source_name,
                "skipped": True,
                "skip_reason": reason,
                "summary_method": "openai"
            },
            word_count=0
        )