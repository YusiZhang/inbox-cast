"""Semantic deduplication using sentence embeddings."""
import os
import pickle
import psutil
import shutil
from pathlib import Path
from typing import List, Set, Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from ..types import RawItem


class SemanticDeduplicator:
    """
    Deduplication using semantic embeddings to detect similar content.
    
    Uses sentence-transformers to create embeddings of article content and
    compares similarity to identify duplicate or near-duplicate articles.
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.85,
        cache_dir: Optional[str] = None,
        cache_days: int = 7
    ):
        """
        Initialize semantic deduplicator.
        
        Args:
            model_name: Sentence transformer model name
            similarity_threshold: Cosine similarity threshold for duplicates (0.0-1.0)
            cache_dir: Directory to cache embeddings
            cache_days: Days to keep cached embeddings
        """
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.cache_days = cache_days
        
        # Initialize model with robust error handling and resource monitoring
        self.model = self._initialize_model(model_name)
        
        # Setup caching
        if cache_dir:
            self.cache_dir = Path(cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_file = self.cache_dir / "embedding_cache.pkl"
            self.embedding_cache = self._load_cache()
        else:
            self.cache_dir = None
            self.embedding_cache = {}
        
        # Track seen items across sessions
        self.seen_embeddings: List[np.ndarray] = []
        self.seen_items: List[RawItem] = []
    
    def deduplicate(self, items: List[RawItem]) -> List[RawItem]:
        """
        Remove semantically similar duplicates from items.

        Args:
            items: List of raw items to deduplicate

        Returns:
            Filtered list with duplicates removed
        """
        if not items:
            return items

        print(f"Semantic dedupe: processing {len(items)} items")

        # If model failed to initialize, fall back to simple deduplication
        if self.model is None:
            print("❌ Semantic model not available, falling back to simple deduplication")
            return self._simple_deduplicate(items)

        # Clean old cache entries
        self._clean_cache()

        unique_items = []
        new_embeddings = []

        for item in items:
            try:
                # Create embedding for this item
                embedding = self._get_embedding(item)

                if embedding is None:
                    # If embedding failed, include item (conservative approach)
                    unique_items.append(item)
                    continue

                # Check against previously seen items
                if not self._is_duplicate(embedding, item):
                    unique_items.append(item)
                    new_embeddings.append(embedding)
                    self.seen_embeddings.append(embedding)
                    self.seen_items.append(item)
            except Exception as e:
                print(f"⚠️  Error processing item '{item.title}': {e}")
                # Include item when processing fails (conservative approach)
                unique_items.append(item)

        # Save cache if enabled
        if self.cache_dir:
            self._save_cache()

        print(f"Semantic dedupe: {len(items)} → {len(unique_items)} items")
        return unique_items
    
    def _get_embedding(self, item: RawItem) -> Optional[np.ndarray]:
        """Get or compute embedding for an item."""
        if self.model is None:
            return None

        # Create cache key from content hash
        content_key = hash(f"{item.title}:{item.content[:500]}")

        # Check cache first
        if content_key in self.embedding_cache:
            cache_entry = self.embedding_cache[content_key]
            # Check if cache entry is still valid
            if datetime.now() - cache_entry['timestamp'] < timedelta(days=self.cache_days):
                return cache_entry['embedding']

        try:
            # Compute new embedding
            # Combine title and content for better semantic representation
            text_to_embed = f"{item.title}. {item.content[:1000]}"  # Limit length for efficiency
            embedding = self.model.encode(text_to_embed, convert_to_numpy=True)

            # Cache the embedding
            self.embedding_cache[content_key] = {
                'embedding': embedding,
                'timestamp': datetime.now(),
                'title': item.title,
                'url': item.url
            }

            return embedding
        except Exception as e:
            print(f"⚠️  Failed to generate embedding for '{item.title}': {e}")
            return None
    
    def _is_duplicate(self, embedding: np.ndarray, item: RawItem) -> bool:
        """Check if item is a duplicate of previously seen items."""
        if not self.seen_embeddings:
            return False
        
        # Compute similarities with all seen embeddings
        seen_matrix = np.array(self.seen_embeddings)
        similarities = cosine_similarity([embedding], seen_matrix)[0]
        
        # Find the maximum similarity
        max_similarity = np.max(similarities)
        
        if max_similarity >= self.similarity_threshold:
            # Find the most similar item for logging
            max_idx = np.argmax(similarities)
            similar_item = self.seen_items[max_idx]
            print(f"Duplicate detected (sim={max_similarity:.3f}): '{item.title}' ~ '{similar_item.title}'")
            return True
        
        return False
    
    def _load_cache(self) -> Dict:
        """Load embedding cache from disk."""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'rb') as f:
                    cache = pickle.load(f)
                print(f"Loaded {len(cache)} cached embeddings")
                return cache
        except Exception as e:
            print(f"Failed to load embedding cache: {e}")
        
        return {}
    
    def _save_cache(self):
        """Save embedding cache to disk."""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.embedding_cache, f)
        except Exception as e:
            print(f"Failed to save embedding cache: {e}")
    
    def _clean_cache(self):
        """Remove old cache entries."""
        if not self.embedding_cache:
            return
        
        cutoff_time = datetime.now() - timedelta(days=self.cache_days)
        old_keys = []
        
        for key, entry in self.embedding_cache.items():
            if entry['timestamp'] < cutoff_time:
                old_keys.append(key)
        
        for key in old_keys:
            del self.embedding_cache[key]
        
        if old_keys:
            print(f"Cleaned {len(old_keys)} old cache entries")
    
    def get_similarity_matrix(self, items: List[RawItem]) -> np.ndarray:
        """
        Get similarity matrix for analysis/debugging.
        
        Returns:
            Square matrix of pairwise similarities
        """
        if not items:
            return np.array([])
        
        embeddings = [self._get_embedding(item) for item in items]
        return cosine_similarity(embeddings)
    
    def find_clusters(self, items: List[RawItem], min_cluster_size: int = 2) -> List[List[int]]:
        """
        Find clusters of similar items.
        
        Returns:
            List of clusters, each containing indices of similar items
        """
        if len(items) < min_cluster_size:
            return []
        
        similarity_matrix = self.get_similarity_matrix(items)
        clusters = []
        used = set()
        
        for i in range(len(items)):
            if i in used:
                continue
            
            cluster = [i]
            for j in range(i + 1, len(items)):
                if j not in used and similarity_matrix[i, j] >= self.similarity_threshold:
                    cluster.append(j)
                    used.add(j)
            
            if len(cluster) >= min_cluster_size:
                clusters.append(cluster)
                used.update(cluster)
        
        return clusters

    def _initialize_model(self, model_name: str) -> Optional[SentenceTransformer]:
        """
        Initialize SentenceTransformer with comprehensive error handling and resource monitoring.

        Returns:
            SentenceTransformer instance or None if initialization fails
        """
        print(f"🔍 Initializing sentence transformer model: {model_name}")

        # Monitor system resources before loading
        self._log_system_resources()

        # Check HuggingFace cache directory
        self._check_cache_directory()

        try:
            print(f"📥 Loading sentence transformer model: {model_name}")
            model = SentenceTransformer(model_name)
            print(f"✅ Successfully loaded model: {model_name}")

            # Log post-loading resource usage
            print("📊 Resource usage after model loading:")
            self._log_system_resources()

            return model

        except MemoryError as e:
            print(f"❌ MEMORY ERROR: Insufficient RAM to load model {model_name}")
            print(f"   Error details: {e}")
            self._log_system_resources()
            return None

        except OSError as e:
            print(f"❌ OS ERROR: Disk/file system issue loading model {model_name}")
            print(f"   Error details: {e}")
            print(f"   This often indicates insufficient disk space or permission issues")
            self._check_cache_directory()
            return None

        except Exception as e:
            print(f"❌ UNEXPECTED ERROR loading model {model_name}")
            print(f"   Error type: {type(e).__name__}")
            print(f"   Error details: {e}")
            print(f"   Full traceback:")
            import traceback
            traceback.print_exc()
            return None

    def _log_system_resources(self):
        """Log current system resource usage."""
        try:
            # Memory info
            memory = psutil.virtual_memory()
            print(f"   💾 Memory: {memory.percent}% used ({memory.used / 1024**3:.2f}GB / {memory.total / 1024**3:.2f}GB)")
            print(f"   🆓 Available: {memory.available / 1024**3:.2f}GB")

            # Disk info for current directory
            disk = psutil.disk_usage('.')
            print(f"   💿 Disk: {disk.percent}% used ({disk.used / 1024**3:.2f}GB / {disk.total / 1024**3:.2f}GB)")
            print(f"   🆓 Disk available: {disk.free / 1024**3:.2f}GB")

        except Exception as e:
            print(f"   ⚠️  Could not get system resource info: {e}")

    def _check_cache_directory(self):
        """Check HuggingFace cache directory status."""
        try:
            from transformers import file_utils
            cache_dir = file_utils.default_cache_path

            print(f"   📁 HuggingFace cache directory: {cache_dir}")

            if os.path.exists(cache_dir):
                # Get cache directory size
                total_size = sum(
                    os.path.getsize(os.path.join(dirpath, filename))
                    for dirpath, dirnames, filenames in os.walk(cache_dir)
                    for filename in filenames
                )
                print(f"   📊 Cache size: {total_size / 1024**2:.2f}MB")

                # Check available space in cache directory
                disk_usage = shutil.disk_usage(cache_dir)
                print(f"   🆓 Available space in cache: {disk_usage.free / 1024**3:.2f}GB")

                if disk_usage.free < 500 * 1024**2:  # Less than 500MB
                    print(f"   ⚠️  WARNING: Low disk space in cache directory!")
            else:
                print(f"   📁 Cache directory does not exist yet (will be created)")

        except Exception as e:
            print(f"   ⚠️  Could not check cache directory: {e}")
            try:
                # Fallback: check home directory cache
                home_cache = os.path.expanduser("~/.cache/huggingface")
                if os.path.exists(home_cache):
                    disk_usage = shutil.disk_usage(home_cache)
                    print(f"   📁 Fallback cache check: {home_cache}")
                    print(f"   🆓 Available space: {disk_usage.free / 1024**3:.2f}GB")
            except Exception as e2:
                print(f"   ⚠️  Fallback cache check also failed: {e2}")

    def _simple_deduplicate(self, items: List[RawItem]) -> List[RawItem]:
        """
        Simple title-based deduplication fallback when semantic model fails.
        """
        print("🔄 Using simple title-based deduplication")
        seen_titles = set()
        unique_items = []

        for item in items:
            # Normalize title for comparison
            normalized_title = item.title.lower().strip()

            if normalized_title not in seen_titles:
                seen_titles.add(normalized_title)
                unique_items.append(item)
            else:
                print(f"   📋 Simple duplicate detected: '{item.title}'")

        print(f"Simple dedupe: {len(items)} → {len(unique_items)} items")
        return unique_items