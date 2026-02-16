import yfinance as yf
import pandas as pd
import numpy as np
from ...domain.interfaces import MarketRegimeEngine
from ...domain.models import MarketRegime

class YFinanceMarketRegimeEngine(MarketRegimeEngine):
    def detect_regime(self) -> MarketRegime:
        spy = yf.Ticker("SPY")
        hist = spy.history(period="2y")['Close']
        
        if len(hist) < 200:
            return MarketRegime(regime_type="Unknown", regime_confidence=0.0, regime_risk_multiplier=1.0)

        # 200 MA
        ma200_series = hist.rolling(window=200).mean()
        ma200 = ma200_series.iloc[-1]
        current_price = hist.iloc[-1]
        
        # Volatility
        returns = hist.pct_change().dropna()
        current_vol = float(returns.tail(20).std() * np.sqrt(252))
        avg_vol = float(returns.tail(252).std() * np.sqrt(252))
        
        # Trend of MA200
        ma200_trending_up = ma200 > ma200_series.iloc[-20]

        regime = "Normal"
        confidence = 0.8
        multiplier = 1.0
        
        if current_price > ma200:
            if current_vol < avg_vol:
                regime = "Bullish Expansion"
                multiplier = 0.8
            else:
                regime = "Bullish Volatile"
                multiplier = 1.2
        else:
            if current_vol > avg_vol:
                regime = "Bearish Contraction"
                multiplier = 1.5
            else:
                regime = "High Volatility Risk-Off"
                multiplier = 2.0

        # Adjust confidence based on trend alignment
        if (current_price > ma200) == ma200_trending_up:
            confidence = 0.9
        else:
            confidence = 0.6

        return MarketRegime(
            regime_type=regime,
            regime_confidence=confidence,
            regime_risk_multiplier=multiplier
        )
