from rest_framework import serializers


class SEOCheckSerializer(serializers.Serializer):
    common_keywords = serializers.ListField(child=serializers.CharField(), required=False)
    status = serializers.CharField()
    description = serializers.CharField(style={"base_template": "textarea.html"})
    code_snippet = serializers.ListField(child=serializers.CharField(style={"base_template": "textarea.html"}), required=False, allow_null=True)
    missing_alt = serializers.ListField(child=serializers.CharField(), required=False)
    redundant_alt = serializers.ListField(child=serializers.CharField(), required=False)
    short_alt = serializers.ListField(child=serializers.CharField(), required=False)
    duplicate_alt = serializers.ListField(child=serializers.CharField(), required=False)
    how_to_fix = serializers.CharField(style={"base_template": "textarea.html"}, required=False, allow_null=True)
    heading_order = serializers.ListField(child=serializers.CharField(), required=False)
    missing_levels = serializers.ListField(child=serializers.CharField(), required=False)
    out_of_order = serializers.BooleanField(required=False)


class SEOResultSerializer(serializers.Serializer):
    status = serializers.CharField()
    analysis_time = serializers.CharField()
    url = serializers.URLField()
    seo_score = serializers.DictField()
    seo_analysis_data = serializers.DictField(child=SEOCheckSerializer())
