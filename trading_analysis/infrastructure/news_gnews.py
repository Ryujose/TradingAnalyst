import urllib.parse
import re
from typing import List
from datetime import datetime
import feedparser
from ..domain.models import NewsItem

class GoogleNewsRSSProvider:
    """
    Fetch news via Google News RSS for specific domains reliably, avoiding heavy scraping.
    It can also consume direct RSS feeds for specific providers when available.
    """

    BASE_URL = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

    DEFAULT_DIRECT_FEEDS = {
        "reuters.com": "https://www.reuters.com/rssFeed/worldNews",
        "wsj.com": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "ft.com": "https://www.ft.com/?format=rss",
        "bloomberg.com": "https://www.bloomberg.com/feed/podcast/etf-report.xml",
        "seekingalpha.com": "https://seekingalpha.com/market-news.xml",
    }

    def __init__(self, domains: List[str] | None = None, direct_feeds: dict | None = None):
        self.domains = domains or [
            "reuters.com",
            "wsj.com",
            "marketwatch.com",
            "bloomberg.com",
            "ft.com",
            "cnbc.com",
            "finance.yahoo.com",
            "barrons.com",
            "seekingalpha.com",
            "investing.com",
            "thestreet.com",
            "zacks.com",
            "morningstar.com",
            "bbc.com",
            "aljazeera.com",
            "politico.com",
            "theguardian.com",
            "asia.nikkei.com",
            "techcrunch.com",
            "theverge.com",
            "wired.com",
            "arstechnica.com",
            "venturebeat.com",
            "coindesk.com",
            "cointelegraph.com",
            "theblock.co"
        ]
        self.direct_feeds = direct_feeds if direct_feeds is not None else self.DEFAULT_DIRECT_FEEDS

    def _build_url(self, ticker: str, domain: str) -> str:
        q = f"{ticker} stock site:{domain}"
        return self.BASE_URL.format(query=urllib.parse.quote_plus(q))

    def get_news(self, ticker: str) -> List[NewsItem]:
        items: List[NewsItem] = []
        ticker_lower = ticker.lower()

        for domain in self.domains:
            # Check for direct feed
            direct_url = self.direct_feeds.get(domain)
            feed_items = []

            if direct_url:
                try:
                    feed = feedparser.parse(direct_url)
                    for entry in feed.entries[:100]:
                        title = getattr(entry, 'title', '')
                        summary = getattr(entry, 'summary', '')
                        # Content check (some feeds use content field)
                        content_list = getattr(entry, 'content', [])
                        content_val = content_list[0].get('value', '') if content_list else ''
                        
                        text_to_check = (title + " " + (summary or "") + " " + content_val).lower()
                        
                        # Use a slightly more robust check: whole word or followed by space/punctuation
                        # to avoid matching "T" in every word.
                        if self._is_ticker_in_text(ticker_lower, text_to_check):
                            published = self._parse_published(entry)
                            feed_items.append(NewsItem(
                                symbol=ticker,
                                title=title,
                                publisher=domain_to_publisher(domain),
                                link=getattr(entry, 'link', ''),
                                provider_publish_time=published,
                                content=summary or content_val
                            ))
                except Exception:
                    # If direct feed fails, we'll let it fall through to Google News
                    pass
            
            # Fallback to Google News RSS search if no items found from direct feed 
            # OR if no direct feed exists for this domain
            if not feed_items:
                url = self._build_url(ticker, domain)
                try:
                    feed = feedparser.parse(url)
                    for entry in feed.entries[:100]:
                        published = self._parse_published(entry)
                        feed_items.append(NewsItem(
                            symbol=ticker,
                            title=getattr(entry, 'title', ''),
                            publisher=domain_to_publisher(domain),
                            link=getattr(entry, 'link', ''),
                            provider_publish_time=published,
                            content=getattr(entry, 'summary', None)
                        ))
                except Exception:
                    pass
            
            items.extend(feed_items)
            
        return items

    def _is_ticker_in_text(self, ticker_lower: str, text_lower: str) -> bool:
        """Checks if ticker is in text, attempting to avoid partial word matches."""
        # Use word boundaries for all tickers to avoid partial matches (e.g., 'META' in 'metabolism')
        pattern = r'\b' + re.escape(ticker_lower) + r'\b'
        return bool(re.search(pattern, text_lower))

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
        "ft.com": "Financial Times",
        "seekingalpha.com": "Seeking Alpha",
        "cnbc.com": "CNBC",
        "finance.yahoo.com": "Yahoo Finance",
        "barrons.com": "Barron's",
        "investing.com": "Investing.com",
    }
    return mapping.get(domain, domain)
