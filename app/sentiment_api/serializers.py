"""
Serializers for the sentiment API - Implemented to pass tests.
"""
from rest_framework import serializers


class SentenceAnalysisSerializer(serializers.Serializer):
    """Serializer for sentence-level sentiment analysis."""
    sentence = serializers.CharField()
    sentiment = serializers.CharField()


class CommentAnalysisSerializer(serializers.Serializer):
    """Serializer for comment-level sentiment analysis."""
    comment = serializers.CharField()
    sentences = SentenceAnalysisSerializer(many=True)


class SentimentRequestSerializer(serializers.Serializer):
    """Serializer for incoming sentiment analysis requests."""
    comments = serializers.ListField(
        allow_empty=True
    )

    def validate_comments(self, value):
        """Validate that all comments are strings."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Comments must be a list")

        for i, comment in enumerate(value):
            if not isinstance(comment, str):
                raise serializers.ValidationError(
                    f"Comment at index {i} must be a string, "
                    f"got {type(comment).__name__}"
                )
        return value
