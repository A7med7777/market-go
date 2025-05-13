from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

SEO_ANALYZER_URL = reverse('seo-analyzer')


def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)


# class PublicSEOAPITests(TestCase):
#     """Test unauthenticated API requests."""

#     def setUp(self):
#         self.client = APIClient()

#     def test_auth_required(self):
#         """Test auth is required to call API."""
#         res = self.client.get(SEO_ANALYZER_URL)
#         self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateSEOAPITests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.user = create_user(
            email="user@example.com",
            password="testPass123"
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_seo_analyze_successful(self):
        """Test successful SEO analysis."""

        res = self.client.get(
            SEO_ANALYZER_URL,
            {"url": "https://example.com"}
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("seo_score", res.data)

    def test_seo_analyze_invalid_url(self):
        """Test SEO analysis with invalid URL."""
        res = self.client.get(SEO_ANALYZER_URL, params={"url": "invalid-url"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["status"], "error")

    def test_seo_analyze_no_url(self):
        """Test SEO analysis without URL."""
        res = self.client.get(SEO_ANALYZER_URL)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["status"], "error")
