import unittest
from unittest.mock import MagicMock
from trading_analysis.domain.models import (
    CompanyFinancials, TechnicalLevels, NewsItem, 
    JudgeOpinion, RiskMetrics, RelativeStrengthReport,
    MonteCarloForecast, MarketRegime, PortfolioImpactReport,
    FinalDecision
)
from trading_analysis.application.analyzer import StockAnalyzer
from datetime import datetime

class TestTradingAnalysis(unittest.TestCase):
    def test_analyzer_flow(self):
        # Setup mocks
        mock_data_provider = MagicMock()
        mock_llm_service = MagicMock()
        mock_risk_engine = MagicMock()
        mock_rs_engine = MagicMock()
        mock_mc_engine = MagicMock()
        mock_regime_engine = MagicMock()
        mock_portfolio_engine = MagicMock()
        
        # Mock data
        mock_data_provider.get_financials.return_value = CompanyFinancials(
            cash=1000.0, debt=500.0, market_cap=5000.0, pe_ratio=15.0, projections="Growth expected"
        )
        mock_data_provider.get_technical_data.return_value = TechnicalLevels(
            supports=[140.0, 145.0], resistances=[160.0, 165.0], current_price=150.0
        )
        mock_data_provider.get_news.return_value = [
            NewsItem(title="Good news", publisher="Reuters", link="http://example.com", provider_publish_time=datetime.now())
        ]
        
        mock_risk_metrics = RiskMetrics(
            volatility_30d=0.2, volatility_90d=0.2, volatility_1y=0.2,
            beta=1.0, max_drawdown_1y=-0.1, max_drawdown_5y=-0.2,
            sharpe_ratio=1.5, sortino_ratio=2.0, var_95=-0.02,
            volatility_regime="Normal"
        )
        mock_risk_engine.compute_metrics.return_value = mock_risk_metrics
        
        mock_rs_report = RelativeStrengthReport(
            perf_vs_spy_3m=0.05, perf_vs_spy_6m=0.1, perf_vs_spy_1y=0.2,
            perf_vs_sector_3m=0.02, perf_vs_sector_6m=0.05, perf_vs_sector_1y=0.1,
            pe_vs_sector_avg=1.1, rev_growth_vs_competitors=0.05,
            margin_vs_competitors=0.02, sector_ranking=2
        )
        mock_rs_engine.compute_report.return_value = mock_rs_report
        
        mock_mc_forecast = MonteCarloForecast(
            prob_up_10=0.6, prob_up_20=0.3, prob_down_10=0.1, prob_down_20=0.05,
            median_return=0.15, percentile_5=-0.1, percentile_95=0.4
        )
        mock_mc_engine.run_simulation.return_value = mock_mc_forecast
        
        mock_market_regime = MarketRegime(
            regime_type="Bullish Expansion", regime_confidence=0.9, regime_risk_multiplier=0.8
        )
        mock_regime_engine.detect_regime.return_value = mock_market_regime
        
        mock_portfolio_impact = PortfolioImpactReport(
            correlation_to_portfolio=0.5, portfolio_volatility=0.15,
            marginal_contribution_to_risk=0.02, sharpe_change=0.1,
            suggested_position_size=0.1, risk_flags=[]
        )
        mock_portfolio_engine.analyze_impact.return_value = mock_portfolio_impact
        
        mock_llm_service.analyze_health.return_value = "Healthy"
        mock_llm_service.analyze_market_value.return_value = "Fair value"
        mock_llm_service.analyze_sentiment.return_value = "Sentiment: Good\nSummary: Bullish"
        
        mock_llm_service.get_trader_opinion.return_value = JudgeOpinion(role="Trader", opinion="Bullish", recommendation="Buy")
        mock_llm_service.get_analyst_opinion.return_value = JudgeOpinion(role="Analyst", opinion="Strong fundamentals", recommendation="Buy")
        mock_llm_service.get_risk_manager_opinion.return_value = JudgeOpinion(role="Risk Manager", opinion="Moderate risk", recommendation="Hold")
        
        mock_final_decision = FinalDecision(
            recommendation="Buy", conviction_score=85, risk_adjusted_rating=4.2,
            agreement_index=0.8, position_size_suggestion=0.1,
            primary_drivers=["Growth", "Momentum"], key_risks=["Market vol"]
        )
        mock_llm_service.resolve_final_decision.return_value = mock_final_decision
        
        # Execute
        analyzer = StockAnalyzer(
            mock_data_provider, mock_llm_service,
            risk_engine=mock_risk_engine,
            rs_engine=mock_rs_engine,
            mc_engine=mock_mc_engine,
            regime_engine=mock_regime_engine,
            portfolio_engine=mock_portfolio_engine
        )
        result = analyzer.run_analysis("AAPL")
        
        # Verify
        self.assertEqual(result.final_decision.recommendation, "Buy")
        self.assertEqual(result.risk_metrics.volatility_1y, 0.2)
        mock_data_provider.get_financials.assert_called_once_with("AAPL")
        mock_risk_engine.compute_metrics.assert_called_once_with("AAPL")
        mock_llm_service.resolve_final_decision.assert_called_once()

if __name__ == "__main__":
    unittest.main()
