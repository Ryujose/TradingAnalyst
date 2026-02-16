from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class CompanyFinancials(BaseModel):
    cash: float
    debt: float
    market_cap: float
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    revenue_growth: Optional[float] = None
    profit_margins: Optional[float] = None
    free_cash_flow: Optional[float] = None
    projections: Optional[str] = None

class TechnicalLevels(BaseModel):
    supports: List[float]
    resistances: List[float]
    current_price: float

class SentimentResult(BaseModel):
    score: float  # 0 to 1 or -1 to 1
    label: str  # Good/Bad or Bullish/Bearish
    summary: str

class NewsItem(BaseModel):
    title: str
    publisher: str
    link: str
    provider_publish_time: datetime
    summary: Optional[str] = None

class AnalysisSummary(BaseModel):
    health_summary: str
    market_value_analysis: str
    sentiment_summary: str
    news_analysis: str

class JudgeOpinion(BaseModel):
    role: str
    opinion: str
    recommendation: str  # Buy, Hold, Sell

class FinalRecommendation(BaseModel):
    trader_opinion: JudgeOpinion
    analyst_opinion: JudgeOpinion
    risk_pro_opinion: JudgeOpinion
    final_user_recommendation: str
    justification: str

class RiskMetrics(BaseModel):
    volatility_30d: float
    volatility_90d: float
    volatility_1y: float
    beta: float
    max_drawdown_1y: float
    max_drawdown_5y: float
    sharpe_ratio: float
    sortino_ratio: float
    var_95: float
    volatility_regime: str

class RelativeStrengthReport(BaseModel):
    perf_vs_spy_3m: float
    perf_vs_spy_6m: float
    perf_vs_spy_1y: float
    perf_vs_sector_3m: float
    perf_vs_sector_6m: float
    perf_vs_sector_1y: float
    pe_vs_sector_avg: float
    rev_growth_vs_competitors: float
    margin_vs_competitors: float
    sector_ranking: Optional[int] = None

class MonteCarloForecast(BaseModel):
    prob_up_10: float
    prob_up_20: float
    prob_down_10: float
    prob_down_20: float
    median_return: float
    percentile_5: float
    percentile_95: float

class MarketRegime(BaseModel):
    regime_type: str
    regime_confidence: float
    regime_risk_multiplier: float

class PortfolioImpactReport(BaseModel):
    correlation_to_portfolio: float
    portfolio_volatility: float
    marginal_contribution_to_risk: float
    sharpe_change: float
    suggested_position_size: float
    risk_flags: List[str]

class FinalDecision(BaseModel):
    recommendation: str  # Buy, Hold, Sell
    conviction_score: float  # 0-100
    risk_adjusted_rating: float
    agreement_index: float
    position_size_suggestion: float
    primary_drivers: List[str]
    key_risks: List[str]

class ComprehensiveAnalysis(BaseModel):
    ticker: str
    risk_metrics: RiskMetrics
    relative_strength: RelativeStrengthReport
    monte_carlo: MonteCarloForecast
    market_regime: MarketRegime
    portfolio_impact: PortfolioImpactReport
    trader_opinion: JudgeOpinion
    analyst_opinion: JudgeOpinion
    risk_pro_opinion: JudgeOpinion
    final_decision: FinalDecision
