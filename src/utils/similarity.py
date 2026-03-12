"""Content similarity detection using SimHash and other algorithms."""

import hashlib
import re
from collections import Counter
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class SimilarityResult:
    """Result of similarity comparison."""
    url1: str
    url2: str
    similarity: float
    method: str
    differences: Optional[List[str]] = None


class SimHasher:
    """SimHash implementation for near-duplicate detection.

    SimHash is a locality-sensitive hashing technique that produces similar
    hashes for similar content. It's efficient for large-scale duplicate detection.
    """

    def __init__(self, hash_bits: int = 64):
        """Initialize SimHasher.

        Args:
            hash_bits: Number of bits in the hash (default 64)
        """
        self.hash_bits = hash_bits

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words and n-grams."""
        # Lowercase and remove punctuation
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)

        # Split into words
        words = text.split()

        # Generate 3-grams for better accuracy
        tokens = words.copy()
        for i in range(len(words) - 2):
            tokens.append(' '.join(words[i:i+3]))

        return tokens

    def _token_hash(self, token: str) -> int:
        """Generate hash for a single token."""
        return int(hashlib.md5(token.encode()).hexdigest(), 16)

    def compute(self, text: str) -> int:
        """Compute SimHash for text.

        Args:
            text: Input text

        Returns:
            SimHash value as integer
        """
        tokens = self._tokenize(text)
        if not tokens:
            return 0

        # Count token frequencies
        token_counts = Counter(tokens)

        # Initialize vector
        v = [0] * self.hash_bits

        for token, count in token_counts.items():
            h = self._token_hash(token)
            for i in range(self.hash_bits):
                if h & (1 << i):
                    v[i] += count
                else:
                    v[i] -= count

        # Convert to hash
        simhash = 0
        for i in range(self.hash_bits):
            if v[i] > 0:
                simhash |= (1 << i)

        return simhash

    def distance(self, hash1: int, hash2: int) -> int:
        """Calculate Hamming distance between two hashes.

        Args:
            hash1: First hash
            hash2: Second hash

        Returns:
            Hamming distance (number of differing bits)
        """
        x = hash1 ^ hash2
        distance = 0
        while x:
            distance += 1
            x &= x - 1
        return distance

    def similarity(self, hash1: int, hash2: int) -> float:
        """Calculate similarity between two hashes.

        Args:
            hash1: First hash
            hash2: Second hash

        Returns:
            Similarity score between 0 and 1
        """
        dist = self.distance(hash1, hash2)
        return 1 - (dist / self.hash_bits)


class ContentSimilarity:
    """Content similarity detection for finding duplicate pages."""

    def __init__(self, similarity_threshold: float = 0.85):
        """Initialize similarity detector.

        Args:
            similarity_threshold: Minimum similarity to consider as duplicate (0-1)
        """
        self.similarity_threshold = similarity_threshold
        self.simhasher = SimHasher()

    def _clean_content(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""

        # Lowercase
        text = text.lower()

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove common boilerplate patterns
        boilerplate_patterns = [
            r'cookie\s*(policy|preferences|settings)',
            r'privacy\s*policy',
            r'terms\s*(of\s*service|and\s*conditions)',
            r'all\s*rights\s*reserved',
            r'copyright\s*\d{4}',
            r'follow\s*us\s*(on)?',
            r'share\s*(this|on)',
            r'newsletter',
            r'subscribe',
        ]

        for pattern in boilerplate_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        return text.strip()

    def compute_simhash(self, text: str) -> int:
        """Compute SimHash for text content."""
        cleaned = self._clean_content(text)
        return self.simhasher.compute(cleaned)

    def jaccard_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Jaccard similarity score (0-1)
        """
        words1 = set(self._clean_content(text1).split())
        words2 = set(self._clean_content(text2).split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def cosine_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Cosine similarity score (0-1)
        """
        words1 = self._clean_content(text1).split()
        words2 = self._clean_content(text2).split()

        if not words1 or not words2:
            return 0.0

        # Build vocabulary
        all_words = list(set(words1 + words2))

        # Create frequency vectors
        vec1 = np.array([words1.count(w) for w in all_words])
        vec2 = np.array([words2.count(w) for w in all_words])

        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def find_differences(self, text1: str, text2: str) -> List[str]:
        """Find key differences between two similar texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            List of differences found
        """
        words1 = set(self._clean_content(text1).split())
        words2 = set(self._clean_content(text2).split())

        only_in_1 = words1 - words2
        only_in_2 = words2 - words1

        differences = []

        if only_in_1:
            # Find significant words (longer than 3 chars)
            significant = [w for w in only_in_1 if len(w) > 3][:10]
            if significant:
                differences.append(f"Solo nel primo: {', '.join(significant)}")

        if only_in_2:
            significant = [w for w in only_in_2 if len(w) > 3][:10]
            if significant:
                differences.append(f"Solo nel secondo: {', '.join(significant)}")

        return differences

    def compare(self, url1: str, text1: str, url2: str, text2: str) -> SimilarityResult:
        """Compare two pages for similarity.

        Args:
            url1: First URL
            text1: First page content
            url2: Second URL
            text2: Second page content

        Returns:
            SimilarityResult with similarity score and details
        """
        # Use SimHash for quick check
        hash1 = self.compute_simhash(text1)
        hash2 = self.compute_simhash(text2)
        simhash_sim = self.simhasher.similarity(hash1, hash2)

        # If SimHash suggests similarity, do more accurate check
        if simhash_sim > 0.7:
            # Use cosine similarity for more accuracy
            cosine_sim = self.cosine_similarity(text1, text2)
            similarity = (simhash_sim + cosine_sim) / 2

            differences = None
            if similarity >= self.similarity_threshold:
                differences = self.find_differences(text1, text2)

            return SimilarityResult(
                url1=url1,
                url2=url2,
                similarity=similarity,
                method='simhash+cosine',
                differences=differences
            )
        else:
            return SimilarityResult(
                url1=url1,
                url2=url2,
                similarity=simhash_sim,
                method='simhash'
            )

    def find_duplicates(self, pages: List[Tuple[str, str]]) -> Dict[str, List[SimilarityResult]]:
        """Find duplicate groups among pages.

        Args:
            pages: List of (url, text_content) tuples

        Returns:
            Dictionary mapping representative URL to list of similar pages
        """
        if not pages:
            return {}

        # Compute SimHashes for all pages
        hashes = []
        for url, text in pages:
            simhash = self.compute_simhash(text)
            hashes.append((url, text, simhash))

        # Group similar pages
        duplicate_groups: Dict[str, List[SimilarityResult]] = {}
        processed: Set[str] = set()

        for i, (url1, text1, hash1) in enumerate(hashes):
            if url1 in processed:
                continue

            group = []
            for j, (url2, text2, hash2) in enumerate(hashes):
                if i >= j or url2 in processed:
                    continue

                # Quick SimHash check
                sim = self.simhasher.similarity(hash1, hash2)
                if sim >= 0.7:
                    # Detailed comparison
                    result = self.compare(url1, text1, url2, text2)
                    if result.similarity >= self.similarity_threshold:
                        group.append(result)
                        processed.add(url2)

            if group:
                duplicate_groups[url1] = group
                processed.add(url1)

        return duplicate_groups

    def categorize_similarity(self, similarity: float) -> str:
        """Categorize similarity score.

        Args:
            similarity: Similarity score (0-1)

        Returns:
            Category string
        """
        if similarity >= 0.95:
            return "duplicato_esatto"
        elif similarity >= 0.85:
            return "quasi_duplicato"
        elif similarity >= 0.70:
            return "contenuto_simile"
        else:
            return "diverso"
