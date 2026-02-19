from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
from .models import (
    CompanyFinancials, TechnicalLevels, NewsItem, FinalRecommendation, 
    AnalysisSummary, RiskMetrics, RelativeStrengthReport, MonteCarloForecast, 
    MarketRegime, PortfolioImpactReport, FinalDecision, JudgeOpinion,
    RunnerItem, ScoreBreakdown, RunnerSnapshot, RunnerNewsLink
)

class DataProvider(ABC):
    @abstractmethod
    def get_financials(self, ticker: str) -> CompanyFinancials:
        pass

    @abstractmethod
    def get_technical_data(self, ticker: str) -> TechnicalLevels:
        pass

    @abstractmethod
    def get_news(self, ticker: str) -> List[NewsItem]:
        pass

class RunnersProvider(ABC):
    @abstractmethod
    def get_market_snapshot(self, tickers: List[str]) -> List[RunnerItem]:
        pass

    @abstractmethod
    def get_top_movers(self) -> List[str]:
        """Returns a list of candidate tickers that are moving."""
        pass

class ScoringEngine(ABC):
    @abstractmethod
    def compute_score(self, item: RunnerItem) -> float:
        pass

    @abstractmethod
    def get_breakdown(self, item: RunnerItem) -> ScoreBreakdown:
        pass

class RunnersService(ABC):
    @abstractmethod
    def get_runners(self, mode: str = "live", top_n: int = 10) -> RunnerSnapshot:
        pass

class RunnersPersistence(ABC):
    @abstractmethod
    def save_snapshot(self, snapshot: RunnerSnapshot):
        pass

    @abstractmethod
    def get_history(self, ticker: Optional[str] = None, start_date: Optional[datetime] = None) -> List[RunnerItem]:
        pass

class BacktestEngine(ABC):
    @abstractmethod
    def run_backtest(self, tickers: List[str], date: datetime) -> dict:
        pass

class RiskEngine(ABC):
    @abstractmethod
    def compute_metrics(self, ticker: str) -> RiskMetrics:
        pass

class RelativeStrengthEngine(ABC):
    @abstractmethod
    def compute_report(self, ticker: str) -> RelativeStrengthReport:
        pass

class MonteCarloEngine(ABC):
    @abstractmethod
    def run_simulation(self, ticker: str, num_simulations: int = 5000) -> MonteCarloForecast:
        pass

class MarketRegimeEngine(ABC):
    @abstractmethod
    def detect_regime(self) -> MarketRegime:
        pass

class PortfolioImpactEngine(ABC):
    @abstractmethod
    def analyze_impact(self, ticker: str, portfolio: Dict[str, float]) -> PortfolioImpactReport:
        pass

class NewsRepository(ABC):
    @abstractmethod
    def add(self, news: NewsItem) -> NewsItem:
        pass

    @abstractmethod
    def update(self, news_id: int, updates: dict) -> NewsItem:
        pass

    @abstractmethod
    def delete(self, news_id: int, soft: bool = True):
        pass

    @abstractmethod
    def get_by_id(self, news_id: int) -> Optional[NewsItem]:
        pass

    @abstractmethod
    def list(self, symbol: Optional[str] = None, news_type: Optional[str] = None, 
             sentiment: Optional[str] = None, limit: int = 50) -> List[NewsItem]:
        pass

    @abstractmethod
    def search(self, keyword: str) -> List[NewsItem]:
        pass

    @abstractmethod
    def link_to_runner(self, runner_id: str, news_id: int) -> RunnerNewsLink:
        pass

    @abstractmethod
    def unlink_from_runner(self, runner_id: str, news_id: int):
        pass

    @abstractmethod
    def get_links_for_runner(self, runner_id: str) -> List[RunnerNewsLink]:
        pass

    @abstractmethod
    def get_news_for_runner(self, runner_id: str) -> List[NewsItem]:
        pass

class NewsService(ABC):
    @abstractmethod
    def add_news(self, symbol: str, title: str, publisher: str, news_type: str, 
                 sentiment: str, catalyst_strength: int, content: Optional[str] = None, 
                 link: Optional[str] = None, publish_time: Optional[datetime] = None) -> NewsItem:
        pass

    @abstractmethod
    def update_news(self, news_id: int, title: Optional[str] = None, 
                    content: Optional[str] = None, sentiment: Optional[str] = None, 
                    catalyst_strength: Optional[int] = None) -> NewsItem:
        pass

    @abstractmethod
    def delete_news(self, news_id: int, force: bool = False):
        pass

    @abstractmethod
    def list_news(self, symbol: Optional[str] = None) -> List[NewsItem]:
        pass

    @abstractmethod
    def search_news(self, keyword: str) -> List[NewsItem]:
        pass

    @abstractmethod
    def link_news_to_runner(self, runner_id: str, news_id: int) -> RunnerNewsLink:
        pass

    @abstractmethod
    def unlink_news_from_runner(self, runner_id: str, news_id: int):
        pass

    @abstractmethod
    def auto_ingest_news(self, symbol: str, catalyst_strength: float) -> List[NewsItem]:
        pass

class LLMService(ABC):
    @abstractmethod
    def analyze_health(self, financials: CompanyFinancials) -> str:
        pass

    @abstractmethod
    def analyze_market_value(self, financials: CompanyFinancials, current_price: float) -> str:
        pass

    @abstractmethod
    def analyze_sentiment(self, news: List[NewsItem]) -> str:
        pass

    @abstractmethod
    def get_trader_opinion(self, data: dict) -> JudgeOpinion:
        pass

    @abstractmethod
    def get_analyst_opinion(self, data: dict) -> JudgeOpinion:
        pass

    @abstractmethod
    def get_risk_manager_opinion(self, data: dict) -> JudgeOpinion:
        pass

    @abstractmethod
    def resolve_final_decision(self, opinions: List[JudgeOpinion], data: dict) -> FinalDecision:
        pass

    @abstractmethod
    def get_judge_opinions(self, data: dict) -> FinalRecommendation:
        pass

    @abstractmethod
    def categorize_news(self, news: List[NewsItem]) -> List[NewsItem]:
        pass
