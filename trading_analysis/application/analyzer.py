from ..domain.interfaces import (
    DataProvider, LLMService, RiskEngine, RelativeStrengthEngine,
    MonteCarloEngine, MarketRegimeEngine, PortfolioImpactEngine
)
from ..domain.models import ComprehensiveAnalysis, FinalDecision, FinalRecommendation
from typing import Dict, Optional

class StockAnalyzer:
    def __init__(
        self, 
        data_provider: DataProvider, 
        llm_service: LLMService,
        risk_engine: Optional[RiskEngine] = None,
        rs_engine: Optional[RelativeStrengthEngine] = None,
        mc_engine: Optional[MonteCarloEngine] = None,
        regime_engine: Optional[MarketRegimeEngine] = None,
        portfolio_engine: Optional[PortfolioImpactEngine] = None
    ):
        self.data_provider = data_provider
        self.llm_service = llm_service
        self.risk_engine = risk_engine
        self.rs_engine = rs_engine
        self.mc_engine = mc_engine
        self.regime_engine = regime_engine
        self.portfolio_engine = portfolio_engine

    def run_analysis(self, ticker: str, portfolio: Optional[Dict[str, float]] = None) -> ComprehensiveAnalysis:
        # 1. Fetch Basic Data
        financials = self.data_provider.get_financials(ticker)
        technical = self.data_provider.get_technical_data(ticker)
        news = self.data_provider.get_news(ticker)

        # 2. Run Quantitative Engines
        risk_metrics = self.risk_engine.compute_metrics(ticker) if self.risk_engine else None
        rel_strength = self.rs_engine.compute_report(ticker) if self.rs_engine else None
        monte_carlo = self.mc_engine.run_simulation(ticker) if self.mc_engine else None
        market_regime = self.regime_engine.detect_regime() if self.regime_engine else None
        portfolio_impact = self.portfolio_engine.analyze_impact(ticker, portfolio or {}) if self.portfolio_engine else None

        # 3. Perform point-by-point analysis via LLM (Context synthesis)
        health_summary = self.llm_service.analyze_health(financials)
        market_value_analysis = self.llm_service.analyze_market_value(financials, technical.current_price)
        sentiment_news_analysis = self.llm_service.analyze_sentiment(news)

        # 4. Prepare Context for Judges
        context_data = {
            "ticker": ticker,
            "financials": financials.model_dump(),
            "technical_levels": technical.model_dump(),
            "health_summary": health_summary,
            "market_value_analysis": market_value_analysis,
            "sentiment_news_analysis": sentiment_news_analysis,
            "recent_news": [f"[{n.publisher}] {n.title} (Source: {n.link})" for n in news[:20]],
            "risk_metrics": risk_metrics.model_dump() if risk_metrics else {},
            "relative_strength": rel_strength.model_dump() if rel_strength else {},
            "monte_carlo": monte_carlo.model_dump() if monte_carlo else {},
            "market_regime": market_regime.model_dump() if market_regime else {},
            "portfolio_impact": portfolio_impact.model_dump() if portfolio_impact else {}
        }

        # 5. Get Individual Judge Opinions
        trader_opinion = self.llm_service.get_trader_opinion(context_data)
        analyst_opinion = self.llm_service.get_analyst_opinion(context_data)
        risk_pro_opinion = self.llm_service.get_risk_manager_opinion(context_data)

        # 6. Final Resolver Logic
        # Deterministic scoring and conflict detection
        risk_score = 100.0
        if risk_metrics:
            risk_score -= risk_metrics.volatility_1y * 10
            risk_score -= abs(risk_metrics.max_drawdown_1y) * 20
        
        conflict_flags = []
        if monte_carlo and market_regime:
            if monte_carlo.prob_up_20 < 0.15 and "Expansion" in market_regime.regime_type:
                conflict_flags.append("Upside probability low despite Bullish Expansion regime")
        
        if portfolio_impact and portfolio_impact.correlation_to_portfolio > 0.8:
            conflict_flags.append("High correlation risk to existing portfolio")

        # Position sizing caps
        max_size = 0.20 
        if market_regime and "Risk-Off" in market_regime.regime_type:
            max_size = 0.05
        
        suggested_size = min(portfolio_impact.suggested_position_size if portfolio_impact else 0.1, max_size)

        context_data["deterministic_analysis"] = {
            "risk_score": max(0, min(100, risk_score * (market_regime.regime_risk_multiplier if market_regime else 1.0))),
            "conflict_flags": conflict_flags,
            "max_position_size_allowed": max_size,
            "final_suggested_size": suggested_size
        }

        final_decision = self.llm_service.resolve_final_decision(
            [trader_opinion, analyst_opinion, risk_pro_opinion],
            context_data
        )

        return ComprehensiveAnalysis(
            ticker=ticker,
            risk_metrics=risk_metrics,
            relative_strength=rel_strength,
            monte_carlo=monte_carlo,
            market_regime=market_regime,
            portfolio_impact=portfolio_impact,
            trader_opinion=trader_opinion,
            analyst_opinion=analyst_opinion,
            risk_pro_opinion=risk_pro_opinion,
            final_decision=final_decision
        )
