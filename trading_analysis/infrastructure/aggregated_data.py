from typing import List
from ..domain.interfaces import DataProvider
from ..domain.models import CompanyFinancials, TechnicalLevels, NewsItem
from .yfinance_data import YFinanceDataProvider
from .search_data import WebSearchDataProvider
from .news_gnews import GoogleNewsRSSProvider

class AggregatedDataProvider(DataProvider):
    def __init__(self):
        self.yf_provider = YFinanceDataProvider()
        self.search_provider = WebSearchDataProvider()
        self.gnews_provider = GoogleNewsRSSProvider()

    def get_financials(self, ticker: str) -> CompanyFinancials:
        return self.yf_provider.get_financials(ticker)

    def get_technical_data(self, ticker: str) -> TechnicalLevels:
        return self.yf_provider.get_technical_data(ticker)

    def get_news(self, ticker: str) -> List[NewsItem]:
        # Get news from yfinance
        yf_news = self.yf_provider.get_news(ticker)
        
        # Get news from Google News RSS (Reuters, WSJ, MarketWatch)
        gnews = self.gnews_provider.get_news(ticker)
        
        # Try web search as a best-effort fallback (may be rate-limited)
        try:
            search_news = self.search_provider.get_news(ticker)
        except Exception:
            search_news = []
        
        # Combine and deduplicate by title
        combined = yf_news + gnews + search_news
        seen_titles = set()
        unique_news = []
        for item in combined:
            norm_title = item.title.strip().lower()
            if norm_title and norm_title not in seen_titles:
                unique_news.append(item)
                seen_titles.add(norm_title)
                
        return unique_news
