from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
)

from rest_framework import status
# from rest_framework.authentication import TokenAuthentication
# from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from seo import seo_analyzer

from seo.serializers import SEOResultSerializer


def calculate_seo_score(data):
    """
    Calculate the SEO score based on the analysis data.
    """
    total_tests = len(data)
    passed_tests = 0
    warnings = 0
    failed_tests = 0

    for key, value in data.items():
        if value["status"] == "passed":
            passed_tests += 1
        elif value["status"] == "warning":
            warnings += 0.5
        elif value["status"] == "failed":
            failed_tests += 1

    score = (
        (passed_tests + warnings) * 100 / total_tests
        if total_tests > 0 else 0
    )

    return {
        "total_tests": total_tests,
        "score": round(score),
        "passed_tests": passed_tests,
        "warnings": warnings,
        "failed_tests": failed_tests,
    }


class SEOView(APIView):
    """
    API view for handling SEO-related requests.
    """
    # authentication_classes = [TokenAuthentication]
    # permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='url',
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description='URL of the website to analyze',
            )
        ],
        responses={200: SEOResultSerializer}
    )
    def get(self, request, format=None):
        url = request.query_params.get('url')
        res = seo_analyzer.analyze_url(url)

        if res["status"] == "error":
            return Response(
                res,
                status=status.HTTP_400_BAD_REQUEST
            )

        seo_score = calculate_seo_score(res["checks"])

        serializer = SEOResultSerializer(
            data={
                "status": res["status"],
                "analysis_time": res["analysis_time"],
                "url": url,
                "seo_score": seo_score,
                "seo_analysis_data": res["checks"],
            }
        )

        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
