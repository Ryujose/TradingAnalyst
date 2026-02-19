from typing import List, Optional
from datetime import datetime, timedelta
from ..domain.interfaces import NewsService, NewsRepository, LLMService
from ..domain.models import NewsItem, NewsType, Sentiment, RunnerNewsLink

class DefaultNewsService(NewsService):
    def __init__(self, repository: NewsRepository, llm_service: Optional[LLMService] = None):
        self.repository = repository
        self.llm_service = llm_service
        from ..infrastructure.news_gnews import GoogleNewsRSSProvider
        self.news_provider = GoogleNewsRSSProvider()

    def add_news(self, symbol: str, title: str, publisher: str, news_type: str, 
                 sentiment: str, catalyst_strength: int, content: Optional[str] = None, 
                 link: Optional[str] = None, publish_time: Optional[datetime] = None) -> NewsItem:
        
        # Validation
        symbol = symbol.upper()
        
        # Normalize enums
        try:
            nt = NewsType(news_type.lower())
        except ValueError:
            nt = NewsType.OTHER
            
        try:
            st = Sentiment(sentiment.lower())
        except ValueError:
            st = Sentiment.NEUTRAL
            
        news = NewsItem(
            symbol=symbol,
            title=title,
            content=content,
            publisher=publisher,
            link=link,
            news_type=nt,
            sentiment=st,
            catalyst_strength=catalyst_strength,
            provider_publish_time=publish_time or datetime.now()
        )
        
        return self.repository.add(news)

    def update_news(self, news_id: int, title: Optional[str] = None, 
                    content: Optional[str] = None, sentiment: Optional[str] = None, 
                    catalyst_strength: Optional[int] = None) -> NewsItem:
        
        updates = {}
        if title: updates['title'] = title
        if content: updates['content'] = content
        if sentiment:
            try:
                updates['sentiment'] = Sentiment(sentiment.lower())
            except ValueError:
                pass
        if catalyst_strength is not None:
            updates['catalyst_strength'] = catalyst_strength
            
        return self.repository.update(news_id, updates)

    def delete_news(self, news_id: int, force: bool = False):
        self.repository.delete(news_id, soft=not force)

    def list_news(self, symbol: Optional[str] = None) -> List[NewsItem]:
        return self.repository.list(symbol=symbol, limit=100)

    def search_news(self, keyword: str) -> List[NewsItem]:
        return self.repository.search(keyword)

    def link_news_to_runner(self, runner_id: str, news_id: int) -> RunnerNewsLink:
        return self.repository.link_to_runner(runner_id, news_id)

    def unlink_news_from_runner(self, runner_id: str, news_id: int):
        self.repository.unlink_from_runner(runner_id, news_id)

    def auto_ingest_news(self, symbol: str, catalyst_strength: float = 1) -> List[NewsItem]:
        symbol = symbol.upper()
        # 1. Fetch news from GNews
        raw_news = self.news_provider.get_news(symbol)
        
        # 2. Filter out already existing news in repository (by title and symbol)
        existing_news = self.repository.list(symbol=symbol, limit=100)
        existing_titles = {n.title.strip().lower() for n in existing_news}
        
        new_items = [n for n in raw_news if n.title.strip().lower() not in existing_titles]
        
        if not new_items:
            return []
            
        # 3. Categorize new items using LLM if available
        if self.llm_service:
            processed_items = self.llm_service.categorize_news(new_items)
            
            # 4. Filter by importance and recency
            # Important (strength >= 4) or recent (< 6 months)
            six_months_ago = datetime.now() - timedelta(days=180)
            
            # 5. Save to repository
            saved_items = []
            for item in processed_items:
                is_important = item.catalyst_strength >= catalyst_strength
                is_recent = item.provider_publish_time >= six_months_ago
                
                if not (is_important or is_recent):
                    continue

                # Double check uniqueness before adding, in case LLM took time
                # and another process added it
                item.symbol = symbol
                saved_items.append(self.repository.add(item))
            return saved_items
        else:
            # If no LLM, just save with defaults (applying same recency filter if possible)
            six_months_ago = datetime.now() - timedelta(days=180)
            saved_items = []
            for item in new_items:
                if item.provider_publish_time < six_months_ago:
                    continue
                item.symbol = symbol
                saved_items.append(self.repository.add(item))
            return saved_items
