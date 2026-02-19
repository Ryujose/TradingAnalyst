import yfinance as yf
import pandas as pd
import numpy as np
from typing import List
from datetime import datetime, timedelta
from ..domain.interfaces import RunnersProvider
from ..domain.models import RunnerItem

class YFinanceRunnersProvider(RunnersProvider):
    def get_top_movers(self) -> List[str]:
        """Returns a list of candidate tickers that are moving using yfinance's screeners."""
        tickers = set()
        try:
            gainers = yf.get_daily_gainers()
            if gainers is not None and not gainers.empty:
                tickers.update(gainers.index.tolist())
        except Exception:
            pass
            
        try:
            active = yf.get_daily_most_active()
            if active is not None and not active.empty:
                tickers.update(active.index.tolist())
        except Exception:
            pass
            
        return list(tickers)

    def get_market_snapshot(self, tickers: List[str]) -> List[RunnerItem]:
        if not tickers:
            return []
            
        # Download 1d data at 5m or 15m intervals for intraday metrics
        # And 1mo data for daily relative volume baseline
        try:
            # For simplicity, we fetch info for each ticker to get market cap, etc.
            # And history for metrics.
            results = []
            
            # Batching might be better but yf.download doesn't return info.
            # We use yf.download for history and separate calls for info.
            
            # 1. Daily baseline (last 30 days)
            daily_data = yf.download(tickers, period="35d", interval="1d", progress=False, group_by='ticker')
            
            # 2. Intraday data
            intraday_data = yf.download(tickers, period="1d", interval="5m", progress=False, group_by='ticker')
            
            for ticker in tickers:
                try:
                    t_daily = daily_data[ticker] if len(tickers) > 1 else daily_data
                    t_intra = intraday_data[ticker] if len(tickers) > 1 else intraday_data
                    
                    if t_daily.empty or t_intra.empty:
                        continue
                        
                    # Basic metrics
                    last_price = float(t_intra['Close'].iloc[-1])
                    prev_close = float(t_daily['Close'].iloc[-2]) # Yesterday's close
                    open_price = float(t_intra['Open'].iloc[0])
                    
                    pct_change = (last_price - prev_close) / prev_close
                    gap_pct = (open_price - prev_close) / prev_close
                    
                    # Relative Volume (Cumulative volume today vs avg volume last 30 days)
                    # Note: Today's volume in t_daily might be incomplete if market is open
                    today_vol = float(t_intra['Volume'].sum())
                    avg_vol_30d = float(t_daily['Volume'].iloc[:-1].tail(30).mean())
                    rel_vol = today_vol / avg_vol_30d if avg_vol_30d > 0 else 1.0
                    
                    # VWAP calculation
                    # VWAP = Sum(Price * Volume) / Sum(Volume)
                    typical_price = (t_intra['High'] + t_intra['Low'] + t_intra['Close']) / 3
                    vwap = (typical_price * t_intra['Volume']).cumsum() / t_intra['Volume'].cumsum()
                    current_vwap = float(vwap.iloc[-1])
                    vwap_dist = (last_price - current_vwap) / current_vwap if current_vwap > 0 else 0.0
                    
                    # Volume Acceleration (last 15m vs avg of the day)
                    last_15m_vol = float(t_intra['Volume'].tail(3).sum())
                    avg_5m_vol = float(t_intra['Volume'].mean())
                    vol_acc = last_15m_vol / (avg_5m_vol * 3) if avg_5m_vol > 0 else 1.0
                    
                    # Range expansion (Intraday range / Avg Daily Range 14d)
                    intraday_range = float(t_intra['High'].max() - t_intra['Low'].min())
                    daily_ranges = (t_daily['High'] - t_daily['Low']).iloc[:-1].tail(14)
                    adr = float(daily_ranges.mean())
                    range_exp = intraday_range / adr if adr > 0 else 1.0
                    
                    # Fetch info for market cap and float (Slow, but necessary if not cached)
                    # In a real app, we would cache this or use a faster provider.
                    info = yf.Ticker(ticker).info
                    mcap = info.get('marketCap')
                    # yfinance float is often missing or called differently
                    float_s = info.get('floatShares')
                    
                    results.append(RunnerItem(
                        ticker=ticker,
                        price=last_price,
                        change=last_price - prev_close,
                        pct_change=pct_change * 100,
                        volume=int(today_vol),
                        relative_volume=rel_vol,
                        gap_pct=gap_pct * 100,
                        vwap_dist=vwap_dist * 100,
                        volatility=float(t_intra['Close'].pct_change().std() * np.sqrt(252 * 78)), # 78 5m bars in a day
                        range_expansion=range_exp,
                        volume_acceleration=vol_acc,
                        market_cap=mcap,
                        float_size=float_s,
                        timestamp=datetime.now()
                    ))
                except Exception as e:
                    # Skip if data is malformed for this ticker
                    continue
            return results
        except Exception:
            return []
