from rest_framework import serializers
from urllib.parse import urlparse


def is_valid_url(url):
    """Checks if a given URL is valid."""
    parsed = urlparse(url)
    return bool(parsed.scheme and parsed.netloc)


class SEOAnalyzerSerializer(serializers.Serializer):
    url = serializers.CharField()

    def validate_url(self, value):
        """Ensure URL is well-formed before making a request."""
        if not is_valid_url(value):
            raise serializers.ValidationError("Invalid URL format.")
        return value
