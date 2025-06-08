"""
Tests for API views.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
import json


class TestSentimentAnalysisView(TestCase):
    """Test cases for SentimentAnalysisView."""

    def setUp(self):
        """Set up test client."""
        self.client = APIClient()
        self.url = reverse('analyze_sentiment')

    def test_valid_request_returns_200(self):
        """Test that valid request returns 200 status."""
        data = {"comments": ["Great product!", "Terrible service."]}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_valid_request_returns_correct_structure(self):
        """Test that valid request returns correct response structure."""
        data = {"comments": ["Great product!"]}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertIsInstance(response_data, list)
        self.assertEqual(len(response_data), 1)

        comment_analysis = response_data[0]
        self.assertIn('comment', comment_analysis)
        self.assertIn('sentences', comment_analysis)
        self.assertEqual(comment_analysis['comment'], "Great product!")
        self.assertIsInstance(comment_analysis['sentences'], list)

    def test_empty_comments_list_returns_empty_response(self):
        """Test that empty comments list returns empty response."""
        data = {"comments": []}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_invalid_data_returns_400(self):
        """Test that invalid data returns 400 status."""
        data = {"comments": "not a list"}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_comments_field_returns_400(self):
        """Test that missing comments field returns 400 status."""
        data = {}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_string_comments_returns_400(self):
        """Test that non-string comments return 400 status."""
        data = {"comments": ["Valid comment", 123]}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('sentiment_api.views.SentimentAnalyzer')
    def test_processing_error_returns_500(self, mock_analyzer_class):
        """Test that processing errors return 500 status."""
        mock_analyzer = MagicMock()

        mock_analyzer.process_comment.side_effect = Exception(
            "Processing error"
        )

        mock_analyzer_class.return_value = mock_analyzer

        data = {"comments": ["Test comment"]}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    def test_multiple_comments_processing(self):
        """Test processing multiple comments."""
        data = {"comments": ["Great!", "Terrible!", "Okay product."]}
        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(len(response_data), 3)

        for i, comment_analysis in enumerate(response_data):
            self.assertEqual(comment_analysis['comment'], data['comments'][i])
