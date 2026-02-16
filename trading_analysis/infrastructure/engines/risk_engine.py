import yfinance as yf
import pandas as pd
import numpy as np
from ...domain.interfaces import RiskEngine
from ...domain.models import RiskMetrics

class YFinanceRiskEngine(RiskEngine):
    def compute_metrics(self, ticker: str) -> RiskMetrics:
        stock = yf.Ticker(ticker)
        spy = yf.Ticker("SPY")
        
        # Get historical data for 5 years
        hist = stock.history(period="5y")['Close']
        spy_hist = spy.history(period="5y")['Close']
        
        if hist.empty:
             # Fallback for some tickers that might not have 5y history in history()
             hist = stock.history(period="max")['Close']
             if hist.empty:
                raise ValueError(f"Insufficient historical data for {ticker}")

        if spy_hist.empty:
            spy_hist = spy.history(period="max")['Close']

        returns = hist.pct_change().dropna()
        spy_returns = spy_hist.pct_change().dropna()
        
        # Align returns for beta calculation
        common_index = returns.index.intersection(spy_returns.index)
        aligned_returns = returns.loc[common_index]
        aligned_spy_returns = spy_returns.loc[common_index]
        
        # Volatility (Annualized)
        vol_30d = float(returns.tail(30).std() * np.sqrt(252))
        vol_90d = float(returns.tail(90).std() * np.sqrt(252))
        vol_1y = float(returns.tail(252).std() * np.sqrt(252)) if len(returns) >= 252 else float(returns.std() * np.sqrt(252))
        
        # Beta vs SPY (using up to 1Y of aligned data)
        ret_1y = aligned_returns.tail(252)
        spy_ret_1y = aligned_spy_returns.tail(252)
        if len(ret_1y) > 30:
            covariance = np.cov(ret_1y, spy_ret_1y)[0][1]
            variance = np.var(spy_ret_1y)
            beta = float(covariance / variance) if variance != 0 else 1.0
        else:
            beta = 1.0
        
        # Drawdown
        def calculate_max_drawdown(series):
            if series.empty: return 0.0
            roll_max = series.cummax()
            drawdown = series / roll_max - 1.0
            return float(drawdown.min())

        max_dd_1y = calculate_max_drawdown(hist.tail(252))
        max_dd_5y = calculate_max_drawdown(hist)
        
        # Sharpe Ratio (assumes risk-free rate = 4% annualized)
        rf_annual = 0.04
        rf_daily = rf_annual / 252
        
        sample_returns = returns.tail(252)
        if not sample_returns.empty and sample_returns.std() != 0:
            excess_returns = sample_returns - rf_daily
            sharpe = float(excess_returns.mean() / sample_returns.std() * np.sqrt(252))
        else:
            sharpe = 0.0
        
        # Sortino Ratio
        downside_returns = sample_returns[sample_returns < 0]
        if not downside_returns.empty and downside_returns.std() != 0:
            sortino = float((sample_returns.mean() - rf_daily) / downside_returns.std() * np.sqrt(252))
        else:
            sortino = 0.0
        
        # 95% VaR (Historical daily)
        var_95 = float(np.percentile(sample_returns, 5)) if not sample_returns.empty else 0.0
        
        # Rolling Volatility Regime
        avg_vol_1y = vol_1y
        if vol_30d > avg_vol_1y * 1.3:
            regime = "High Volatility / Expansion"
        elif vol_30d < avg_vol_1y * 0.7:
            regime = "Low Volatility / Compression"
        else:
            regime = "Normal"

        return RiskMetrics(
            volatility_30d=vol_30d,
            volatility_90d=vol_90d,
            volatility_1y=vol_1y,
            beta=beta,
            max_drawdown_1y=max_dd_1y,
            max_drawdown_5y=max_dd_5y,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            var_95=var_95,
            volatility_regime=regime
        )
