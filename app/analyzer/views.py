from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
from bs4 import BeautifulSoup
import nltk
from nltk.tokenize import word_tokenize
from urllib.parse import urlparse, urljoin
from .serializers import SEOAnalyzerSerializer


nltk.download('stopwords', quiet=True)
nltk.download('punkt_tab')
nltk.download('punkt', quiet=True)  # Ensure 'punkt' is available


def fetch_page(url_to_fetch):
    """Fetches the HTML content of a given URL."""
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        response = requests.get(url_to_fetch, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text, response.headers, response.url
    except requests.exceptions.RequestException as re:
        print(f"Error fetching page: {re}")
        return None, None, None


def analyze_keywords(soup):
    """Finds frequently occurring words using TF-IDF."""
    text = soup.get_text()
    words = [word.lower() for word in word_tokenize(text)]
    stopwords = set(nltk.corpus.stopwords.words('english'))
    filtered_words = [
        word for word in words if word.isalpha() and word not in stopwords
    ]
    freq = nltk.FreqDist(filtered_words)
    return freq.most_common(10)


def analyze_meta(soup, meta_name):
    """Analyzes the meta description or other meta-tags."""
    meta = soup.find("meta", attrs={"name": meta_name})
    return meta["content"] if meta else "Not Found"


def analyze_headings(soup, tag):
    """Extracts all specified heading tags."""
    return [h.get_text().strip() for h in soup.find_all(tag)]


def analyze_images(soup):
    """Analyzes the 'alt' attributes of images."""
    img_tags = soup.find_all("img")
    images = {}

    for image in img_tags:
        alt_text = image.get("alt", "").strip()
        images[image.get("src", "Unknown")] = \
            alt_text if alt_text else "Missing"

    return images


def analyze_lazy_loading(soup):
    """Checks if images use lazy loading."""
    return all(
        img.get("loading", "") == "lazy" for img in soup.find_all("img")
    )


def analyze_links(soup, base_url):
    """Checks the ratio of internal to external links."""
    internal, external, broken = 0, 0, 0
    parsed_url = urlparse(base_url)
    domain = parsed_url.netloc
    a_tags = soup.find_all("a")

    for a in a_tags:
        href = a.get("href")

        if not href:
            continue

        full_url = urljoin(base_url, href)

        try:
            response = requests.get(full_url, timeout=10)

            if response.status_code >= 400:
                broken += 1
                continue
        except requests.exceptions.RequestException:
            broken += 1
            continue

        if urlparse(full_url).netloc == domain:
            internal += 1
        else:
            external += 1

    total_links = len(a_tags) or 1  # Prevents division by zero

    return {
        "internal_links": internal,
        "internal_percentage": (internal / total_links) * 100,
        "external_links": external,
        "external_percentage": (external / total_links) * 100,
        "broken_links": broken,
        "broken_percentage": (broken / total_links) * 100,
    }


def check_canonical(soup):
    """Checks for a canonical URL."""
    canonical = soup.find("link", rel="canonical")
    return canonical["href"] if canonical else "Not Found"


def check_noindex(soup):
    """Checks if the page has a noindex meta tag."""
    meta = soup.find("meta", attrs={"name": "robots"})
    return "noindex" in meta["content"] if meta else False


def check_opengraph(soup):
    """Checks if OpenGraph meta tags exist."""
    return bool(
        soup.find("meta", property=lambda x: x and x.startswith("og:"))
    )


def check_robots_txt(url):
    """Checks for a valid robots.txt file."""
    try:
        parsed_url = urlparse(url)
        robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
        response = requests.get(robots_url, timeout=10)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def analyze_schema_org(soup):
    """Checks for Schema.org metadata."""
    return bool(soup.find(attrs={"itemtype": True}))


def check_favicon(soup):
    """Checks if the site has a favicon."""
    return bool(soup.find("link", rel="icon"))


def check_amp(soup):
    """Checks for the presence of an AMP page."""
    return bool(soup.find("link", rel="amphtml"))


def check_http_redirect(url):
    """Checks if HTTP requests redirect to HTTPS."""
    try:
        http_url = url.replace("https://", "http://")
        response = requests.get(http_url, allow_redirects=True, timeout=10)
        return response.url.startswith("https")
    except requests.exceptions.RequestException:
        return False


def check_404_page(url):
    """Checks if the site has a custom 404 page."""
    try:
        test_url = url.rstrip("/") + "/nonexistentpage"
        response = requests.get(test_url, timeout=10)
        return response.status_code == 404
    except requests.exceptions.RequestException:
        return False


def check_text_compression(headers):
    """Checks if the server supports text compression (gzip or Brotli)."""
    return "gzip" in headers.get("Content-Encoding", "") or \
        "br" in headers.get("Content-Encoding", "")


def check_viewport_meta(soup):
    """Checks if the page has a viewport meta-tag for mobile-friendliness."""
    return bool(soup.find("meta", attrs={"name": "viewport"}))


def check_social_meta(soup):
    """Checks if the page includes Twitter Card and OpenGraph meta-tags."""
    return bool(soup.find("meta", attrs={"name": "twitter:card"}))


def check_iframe_usage(soup):
    """Checks if the page has too many iframes."""
    return len(soup.find_all("iframe"))


class SEOAnalyzerView(APIView):
    def post(self, request):
        serializer = SEOAnalyzerSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        url = serializer.validated_data["url"]
        if not url:
            return Response(
                {"error": "URL is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        html, headers, final_url = fetch_page(url)
        if not html:
            return Response(
                {"error": "Failed to fetch page"},
                status=status.HTTP_400_BAD_REQUEST
            )

        soup = BeautifulSoup(html, "html.parser")

        report = {
            "keywords": analyze_keywords(soup),
            "meta_description": analyze_meta(soup, "description"),
            "h1_tags": analyze_headings(soup, "h1"),
            "h2_tags": analyze_headings(soup, "h2"),
            "images": analyze_images(soup),
            "lazy_loading": analyze_lazy_loading(soup),
            "links": analyze_links(soup, final_url),
            "canonical_url": check_canonical(soup),
            "noindex_meta": check_noindex(soup),
            "opengraph": check_opengraph(soup),
            "robots_txt": check_robots_txt(final_url),
            "schema_org": analyze_schema_org(soup),
            "secure_connection": final_url.startswith("https"),
            "favicon_present": check_favicon(soup),
            "amp_page": check_amp(soup),
            "http_to_https_redirect": check_http_redirect(final_url),
            "custom_404_page": check_404_page(final_url),
            "text_compression": check_text_compression(headers),
            "viewport_meta": check_viewport_meta(soup),
            "social_meta": check_social_meta(soup),
            "iframe_count": check_iframe_usage(soup),
        }

        return Response(report, status=status.HTTP_200_OK)
