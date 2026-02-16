from abc import ABC, abstractmethod
from typing import List
from .models import (
    CompanyFinancials, TechnicalLevels, NewsItem, FinalRecommendation, 
    AnalysisSummary, RiskMetrics, RelativeStrengthReport, MonteCarloForecast, 
    MarketRegime, PortfolioImpactReport, FinalDecision, JudgeOpinion
)
from typing import List, Dict

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
