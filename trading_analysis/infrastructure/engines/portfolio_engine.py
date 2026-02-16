import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict
from ...domain.interfaces import PortfolioImpactEngine
from ...domain.models import PortfolioImpactReport

class YFinancePortfolioImpactEngine(PortfolioImpactEngine):
    def analyze_impact(self, ticker: str, portfolio: Dict[str, float]) -> PortfolioImpactReport:
        # portfolio: {ticker: weight, ...}
        # If empty or only the target ticker, assume a benchmark comparison to SPY
        if not portfolio or list(portfolio.keys()) == [ticker]:
             portfolio_weights = {"SPY": 1.0}
        else:
             portfolio_weights = portfolio

        tickers_to_fetch = list(portfolio_weights.keys())
        if ticker not in tickers_to_fetch:
            tickers_to_fetch.append(ticker)
            
        # Fetch historical data
        try:
            data = yf.download(tickers_to_fetch, period="1y", progress=False)['Close']
            # If multiple tickers, data is a DataFrame. If one, it might be a Series or DataFrame.
            if isinstance(data, pd.Series):
                data = data.to_frame()
            
            returns = data.pct_change().dropna()
        except Exception as e:
            # Fallback if download fails
            return PortfolioImpactReport(
                correlation_to_portfolio=0.0,
                portfolio_volatility=0.0,
                marginal_contribution_to_risk=0.0,
                sharpe_change=0.0,
                suggested_position_size=0.05,
                risk_flags=[f"Error fetching portfolio data: {e}"]
            )
        
        if returns.empty or ticker not in returns.columns:
             return PortfolioImpactReport(
                correlation_to_portfolio=0.0,
                portfolio_volatility=0.0,
                marginal_contribution_to_risk=0.0,
                sharpe_change=0.0,
                suggested_position_size=0.05,
                risk_flags=["Insufficient data for portfolio impact analysis"]
            )

        # Calculate portfolio returns
        port_returns = pd.Series(0.0, index=returns.index)
        for t, weight in portfolio_weights.items():
            if t in returns.columns:
                port_returns += returns[t] * weight
            else:
                # If a ticker is missing, we just ignore it for the weighted sum
                pass
        
        # Correlation of ticker to existing portfolio
        correlation = float(returns[ticker].corr(port_returns))
        
        # Portfolio Volatility (Annualized)
        port_vol = float(port_returns.std() * np.sqrt(252))
        
        # Marginal contribution to risk (MCTR)
        # MCTR_i = Cov(R_i, R_p) / Vol_p
        cov_matrix = returns.cov() * 252
        # Cov(R_i, R_p) = Sum_j( weight_j * Cov(i, j) )
        cov_ticker_port = 0.0
        for t, weight in portfolio_weights.items():
            if t in cov_matrix.columns:
                cov_ticker_port += weight * cov_matrix.loc[ticker, t]
        
        mctr = float(cov_ticker_port / (port_vol + 1e-9))
        
        # Kelly Fraction (Capped)
        # Simplified Kelly = (Expected Return - Risk Free) / Variance
        ticker_mu = returns[ticker].mean() * 252
        ticker_var = returns[ticker].var() * 252
        rf = 0.04
        
        kelly = (ticker_mu - rf) / (ticker_var + 1e-9)
        suggested_size = float(max(0, min(kelly * 0.5, 0.2))) # Fractional Kelly (0.5) capped at 20%
        
        risk_flags = []
        if correlation > 0.7:
            risk_flags.append("High correlation to existing portfolio (>0.7)")
        if mctr > port_vol:
            risk_flags.append("Position increases overall portfolio risk (MCTR > Portfolio Vol)")
        if ticker_var > 0.5: # High absolute vol
            risk_flags.append("High asset volatility")

        return PortfolioImpactReport(
            correlation_to_portfolio=correlation,
            portfolio_volatility=port_vol,
            marginal_contribution_to_risk=mctr,
            sharpe_change=0.0, # Placeholder for more complex logic
            suggested_position_size=suggested_size,
            risk_flags=risk_flags
        )
