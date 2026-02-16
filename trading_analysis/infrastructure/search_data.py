import logging
import time
from typing import List
from datetime import datetime
from ddgs import DDGS
from ..domain.models import NewsItem

class WebSearchDataProvider:
    def __init__(self):
        self.sources = [
            "reuters.com",
            "wsj.com",
            "marketwatch.com",
            "x.com"
        ]

    def get_news(self, ticker: str) -> List[NewsItem]:
        all_news = []
        # General query first to ensure we get something
        queries = [
            (f"{ticker} stock news", "news"),
            (f"{ticker} stock site:reuters.com", "news"),
            (f"{ticker} stock site:wsj.com", "news"),
            (f"{ticker} stock site:marketwatch.com", "news"),
            (f"{ticker} stock site:x.com", "text")
        ]
        
        with DDGS() as ddgs:
            for query_str, search_type in queries:
                try:
                    if search_type == "news":
                        results = list(ddgs.news(query_str, max_results=5))
                        for r in results:
                            all_news.append(NewsItem(
                                title=r.get('title', ''),
                                publisher=r.get('source', 'Web'),
                                link=r.get('url', ''),
                                provider_publish_time=self._parse_date(r.get('date')),
                                summary=r.get('body')
                            ))
                    else: # text search
                        results = list(ddgs.text(query_str, max_results=5))
                        for r in results:
                            all_news.append(NewsItem(
                                title=r.get('title', ''),
                                publisher='X (Twitter)',
                                link=r.get('href', ''),
                                provider_publish_time=datetime.now(),
                                summary=r.get('body')
                            ))
                    # Wait between queries to avoid rate limits
                    time.sleep(1.5)
                except Exception as e:
                    logging.warning(f"Search failed for '{query_str}': {e}")
                    if "Ratelimit" in str(e):
                        time.sleep(5) # Wait longer on rate limit
        
        return all_news

    def _parse_date(self, date_str: str) -> datetime:
        if not date_str:
            return datetime.now()
        try:
            # Handle ISO format from DDG
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception:
            return datetime.now()
