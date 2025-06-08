"""
Tests for serializers - Written first following TDD approach.
"""
from django.test import TestCase
from sentiment_api.serializers import SentimentRequestSerializer
from sentiment_api.serializers import CommentAnalysisSerializer


class TestSentimentRequestSerializer(TestCase):
    """Test cases for SentimentRequestSerializer."""

    def test_valid_data(self):
        """Test serializer with valid data."""
        data = {"comments": ["Test comment 1", "Test comment 2"]}
        serializer = SentimentRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(
            serializer.validated_data['comments'],
            data['comments']
        )

    def test_empty_comments_list(self):
        """Test serializer with empty comments list."""
        data = {"comments": []}
        serializer = SentimentRequestSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['comments'], [])

    def test_missing_comments_field(self):
        """Test serializer with missing comments field."""
        data = {}
        serializer = SentimentRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('comments', serializer.errors)

    def test_non_string_comments(self):
        """Test serializer with non-string comments."""
        data = {"comments": ["Valid comment", 123, None]}
        serializer = SentimentRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('comments', serializer.errors)

    def test_non_list_comments(self):
        """Test serializer with non-list comments field."""
        data = {"comments": "Not a list"}
        serializer = SentimentRequestSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class TestCommentAnalysisSerializer(TestCase):
    """Test cases for CommentAnalysisSerializer."""

    def test_serialization_valid_data(self):
        """Test serialization of valid comment analysis data."""
        data = {
            "comment": "Test comment",
            "sentences": [
                {"sentence": "Test sentence", "sentiment": "positive"}
            ]
        }
        serializer = CommentAnalysisSerializer(data)
        expected_data = data
        self.assertEqual(serializer.data, expected_data)
