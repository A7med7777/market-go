from typing import List

import re
import nltk
import json
import requests

from collections import Counter

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


def analyze_meta(soup):
    """Analyzes the meta-description."""
    meta = soup.find("meta", attrs={"name": "description"})

    if meta and meta.has_attr("content"):
        meta_content = ' '.join(meta["content"].split())
        length = len(meta_content)

        if length < 50:
            return {
                "status": "warning",

                "description": f"Meta description is too short ({length} characters). Recommended length is 50–160 "
                               f"characters.",

                "code_snippet": [summarize(str(meta))],

                "how_to_fix": "Expand your meta description to better summarize the page content and include relevant "
                              "keywords."
            }
        elif length > 160:
            return {
                "status": "warning",

                "description": f"Meta description is too long ({length} characters). It may be truncated in search "
                               f"results.",

                "code_snippet": [summarize(str(meta))],
                "how_to_fix": "Shorten your meta description to keep it within 160 characters."
            }
        else:
            return {
                "status": "passed",
                "description": f"Meta description length is optimal ({length} characters).",
                "code_snippet": [summarize(str(meta))],
                "how_to_fix": "No changes needed. Your meta description is well-optimized."
            }
    else:
        return {
            "status": "failed",
            "description": "No meta description was found for your page.",
            "code_snippet": None,
            "how_to_fix": "Write a meta-description for your page."
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
            "code_snippet": code_snippet,

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
            "code_snippet": code_snippet,
            "how_to_fix": "No changes needed. Your heading structure is optimal.",
            "heading_order": heading_sequence,
            "missing_levels": [],
            "out_of_order": False
        }


def analyze_images(soup):
    """Analyzes <img> tags for 'alt' attribute quality: missing, redundant, short, or duplicate."""
    images = soup.find_all("img")
    total = len(images)

    # Filters
    missing_alt = []
    redundant_alt = []
    short_alt = []
    alt_values = []

    # Define weak alt texts
    redundant_words = {"image", "photo", "pic", "picture", "img"}
    non_descriptive = {"a", "-", "x"}

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

    # Check for duplicates
    alt_count = Counter(alt_values)
    duplicate_values = {alt for alt, count in alt_count.items() if count > 1}

    # Return logic
    issues = []

    if total == 0:
        return {
            "status": "warning",
            "description": "No <img> tags found on the page.",
            "code_snippet": None,
            "how_to_fix": "If your page uses images, be sure to include descriptive alt attributes for accessibility "
                          "and SEO."
        }

    if missing_alt:
        issues.append(f"{len(missing_alt)} missing alt")

    if redundant_alt:
        issues.append(f"{len(redundant_alt)} redundant alt")

    if short_alt:
        issues.append(f"{len(short_alt)} very short/non-descriptive alt")

    if duplicate_values:
        issues.append(f"{len(duplicate_values)} duplicate alt text values")

    if not issues:
        return {
            "status": "passed",
            "description": f"All {total} images have clear, descriptive 'alt' attributes.",
            "code_snippet": [str(img) for img in images],
            "how_to_fix": "No changes needed. Your images are well-optimized."
        }

    return {
        "status": "warning" if missing_alt or redundant_alt or short_alt else "failed",
        "description": f"Issues detected with image alt attributes: {', '.join(issues)}.",
        "code_snippet": None,
        "missing_alt": [str(img) for img in missing_alt],
        "redundant_alt": [str(img) for img in redundant_alt],
        "short_alt": [str(img) for img in short_alt],
        "duplicate_alt": list(duplicate_values),
        "how_to_fix": "Ensure all images have descriptive, unique 'alt' text. Avoid generic words like 'image', "
                      "'pic', or 'photo'. Don't use extremely short or duplicate alt texts."
    }


def analyze_lazy_loading(soup):
    """Checks if <img> and <iframe> tags implement lazy loading correctly."""
    img_tags = soup.find_all("img")
    iframe_tags = soup.find_all("iframe")
    elements = img_tags + iframe_tags
    total = len(elements)

    missing_lazy = [
        el for el in elements
        if el.get("loading", "").strip().lower() != "lazy"
    ]

    # Optional: skip if marked as critical/priority
    # missing_lazy = [el for el in missing_lazy if not el.get("data-critical") and el.get("priority") != "high"]

    if total == 0:
        return {
            "status": "warning",
            "description": "No <img> or <iframe> elements found for lazy loading analysis.",
            "code_snippet": None,
            "how_to_fix": "If your page includes images or iframes, use lazy loading to improve performance."
        }

    elif len(missing_lazy) == total:
        return {
            "status": "failed",
            "description": "None of the <img> or <iframe> elements use lazy loading.",
            "code_snippet": [summarize(el) for el in missing_lazy],
            "how_to_fix": "Add `loading=\"lazy\"` to your <img> and <iframe> tags to defer offscreen content."
        }

    elif len(missing_lazy) > 0:
        return {
            "status": "warning",
            "description": f"{len(missing_lazy)} of {total} image/iframe elements are missing `loading=\"lazy\"`.",
            "code_snippet": [summarize(el) for el in missing_lazy],
            "how_to_fix": "Add `loading=\"lazy\"` to these elements to improve performance and reduce initial load."
        }

    else:
        return {
            "status": "passed",
            "description": f"All {total} <img> and <iframe> elements use lazy loading.",
            "code_snippet": [summarize(el) for el in elements],
            "how_to_fix": "No changes needed. Lazy loading is properly implemented."
        }


def analyze_links(soup, base_url):
    """Analyzes internal vs external links and checks for broken ones."""
    internal, external, broken = [], [], []
    parsed_url = urlparse(base_url)
    domain = parsed_url.netloc
    a_tags = soup.find_all("a")

    for a in a_tags:
        href = a.get("href")

        if not href or href.strip().startswith(("#", "mailto:", "tel:")):
            continue  # Skip anchors, mailto, tel links

        full_url = urljoin(base_url, href.strip())

        try:
            response = requests.head(full_url, allow_redirects=True, timeout=10)

            if response.status_code >= 400:
                broken.append(full_url)
                continue
        except requests.RequestException:
            broken.append(full_url)
            continue

        if urlparse(full_url).netloc == domain:
            internal.append(full_url)
        else:
            external.append(full_url)

    total = len(internal) + len(external) + len(broken)
    total_internal = len(internal)
    total_external = len(external)
    total_broken = len(broken)

    def summarize_links(links):
        return links if len(links) <= 10 else links[:10] + ["...and more"]

    if total == 0:
        return {
            "status": "failed",

            "description": "No usable links found. A page should guide users through relevant internal and external "
                           "pages.",

            "code_snippet": None,
            "how_to_fix": "Add meaningful internal and external links to guide users and improve SEO."
        }

    internal_ratio = total_internal / total

    if total_broken > 0:
        return {
            "status": "failed",

            "description": f"{total_broken} broken link(s) detected. Internal: {total_internal}, "
                           f"External: {total_external}, Broken: {total_broken}",

            "code_snippet": summarize_links(broken),
            "how_to_fix": "Fix or remove broken links. Verify they return a valid 2xx or 3xx status code."
        }

    elif internal_ratio < 0.4:
        return {
            "status": "warning",

            "description": f"Low internal link ratio: {internal_ratio:.0%}. Internal: {total_internal}, "
                           f"External: {total_external}, Broken: {total_broken}",

            "code_snippet": summarize_links(internal),
            "how_to_fix": "Add more internal links to help users and search engines navigate your content structure."
        }

    else:
        return {
            "status": "passed",

            "description": f"Healthy link profile. Internal: {total_internal}, External: {total_external}, "
                           f"Broken: {total_broken}",

            "code_snippet": summarize_links(internal + external),
            "how_to_fix": "No issues. Maintain a good balance of internal and external links."
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


def check_opengraph(soup):
    """Checks if essential OpenGraph meta-tags exist and are populated."""
    required_og_tags = ["og:title", "og:description", "og:image", "og:url"]

    og_tags = {tag.get("property"): tag.get("content", "").strip() for tag in
               soup.find_all("meta", property=lambda x: x and x.startswith("og:"))}

    missing = []
    empty = []

    for prop in required_og_tags:
        if prop not in og_tags:
            missing.append(prop)
        elif not og_tags[prop]:
            empty.append(prop)

    if not og_tags:
        return {
            "status": "failed",

            "description": "No OpenGraph meta tags found. These tags help control how your pages appear when shared "
                           "on social media.",

            "code_snippet": None,

            "how_to_fix": "Add OpenGraph tags in the <head> section of your HTML to improve social sharing appearance "
                          "and CTR."
        }

    elif missing or empty:
        problems = []

        if missing:
            problems.append(f"Missing: {', '.join(missing)}")

        if empty:
            problems.append(f"Empty: {', '.join(empty)}")

        return {
            "status": "warning",
            "description": f"OpenGraph tags found, but some issues detected. {'; '.join(problems)}.",
            "code_snippet": [f'<meta property="{k}" content="{v}">' for k, v in og_tags.items()],
            "how_to_fix": "Ensure all required OpenGraph tags are present and contain meaningful values."
        }

    return {
        "status": "passed",
        "description": f"All required OpenGraph tags are present and populated. ({', '.join(required_og_tags)})",
        "code_snippet": [f'<meta property="{k}" content="{v}">' for k, v in og_tags.items()],
        "how_to_fix": "No action needed. Your OpenGraph setup looks great."
    }


def check_robots_txt(url):
    """Checks for the existence, accessibility, and structure of a robots.txt file."""
    parsed_url = urlparse(url)
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"

    try:
        response = requests.get(robots_url, timeout=10)
        content = response.text.strip()

        if response.status_code == 200 and "User-agent" in content:
            lines = content.splitlines()

            has_disallow_all = any("Disallow: /" in line and "User-agent: *" in lines[i - 1]
                                   for i, line in enumerate(lines) if i > 0)

            has_sitemap = any("Sitemap:" in line for line in lines)

            if has_disallow_all:
                return {
                    "status": "warning",
                    "description": f"A `robots.txt` file is found, but it blocks all bots with `Disallow: /`.",
                    "code_snippet": lines[:6],
                    "how_to_fix": "Ensure this is intentional. If not, change `Disallow: /` to allow crawling."
                }

            message = f"A valid robots.txt file was found at {robots_url}."

            if not has_sitemap:
                message += " However, no Sitemap directive was found."

            return {
                "status": "passed" if has_sitemap else "warning",
                "description": message,
                "code_snippet": lines[:6],
                "how_to_fix": "No action needed." if has_sitemap else
                "Add a `Sitemap: https://example.com/sitemap.xml` line to your robots.txt file."
            }
        elif response.status_code == 404:
            return {
                "status": "failed",

                "description": "No robots.txt file was found. This may prevent search engines from knowing what to "
                               "crawl or avoid.",

                "code_snippet": ['robots.txt not found at ' + robots_url],

                "how_to_fix": "Create a `robots.txt` file at the root of your domain to control crawler behavior. "
                              "Example:\n\nUser-agent: *\nDisallow:\nAllow: /\nSitemap: https://example.com/sitemap.xml"
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

            "how_to_fix": "Check your server configuration, internet connection, or firewall settings to ensure "
                          "robots.txt is publicly accessible."
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
    """Checks if the site has a valid favicon link in the <head>."""
    favicon_tags = soup.find_all(
        "link",
        rel=lambda x: x and any(
            icon in x.lower() for icon in ["icon", "shortcut icon", "apple-touch-icon", "mask-icon"]
        )
    )

    for tag in favicon_tags:
        href = tag.get("href")

        if href:  # Ensure the link actually points to a file
            return {
                "status": "passed",
                "description": "Favicon found in the HTML head. This helps with branding and browser recognition.",
                "code_snippet": [str(tag)],
                "how_to_fix": "No action needed. A favicon is correctly set."
            }

    return {
        "status": "failed",

        "description": "No favicon with a valid href found in the HTML. This may result in a generic or blank tab "
                       "icon, reducing brand visibility.",

        "code_snippet": None,

        "how_to_fix": "Add a `<link rel=\"icon\" href=\"/favicon.ico\">` tag in the <head> of your HTML. Make sure "
                      "the file is accessible and correctly formatted (.ico, .png, .svg, etc)."
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


def check_viewport_meta(soup):
    """
    Checks if the page has a properly configured viewport meta-tag for mobile-friendliness.
    """
    viewport_tag = soup.find("meta", attrs={"name": "viewport"})

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
    else:
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
    """Analyzes the size of the HTML document."""
    html_bytes = html.encode('utf-8')
    size_kb = len(html_bytes) / 1024  # convert to KB

    if size_kb < 100:
        status = "passed"
        description = f"HTML size is optimal at {size_kb:.2f} KB."
        how_to_fix = None
    elif size_kb < 300:
        status = "warning"
        description = f"HTML size is moderately large at {size_kb:.2f} KB."
        how_to_fix = (
            "Consider removing unnecessary inline scripts, whitespace, comments, or unused HTML elements."
        )
    else:
        status = "failed"
        description = f"HTML size is too large at {size_kb:.2f} KB."
        how_to_fix = (
            "Minify the HTML, defer non-critical resources, reduce DOM complexity, "
            "and avoid excessive inline styles or large embedded data."
        )

    return {
        "status": status,
        "description": description,
        "code_snippet": [f"HTML Size: {size_kb:.2f} KB"],
        "how_to_fix": how_to_fix
    }


def analyze_minification(soup, asset_type):
    """Analyzes whether CSS or JS files are minified."""
    assert asset_type in ("css", "js"), "asset_type must be either 'css' or 'js'"
    minified_count = 0
    total_count = 0
    unminified_snippets: List[str] = []

    if asset_type == "js":
        tags = soup.find_all("script", src=True)
        for tag in tags:
            src = tag["src"]
            total_count += 1
            if ".min.js" in src or re.search(r"\S{100,}", src):
                minified_count += 1
            else:
                unminified_snippets.append(f'<script src="{src}"></script>')
    elif asset_type == "css":
        tags = soup.find_all("link", rel="stylesheet", href=True)
        for tag in tags:
            href = tag["href"]
            total_count += 1
            if ".min.css" in href or re.search(r"\S{100,}", href):
                minified_count += 1
            else:
                unminified_snippets.append(f'<link rel="stylesheet" href="{href}">')

    if total_count == 0:
        status = "warning"
        description = f"No external {asset_type.upper()} files found to analyze for minification."
        how_to_fix = None
    elif minified_count == total_count:
        status = "passed"
        description = f"All {total_count} {asset_type.upper()} files appear to be minified."
        how_to_fix = None
    elif minified_count >= total_count * 0.5:
        status = "warning"
        description = (f"{minified_count}/{total_count} {asset_type.upper()} files are minified. Some still need "
                       f"optimization.")
        how_to_fix = (f"Minify all your {asset_type.upper()} files using tools like Terser, UglifyJS, cssnano, "
                      f"or online minifiers. Prefer `.min.{asset_type}` naming convention.")
    else:
        status = "failed"
        description = (f"Only {minified_count}/{total_count} {asset_type.upper()} files are minified. Most are not "
                       f"optimized.")
        how_to_fix = (f"Minify your {asset_type.upper()} assets for faster load times. Consider automating this with "
                      f"your CI/CD pipeline or Webpack/Gulp build process.")

    code_snippet = [unminified_snippets[0]] if unminified_snippets else None

    return {
        "status": status,
        "description": description,
        "code_snippet": code_snippet,
        "how_to_fix": how_to_fix
    }


def analyze(url):
    html, headers, final_url = fetch_page(url)

    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    report = {
        "keywords": analyze_keywords(soup),
        "meta_description": analyze_meta(soup),
        "h1_tags": analyze_h1s(soup),
        "heading_structure": analyze_heading_structure(soup),
        "images": analyze_images(soup),
        "lazy_loading": analyze_lazy_loading(soup),
        "links": analyze_links(soup, final_url),
        "canonical_url": check_canonical(soup),
        "noindex_meta": check_noindex(soup),
        "opengraph": check_opengraph(soup),
        "robots_txt": check_robots_txt(final_url),
        "schema_org": analyze_schema_org(soup),
        # "secure_connection": {"status": "passed"}, # final_url.startswith("https"),
        "favicon_present": check_favicon(soup),
        "amp_page": check_amp(soup),
        "http_to_https_redirect": check_http_redirect(final_url),
        "custom_404_page": check_404_page(final_url),
        "text_compression": check_text_compression(final_url),
        "viewport_meta": check_viewport_meta(soup),
        "social_meta": check_social_meta(soup),
        "iframe_count": check_iframe_usage(soup),
        "minified_css": analyze_minification(soup, "css"),
        "minified_js": analyze_minification(soup, "js"),
        "html_size": analyze_html_size(html),
    }

    return report
