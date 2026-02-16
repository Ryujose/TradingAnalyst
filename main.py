#!/usr/bin/env python3
import argparse
import sys
from trading_analysis.infrastructure.aggregated_data import AggregatedDataProvider
from trading_analysis.infrastructure.llm_service import LiteLLMService
from trading_analysis.application.analyzer import StockAnalyzer
from trading_analysis.config import Config
from trading_analysis.infrastructure.engines.risk_engine import YFinanceRiskEngine
from trading_analysis.infrastructure.engines.relative_strength import YFinanceRelativeStrengthEngine
from trading_analysis.infrastructure.engines.monte_carlo import GBM_MonteCarloEngine
from trading_analysis.infrastructure.engines.market_regime import YFinanceMarketRegimeEngine
from trading_analysis.infrastructure.engines.portfolio_engine import YFinancePortfolioImpactEngine

def main():
    parser = argparse.ArgumentParser(description="Trading Analysis App")
    parser.add_argument("ticker", help="Stock ticker symbol (e.g., AAPL, TSLA)")
    parser.add_argument("--model", default=Config.DEFAULT_MODEL, help="LLM model to use (e.g., gpt-4o, ollama/llama3, lm_studio/model)")
    
    args = parser.parse_args()
    
    print(f"--- Analyzing {args.ticker} using {args.model} ---")
    
    try:
        data_provider = AggregatedDataProvider()
        llm_service = LiteLLMService(model=args.model)
        
        # Instantiate Quantitative Engines
        risk_engine = YFinanceRiskEngine()
        rs_engine = YFinanceRelativeStrengthEngine()
        mc_engine = GBM_MonteCarloEngine()
        regime_engine = YFinanceMarketRegimeEngine()
        portfolio_engine = YFinancePortfolioImpactEngine()
        
        analyzer = StockAnalyzer(
            data_provider, 
            llm_service,
            risk_engine=risk_engine,
            rs_engine=rs_engine,
            mc_engine=mc_engine,
            regime_engine=regime_engine,
            portfolio_engine=portfolio_engine
        )
        
        # Placeholder for portfolio - in a real app, this could be loaded from a file/DB
        dummy_portfolio = {"SPY": 0.5, "QQQ": 0.3, "TLT": 0.2}
        
        result = analyzer.run_analysis(args.ticker, portfolio=dummy_portfolio)
        
        print("\n=== QUANTITATIVE INSIGHTS ===")
        print(f"Market Regime: {result.market_regime.regime_type} (Confidence: {result.market_regime.regime_confidence:.2f})")
        print(f"1Y Volatility: {result.risk_metrics.volatility_1y:.2f}")
        print(f"Beta vs SPY: {result.risk_metrics.beta:.2f}")
        print(f"Sharpe Ratio: {result.risk_metrics.sharpe_ratio:.2f}")
        print(f"Monte Carlo Median Return (1Y): {result.monte_carlo.median_return:.2%}")
        print(f"Prob of +20% move: {result.monte_carlo.prob_up_20:.2%}")
        
        print("\n=== JUDGE OPINIONS ===")
        for opinion in [result.trader_opinion, result.analyst_opinion, result.risk_pro_opinion]:
            print(f"\n[{opinion.role}]")
            print(f"Recommendation: {opinion.recommendation}")
            print(f"Opinion: {opinion.opinion}")
            
        print("\n" + "="*50)
        print(f"FINAL DECISION: {result.final_decision.recommendation}")
        print(f"Conviction Score: {result.final_decision.conviction_score}/100")
        print(f"Risk-Adjusted Rating: {result.final_decision.risk_adjusted_rating}/5.0")
        print(f"Suggested Position Size: {result.final_decision.position_size_suggestion:.2%}")
        print(f"Agreement Index: {result.final_decision.agreement_index:.2f}")
        print("\nPrimary Drivers:")
        for driver in result.final_decision.primary_drivers:
            print(f"- {driver}")
        print("\nKey Risks:")
        for risk in result.final_decision.key_risks:
            print(f"- {risk}")
        print("="*50)
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
