import time
from typing import List

import re
import nltk
import json
import requests

from collections import Counter, defaultdict

from bs4 import BeautifulSoup
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from urllib.parse import urlparse, urljoin

try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')


def summarize(el):
    return str(el)[:100].replace("\n", "") + "..." if el else None


def fetch_page(url_to_fetch):
    """Fetches the HTML content of a given URL."""
    if not url_to_fetch or not isinstance(url_to_fetch, str):
        print("Invalid URL provided.")
        return None, None, None

    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        response = requests.get(url_to_fetch, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text, response.headers, response.url
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page: {e}")
        return None, None, None


def analyze_keywords(soup):
    """Finds frequently occurring words using word frequency."""
    if soup is None or not hasattr(soup, 'get_text'):
        return {
            "common_keywords": [],
            "status": "failed",
            "description": "Could not extract text from the provided HTML.",
            "code_snippet": None,
            "how_to_fix": "Ensure valid BeautifulSoup object is passed."
        }

    text = soup.get_text()
    words = [word.lower() for word in word_tokenize(text)]
    stop_words = set(stopwords.words('english'))
    filtered_words = [word for word in words if word.isalpha() and word not in stop_words]
    freq = nltk.FreqDist(filtered_words)

    return {
        "common_keywords": [f"({item[0]}, {item[1]})" for item in freq.most_common(10)],
        "status": "passed",
        "description": "A list of keywords that appear frequently in the text of your content.",
        "code_snippet": None,
        "how_to_fix": None
    }


def check_title_tag(soup: BeautifulSoup):
    """Analyze title tag for SEO best practices."""
    title_tag = soup.find("title")

    if not title_tag or not title_tag.text.strip():
        return {
            "status": "failed",
            "description": "No title tag found or title is empty.",
            "code_snippet": None,
            "how_to_fix": "Add a descriptive title tag to your page: <title>Your Page Title</title>"
        }

    title_text = title_tag.text.strip()
    title_length = len(title_text)

    # Check if title is too short
    if title_length < 30:
        return {
            "status": "warning",
            "description": f"Title tag is too short ({title_length} characters). Ideal length is 50-60 characters.",
            "code_snippet": [str(title_tag)],
            "how_to_fix": "Expand your title to include more relevant keywords while keeping it under 60 characters."
        }

    # Check if title is too long (might be truncated in search results)
    if title_length > 60:
        return {
            "status": "warning",
            "description": f"Title tag is too long ({title_length} characters). It may be truncated in search results.",
            "code_snippet": [str(title_tag)],
            "how_to_fix": "Shorten your title to 50-60 characters to ensure it displays correctly in search results."
        }

    # Check for common SEO patterns in titles
    title_lower = title_text.lower()

    if title_lower.count(" - ") > 1 or title_lower.count(" | ") > 1:
        return {
            "status": "warning",
            "description": "Title tag contains multiple separators, which may look keyword-stuffed.",
            "code_snippet": [str(title_tag)],
            "how_to_fix": "Simplify your title structure by using only one separator between brand and page name."
        }

    return {
        "status": "passed",
        "description": f"Title tag is well-optimized with {title_length} characters.",
        "code_snippet": [str(title_tag)],
        "how_to_fix": "No changes needed. Your title tag is well-optimized."
    }


MIN_LENGTH = 50
MAX_LENGTH = 160

CANDIDATE_SELECTORS = [
    {"name": "description"},
    {"property": "og:description"},
    {"property": "description"},
    {"name": "twitter:description"},
]

def analyze_meta(soup: BeautifulSoup):
    """Analyze meta description tag(s) for SEO best practices."""

    # Find the first valid meta description tag with content
    meta = None
    for selector in CANDIDATE_SELECTORS:
        tag = soup.find("meta", attrs=selector)
        if tag and tag.has_attr("content") and tag["content"].strip():
            meta = tag
            break

    # Get all candidate tags for debugging or reporting malformed ones
    meta_tags = soup.find_all("meta")
    meta_descriptions = [
        tag for tag in meta_tags
        if (tag.get("name") == "description"
            or tag.get("property") in ["description", "og:description"]
            or tag.get("name") == "twitter:description")
    ]

    if meta is None:
        if meta_descriptions:
            return {
                "status": "warning",
                "description": "Meta description tags found but none have a valid 'content' attribute.",
                "code_snippet": [summarize(str(tag)) for tag in meta_descriptions[:3]],
                "how_to_fix": "Ensure your meta description tags include a non-empty 'content' attribute."
            }
        else:
            return {
                "status": "failed",
                "description": "No meta description was found for your page.",
                "code_snippet": [],
                "how_to_fix": "Add a meta description in the head section like: "
                              "<meta name=\"description\" content=\"Your description here\">. "
                              "Keep it between 50–160 characters summarizing the page content."
            }

    meta_content = ' '.join(meta["content"].split())
    length = len(meta_content)

    if length < MIN_LENGTH:
        return {
            "status": "warning",
            "description": f"Meta description is too short ({length} characters). Recommended is 50–160.",
            "code_snippet": [summarize(str(meta))],
            "how_to_fix": "Expand your meta description to better summarize your page content and include keywords."
        }

    if length > MAX_LENGTH:
        return {
            "status": "warning",
            "description": f"Meta description is too long ({length} characters). It may be truncated in search results.",
            "code_snippet": [summarize(str(meta))],
            "how_to_fix": "Shorten your meta description to fit within 160 characters."
        }

    return {
        "status": "passed",
        "description": f"Meta description is present and optimal ({length} characters).",
        "code_snippet": [summarize(str(meta))],
        "how_to_fix": "No changes needed. Your meta description is well-optimized."
    }


def analyze_h1s(soup):
    """Analyzes the usage of <h1> tags for SEO optimization."""
    headings = soup.find_all("h1")
    count = len(headings)
    snippet = [str(tag) for tag in headings]

    if count == 0:
        return {
            "status": "failed",
            "description": "No <h1> tag found on the page.",
            "code_snippet": None,
            "how_to_fix": "Include one clear and relevant <h1> tag to define the main topic of your page."
        }
    elif count == 1:
        return {
            "status": "passed",
            "description": "One <h1> tag found. Ideal for SEO.",
            "code_snippet": snippet,
            "how_to_fix": "No changes needed. Your <h1> structure is well-optimized."
        }
    else:
        return {
            "status": "warning",

            "description": f"{count} <h1> tags found. It's recommended to use only one <h1> tag per page for clear "
                           f"hierarchy.",

            "code_snippet": snippet,

            "how_to_fix": "Consolidate multiple <h1> tags into a single, primary heading to help search engines "
                          "understand your page's topic."
        }


def analyze_heading_structure(soup):
    """Analyzes the heading structure from <h1> to <h6> to detect hierarchy issues."""
    heading_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    found_headings = soup.find_all(heading_tags)

    # Store actual sequence of headings like ['h1', 'h2', 'h4', 'h3']
    heading_sequence = [tag.name for tag in found_headings]

    # Track numeric levels only, like [1, 2, 4, 3]
    numeric_levels = [int(tag.name[1]) for tag in found_headings]

    # Detect missing levels
    used_levels = sorted(set(numeric_levels))
    missing_levels = []
    for i in range(1, max(used_levels) + 1):
        if i not in used_levels:
            missing_levels.append(f"h{i}")

    # Detect out-of-order jumps (not strictly ascending or structured)
    out_of_order = False
    last_level = 0
    for level in numeric_levels:
        if level - last_level > 1 and last_level != 0:
            out_of_order = True
            break
        last_level = level

    # Prepare code snippet
    code_snippet = [str(tag) for tag in found_headings]

    # Decision logic
    if not heading_sequence:
        return {
            "status": "failed",
            "description": "No heading tags (h1–h6) found on the page.",
            "code_snippet": None,
            "how_to_fix": "Use structured headings to define content hierarchy (starting from <h1>).",
            "heading_order": [],
            "missing_levels": ["h1", "h2", "h3", "h4", "h5", "h6"],
            "out_of_order": False
        }
    elif out_of_order or missing_levels:
        return {
            "status": "warning",
            "description": "Heading tags are either out of order or have skipped levels.",
            "code_snippet": None,

            "how_to_fix": "Ensure headings follow a logical structure (e.g., h1 → h2 → h3). Avoid skipping levels or "
                          "jumping back.",

            "heading_order": heading_sequence,
            "missing_levels": missing_levels,
            "out_of_order": out_of_order
        }
    else:
        return {
            "status": "passed",
            "description": "Heading tags are well-structured and follow a logical hierarchy.",
            "code_snippet": None,
            "how_to_fix": "No changes needed. Your heading structure is optimal.",
            "heading_order": heading_sequence,
            "missing_levels": [],
            "out_of_order": False
        }


def analyze_images(soup: BeautifulSoup):
    """Analyze img tags for 'alt' attribute quality."""
    images = soup.find_all("img")
    total = len(images)

    if total == 0:
        return {
            "status": "warning",
            "description": "No <img> tags found on the page.",
            "code_snippet": None,

            "how_to_fix": "If your page uses images, be sure to include descriptive alt attributes for accessibility "
                          "and SEO."
        }

    # Prepare filters with initial capacities
    missing_alt = []
    redundant_alt = []
    short_alt = []
    alt_values = []

    # Define weak alt texts as sets for O(1) lookups
    redundant_words = {"image", "photo", "pic", "picture", "img"}
    non_descriptive = {"a", "-", "x"}

    # Analyze all images in one pass
    for img in images:
        alt = img.get('alt')

        if not alt or alt.strip() == "":
            missing_alt.append(img)
        else:
            alt_clean = alt.strip().lower()
            alt_values.append(alt_clean)

            if alt_clean in redundant_words:
                redundant_alt.append(img)
            elif len(alt_clean) < 3 or alt_clean in non_descriptive:
                short_alt.append(img)

    # Use Counter for frequency analysis - more efficient
    alt_count = Counter(alt_values)
    duplicate_values = {alt for alt, count in alt_count.items() if count > 1}

    # Build issues list efficiently
    issues = []

    if missing_alt:
        issues.append(f"{len(missing_alt)} missing alt")

    if redundant_alt:
        issues.append(f"{len(redundant_alt)} redundant alt")

    if short_alt:
        issues.append(f"{len(short_alt)} very short/non-descriptive alt")

    if duplicate_values:
        issues.append(f"{len(duplicate_values)} duplicate alt text values")

    # Return appropriate result
    if not issues:
        return {
            "status": "passed",
            "description": f"All {total} images have clear, descriptive 'alt' attributes.",
            "code_snippet": [str(img) for img in images[:3]] + (["..."] if total > 3 else []),
            "how_to_fix": "No changes needed. Your images are well-optimized."
        }

    return {
        "status": "warning" if missing_alt or redundant_alt or short_alt else "failed",
        "description": f"Issues detected with image alt attributes: {', '.join(issues)}.",
        "code_snippet": None,
        "missing_alt": [str(img) for img in missing_alt[:3]] + (["..."] if len(missing_alt) > 3 else []),
        "redundant_alt": [str(img) for img in redundant_alt[:3]] + (["..."] if len(redundant_alt) > 3 else []),
        "short_alt": [str(img) for img in short_alt[:3]] + (["..."] if len(short_alt) > 3 else []),
        "duplicate_alt": list(duplicate_values)[:5] + (["..."] if len(duplicate_values) > 5 else []),

        "how_to_fix": "Ensure all images have descriptive, unique 'alt' text. Avoid generic words like 'image', "
                      "'pic', or 'photo'. Don't use extremely short or duplicate alt texts."
    }


def analyze_lazy_loading(soup: BeautifulSoup):
    """Check for lazy loading on images and iframes."""
    # Find all images and iframes in one soup operation
    media_elements = soup.find_all(['img', 'iframe'])
    total = len(media_elements)

    if total == 0:
        return {
            "status": "warning",
            "description": "No <img> or <iframe> elements found for lazy loading analysis.",
            "code_snippet": None,
            "how_to_fix": "If your page includes images or iframes, use lazy loading to improve performance."
        }

    # Check which elements are missing lazy loading in one pass
    missing_lazy = [el for el in media_elements if el.get("loading", "").strip().lower() != "lazy"]
    missing_count = len(missing_lazy)

    if missing_count == total:
        return {
            "status": "failed",
            "description": "None of the <img> or <iframe> elements use lazy loading.",
            "code_snippet": [summarize(el) for el in missing_lazy[:3]] + (["..."] if missing_count > 3 else []),
            "how_to_fix": "Add `loading=\"lazy\"` to your <img> and <iframe> tags to defer off screen content."
        }
    elif missing_count > 0:
        return {
            "status": "warning",
            "description": f"{missing_count} of {total} image/iframe elements are missing `loading=\"lazy\"`.",
            "code_snippet": [summarize(el) for el in missing_lazy[:3]] + (["..."] if missing_count > 3 else []),
            "how_to_fix": "Add `loading=\"lazy\"` to these elements to improve performance and reduce initial load."
        }
    else:
        return {
            "status": "passed",
            "description": f"All {total} <img> and <iframe> elements use lazy loading.",
            "code_snippet": [summarize(el) for el in media_elements[:3]] + (["..."] if total > 3 else []),
            "how_to_fix": "No changes needed. Lazy loading is properly implemented."
        }


def analyze_links(soup: BeautifulSoup, base_url: str):
    """Analyze links."""
    parsed_url = urlparse(base_url)
    domain = parsed_url.netloc
    a_tags = soup.find_all("a")

    if not a_tags:
        return {
            "status": "failed",
            "description": "No usable links found. A page should guide users through relevant internal and external "
                           "pages.",
            "code_snippet": None,
            "how_to_fix": "Add meaningful internal and external links to guide users and improve SEO."
        }

    internal, external, broken = [], [], []

    # Prepare full URLs and categorize without making requests yet
    urls_to_check = []

    for a in a_tags:
        href = a.get("href")

        if not href or href.strip().startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        full_url = urljoin(base_url, href.strip())
        urls_to_check.append((full_url, a.get_text(strip=True) or "[No anchor text]"))

        # Pre-categorize as internal or external based on domain
        if urlparse(full_url).netloc == domain:
            internal.append(full_url)
        else:
            external.append(full_url)

    # Check link validity asynchronously - only check the first 20 links
    check_limit = min(20, len(urls_to_check))

    def check_link(url_info):
        url, anchor_text = url_info
        try:
            # Try HEAD request first
            try:
                response = requests.head(url, allow_redirects=True, timeout=10)
                response.raise_for_status()
                if response.status_code < 400:  # Success or redirect
                    return url, "valid", anchor_text
            except requests.exceptions.RequestException:
                # If HEAD fails, try GET as fallback
                pass

            # Fallback to GET request if HEAD fails
            try:
                response = requests.get(url, allow_redirects=True, timeout=10)
                response.raise_for_status()
                if response.status_code < 400:  # Success or redirect
                    return url, "valid", anchor_text
                return url, "broken", anchor_text
            except requests.exceptions.RequestException:
                # Only mark as broken if both HEAD and GET fail
                return url, "broken", anchor_text

        except Exception as e:
            # Log the specific error for debugging
            error_type = type(e).__name__
            return url, "broken", f"{anchor_text} (Error: {error_type})"

    # Check links in chunks to avoid overwhelming the server
    broken_details = []
    if check_limit > 0:
        results = [check_link(url_info) for url_info in urls_to_check[:check_limit]]

        # Process results
        for result in results:
            if isinstance(result, tuple):
                url, status, anchor_text = result

                if status == "broken":
                    broken.append(url)
                    broken_details.append(f"{url} (Anchor: {anchor_text})")
                    # Remove from internal/external if broken
                    if url in internal:
                        internal.remove(url)
                    elif url in external:
                        external.remove(url)

    # Calculate statistics
    total = len(internal) + len(external) + len(broken)
    total_internal = len(internal)
    total_external = len(external)
    total_broken = len(broken)

    # Generate report
    def summarize_links(links):
        return links[:5] + (["...and more"] if len(links) > 5 else [])

    if total_broken > 0:
        return {
            "status": "warning",  # Changed from "failed" to "warning" since broken links need verification
            "description": f"{total_broken} potentially broken link(s) detected. Internal: {total_internal}, External: "
                           f"{total_external}, Potentially broken: {total_broken}",
            "code_snippet": summarize_links(broken_details),
            "how_to_fix": "Verify these links manually as they may be false positives. They either returned a 4xx/5xx "
                          "status code or timed out during testing."
        }
    elif total > 0:
        internal_ratio = total_internal / total

        if internal_ratio < 0.4:
            return {
                "status": "warning",
                "description": f"Low internal link ratio: {internal_ratio:.0%}. Internal: {total_internal}, External: "
                               f"{total_external}, Broken: {total_broken}",
                "code_snippet": summarize_links(internal),
                "how_to_fix": "Add more internal links to help users and search engines navigate your content "
                              "structure."
            }
        else:
            return {
                "status": "passed",
                "description": f"Healthy link profile. Internal: {total_internal}, External: {total_external}, Broken: "
                               f"{total_broken}",
                "code_snippet": summarize_links(internal + external),
                "how_to_fix": "No issues. Maintain a good balance of internal and external links."
            }
    else:
        return {
            "status": "failed",
            "description": "No usable links found after filtering out anchors and invalid URLs.",
            "code_snippet": None,
            "how_to_fix": "Add meaningful internal and external links to guide users and improve SEO."
        }


def check_canonical(soup):
    """Checks for a canonical URL inside the <head> section and validates its format."""
    head = soup.find("head")
    canonical_tag = soup.find("link", rel="canonical")
    canonical_href = canonical_tag.get("href") if canonical_tag else None

    if not canonical_tag or not canonical_href:
        return {
            "status": "failed",
            "description": "No canonical URL tag found. This may lead to duplicate content issues.",
            "code_snippet": None,

            "how_to_fix": "Add a canonical tag in the <head> section of your page to indicate the preferred version "
                          "of the URL, e.g. <link rel=\"canonical\" href=\"https://example.com/page\">."
        }

    if head and canonical_tag not in head:
        return {
            "status": "warning",
            "description": "Canonical tag found, but not inside the <head> section.",
            "code_snippet": [summarize(str(canonical_tag))],
            "how_to_fix": "Move your canonical tag into the <head> section for proper SEO recognition."
        }

    if not urlparse(canonical_href).scheme:
        return {
            "status": "warning",
            "description": f"Canonical tag uses a relative URL: {canonical_href}",
            "code_snippet": [summarize(str(canonical_tag))],
            "how_to_fix": "Use an absolute URL in your canonical tag to ensure search engines interpret it correctly."
        }

    return {
        "status": "passed",
        "description": f"Canonical URL is set correctly: {canonical_href}",
        "code_snippet": [summarize(str(canonical_tag))],
        "how_to_fix": "No action needed. Your canonical tag is correctly implemented."
    }


def check_noindex(soup):
    """Checks if the page has a noindex directive in robots or googlebot meta-tags."""
    meta_tags = soup.find_all("meta", attrs={"name": ["robots", "googlebot"]})
    noindex_tags = []

    for tag in meta_tags:
        content = tag.get("content", "").lower()

        if "noindex" in content:
            noindex_tags.append(tag)

    if noindex_tags:
        return {
            "status": "failed",

            "description": f'The page contains {len(noindex_tags)} meta tag(s) with a `noindex` directive, '
                           f'preventing it from being indexed by search engines.',

            "code_snippet": [str(tag) for tag in noindex_tags],
            "how_to_fix": "Remove the `noindex` directive(s) if you want this page to appear in search engine results."
        }
    elif len(meta_tags) > 1:
        return {
            "status": "warning",

            "description": f"Multiple meta robots or googlebot tags found ({len(meta_tags)} total). "
                           f"This could lead to conflicting instructions for search engines.",

            "code_snippet": [str(tag) for tag in meta_tags],
            "how_to_fix": "Ensure you only include one meta tag for robot directives to avoid ambiguity."
        }

    return {
        "status": "passed",
        "description": "No 'noindex' directive found. Your page is indexable by search engines.",
        "code_snippet": None,
        "how_to_fix": "No action needed."
    }


def parse_robots_directives(lines):
    directives = defaultdict(list)
    current_agent = None

    for line in lines:
        line = line.strip()
        if line.lower().startswith("user-agent:"):
            current_agent = line.split(":", 1)[1].strip()
        elif current_agent and line.lower().startswith("disallow:"):
            directives[current_agent].append(line.split(":", 1)[1].strip())

    return directives

def check_robots_txt(url):
    """Checks for the existence, accessibility, and structure of a robots.txt file."""
    parsed_url = urlparse(url)
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"

    try:
        response = requests.get(robots_url, timeout=10)
        content = response.text.strip()
        lines = content.splitlines()

        if response.status_code == 200:
            if not any("User-agent" in line for line in lines):
                return {
                    "status": "warning",
                    "description": "robots.txt file is accessible but contains no `User-agent` directives.",
                    "code_snippet": lines[:min(6, len(lines))],
                    "how_to_fix": "Add at least one `User-agent` directive to control bot behavior."
                }

            directives = parse_robots_directives(lines)
            has_disallow_all = "*" in directives and "/" in directives["*"]
            has_sitemap = any("Sitemap:" in line for line in lines)

            if has_disallow_all:
                return {
                    "status": "warning",
                    "description": "A `robots.txt` file is found, but it blocks all bots with `Disallow: /`.",
                    "code_snippet": lines[:min(6, len(lines))],
                    "how_to_fix": "Ensure this is intentional. If not, change `Disallow: /` to allow crawling."
                }

            description = f"A valid robots.txt file was found at {robots_url}."
            if not has_sitemap:
                description += " However, no Sitemap directive was found."

            return {
                "status": "passed" if has_sitemap else "warning",
                "description": description,
                "code_snippet": lines[:min(6, len(lines))],
                "how_to_fix": "No action needed." if has_sitemap else "Add a `Sitemap: https://example.com/sitemap.xml` line to your robots.txt file."
            }

        elif response.status_code == 404:
            return {
                "status": "failed",
                "description": "No robots.txt file was found. This may prevent search engines from knowing what to crawl or avoid.",
                "code_snippet": [f"robots.txt not found at {robots_url}"],
                "how_to_fix": (
                    "Create a `robots.txt` file at the root of your domain to control crawler behavior. Example:\n\n"
                    "User-agent: *\nDisallow:\nAllow: /\nSitemap: https://example.com/sitemap.xml"
                )
            }

        else:
            return {
                "status": "warning",
                "description": f"A robots.txt file was found but returned status code {response.status_code}.",
                "code_snippet": [f"Status Code: {response.status_code}"],
                "how_to_fix": f"Ensure that the file is accessible at {robots_url} and returns a 200 status code."
            }

    except requests.RequestException as e:
        return {
            "status": "failed",
            "description": f"An error occurred while trying to access robots.txt: {str(e)}",
            "code_snippet": [f"robots.txt URL: {robots_url}"],
            "how_to_fix": "Check your server configuration, internet connection, or firewall settings to ensure robots.txt is publicly accessible."
        }


def analyze_schema_org(soup):
    """Checks for Schema.org metadata in JSON-LD or Microdata format."""
    microdata_tags = soup.find_all(attrs={"itemscope": True, "itemtype": True})
    json_ld_tags = soup.find_all("script", type="application/ld+json")
    valid_json_ld = []

    for tag in json_ld_tags:
        try:
            data = json.loads(tag.string.strip())

            if isinstance(data, dict) and ("@context" in data or "@type" in data):
                valid_json_ld.append(tag)
        except (json.JSONDecodeError, AttributeError):
            continue

    if valid_json_ld or microdata_tags:
        if valid_json_ld and microdata_tags:
            format_used = "JSON-LD and Microdata"
        elif valid_json_ld:
            format_used = "JSON-LD"
        else:
            format_used = "Microdata"

        sample_snippet = ""
        if valid_json_ld:
            sample_snippet = valid_json_ld[0].text.strip()
        elif microdata_tags:
            sample_snippet = str(microdata_tags[0])

        return {
            "status": "passed",
            "description": f"Schema.org structured data found ({format_used}).",
            "code_snippet": [sample_snippet[:500] + ("..." if len(sample_snippet) > 500 else "")],
            "how_to_fix": "No action needed. Your page includes valid Schema.org metadata."
        }
    elif json_ld_tags:
        return {
            "status": "warning",
            "description": "Found JSON-LD tags, but none appear to contain valid Schema.org metadata.",
            "code_snippet": json_ld_tags[0].text.strip()[:500],
            "how_to_fix": "Ensure your JSON-LD contains Schema.org-compliant fields like `@context` and `@type`."
        }
    else:
        return {
            "status": "failed",
            "description": "No Schema.org metadata found. This may prevent rich snippets in search results.",
            "code_snippet": None,
            "how_to_fix": "Add Schema.org metadata using JSON-LD or Microdata format. Refer to https://schema.org."
        }


def check_favicon(soup):
    """Checks if the site has a valid favicon defined in the <head> section."""
    if not soup:
        return {
            "status": "failed",
            "description": "No HTML content provided to check for favicon.",
            "code_snippet": None,
            "how_to_fix": "Ensure the page was fetched and parsed before checking."
        }

    head = soup.find("head")
    if not head:
        return {
            "status": "warning",
            "description": "No <head> section found in the HTML. Cannot properly check for favicon.",
            "code_snippet": None,
            "how_to_fix": "Ensure your HTML includes a <head> section and define a favicon there."
        }

    # Collect <link rel=...> tags that match any known favicon types
    link_tags = soup.find_all("link", rel=True)
    favicon_tags = []

    for tag in link_tags:
        rel_attr = tag.get("rel")
        rel_values = rel_attr if isinstance(rel_attr, list) else [rel_attr]
        if any("icon" in r.lower() for r in rel_values):
            favicon_tags.append(tag)

    # Check for <link href="/favicon.ico">
    explicit_ico = soup.find("link", href=lambda x: x and x.strip().endswith("/favicon.ico"))
    if explicit_ico and explicit_ico not in favicon_tags:
        favicon_tags.append(explicit_ico)

    # Check <meta name="msapplication-TileImage" content="...">
    ms_tile = soup.find("meta", attrs={"name": "msapplication-TileImage"})
    if ms_tile and ms_tile.get("content"):
        return {
            "status": "passed",
            "description": "Favicon found via Microsoft meta tag.",
            "code_snippet": [str(ms_tile)],
            "how_to_fix": "No action needed. Favicon is defined using a meta tag."
        }

    # Validate all discovered favicon tags
    for tag in favicon_tags:
        href = tag.get("href")
        if not href:
            continue

        if tag.parent != head:
            return {
                "status": "warning",
                "description": "Favicon found but not within the <head> section. This may reduce compatibility.",
                "code_snippet": [str(tag)],
                "how_to_fix": "Move the <link> tag defining the favicon into the <head> section."
            }

        return {
            "status": "passed",
            "description": "Favicon found and correctly declared in the <head> section.",
            "code_snippet": [str(tag)],
            "how_to_fix": "No action needed. Favicon is correctly defined."
        }

    # Fallback: no favicon found
    return {
        "status": "failed",
        "description": "No favicon declared in the HTML. This may result in a blank browser tab icon.",
        "code_snippet": None,
        "how_to_fix": (
            "Add a <link rel=\"icon\" href=\"/favicon.ico\"> or similar tag inside the <head> section "
            "of your HTML. Supported formats: .ico, .png, .svg."
        )
    }


def check_amp(soup):
    """Checks for the presence of an AMP page via <link rel='amphtml'>."""
    amp_link = soup.find("link", rel="amphtml")

    if amp_link and amp_link.get("href"):
        return {
            "status": "passed",
            "description": "AMP version of the page is linked using <link rel='amphtml'>.",
            "code_snippet": [str(amp_link)],
            "how_to_fix": "No action needed. AMP page is present and referenced correctly."
        }
    else:
        return {
            "status": "warning",

            "description": "No AMP version found. While not mandatory, having an AMP version can improve mobile speed "
                           "and visibility in mobile search results.",

            "code_snippet": None,

            "how_to_fix": "Create a valid AMP version of your content and link it in the <head> with "
                          "<link rel='amphtml'> to benefit from faster load times and potential search enhancements."
        }


def check_http_redirect(base_url):
    """Checks if HTTP requests redirect to HTTPS."""
    parsed_url = urlparse(base_url)
    domain = parsed_url.netloc or parsed_url.path
    http_url = f"http://{domain}"

    try:
        response = requests.get(http_url, allow_redirects=True, timeout=10)
        final_url = response.url
        redirect_chain = " -> ".join([resp.url for resp in response.history] + [final_url])

        if final_url.startswith("https://"):
            return {
                "status": "passed",
                "description": f"HTTP traffic is redirected to HTTPS at {final_url}.",
                "code_snippet": [f"Redirect chain: {redirect_chain}"],
                "how_to_fix": "No action needed. HTTP requests are correctly redirected to HTTPS."
            }
        else:
            return {
                "status": "failed",

                "description": "HTTP traffic is not redirected to HTTPS. This exposes your site to potential security "
                               "risks.",

                "code_snippet": [f"Final URL: {final_url}\nRedirect chain: {redirect_chain}"],

                "how_to_fix": "Configure your server (e.g., Nginx, Apache) to enforce redirection from HTTP to HTTPS "
                              "using a 301 redirect."
            }
    except requests.RequestException as e:
        return {
            "status": "failed",
            "description": f"Unable to perform HTTP to HTTPS redirect check due to an error: {str(e)}",
            "code_snippet": [f"Attempted HTTP URL: {http_url}"],

            "how_to_fix": "Ensure your site is online and accessible. Then, set up automatic redirection from HTTP to "
                          "HTTPS."
        }


def is_custom_404(content: str) -> bool:
    """Helper to determine if content suggests a custom 404 page."""
    phrases = ["404", "page not found", "not be found"]
    return any(phrase in content for phrase in phrases)


def check_404_page(base_url):
    """Checks if the site has a custom 404 page."""
    fake_path = "/this-page-should-not-exist-xyz"
    test_url = base_url.rstrip("/") + fake_path

    try:
        response = requests.get(test_url, timeout=10)
        status_code = response.status_code
        content = response.text.lower()

        snippet = content[:200] + ("..." if len(content) > 200 else "")

        if status_code == 404:
            if is_custom_404(content):
                return {
                    "status": "passed",
                    "description": "Custom 404 page is in place with appropriate messaging.",
                    "code_snippet": [f"URL: {test_url} returned HTTP 404\nSample content: {snippet}"],
                    "how_to_fix": "No action needed. Custom 404 page is working."
                }
            else:
                return {
                    "status": "warning",
                    "description": "Page returns 404 but content doesn't appear customized.",
                    "code_snippet": [f"URL: {test_url} returned HTTP 404\nSample content: {snippet}"],
                    "how_to_fix": "Design a user-friendly 404 page with helpful navigation links or a search bar."
                }
        elif status_code == 200:
            return {
                "status": "failed",
                "description": f"Invalid URL returned HTTP 200 instead of 404. This confuses search engines and users.",
                "code_snippet": [f"HTTP {status_code} returned for {test_url}"],

                "how_to_fix": "Ensure the server returns HTTP 404 status code for non-existent pages and displays a "
                              "custom 404 error page."
            }
        else:
            return {
                "status": "warning",
                "description": f"Unexpected HTTP {status_code} returned for an invalid URL. Check your error handling.",
                "code_snippet": [f"HTTP {status_code} returned for {test_url}"],
                "how_to_fix": "Make sure broken or missing pages return HTTP 404 with a helpful custom message."
            }
    except requests.RequestException as e:
        return {
            "status": "failed",
            "description": f"Could not perform 404 page check due to an error: {str(e)}",
            "code_snippet": [f"Attempted URL: {test_url}"],

            "how_to_fix": "Ensure your site is online and reachable. Then test custom 404 responses manually or via "
                          "SEO tools."
        }


def check_text_compression(url):
    """
    Checks if the server supports text compression (gzip or Brotli).
    """
    headers = {
        "Accept-Encoding": "gzip, br"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        encoding = response.headers.get("Content-Encoding", "").lower().strip()

        if "br" in encoding:
            return {
                "status": "passed",

                "description": "Server supports Brotli compression, which offers superior performance for modern "
                               "browsers.",

                "code_snippet": [f"Content-Encoding: {encoding}"],
                "how_to_fix": "No action needed. Brotli compression is enabled and working."
            }
        elif "gzip" in encoding:
            return {
                "status": "passed",
                "description": "Server supports Gzip compression, which effectively reduces text content size.",
                "code_snippet": [f"Content-Encoding: {encoding}"],
                "how_to_fix": "No action needed. Gzip compression is active."
            }
        else:
            return {
                "status": "failed",

                "description": "No Brotli or Gzip compression detected. This may impact page load times, especially "
                               "on slower networks.",

                "code_snippet": [f"Content-Encoding: {encoding or 'Header not present'}"],

                "how_to_fix": (
                    "Enable Gzip or Brotli compression on your web server:\n"
                    "- For Nginx: use `gzip on;` or enable Brotli module.\n"
                    "- For Apache: enable `mod_deflate` or `mod_brotli`.\n"
                    "- For Express.js: use `compression` middleware.\n"
                    "- For other platforms: consult server documentation."
                )
            }
    except requests.RequestException as e:
        return {
            "status": "failed",
            "description": f"Could not perform compression check due to an error: {str(e)}",
            "code_snippet": [f"Attempted URL: {url}"],

            "how_to_fix": "Ensure the server is online and reachable. Then enable and verify Brotli or Gzip "
                          "compression for text assets."
        }


def check_viewport_meta(soup, html_content=None):
    """
    Checks if the page has a properly configured viewport meta-tag for mobile-friendliness.
    Robust to different HTML structures and parsing issues.
    """
    viewport_tag = None

    # Method 1: Standard BeautifulSoup search
    viewport_tag = soup.find("meta", attrs={"name": "viewport"})

    # Method 2: Case-insensitive search through all meta-tags
    if not viewport_tag:
        for meta in soup.find_all("meta"):
            name_attr = meta.get("name", "")
            if name_attr and name_attr.lower() == "viewport":
                viewport_tag = meta
                break

    # Method 3: If we have the raw HTML, use regex as a last resort
    if not viewport_tag and html_content:
        import re
        viewport_pattern = r'<meta[^>]*name=["|\']viewport["|\'][^>]*content=["|\']([^"\']+)["|\'][^>]*>'
        raw_match = re.search(viewport_pattern, html_content, re.IGNORECASE | re.DOTALL)

        if raw_match:
            # We found the tag with regex, but BeautifulSoup couldn't parse it
            content = raw_match.group(1) if len(raw_match.groups()) > 0 else ""
            width_ok = "width=device-width" in content.lower()
            scale_ok = "initial-scale" in content.lower()

            if width_ok and scale_ok:
                return {
                    "status": "passed",
                    "description": "The page contains a valid viewport meta tag optimized for responsive mobile "
                                   "viewing (detected via regex).",
                    "code_snippet": [raw_match.group(0)],
                    "how_to_fix": "No action needed. The viewport tag is correctly implemented for mobile devices."
                }
            else:
                return {
                    "status": "warning",
                    "description": "Viewport meta tag is present but may be misconfigured or missing key attributes ("
                                   "detected via regex).",
                    "code_snippet": [raw_match.group(0)],
                    "how_to_fix": (
                        "Ensure your tag looks like:\n"
                        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
                    )
                }

    # Process results if found with BeautifulSoup methods
    if viewport_tag:
        content = viewport_tag.get("content", "").lower().strip()
        width_ok = "width=device-width" in content
        scale_ok = "initial-scale" in content

        if width_ok and scale_ok:
            return {
                "status": "passed",
                "description": "The page contains a valid viewport meta tag optimized for responsive mobile viewing.",
                "code_snippet": [str(viewport_tag)],
                "how_to_fix": "No action needed. The viewport tag is correctly implemented for mobile devices."
            }
        else:
            return {
                "status": "warning",
                "description": "Viewport meta tag is present but may be misconfigured or missing key attributes.",
                "code_snippet": [str(viewport_tag)],
                "how_to_fix": (
                    "Ensure your tag looks like:\n"
                    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
                )
            }

    # If we got here, we couldn't find the tag with any method
    return {
        "status": "failed",
        "description": "No viewport meta tag found. This can negatively affect mobile usability and SEO.",
        "code_snippet": None,
        "how_to_fix": (
            "Add the following tag inside the <head> section of your HTML:\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">"
        )
    }


def check_social_meta(soup):
    """
    Checks if the page includes Open Graph and Twitter Card meta-tags for social media optimization.
    """
    og_tags = soup.find_all("meta", attrs={"property": lambda x: x and x.startswith("og:")})
    twitter_tags = soup.find_all("meta", attrs={"name": lambda x: x and x.startswith("twitter:")})

    og_count = len(og_tags)
    twitter_count = len(twitter_tags)

    if og_tags and twitter_tags:
        return {
            "status": "passed",
            "description": "Both Open Graph and Twitter Card meta tags are present for rich social sharing previews.",
            "code_snippet": [f"Open Graph tags found: {og_count}\nTwitter Card tags found: {twitter_count}"],
            "how_to_fix": "No action needed. Social meta tags are correctly implemented."
        }
    elif og_tags or twitter_tags:
        missing_type = "Twitter Card" if og_tags else "Open Graph"

        return {
            "status": "warning",

            "description": (
                "Partial social meta tag support detected. Full coverage improves visibility on all platforms."
            ),

            "code_snippet": [f"Open Graph tags found: {og_count}\nTwitter Card tags found: {twitter_count}"],
            "how_to_fix": f"Add missing {missing_type} meta tags to your <head> section for complete support."
        }
    else:
        return {
            "status": "failed",

            "description": (
                "No social media meta tags detected. Shared links may not display thumbnails or summaries on platforms "
                "like Facebook and Twitter."
            ),

            "code_snippet": None,

            "how_to_fix": (
                "Add Open Graph and Twitter Card meta tags in the <head> section, such as:\n"
                "<meta property=\"og:title\" content=\"Your Title\" />\n"
                "<meta name=\"twitter:card\" content=\"summary_large_image\" />"
            )
        }


def check_iframe_usage(soup, threshold: int = 3):
    """
    Checks if the page uses iframes, which can affect SEO, performance, and accessibility.
    Flags high usage based on a configurable threshold.
    """
    iframes = soup.find_all("iframe")
    iframe_count = len(iframes)

    if iframe_count == 0:
        return {
            "status": "passed",
            "description": "No iframes found on the page. This is optimal for SEO and performance.",
            "code_snippet": None,
            "how_to_fix": "No action needed. Avoiding iframes improves load speed and accessibility."
        }
    elif iframe_count <= threshold:
        return {
            "status": "warning",

            "description": f"{iframe_count} iframe(s) found. While acceptable, consider minimizing them for better "
                           f"performance.",

            "code_snippet": ["\n".join(str(tag) for tag in iframes[:3]) + ("\n..." if iframe_count > 3 else "")],

            "how_to_fix": (
                "Use iframes only when necessary. Consider alternatives such as JavaScript embeds or server-side "
                "includes."
            )
        }
    else:
        return {
            "status": "failed",

            "description": f"{iframe_count} iframes detected, which can hurt SEO, slow down rendering, and reduce "
                           f"accessibility.",

            "code_snippet": ["\n".join(str(tag) for tag in iframes[:3]) + "\n..." if iframe_count > 3 else ""],
            "how_to_fix": (
                "Reduce iframe usage. Where possible, replace with native HTML, JavaScript widgets, or lazy-loaded "
                "embeds."
            )
        }


def analyze_html_size(html):
    """Analyzes the size of the HTML document and provides SEO-friendly recommendations."""
    html_bytes = html.encode('utf-8')
    size_kb = len(html_bytes) / 1024  # Convert to KB

    if size_kb < 100:
        return {
            "status": "passed",
            "description": f"HTML size is optimal at {size_kb:.2f} KB.",
            "code_snippet": [f"HTML Size: {size_kb:.2f} KB"],
            "how_to_fix": "No action needed. HTML size is within optimal range."
        }
    elif size_kb < 300:
        return {
            "status": "warning",
            "description": f"HTML size is moderately large at {size_kb:.2f} KB.",
            "code_snippet": [f"HTML Size: {size_kb:.2f} KB"],

            "how_to_fix": (
                "Consider removing inline scripts/styles, comments, whitespace, and unused HTML tags. "
                "Use external resources where possible."
            )
        }
    else:
        return {
            "status": "failed",
            "description": f"HTML size is too large at {size_kb:.2f} KB. This can impact loading time and crawl efficiency.",
            "code_snippet": [f"HTML Size: {size_kb:.2f} KB"],

            "how_to_fix": (
                "Minify the HTML, defer or load scripts asynchronously, remove unused elements, "
                "and reduce DOM depth and complexity."
            )
        }


def analyze_minification(soup, asset_type: str):
    """Analyzes whether external CSS or JS files are minified based on their file names or URL characteristics."""
    assert asset_type in ("css", "js"), "asset_type must be either 'css' or 'js'"

    minified_count = 0
    total_count = 0
    unminified_snippets: List[str] = []

    if asset_type == "js":
        tags = soup.find_all("script", src=True)

        for tag in tags:
            src = tag["src"]
            total_count += 1

            if ".min.js" in src or re.search(r"[^\s]{100,}", src):
                minified_count += 1
            else:
                unminified_snippets.append(f'<script src="{src}"></script>')
    elif asset_type == "css":
        tags = soup.find_all("link", rel="stylesheet", href=True)

        for tag in tags:
            href = tag["href"]
            total_count += 1

            if ".min.css" in href or re.search(r"[^\s]{100,}", href):
                minified_count += 1
            else:
                unminified_snippets.append(f'<link rel="stylesheet" href="{href}">')

    if total_count == 0:
        return {
            "status": "warning",
            "description": f"No external {asset_type.upper()} files found to analyze for minification.",
            "code_snippet": None,
            "how_to_fix": f"Include external {asset_type.upper()} files via <script> or <link> tags for performance benefits."
        }

    minified_ratio = minified_count / total_count

    if minified_ratio == 1.0:
        status = "passed"
        description = f"All {total_count} {asset_type.upper()} files are minified."
        how_to_fix = "No action needed. All assets are optimized."
    elif minified_ratio >= 0.5:
        status = "warning"
        description = f"{minified_count}/{total_count} {asset_type.upper()} files are minified. Some are not."

        how_to_fix = (
            f"Minify remaining {asset_type.upper()} files using tools like Terser, UglifyJS, cssnano, or a CI/CD pipeline. "
            f"Prefer using `.min.{asset_type}` naming for clarity."
        )
    else:
        status = "failed"
        description = f"Only {minified_count}/{total_count} {asset_type.upper()} files are minified. Most are not optimized."

        how_to_fix = (
            f"Minify all your {asset_type.upper()} files to improve load time and performance. "
            f"Automate this using build tools like Webpack, Gulp, or CI/CD scripts."
        )

    return {
        "status": status,
        "description": description,
        "code_snippet": [unminified_snippets[0]] if unminified_snippets else None,
        "how_to_fix": how_to_fix
    }


def check_secure_connection(final_url: str):
    """Checks if the website uses a secure HTTPS connection."""
    try:
        if final_url.startswith("https://"):
            return {
                "status": "passed",
                "description": "The site uses HTTPS, ensuring secure communication.",
                "code_snippet": [f"Final URL: {final_url}"],
                "how_to_fix": "No action needed. The site uses HTTPS."
            }
        else:
            return {
                "status": "failed",
                "description": "The site does not use HTTPS. This may pose a security risk and affect SEO.",
                "code_snippet": [f"Final URL: {final_url}"],

                "how_to_fix": (
                    "Enable HTTPS by installing an SSL certificate. "
                    "You can use free services like Let's Encrypt. "
                    "Also, redirect all HTTP requests to HTTPS in your server configuration."
                )
            }
    except Exception as e:
        return {
            "status": "failed",
            "description": f"Unable to determine if the connection is secure: {str(e)}",
            "code_snippet": [f"URL: {final_url}"],
            "how_to_fix": "Ensure your URL is correctly formatted and check server SSL configuration."
        }


def check_url_structure(current_url: str):
    """Analyze URL structure for SEO best practices."""
    parsed = urlparse(current_url)
    path = parsed.path

    # Check for session IDs or tracking parameters
    query_params = parsed.query.split("&") if parsed.query else []
    suspicious_params = ["sid", "sessionid", "utm_", "fbclid", "gclid"]

    has_suspicious_params = any(any(p.startswith(s) for s in suspicious_params) for p in query_params)
    has_uppercase = any(c.isupper() for c in path)
    has_spaces = " " in path
    has_underscores = "_" in path
    has_multiple_extensions = len(re.findall(r"\.\w+\.", path)) > 0
    has_numeric_id = bool(re.search(r"/\d+/?", path))
    depth = len([p for p in path.split("/") if p]) - 1 if path != "/" else 0

    issues = []
    solutions = []

    if has_suspicious_params:
        issues.append("Contains tracking parameters or session IDs")
        solutions.append("Use rel=canonical tag and robots.txt to prevent indexing of URLs with tracking parameters")

    if has_uppercase:
        issues.append("Contains uppercase letters")
        solutions.append("Convert URL to lowercase for consistency")

    if has_spaces:
        issues.append("Contains spaces")
        solutions.append("Replace spaces with hyphens")

    if has_underscores:
        issues.append("Contains underscores")
        solutions.append("Use hyphens instead of underscores to separate words")

    if has_multiple_extensions:
        issues.append("Contains multiple file extensions")
        solutions.append("Simplify URL structure")

    if has_numeric_id:
        issues.append("Contains numeric IDs")
        solutions.append("Consider using descriptive slugs instead of numeric IDs")

    if depth > 3:
        issues.append(f"Deep URL structure ({depth} levels)")
        solutions.append("Consider a flatter URL structure for important content")

    if issues:
        return {
            "status": "warning",
            "description": f"URL structure has potential issues: {', '.join(issues)}",
            "code_snippet": [current_url],
            "how_to_fix": "\n".join(f"- {solution}" for solution in solutions)
        }

    return {
        "status": "passed",
        "description": "URL structure follows SEO best practices.",
        "code_snippet": [current_url],
        "how_to_fix": "No action needed. Your URL structure is SEO-friendly."
    }


def check_page_speed_indicators(soup: BeautifulSoup, html: str):
    """Analyze indicators that might affect page speed."""
    # Check for render-blocking resources
    render_blocking = []
    inline_styles = soup.find_all("style")
    inline_scripts = soup.find_all("script", src=None)
    head_scripts = soup.select("head script[src]")

    css_files = soup.select("link[rel='stylesheet']")

    # Calculate HTML size
    html_size_kb = len(html) / 1024

    # Count and analyze JavaScript files
    js_files = soup.find_all("script", src=True)
    js_count = len(js_files)
    js_paths = [script.get("src", "") for script in js_files]

    deferred_scripts = len([js for js in js_files if js.get("defer") or js.get("async")])

    # Add scripts in the head without async/defer to a render-blocking list
    for script in head_scripts:
        if not script.get("async") and not script.get("defer"):
            render_blocking.append(str(script))

    # Add CSS files to render-blocking list
    for css in css_files:
        render_blocking.append(str(css))

    # Issues to check
    issues = []
    solutions = []

    if html_size_kb > 100:
        issues.append(f"Large HTML size: {html_size_kb:.1f}KB (recommended < 100KB)")
        solutions.append("Minify HTML and remove unnecessary comments, whitespace, or hidden elements.")

    if len(inline_styles) > 3:
        issues.append(f"Multiple inline style blocks: {len(inline_styles)} found")
        solutions.append("Consider consolidating inline styles or moving them to external CSS files.")

    if len(render_blocking) > 3:
        issues.append(f"Many render-blocking resources: {len(render_blocking)} found")
        solutions.append("Use 'async' or 'defer' for scripts and move non-critical CSS to be loaded asynchronously.")

    if js_count > 15:
        issues.append(f"Too many JavaScript files: {js_count} found")
        solutions.append("Bundle JavaScript files to reduce HTTP requests.")

    if deferred_scripts < js_count / 2 and js_count > 5:
        issues.append(f"Only {deferred_scripts} of {js_count} scripts use defer/async attributes")
        solutions.append("Add 'defer' or 'async' attributes to non-critical scripts.")

    if not issues:
        return {
            "status": "passed",
            "description": "No significant page speed issues detected in the HTML structure.",
            "code_snippet": None,
            "how_to_fix": "Continue monitoring page speed with tools like Lighthouse or PageSpeed Insights."
        }

    return {
        "status": "warning",
        "description": "Potential page speed issues detected: " + "; ".join(issues),
        "code_snippet": render_blocking[:3] + (["..."] if len(render_blocking) > 3 else []),
        "how_to_fix": "\n".join(f"- {solution}" for solution in solutions)
    }


def analyze_url(url: str):
    """Main function to analyze a URL for SEO factors."""
    print(f"Analyzing URL: {url}")
    start_time = time.time()

    # Fetch the page content
    html, headers, final_url = fetch_page(url)

    if not html:
        return {
            "status": "error",
            "url": url,
            "message": "Failed to fetch or parse the page.",
            "checks": {}
        }

    soup = BeautifulSoup(html, "lxml")

    # Run all checks in parallel for better performance
    checks = {}

    # Basic checks
    checks["https"] = check_secure_connection(final_url)
    checks["title"] = check_title_tag(soup)
    checks["meta_description"] = analyze_meta(soup)
    checks["h1"] = analyze_h1s(soup)
    checks["heading_structure"] = analyze_heading_structure(soup)
    checks["analyze_html_size"] = analyze_html_size(html)
    checks["keywords"] = analyze_keywords(soup)
    checks["check_favicon"] = check_favicon(soup)

    # Technical SEO checks
    checks["canonical"] = check_canonical(soup)
    checks["noindex"] = check_noindex(soup)
    checks["mobile_friendly"] = check_viewport_meta(soup, html)
    checks["page_speed"] = check_page_speed_indicators(soup, html)
    checks["url_structure"] = check_url_structure(final_url)
    checks["check_amp"] = check_amp(soup)
    checks["check_http_redirect"] = check_http_redirect(final_url)
    checks["check_404_page"] = check_404_page(final_url)
    checks["check_text_compression"] = check_text_compression(final_url)
    checks["check_iframe_usage"] = check_iframe_usage(soup)

    # Media and accessibility checks
    checks["images"] = analyze_images(soup)
    checks["lazy_loading"] = analyze_lazy_loading(soup)

    # Social media and schema checks
    checks["social_tags"] = check_social_meta(soup)
    checks["schema_org"] = analyze_schema_org(soup)

    checks["analyze_css"] = analyze_minification(soup, "css")
    checks["analyze_js"] = analyze_minification(soup, "js")
    checks["robots_txt"] = check_robots_txt(final_url)
    checks["links"] = analyze_links(soup, final_url)

    end_time = time.time()
    analysis_time = end_time - start_time

    return {
        "status": "success",
        "url": final_url,
        "analysis_time": f"{analysis_time:.2f} seconds",
        "checks": checks
    }
