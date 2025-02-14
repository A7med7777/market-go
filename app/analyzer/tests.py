from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status


class SEOAnalyzerAPITest(TestCase):
    def setUp(self):
        """Set up test client"""
        self.client = APIClient()
        self.url = "/api/analyze/"  # API endpoint

    def test_invalid_url(self):
        response = self.client.post(self.url, {"url": "invalid-url"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("url", response.data)
        self.assertEqual(response.data["url"][0], "Invalid URL format.")

    def test_missing_url(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("url", response.data)
        self.assertEqual(response.data["url"][0], "This field is required.")

    def test_valid_url(self):
        """Test API returns SEO analysis for a valid URL"""
        response = self.client.post(self.url, {"url": "https://example.com"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("keywords", response.data)
        self.assertIn("meta_description", response.data)
