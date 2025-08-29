"""Pre-LLM policy checks that run before expensive OpenAI calls."""
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass
from ..types import RawItem
from ..clean.readability import ReadabilityContentCleaner


@dataclass
class PreLLMCheckResult:
    """Result of pre-LLM policy check."""
    passed: bool
    reason: Optional[str] = None
    notes: Dict[str, Any] = None

    def __post_init__(self):
        if self.notes is None:
            self.notes = {}


class PreLLMPolicyChecker:
    """Checks that run before expensive OpenAI API calls."""
    
    def __init__(
        self,
        paywall_detection: bool = True,
        min_content_length: bool = True, 
        content_quality_check: bool = True,
        url_allowlist_check: bool = False,
        min_words: int = 20,
        use_readability: bool = True
    ):
        self.paywall_detection = paywall_detection
        self.min_content_length = min_content_length
        self.content_quality_check = content_quality_check
        self.url_allowlist_check = url_allowlist_check
        self.min_words = min_words
        
        # Initialize content cleaner if needed
        self.content_cleaner = ReadabilityContentCleaner() if use_readability else None
        
        # Paywall indicators
        self.paywall_indicators = [
            "subscribe to continue reading",
            "unlock this article", 
            "premium subscribers only",
            "this content is for subscribers",
            "sign up to read",
            "become a member to read",
            "subscriber-only content",
            "subscription required",
            "premium access required"
        ]
        
        # Quality indicators (content to skip)
        self.low_quality_indicators = [
            "404 not found",
            "page not found", 
            "access denied",
            "please enable javascript",
            "loading...",
            "click here to continue",
            "advertisement"
        ]
    
    def check_item(self, item: RawItem) -> PreLLMCheckResult:
        """Run all pre-LLM checks on an item."""
        
        # Clean content if cleaner available
        if self.content_cleaner:
            try:
                cleaned_content = self.content_cleaner.extract_content(item.content, item.url)
                paywall_detected = self.content_cleaner.detect_paywall(item.content, item.url)
            except Exception as e:
                cleaned_content = self._basic_clean(item.content)
                paywall_detected = self._basic_paywall_detection(item.content)
        else:
            cleaned_content = self._basic_clean(item.content)
            paywall_detected = self._basic_paywall_detection(item.content)
        
        # Check 1: Paywall detection
        if self.paywall_detection and paywall_detected:
            return PreLLMCheckResult(
                passed=False,
                reason="paywall_detected",
                notes={"cleaned_content_length": len(cleaned_content.split())}
            )
        
        # Check 2: Content length
        word_count = len(cleaned_content.split())
        if self.min_content_length and word_count < self.min_words:
            return PreLLMCheckResult(
                passed=False,
                reason=f"insufficient_content: {word_count} words < {self.min_words}",
                notes={"word_count": word_count}
            )
        
        # Check 3: Content quality
        if self.content_quality_check:
            content_lower = cleaned_content.lower()
            for indicator in self.low_quality_indicators:
                if indicator in content_lower:
                    return PreLLMCheckResult(
                        passed=False,
                        reason=f"low_quality_content: {indicator}",
                        notes={"word_count": word_count}
                    )
        
        # Check 4: URL allowlist (if enabled - placeholder for future)
        if self.url_allowlist_check:
            # Placeholder - would check against allowed domains
            pass
        
        # All checks passed
        return PreLLMCheckResult(
            passed=True,
            notes={
                "word_count": word_count,
                "cleaned_content_preview": cleaned_content[:200] + "..." if len(cleaned_content) > 200 else cleaned_content
            }
        )
    
    def _basic_clean(self, content: str) -> str:
        """Basic HTML cleaning fallback."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', content)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _basic_paywall_detection(self, content: str) -> bool:
        """Basic paywall detection."""
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in self.paywall_indicators)