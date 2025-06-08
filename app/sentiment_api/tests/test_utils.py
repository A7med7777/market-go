"""
Tests for utility functions.
"""
from django.test import TestCase

from sentiment_api.utils import SentimentAnalyzer


class TestSentimentAnalyzer(TestCase):
    """Test cases for SentimentAnalyzer utility class."""

    def setUp(self):
        """Set up test dependencies."""
        self.analyzer = SentimentAnalyzer()

    def test_split_into_sentences_with_valid_text(self):
        """Test splitting text into sentences with valid input."""
        text = "I love this product! It works great. Amazing quality."

        expected = [
            "I love this product!",
            "It works great.",
            "Amazing quality."
        ]

        result = self.analyzer.split_into_sentences(text)
        self.assertEqual(result, expected)

    def test_split_into_sentences_with_empty_text(self):
        """Test splitting empty text returns empty list."""
        result = self.analyzer.split_into_sentences("")
        self.assertEqual(result, [])

    def test_split_into_sentences_with_none(self):
        """Test splitting None returns empty list."""
        result = self.analyzer.split_into_sentences(None)
        self.assertEqual(result, [])

    def test_split_into_sentences_with_single_sentence(self):
        """Test splitting single sentence without punctuation."""
        text = "This is a single sentence"
        result = self.analyzer.split_into_sentences(text)
        self.assertEqual(result, ["This is a single sentence"])

    def test_analyze_sentiment_positive(self):
        """Test sentiment analysis returns positive for positive text."""
        text = "I absolutely love this amazing product!"
        result = self.analyzer.analyze_sentiment(text)
        self.assertEqual(result, "positive")

    def test_analyze_sentiment_negative(self):
        """Test sentiment analysis returns negative for negative text."""
        text = "This product is terrible, awful, and completely useless!"
        result = self.analyzer.analyze_sentiment(text)
        self.assertEqual(result, "negative")

    def test_analyze_sentiment_neutral(self):
        """Test sentiment analysis returns neutral for neutral text."""
        text = "This is a product description."
        result = self.analyzer.analyze_sentiment(text)
        self.assertEqual(result, "neutral")

    def test_analyze_sentiment_empty_text(self):
        """Test sentiment analysis returns neutral for empty text."""
        result = self.analyzer.analyze_sentiment("")
        self.assertEqual(result, "neutral")

    def test_analyze_sentiment_none(self):
        """Test sentiment analysis returns neutral for None."""
        result = self.analyzer.analyze_sentiment(None)
        self.assertEqual(result, "neutral")

    def test_process_comment_valid_input(self):
        """Test processing a valid comment."""
        comment = "Great product! However, shipping was slow."
        result = self.analyzer.process_comment(comment)

        # Verify structure and first sentence
        self.assertEqual(result["comment"], comment)
        self.assertEqual(len(result["sentences"]), 2)
        self.assertEqual(result["sentences"][0]["sentence"], "Great product!")
        self.assertEqual(result["sentences"][0]["sentiment"], "positive")

        self.assertEqual(
            result["sentences"][1]["sentence"],
            "However, shipping was slow."
        )

        self.assertIn(
            result["sentences"][1]["sentiment"],
            ["negative", "neutral"]
        )

    def test_process_comment_clearly_negative(self):
        """Test processing a comment with clearly negative sentiment."""
        comment = "Excellent product! This is absolutely terrible and useless."
        result = self.analyzer.process_comment(comment)

        # Verify structure
        self.assertEqual(result["comment"], comment)
        self.assertEqual(len(result["sentences"]), 2)

        # First sentence should be positive
        self.assertEqual(
            result["sentences"][0]["sentence"],
            "Excellent product!"
        )

        self.assertEqual(result["sentences"][0]["sentiment"], "positive")

        # Second sentence should be negative
        self.assertEqual(
            result["sentences"][1]["sentence"],
            "This is absolutely terrible and useless."
        )

        self.assertEqual(result["sentences"][1]["sentiment"], "negative")

    def test_process_comment_empty_input(self):
        """Test processing empty comment."""
        result = self.analyzer.process_comment("")
        expected = {
            "comment": "",
            "sentences": []
        }
        self.assertEqual(result, expected)
