"""Legal and policy compliance guards."""
import re
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class PolicyResult:
    """Result of policy compliance check."""
    passed: bool
    violations: List[str]
    warnings: List[str]
    reason: Optional[str] = None
    
    @property
    def has_violations(self) -> bool:
        return len(self.violations) > 0
    
    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


class QuoteChecker:
    """Checks for and validates direct quotes in content."""
    
    def __init__(self, max_quote_words: int = 30):
        self.max_quote_words = max_quote_words
        
        # Patterns for detecting quotes
        self.quote_patterns = [
            r'"([^"]{10,})"',  # Text in double quotes
            r"'([^']{10,})'",  # Text in single quotes  
            r"according to[^.]{10,}[.!?]",  # Attribution patterns
            r"the article states[^.]{10,}[.!?]",
            r"as mentioned in[^.]{10,}[.!?]",
        ]
    
    def check_quotes(self, text: str) -> PolicyResult:
        """Check text for quote policy violations."""
        violations = []
        warnings = []
        
        # Find direct quotes
        quotes_found = []
        for pattern in self.quote_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                quote = match.group(1) if match.groups() else match.group()
                quotes_found.append(quote.strip())
        
        # Check quote lengths
        long_quotes = []
        for quote in quotes_found:
            word_count = len(quote.split())
            if word_count > self.max_quote_words:
                long_quotes.append(quote[:100] + "..." if len(quote) > 100 else quote)
                violations.append(f"quote_exceeds_limit: {word_count} words > {self.max_quote_words}")
        
        # Warn about any quotes (even short ones)
        if quotes_found and not violations:
            warnings.append(f"quotes_detected: {len(quotes_found)} quotes found")
        
        return PolicyResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            reason='; '.join(violations) if violations else None
        )


class PaywallDetector:
    """Detects paywalled content that shouldn't be processed."""
    
    def __init__(self):
        # Strong indicators that definitely signal paywall
        self.strong_indicators = [
            "subscribe to continue reading",
            "unlock this article", 
            "premium subscribers only",
            "this content is for subscribers",
            "sign up to read",
            "become a member to read",
            "subscriber-only content",
            "behind paywall",
            "subscription required",
            "premium access required"
        ]
        
        # Moderate indicators that suggest paywall when combined
        self.moderate_indicators = [
            "subscribe",
            "subscription", 
            "premium",
            "sign in to read",
            "free trial",
            "members only",
            "subscriber",
            "paywall"
        ]
        
        # Weak indicators
        self.weak_indicators = [
            "register",
            "sign up",
            "join us",
            "free account"
        ]
    
    def detect_paywall(self, content: str, url: Optional[str] = None) -> PolicyResult:
        """Detect if content is behind a paywall."""
        content_lower = content.lower()
        violations = []
        warnings = []
        
        # Check strong indicators
        strong_found = []
        for indicator in self.strong_indicators:
            if indicator in content_lower:
                strong_found.append(indicator)
        
        if strong_found:
            violations.append(f"paywall_detected: {', '.join(strong_found)}")
        
        # Check moderate indicators
        moderate_found = []
        for indicator in self.moderate_indicators:
            if indicator in content_lower:
                moderate_found.append(indicator)
        
        # Multiple moderate indicators suggest paywall
        if len(moderate_found) >= 2:
            violations.append(f"paywall_likely: multiple indicators ({', '.join(moderate_found)})")
        elif moderate_found:
            # Short content with subscription mentions is suspicious
            word_count = len(content.split())
            if word_count < 100:
                violations.append(f"paywall_likely: short content ({word_count} words) with subscription mention")
            else:
                warnings.append(f"paywall_possible: found {', '.join(moderate_found)}")
        
        return PolicyResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            reason='; '.join(violations) if violations else None
        )


class TransformativeChecker:
    """Checks if content is sufficiently transformative for legal compliance."""
    
    def __init__(self):
        # Indicators of transformative content
        self.transformative_phrases = [
            "this means",
            "the implications", 
            "why this matters",
            "looking ahead",
            "the key insight",
            "what's significant",
            "the takeaway",
            "this suggests",
            "in other words",
            "to put it simply",
            "the bigger picture",
            "breaking it down"
        ]
        
        # Indicators of derivative content
        self.derivative_phrases = [
            "according to the article",
            "the article states",
            "as mentioned in the piece", 
            "the author writes",
            "the piece explains",
            "as stated in",
            "the document says",
            "quoting from"
        ]
    
    def check_transformative(self, text: str, title: str = "") -> PolicyResult:
        """Check if content is sufficiently transformative."""
        text_lower = text.lower()
        violations = []
        warnings = []
        
        # Check for transformative language
        transformative_count = sum(
            1 for phrase in self.transformative_phrases 
            if phrase in text_lower
        )
        
        # Check for derivative language
        derivative_count = sum(
            1 for phrase in self.derivative_phrases
            if phrase in text_lower
        )
        
        # Analyze transformative ratio
        if transformative_count == 0:
            violations.append("lacks_transformative_analysis: no analytical language found")
        elif transformative_count < 2:
            warnings.append("minimal_transformative_language: consider adding more analysis")
        
        if derivative_count > 0:
            violations.append(f"derivative_language_detected: {derivative_count} instances")
        
        # Check for verbatim title copying
        if title and len(title.split()) > 3:
            title_words = set(title.lower().split())
            text_words = set(text_lower.split())
            overlap = len(title_words & text_words) / len(title_words)
            if overlap > 0.8:
                warnings.append("high_title_overlap: consider paraphrasing title content")
        
        return PolicyResult(
            passed=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            reason='; '.join(violations) if violations else None
        )


class ComprehensivePolicyGuard:
    """Comprehensive policy compliance checker combining all guards."""
    
    def __init__(
        self,
        max_quote_words: int = 30,
        max_script_words: int = 50,
        strict_mode: bool = False
    ):
        self.max_quote_words = max_quote_words
        self.max_script_words = max_script_words
        self.strict_mode = strict_mode
        
        # Initialize individual checkers
        self.quote_checker = QuoteChecker(max_quote_words)
        self.paywall_detector = PaywallDetector()
        self.transformative_checker = TransformativeChecker()
    
    def check_compliance(
        self, 
        script: str, 
        original_content: str = "",
        title: str = "",
        url: Optional[str] = None
    ) -> PolicyResult:
        """Run comprehensive compliance check."""
        all_violations = []
        all_warnings = []
        
        # Check word count
        word_count = len(script.split())
        if word_count > self.max_script_words:
            all_violations.append(f"exceeds_word_limit: {word_count} > {self.max_script_words}")
        
        # Run individual checks
        checks = [
            ("quotes", self.quote_checker.check_quotes(script)),
            ("transformative", self.transformative_checker.check_transformative(script, title))
        ]
        
        # Check paywall if original content provided
        if original_content:
            checks.append(("paywall", self.paywall_detector.detect_paywall(original_content, url)))
        
        # Aggregate results
        for check_name, result in checks:
            all_violations.extend(result.violations)
            all_warnings.extend(result.warnings)
        
        # In strict mode, warnings become violations
        if self.strict_mode:
            all_violations.extend(all_warnings)
            all_warnings = []
        
        return PolicyResult(
            passed=len(all_violations) == 0,
            violations=all_violations,
            warnings=all_warnings,
            reason='; '.join(all_violations) if all_violations else None
        )