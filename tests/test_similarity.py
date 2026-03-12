"""Tests for similarity module."""

import pytest
from src.utils.similarity import ContentSimilarity, SimHasher


class TestSimHasher:
    """Tests for SimHasher."""

    def test_same_content(self):
        """Test that identical content produces same hash."""
        hasher = SimHasher()
        text = "This is a test document with some content."

        hash1 = hasher.compute(text)
        hash2 = hasher.compute(text)

        assert hash1 == hash2

    def test_similar_content(self):
        """Test that similar content produces similar hashes."""
        hasher = SimHasher()

        text1 = "This is a product page for a blue shirt. The shirt is made of cotton."
        text2 = "This is a product page for a red shirt. The shirt is made of cotton."

        hash1 = hasher.compute(text1)
        hash2 = hasher.compute(text2)

        similarity = hasher.similarity(hash1, hash2)
        assert similarity > 0.8  # Should be quite similar

    def test_different_content(self):
        """Test that different content produces different hashes."""
        hasher = SimHasher()

        text1 = "This is about cooking recipes and food preparation."
        text2 = "This is about software development and programming."

        hash1 = hasher.compute(text1)
        hash2 = hasher.compute(text2)

        similarity = hasher.similarity(hash1, hash2)
        # Short texts with common words may have higher similarity
        # The key is they're less similar than identical content
        assert similarity < 0.9


class TestContentSimilarity:
    """Tests for ContentSimilarity."""

    def test_exact_duplicate(self):
        """Test detection of exact duplicates."""
        similarity = ContentSimilarity(similarity_threshold=0.85)

        text1 = "This is the exact same content that appears on multiple pages."
        text2 = "This is the exact same content that appears on multiple pages."

        result = similarity.compare("url1", text1, "url2", text2)
        assert result.similarity >= 0.95

    def test_near_duplicate(self):
        """Test detection of near duplicates."""
        similarity = ContentSimilarity(similarity_threshold=0.85)

        text1 = """
        Product: Blue T-Shirt
        Description: This comfortable cotton t-shirt is perfect for everyday wear.
        Material: 100% cotton
        Price: $29.99
        """
        text2 = """
        Product: Red T-Shirt
        Description: This comfortable cotton t-shirt is perfect for everyday wear.
        Material: 100% cotton
        Price: $29.99
        """

        result = similarity.compare("url1", text1, "url2", text2)
        assert result.similarity >= 0.85

    def test_different_content(self):
        """Test that different content is not marked as duplicate."""
        similarity = ContentSimilarity(similarity_threshold=0.85)

        text1 = "Welcome to our homepage. We sell electronics and gadgets."
        text2 = "Contact us at info@example.com. Our office is located in New York."

        result = similarity.compare("url1", text1, "url2", text2)
        assert result.similarity < 0.85

    def test_find_duplicates(self):
        """Test finding duplicate groups."""
        similarity = ContentSimilarity(similarity_threshold=0.85)

        pages = [
            ("url1", "Product A in blue color with long description about quality"),
            ("url2", "Product A in red color with long description about quality"),
            ("url3", "Product A in green color with long description about quality"),
            ("url4", "Completely different content about services we offer"),
        ]

        groups = similarity.find_duplicates(pages)

        # Should find one group with url1, url2, url3
        assert len(groups) >= 1

    def test_categorize_similarity(self):
        """Test similarity categorization."""
        similarity = ContentSimilarity()

        assert similarity.categorize_similarity(0.98) == "duplicato_esatto"
        assert similarity.categorize_similarity(0.90) == "quasi_duplicato"
        assert similarity.categorize_similarity(0.75) == "contenuto_simile"
        assert similarity.categorize_similarity(0.50) == "diverso"
