import numpy as np
import yfinance as yf
from ...domain.interfaces import MonteCarloEngine
from ...domain.models import MonteCarloForecast

class GBM_MonteCarloEngine(MonteCarloEngine):
    def run_simulation(self, ticker: str, num_simulations: int = 5000) -> MonteCarloForecast:
        # Set seed for reproducibility
        np.random.seed(42)
        
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")['Close']
        if hist.empty:
            hist = stock.history(period="max")['Close']
            if hist.empty:
                raise ValueError(f"Insufficient historical data for {ticker}")

        returns = hist.pct_change().dropna()
        if returns.empty:
             return MonteCarloForecast(
                prob_up_10=0, prob_up_20=0, prob_down_10=0, prob_down_20=0,
                median_return=0, percentile_5=0, percentile_95=0
            )
            
        mu = returns.mean()
        sigma = returns.std()
        
        current_price = hist.iloc[-1]
        T = 252 # 1 year forecast horizon
        
        # S(T) = S(0) * exp((mu - 0.5 * sigma^2) * T + sigma * sqrt(T) * Z)
        Z = np.random.standard_normal(num_simulations)
        future_prices = current_price * np.exp((mu - 0.5 * sigma**2) * T + sigma * np.sqrt(T) * Z)
        
        forecast_returns = (future_prices / current_price) - 1.0
        
        prob_up_10 = float(np.mean(forecast_returns >= 0.10))
        prob_up_20 = float(np.mean(forecast_returns >= 0.20))
        prob_down_10 = float(np.mean(forecast_returns <= -0.10))
        prob_down_20 = float(np.mean(forecast_returns <= -0.20))
        
        median_return = float(np.median(forecast_returns))
        percentile_5 = float(np.percentile(forecast_returns, 5))
        percentile_95 = float(np.percentile(forecast_returns, 95))

        return MonteCarloForecast(
            prob_up_10=prob_up_10,
            prob_up_20=prob_up_20,
            prob_down_10=prob_down_10,
            prob_down_20=prob_down_20,
            median_return=median_return,
            percentile_5=percentile_5,
            percentile_95=percentile_95
        )
