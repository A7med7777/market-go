"""
API views for sentiment analysis.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiParameter,
)

from .serializers import SentimentRequestSerializer, CommentAnalysisSerializer
from .utils import SentimentAnalyzer
from .comments_scraper import run_scraper


class SentimentAnalysisView(APIView):
    """
    API endpoint that analyzes sentiment of comments at the sentence level.
    """

    def __init__(self, **kwargs):
        """Initialize the view with sentiment analyzer."""
        super().__init__(**kwargs)
        self.analyzer = SentimentAnalyzer()

    @extend_schema(
        request=SentimentRequestSerializer,
        parameters=[
            OpenApiParameter(
                name='url',
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description='URL to scrape comments from',
            )
        ],
        responses={
            200: CommentAnalysisSerializer(many=True),
            400: OpenApiExample(
                'Bad Request',
                value={
                    "error": "Invalid input",
                    "details": {
                        "comments": ["This field is required."]
                    }
                },
                response_only=True
            ),
            500: OpenApiExample(
                'Server Error',
                value={
                    "error": "Error processing comments",
                    "details": "Processing error details"
                },
                response_only=True
            )
        },
        summary="Analyze sentiment of comments",
        description=(
            "Process a batch of comments and analyze sentiment at the "
            "sentence level. Returns sentiment analysis (positive, negative, "
            "neutral) for each sentence in each comment."
        ),
    )
    def post(self, request, *args, **kwargs):
        """
        Process a batch of comments for sentiment analysis.
        """
        # Validate input
        url = request.query_params.get('url')
        data = run_scraper(url)

        if "error" in data:
            return Response(
                {"error": "Scraper error", "details": data["error"]},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SentimentRequestSerializer(data=data)

        if not serializer.is_valid():
            return Response(
                {"error": "Invalid input", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        comments = serializer.validated_data.get('comments', [])

        # Handle empty input
        if not comments:
            return Response([], status=status.HTTP_200_OK)

        # Process each comment
        results = []
        try:
            for comment in comments:
                processed_comment = self.analyzer.process_comment(comment)
                results.append(processed_comment)
        except Exception as e:
            return Response(
                {"error": "Error processing comments", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        positive_count = 0
        negative_count = 0
        neutral_count = 0

        for result in results:
            if "sentences" in result:
                for sentence in result["sentences"]:
                    sentiment = sentence.get("sentiment", "neutral")
                    if sentiment == "positive":
                        positive_count += 1
                    elif sentiment == "negative":
                        negative_count += 1
                    elif sentiment == "neutral":
                        neutral_count += 1

        final_result = {
            "comments": results,
            "summary": {
                "positive_count": positive_count,
                "negative_count": negative_count,
                "neutral_count": neutral_count
            }
        }

        return Response(final_result, status=status.HTTP_200_OK)
