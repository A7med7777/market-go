from django.urls import path

from rest_framework.urlpatterns import format_suffix_patterns

from seo.views import SEOView

urlpatterns = format_suffix_patterns(
    [path('', SEOView.as_view(), name='seo-analyzer')]
)
