from typing import Optional
from ...domain.interfaces import ScoringEngine, NewsRepository
from ...domain.models import RunnerItem, ScoreBreakdown, Sentiment, NewsType

class MomentumScoringEngine(ScoringEngine):
    def __init__(self, weights=None, news_repository: Optional[NewsRepository] = None):
        self.weights = weights or {
            "momentum": 0.4,
            "liquidity": 0.2,
            "volatility": 0.1,
            "acceleration": 0.1,
            "catalyst": 0.2
        }
        self.news_repository = news_repository

    def compute_score(self, item: RunnerItem) -> float:
        breakdown = self.get_breakdown(item)
        return breakdown.total_score

    def get_breakdown(self, item: RunnerItem) -> ScoreBreakdown:
        # 1. Momentum Score (0-100)
        # Based on pct change (max at 15%) and range expansion
        m_score = min(100, (item.pct_change * 5) + (item.range_expansion * 10))
        
        # 2. Liquidity Score (0-100)
        # Based on relative volume (high rel vol is good)
        l_score = min(100, item.relative_volume * 10)
        
        # 3. Volatility Score (0-100)
        # High intraday volatility relative to normal
        v_score = min(100, item.volatility * 100) # Simplified
        
        # 4. Acceleration Score (0-100)
        a_score = min(100, item.volume_acceleration * 20)

        # 5. Catalyst Score (0-100)
        c_score = 0.0
        if self.news_repository:
            # Check for news in the last 24 hours
            news_items = self.news_repository.list(symbol=item.ticker, limit=5)
            if news_items:
                # Use the most recent news for scoring
                latest = news_items[0]
                base_c = latest.catalyst_strength * 10 # 10 to 50
                
                sentiment_multiplier = 1.0
                if latest.sentiment == Sentiment.POSITIVE:
                    sentiment_multiplier = 1.5
                elif latest.sentiment == Sentiment.NEGATIVE:
                    sentiment_multiplier = 0.5
                
                type_multiplier = 1.0
                if latest.news_type in [NewsType.EARNINGS, NewsType.FDA, NewsType.GUIDANCE]:
                    type_multiplier = 1.5
                
                c_score = min(100, base_c * sentiment_multiplier * type_multiplier)
        
        total = (
            m_score * self.weights["momentum"] +
            l_score * self.weights["liquidity"] +
            v_score * self.weights["volatility"] +
            a_score * self.weights["acceleration"] +
            c_score * self.weights["catalyst"]
        )
        
        return ScoreBreakdown(
            momentum_score=m_score,
            liquidity_score=l_score,
            volatility_score=v_score,
            acceleration_score=a_score,
            catalyst_score=c_score,
            total_score=total
        )
