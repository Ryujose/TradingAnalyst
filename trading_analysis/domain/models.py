from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import re

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

from enum import Enum

class NewsType(str, Enum):
    EARNINGS = "earnings"
    GUIDANCE = "guidance"
    FDA = "FDA"
    MERGER = "merger"
    ACQUISITION = "acquisition"
    OFFERING = "offering"
    DILUTION = "dilution"
    CONTRACT = "contract"
    ANALYST_UPGRADE = "analyst_upgrade"
    ANALYST_DOWNGRADE = "analyst_downgrade"
    MACRO = "macro"
    OTHER = "other"

class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"

class NewsItem(BaseModel):
    id: Optional[int] = None
    symbol: str
    title: str
    content: Optional[str] = None
    publisher: str
    link: Optional[str] = None
    news_type: NewsType = NewsType.OTHER
    sentiment: Sentiment = Sentiment.NEUTRAL
    catalyst_strength: int = Field(default=1, ge=1, le=5)
    provider_publish_time: datetime
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = True

    @field_validator('symbol')
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        return v.upper()

class RunnerNewsLink(BaseModel):
    id: Optional[int] = None
    runner_id: str
    news_id: int
    linked_at: datetime = Field(default_factory=datetime.now)

class AnalysisSummary(BaseModel):
    health_summary: str
    market_value_analysis: str
    sentiment_summary: str
    news_analysis: str

class JudgeOpinion(BaseModel):
    role: str = Field(default="Judge")
    opinion: str = Field(default="No opinion provided.")
    recommendation: str = Field(default="Hold")  # Buy, Hold, Sell

    @field_validator('opinion', mode='before')
    @classmethod
    def stringify_opinion(cls, v):
        if isinstance(v, (dict, list)):
            return json.dumps(v, indent=2)
        return v

    @model_validator(mode='before')
    @classmethod
    def validate_opinion_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Ensure recommendation exists and is normalized
            rec = data.get('recommendation', '')
            if not rec:
                # Try to infer from opinion
                opinion_text = str(data.get('opinion', '')).lower()
                if any(k in opinion_text for k in ['buy', 'bullish', 'long', 'undervalued', 'growth']):
                    data['recommendation'] = 'Buy'
                elif any(k in opinion_text for k in ['sell', 'bearish', 'short', 'overvalued', 'risk']):
                    data['recommendation'] = 'Sell'
                else:
                    data['recommendation'] = 'Hold'
            else:
                # Normalize recommendation
                rec_lower = str(rec).lower()
                if 'buy' in rec_lower or 'bullish' in rec_lower:
                    data['recommendation'] = 'Buy'
                elif 'sell' in rec_lower or 'bearish' in rec_lower:
                    data['recommendation'] = 'Sell'
                else:
                    data['recommendation'] = 'Hold'
            
            # Ensure role exists
            if 'role' not in data:
                data['role'] = 'Judge'
                
        return data

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
    recommendation: str = Field(default="Hold")  # Buy, Hold, Sell
    conviction_score: float = Field(default=50.0)  # 0-100
    risk_adjusted_rating: float = Field(default=2.5)
    agreement_index: float = Field(default=0.5)
    position_size_suggestion: float = Field(default=0.0)
    primary_drivers: List[str] = Field(default_factory=list)
    key_risks: List[str] = Field(default_factory=list)

    @model_validator(mode='before')
    @classmethod
    def normalize_decision(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # 1. Normalize recommendation
            rec = data.get('recommendation', '')
            if not rec:
                opinion_text = str(data.get('logic_audit', '')).lower()
                if any(k in opinion_text for k in ['buy', 'bullish', 'long', 'undervalued', 'growth']):
                    data['recommendation'] = 'Buy'
                elif any(k in opinion_text for k in ['sell', 'bearish', 'short', 'overvalued', 'risk']):
                    data['recommendation'] = 'Sell'
                else:
                    data['recommendation'] = 'Hold'
            else:
                rec_lower = str(rec).lower()
                if 'buy' in rec_lower or 'bullish' in rec_lower:
                    data['recommendation'] = 'Buy'
                elif 'sell' in rec_lower or 'bearish' in rec_lower:
                    data['recommendation'] = 'Sell'
                else:
                    data['recommendation'] = 'Hold'

            # 2. Robust numeric parsing
            numeric_fields = {
                'conviction_score': 50.0,
                'risk_adjusted_rating': 2.5,
                'agreement_index': 0.5,
                'position_size_suggestion': 0.0
            }
            
            for field, default in numeric_fields.items():
                val = data.get(field)
                if val is not None and not isinstance(val, (int, float)):
                    # Try to extract number from string
                    str_val = str(val)
                    num_match = re.search(r'(\d+\.?\d*)', str_val)
                    if num_match:
                        try:
                            data[field] = float(num_match.group(1))
                        except (ValueError, TypeError):
                            data[field] = default
                    else:
                        data[field] = default
                elif val is None:
                    data[field] = default
                    
        return data

class ComprehensiveAnalysis(BaseModel):
    ticker: str
    risk_metrics: Optional[RiskMetrics] = None
    relative_strength: Optional[RelativeStrengthReport] = None
    monte_carlo: Optional[MonteCarloForecast] = None
    market_regime: Optional[MarketRegime] = None
    portfolio_impact: Optional[PortfolioImpactReport] = None
    trader_opinion: JudgeOpinion
    analyst_opinion: JudgeOpinion
    risk_pro_opinion: JudgeOpinion
    final_decision: FinalDecision

class RunnerItem(BaseModel):
    ticker: str
    price: float
    change: float
    pct_change: float
    volume: int
    relative_volume: Optional[float] = None
    gap_pct: Optional[float] = None
    vwap_dist: Optional[float] = None
    atr: Optional[float] = None
    volatility: Optional[float] = None
    range_expansion: Optional[float] = None
    volume_acceleration: Optional[float] = None
    market_cap: Optional[float] = None
    float_size: Optional[float] = None
    score: float = 0.0
    classification: str = "Ignore"  # Strong Runner, Developing Runner, Ignore
    timestamp: datetime = Field(default_factory=datetime.now)

class ScoreBreakdown(BaseModel):
    momentum_score: float
    liquidity_score: float
    volatility_score: float
    acceleration_score: float
    catalyst_score: float = 0.0
    total_score: float

class RunnerSnapshot(BaseModel):
    timestamp: datetime
    runners: List[RunnerItem]
    universe_size: int

class ExportData(BaseModel):
    timestamp: datetime
    ticker: str
    signal: str  # Buy/Hold/Sell
    conviction: float
    key_metrics: dict

class PortfolioItem(BaseModel):
    ticker: str
    weight: float
    entry_price: Optional[float] = None
    name: Optional[str] = None
