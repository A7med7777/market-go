from apify_client import ApifyClient
import asyncio
import time
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
from urllib.parse import urlparse
from datetime import datetime
import json
import logging
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Comment:
    """Data class to represent a social media comment"""
    text: str
    author: str
    timestamp: str
    platform: str
    comment_id: Optional[str] = None
    reply_to: Optional[str] = None
    likes: Optional[int] = None


class RateLimiter:
    """Rate limiter to handle API rate limits"""
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []

    async def acquire(self):
        """Acquire permission to make a request"""
        now = time.time()
        # Remove old requests outside the time window
        self.requests = [
            req_time
            for req_time in self.requests
            if now - req_time < self.time_window
        ]

        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[0])
            if sleep_time > 0:
                logger.info(
                    f"Rate limit reached. "
                    f"Sleeping for {sleep_time:.2f} seconds"
                )
                await asyncio.sleep(sleep_time)

        self.requests.append(now)


class BasePlatformScraper(ABC):
    """Abstract base class for platform-specific scrapers"""

    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.session = None

    @abstractmethod
    async def get_comments(
        self, url: str, max_comments: int = 10
    ) -> List[Comment]:
        """Get comments for a post"""
        pass

    @abstractmethod
    def is_valid_url(self, url: str) -> bool:
        """Check if URL belongs to this platform"""
        pass


class TikTokScraper(BasePlatformScraper):
    """TikTok comment scraper"""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__(RateLimiter(300, 900))  # 300 requests per 15 minutes
        self.api_key = api_key

    def is_valid_url(self, url: str) -> bool:
        return 'tiktok.com' in url

    async def get_comments(
        self, url: str, max_comments: int = 10
    ) -> List[Comment]:
        """Get TikTok replies (comments)"""
        if not self.api_key:
            logger.warning("TikTok API key not provided. Using mock data.")
            return self._get_mock_comments(url, "TikTok")

        await self.rate_limiter.acquire()

        try:
            data = []
            # Initialize the ApifyClient with your API token
            client = ApifyClient(self.api_key)

            # Prepare the Actor input
            run_input = {
                "postURLs": [url],
                "commentsPerPost": max_comments,
                "maxRepliesPerComment": 0,
                "resultsPerPage": 100,
                "profileScrapeSections": ["videos"],
                "profileSorting": "latest",
                "excludePinnedPosts": False,
            }

            # Run the Actor and wait for it to finish
            run = client.actor("BDec00yAmCm1QbMEI").call(run_input=run_input)

            # Fetch and print Actor results from the run's dataset
            # (if there are any)
            for item in client.dataset(
                run["defaultDatasetId"]
            ).iterate_items():
                data.append(item)

            return self._parse_tiktok_comments(data)

        except Exception as e:
            logger.error(f"Error fetching TikTok comments: {e}")
            return []

    def _parse_tiktok_comments(self, data: dict) -> List[Comment]:
        """Parse TikTok API response into Comment objects"""
        comments = []

        for item in data:
            comment = Comment(
                text=item.get('text', ''),
                author=item.get("uniqueId", 'Unknown'),
                timestamp=item.get('createTimeISO', ''),
                platform='TikTok',
                comment_id=item.get('cid'),
                likes=item.get('diggCount', 0)
            )
            comments.append(comment)

        return comments

    def _get_mock_comments(self, post_id: str, platform: str) -> List[Comment]:
        """Generate mock comments for demonstration"""
        return [
            Comment(
                text="Great post! Thanks for sharing.",
                author="user123",
                timestamp=datetime.now().isoformat(),
                platform=platform,
                comment_id=f"mock_{i}",
                likes=5
            ) for i in range(3)
        ]


class InstagramScraper(BasePlatformScraper):
    """Instagram comment scraper"""

    def __init__(self, access_token: Optional[str] = None):
        super().__init__(RateLimiter(200, 3600))  # 200 requests per hour
        self.access_token = access_token

    def is_valid_url(self, url: str) -> bool:
        return 'instagram.com' in url

    async def get_comments(
        self, url: str, max_comments: int = 10
    ) -> List[Comment]:
        """Get Instagram comments"""
        if not self.access_token:
            logger.warning(
                "Instagram access token not provided. Using mock data."
            )
            return self._get_mock_comments(url, "Instagram")

        await self.rate_limiter.acquire()

        try:
            data = []
            # Initialize the ApifyClient with your API token
            client = ApifyClient(self.access_token)

            # Prepare the Actor input
            run_input = {
                "directUrls": [url],
                "resultsLimit": max_comments,
            }

            # Run the Actor and wait for it to finish
            run = client.actor("SbK00X0JYCPblD2wp").call(run_input=run_input)

            # Fetch and print Actor results from the run's dataset
            # (if there are any)
            for item in client.dataset(
                run["defaultDatasetId"]
            ).iterate_items():
                data.append(item)

            return self._parse_instagram_comments(data)

        except Exception as e:
            logger.error(f"Error fetching Instagram comments: {e}")
            return []

    def _parse_instagram_comments(self, data: dict) -> List[Comment]:
        """Parse Instagram API response into Comment objects"""
        comments = []

        for comment in data:
            comment_obj = Comment(
                text=comment.get('text', ''),
                author=comment.get('ownerUsername', 'Unknown'),
                timestamp=comment.get('timestamp', ''),
                platform='Instagram',
                comment_id=comment.get('id'),
                likes=comment.get('likesCount', 0)
            )
            comments.append(comment_obj)

        return comments

    def _get_mock_comments(self, post_id: str, platform: str) -> List[Comment]:
        """Generate mock comments for demonstration"""
        return [
            Comment(
                text="Amazing photo! Love it ❤️",
                author=f"user{i}",
                timestamp=datetime.now().isoformat(),
                platform=platform,
                comment_id=f"mock_{i}",
                likes=10 + i
            ) for i in range(3)
        ]


class YoutubeScraper(BasePlatformScraper):
    """Youtube comment scraper"""

    def __init__(self, access_token: Optional[str] = None):
        super().__init__(RateLimiter(200, 3600))  # 200 requests per hour
        self.access_token = access_token

    def is_valid_url(self, url: str) -> bool:
        return 'youtube.com' in url

    async def get_comments(
        self, url: str, max_comments: int = 10
    ) -> List[Comment]:
        """Get YouTube comments"""
        if not self.access_token:
            logger.warning(
                "YouTube access token not provided. Using mock data."
            )
            return self._get_mock_comments(url, "YouTube")

        await self.rate_limiter.acquire()

        try:
            data = []
            # Initialize the ApifyClient with your API token
            client = ApifyClient(self.access_token)

            # Prepare the Actor input
            run_input = {
                "startUrls": [{"url": url}],
                "maxComments": max_comments,
                "commentsSortBy": "1",
            }

            # Run the Actor and wait for it to finish
            run = client.actor("p7UMdpQnjKmmpR21D").call(run_input=run_input)

            # Fetch and print Actor results from the run's dataset
            # (if there are any)
            for item in client.dataset(
                run["defaultDatasetId"]
            ).iterate_items():
                data.append(item)

            return self._parse_youtube_comments(data)

        except Exception as e:
            logger.error(f"Error fetching YouTube comments: {e}")
            return []

    def _parse_youtube_comments(self, data: dict) -> List[Comment]:
        """Parse YouTube API response into Comment objects"""
        comments = []

        for comment in data:
            comment_obj = Comment(
                text=comment.get('comment', ''),
                author=comment.get('author', 'Unknown'),
                timestamp=comment.get('publishedTimeText', ''),
                platform='YouTube',
                comment_id=comment.get('cid'),
                likes=comment.get('voteCount', 0)
            )
            comments.append(comment_obj)

        return comments

    def _get_mock_comments(self, post_id: str, platform: str) -> List[Comment]:
        """Generate mock comments for demonstration"""
        return [
            Comment(
                text="Interesting video! Thanks for sharing your thoughts.",
                author=f"User {i+1}",
                timestamp=datetime.now().isoformat(),
                platform=platform,
                comment_id=f"mock_{i}",
                likes=3 + i
            ) for i in range(3)
        ]


class SocialMediaCommentScraper:
    """Main class to orchestrate comment scraping across platforms"""

    def __init__(self, api_key: Optional[str] = None):

        self.scrapers = {
            'tiktok': TikTokScraper(api_key),
            'instagram': InstagramScraper(api_key),
            'youtube': YoutubeScraper(api_key)
        }

    def _identify_platform(self, url: str) -> Optional[str]:
        """Identify which platform the URL belongs to"""
        for platform, scraper in self.scrapers.items():
            if scraper.is_valid_url(url):
                return platform
        return None

    def _validate_url(self, url: str) -> bool:
        """Validate if URL is properly formatted"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    async def get_comments(
        self,
        url: str,
        max_comments: int = 10,
        include_replies: bool = True
    ) -> Dict[str, Union[List[Comment], str]]:
        """
        Main function to retrieve comments from a social media post URL

        Args:
            url: Social media post URL
            max_comments: Maximum number of comments to retrieve
            include_replies: Whether to include reply comments

        Returns:
            Dictionary containing comments list and metadata
        """

        # Validate URL format
        if not self._validate_url(url):
            return {
                'error': 'Invalid URL format',
                'comments': [],
                'platform': None,
                'url': None
            }

        # Identify platform
        platform = self._identify_platform(url)
        if not platform:
            return {
                'error': 'Unsupported platform or invalid URL',
                'comments': [],
                'platform': None,
                'url': None
            }

        # Get appropriate scraper
        scraper = self.scrapers[platform]

        # Fetch comments
        try:
            logger.info(f"Fetching comments for {platform} post url: {url}")
            comments = await scraper.get_comments(url, max_comments)

            return {
                'comments': comments,
                'platform': platform,
                'url': url,
                'total_comments': len(comments),
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error scraping comments: {e}")
            return {
                'error': f'Error fetching comments: {str(e)}',
                'comments': [],
                'platform': platform,
                'url': url
            }

    def format_comments(
        self,
        comments: List[Comment],
        output_format: str = 'json'
    ) -> str:
        """Format comments for output"""
        if output_format.lower() == 'json':
            return json.dumps([{
                'text': comment.text,
                'author': comment.author,
                'timestamp': comment.timestamp,
                'platform': comment.platform,
                'comment_id': comment.comment_id,
                'likes': comment.likes
            } for comment in comments], indent=2)

        elif output_format.lower() == 'csv':
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                'Text', 'Author', 'Timestamp', 'Platform',
                'Comment ID', 'Likes'
            ])

            for comment in comments:
                writer.writerow([
                    comment.text,
                    comment.author,
                    comment.timestamp,
                    comment.platform,
                    comment.comment_id,
                    comment.likes
                ])

            return output.getvalue()

        else:  # Plain text format
            formatted = []
            for comment in comments:
                formatted.append(f"Author: {comment.author}")
                formatted.append(f"Time: {comment.timestamp}")
                formatted.append(f"Platform: {comment.platform}")
                formatted.append(f"Likes: {comment.likes}")
                formatted.append(f"Text: {comment.text}")
                formatted.append("-" * 50)

            return "\n".join(formatted)

# Example usage and demonstration


async def main(url: str):
    """Example usage of the social media comment scraper"""

    # Initialize the scraper (API keys would be required for real usage)
    scraper = SocialMediaCommentScraper(
        "apify_api_vFghAgx6atmhHBvwNUZbGAfBHYR9Y20s2pjH"
    )

    # Example URLs (these would need to be real URLs for actual scraping)
    test_urls = [url]

    # test_urls = [
    #     "https://www.tiktok.com/@bellapoarch/video/6862153058223197445",
    #     "https://www.instagram.com/p/DCZlEDqy2to",
    #     "https://www.instagram.com/reel/DDIJAfeyemG",
    #     "https://www.youtube.com/watch?v=xObhZ0Ga7EQ"
    # ]

    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"Scraping comments from: {url}")
        print('='*60)

        result = await scraper.get_comments(url, max_comments=15)

        if 'error' in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Platform: {result['platform']}")
            print(f"URL: {result['url']}")
            print(f"Total comments found: {result['total_comments']}")
            print("\nComments:")
            print(scraper.format_comments(result['comments'], 'text'))

        return result


def run_scraper(url: str):
    """Run the scraper in an event loop"""
    results = asyncio.run(main(url))

    comments = {
        "comments": [item.text for item in results.get("comments", [])]
    }

    return comments
