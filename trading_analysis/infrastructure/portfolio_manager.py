import json
import os
from typing import Dict, Any
import yfinance as yf
from ..domain.models import PortfolioItem

class PortfolioManager:
    def __init__(self, filepath: str = "portfolio.json"):
        self.filepath = filepath
        self._portfolio = self._load()

    def _load(self) -> Dict[str, PortfolioItem]:
        if not os.path.exists(self.filepath):
            # Default portfolio if file doesn't exist
            return {
                "SPY": PortfolioItem(ticker="SPY", weight=0.5, name="SPDR S&P 500 ETF Trust"),
                "QQQ": PortfolioItem(ticker="QQQ", weight=0.3, name="Invesco QQQ Trust"),
                "TLT": PortfolioItem(ticker="TLT", weight=0.2, name="iShares 20+ Year Treasury Bond ETF")
            }
        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)
                
            portfolio = {}
            for ticker, val in data.items():
                if isinstance(val, (int, float)):
                    # Migration from old format: {ticker: weight}
                    portfolio[ticker] = PortfolioItem(ticker=ticker, weight=val)
                elif isinstance(val, dict):
                    portfolio[ticker] = PortfolioItem(**val)
                else:
                    # Fallback
                    portfolio[ticker] = PortfolioItem(ticker=ticker, weight=0.0)
            return portfolio
        except Exception:
            return {
                "SPY": PortfolioItem(ticker="SPY", weight=0.5, name="SPDR S&P 500 ETF Trust"),
                "QQQ": PortfolioItem(ticker="QQQ", weight=0.3, name="Invesco QQQ Trust"),
                "TLT": PortfolioItem(ticker="TLT", weight=0.2, name="iShares 20+ Year Treasury Bond ETF")
            }

    def save(self):
        with open(self.filepath, 'w') as f:
            data = {ticker: item.model_dump() for ticker, item in self._portfolio.items()}
            json.dump(data, f, indent=4)

    def get_portfolio(self) -> Dict[str, PortfolioItem]:
        return self._portfolio

    def update_ticker(self, ticker: str, weight: float, entry_price: float = None, name: str = None):
        if weight <= 0:
            if ticker in self._portfolio:
                del self._portfolio[ticker]
        else:
            if not name:
                # Try to get name from yfinance if not provided and it's a new ticker or name missing
                if ticker not in self._portfolio or not self._portfolio[ticker].name:
                    try:
                        stock = yf.Ticker(ticker)
                        name = stock.info.get('longName', ticker)
                    except Exception:
                        name = ticker
                else:
                    name = self._portfolio[ticker].name
            
            if entry_price is None and ticker in self._portfolio:
                entry_price = self._portfolio[ticker].entry_price

            self._portfolio[ticker] = PortfolioItem(
                ticker=ticker, 
                weight=weight, 
                entry_price=entry_price,
                name=name
            )
        self.save()

    def remove_ticker(self, ticker: str):
        if ticker in self._portfolio:
            del self._portfolio[ticker]
            self.save()
