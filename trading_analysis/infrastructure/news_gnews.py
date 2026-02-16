import urllib.parse
from typing import List
from datetime import datetime
import feedparser
from ..domain.models import NewsItem

class GoogleNewsRSSProvider:
    """
    Fetch news via Google News RSS for specific domains reliably, avoiding heavy scraping.
    """

    BASE_URL = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

    def __init__(self, domains: List[str] | None = None):
        self.domains = domains or [
            "reuters.com",
            "wsj.com",
            "marketwatch.com",
            "bloomberg.com",
        ]

    def _build_url(self, ticker: str, domain: str) -> str:
        q = f"{ticker} stock site:{domain}"
        return self.BASE_URL.format(query=urllib.parse.quote_plus(q))

    def get_news(self, ticker: str) -> List[NewsItem]:
        items: List[NewsItem] = []
        for domain in self.domains:
            url = self._build_url(ticker, domain)
            feed = feedparser.parse(url)
            for entry in feed.entries[:6]:  # take a few per domain
                published = self._parse_published(entry)
                items.append(NewsItem(
                    title=getattr(entry, 'title', ''),
                    publisher=domain_to_publisher(domain),
                    link=getattr(entry, 'link', ''),
                    provider_publish_time=published,
                    summary=getattr(entry, 'summary', None)
                ))
        return items

    def _parse_published(self, entry) -> datetime:
        try:
            if hasattr(entry, 'published_parsed') and entry.published_parsed is not None:
                # convert time.struct_time to datetime
                return datetime(*entry.published_parsed[:6])
        except Exception:
            pass
        return datetime.now()


def domain_to_publisher(domain: str) -> str:
    mapping = {
        "reuters.com": "Reuters",
        "wsj.com": "The Wall Street Journal",
        "marketwatch.com": "MarketWatch",
        "bloomberg.com": "Bloomberg",
    }
    return mapping.get(domain, domain)
