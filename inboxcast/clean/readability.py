"""HTML content cleaning with readability extraction."""
import re
import requests
from html import unescape
from typing import Optional
from readability import Document
from bs4 import BeautifulSoup


class ReadabilityContentCleaner:
    """Content cleaner using readability algorithm for main content extraction."""
    
    def __init__(self, fetch_full_content: bool = True, timeout: int = 10):
        """
        Initialize the content cleaner.
        
        Args:
            fetch_full_content: Whether to fetch full HTML from URL if needed
            timeout: Request timeout in seconds
        """
        self.fetch_full_content = fetch_full_content
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; InboxCast/1.0; +https://inboxcast.ai)'
        })
    
    def extract_content(self, raw_content: str, url: Optional[str] = None) -> str:
        """
        Extract clean content from HTML using readability algorithm.
        
        Args:
            raw_content: Raw HTML content from RSS
            url: Original URL for fetching full content if needed
            
        Returns:
            Clean text content suitable for summarization
        """
        try:
            # First try to extract from provided content
            cleaned = self._extract_with_readability(raw_content)
            
            # If content seems too short and we have a URL, try fetching full page
            if self.fetch_full_content and url and len(cleaned.split()) < 50:
                full_content = self._fetch_full_content(url)
                if full_content:
                    full_cleaned = self._extract_with_readability(full_content)
                    if len(full_cleaned.split()) > len(cleaned.split()):
                        cleaned = full_cleaned
            
            return cleaned
            
        except Exception as e:
            print(f"Content extraction failed: {e}")
            # Fallback to basic HTML cleaning
            return self._basic_html_clean(raw_content)
    
    def _extract_with_readability(self, html_content: str) -> str:
        """Extract main content using readability algorithm."""
        try:
            # Validate HTML content before processing
            if not html_content or not html_content.strip():
                print("HTML content is empty, falling back to basic cleaning")
                return self._basic_html_clean(html_content or "")
            
            # Check if content has minimal HTML structure
            if len(html_content.strip()) < 50:
                print("HTML content too short for readability processing")
                return self._basic_html_clean(html_content)
            
            # Use readability to extract main content
            doc = Document(html_content)
            article_html = doc.summary()
            
            # Convert to clean text
            soup = BeautifulSoup(article_html, 'lxml')
            
            # Remove unwanted elements
            for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                element.decompose()
            
            # Extract text
            text = soup.get_text()
            
            # Clean whitespace and normalize
            text = self._normalize_text(text)
            
            return text
            
        except Exception as e:
            print(f"Readability extraction failed: {e}")
            return self._basic_html_clean(html_content)
    
    def _fetch_full_content(self, url: str) -> Optional[str]:
        """Fetch full HTML content from URL."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Failed to fetch full content from {url}: {e}")
            return None
    
    def _basic_html_clean(self, html_content: str) -> str:
        """Basic HTML cleaning fallback."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)
        
        # Decode HTML entities
        text = unescape(text)
        
        # Normalize text
        return self._normalize_text(text)
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text content."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove extra newlines but preserve paragraph breaks
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Clean up common artifacts
        text = re.sub(r'^\s*\|\s*', '', text)  # Remove table separators
        text = re.sub(r'\s*\|\s*$', '', text)
        
        # Remove social media artifacts
        text = re.sub(r'(Share on|Follow us|Subscribe)', '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def detect_paywall(self, content: str, url: Optional[str] = None) -> bool:
        """Enhanced paywall detection."""
        # TODO: Implement more sophisticated paywall detection logic
        content_lower = content.lower()
        
        # Strong paywall indicators
        strong_indicators = [
            "subscribe to continue reading",
            "unlock this article",
            "premium subscribers only",
            "this content is for subscribers",
            "sign up to read",
            "become a member",
            "subscriber-only content",
            "behind paywall"
        ]
        
        # Moderate indicators
        moderate_indicators = [
            "subscribe",
            "subscription",
            "premium",
            "sign in to read",
            "free trial",
            "members only"
        ]
        
        # Strong indicators are definitive
        if any(indicator in content_lower for indicator in strong_indicators):
            return True
        
        # Multiple moderate indicators suggest paywall
        moderate_count = sum(1 for indicator in moderate_indicators if indicator in content_lower)
        if moderate_count >= 2:
            return True
        
        # Short content with subscription indicators
        word_count = len(content.split())
        if word_count < 100 and moderate_count >= 1:
            return True
        
        return False