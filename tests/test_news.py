import pytest
from datetime import datetime, timedelta
from trading_analysis.domain.models import NewsItem, NewsType, Sentiment, RunnerItem
from trading_analysis.infrastructure.persistence import SQLAlchemyNewsRepository
from trading_analysis.application.news_service import DefaultNewsService
from trading_analysis.infrastructure.engines.runners_scoring import MomentumScoringEngine

@pytest.fixture
def news_repo():
    # Use in-memory SQLite for testing
    return SQLAlchemyNewsRepository("sqlite:///:memory:")

@pytest.fixture
def news_service(news_repo):
    return DefaultNewsService(news_repo)

def test_news_crud(news_service):
    # Add
    news = news_service.add_news(
        symbol="TSLA",
        title="Earnings Beat",
        publisher="Reuters",
        news_type="earnings",
        sentiment="positive",
        catalyst_strength=5
    )
    assert news.id is not None
    assert news.symbol == "TSLA"
    assert news.news_type == NewsType.EARNINGS
    assert news.sentiment == Sentiment.POSITIVE

    # List
    items = news_service.list_news(symbol="TSLA")
    assert len(items) == 1
    assert items[0].title == "Earnings Beat"

    # Update
    updated = news_service.update_news(news.id, title="Massive Earnings Beat", catalyst_strength=4)
    assert updated.title == "Massive Earnings Beat"
    assert updated.catalyst_strength == 4

    # Search
    search_results = news_service.search_news("Massive")
    assert len(search_results) == 1

    # Delete (soft)
    news_service.delete_news(news.id)
    items_after_del = news_service.list_news(symbol="TSLA")
    assert len(items_after_del) == 0

def test_news_linking(news_service):
    news = news_service.add_news("AAPL", "New iPhone", "Apple", "other", "positive", 3)
    runner_id = "20250218-AAPL"
    
    link = news_service.link_news_to_runner(runner_id, news.id)
    assert link.runner_id == runner_id
    assert link.news_id == news.id
    
    # Get news for runner
    news_for_runner = news_service.repository.get_news_for_runner(runner_id)
    assert len(news_for_runner) == 1
    assert news_for_runner[0].title == "New iPhone"
    
    # Unlink
    news_service.unlink_news_from_runner(runner_id, news.id)
    news_after_unlink = news_service.repository.get_news_for_runner(runner_id)
    assert len(news_after_unlink) == 0

def test_catalyst_scoring(news_repo):
    scoring_engine = MomentumScoringEngine(news_repository=news_repo)
    
    # Item with no news
    item = RunnerItem(
        ticker="AMD", price=100.0, change=5.0, pct_change=5.0, volume=1000000,
        relative_volume=2.0, range_expansion=1.5, volatility=0.02, volume_acceleration=1.2
    )
    
    breakdown_no_news = scoring_engine.get_breakdown(item)
    assert breakdown_no_news.catalyst_score == 0.0
    
    # Add positive earnings news
    news_repo.add(NewsItem(
        symbol="AMD", title="Earnings Beat", publisher="AMD",
        news_type=NewsType.EARNINGS, sentiment=Sentiment.POSITIVE,
        catalyst_strength=5, provider_publish_time=datetime.now()
    ))
    
    breakdown_with_news = scoring_engine.get_breakdown(item)
    # Catalyst score: strength 5 (50) * positive (1.5) * earnings (1.5) = 112.5 (capped at 100)
    assert breakdown_with_news.catalyst_score == 100.0
    assert breakdown_with_news.total_score > breakdown_no_news.total_score
