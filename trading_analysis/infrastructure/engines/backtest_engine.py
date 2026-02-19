import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Optional
from datetime import datetime, timedelta
from ...domain.interfaces import BacktestEngine, NewsRepository

class MomentumBacktestEngine(BacktestEngine):
    def __init__(self, news_repository: Optional[NewsRepository] = None):
        self.news_repository = news_repository

    def run_backtest(self, tickers: List[str], date: datetime) -> dict:
        if not tickers:
            return {"error": "No tickers provided"}
            
        start_date = date.strftime('%Y-%m-%d')
        end_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')
        
        try:
            # Download intraday data for the backtest date
            data = yf.download(tickers, start=start_date, end=end_date, interval="5m", progress=False, group_by='ticker')
            
            results = []
            for ticker in tickers:
                try:
                    t_data = data[ticker] if len(tickers) > 1 else data
                    if t_data.empty: continue
                    
                    # Simulated entry at the end of the first hour (approx 10:30 AM)
                    # 9:30 to 10:30 is 12 bars of 5m
                    if len(t_data) < 13: continue
                    
                    entry_price = float(t_data['Close'].iloc[12])
                    remaining_data = t_data['Close'].iloc[12:]
                    
                    max_price = float(remaining_data.max())
                    min_price = float(remaining_data.min())
                    final_price = float(remaining_data.iloc[-1])
                    
                    extension = (max_price - entry_price) / entry_price
                    drawdown = (min_price - entry_price) / entry_price
                    return_pct = (final_price - entry_price) / entry_price
                    
                    results.append({
                        "ticker": ticker,
                        "extension": extension,
                        "max_drawdown": drawdown,
                        "return": return_pct,
                        "success": extension > 0.02, # 2% move after detection
                        "has_catalyst": self._check_catalyst(ticker, date)
                    })
                except Exception:
                    continue
            
            if not results:
                return {"error": "No valid data for backtest"}
                
            # Aggregate metrics
            win_rate = sum(1 for r in results if r['return'] > 0) / len(results)
            avg_return = sum(r['return'] for r in results) / len(results)
            avg_extension = sum(r['extension'] for r in results) / len(results)
            
            # Metrics with catalyst
            with_cat = [r for r in results if r['has_catalyst']]
            cat_metrics = None
            if with_cat:
                cat_metrics = {
                    "count": len(with_cat),
                    "win_rate": sum(1 for r in with_cat if r['return'] > 0) / len(with_cat),
                    "avg_return": sum(r['return'] for r in with_cat) / len(with_cat),
                    "avg_extension": sum(r['extension'] for r in with_cat) / len(with_cat)
                }

            return {
                "date": start_date,
                "tickers_count": len(results),
                "win_rate": win_rate,
                "avg_return": avg_return,
                "avg_extension": avg_extension,
                "catalyst_metrics": cat_metrics,
                "details": results
            }
        except Exception as e:
            return {"error": str(e)}

    def _check_catalyst(self, ticker: str, date: datetime) -> bool:
        if not self.news_repository:
            return False
        # Simplified: Check if any news existed for this symbol before or on the date
        news = self.news_repository.list(symbol=ticker, limit=10)
        # Filters news that happened within 48h before the backtest date
        catalysts = [n for n in news if 0 <= (date - n.provider_publish_time).total_seconds() <= 172800]
        return len(catalysts) > 0

