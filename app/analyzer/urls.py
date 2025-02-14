from django.urls import path
from .views import SEOAnalyzerView

app_name = "analyzer"

urlpatterns = [
    path("analyze/", SEOAnalyzerView.as_view(), name="seo-analyze"),
]
