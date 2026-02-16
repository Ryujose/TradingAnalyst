import yfinance as yf
import pandas as pd
import numpy as np
from typing import List
from datetime import datetime, timedelta
from ..domain.interfaces import DataProvider
from ..domain.models import CompanyFinancials, TechnicalLevels, NewsItem

class YFinanceDataProvider(DataProvider):
    def get_financials(self, ticker: str) -> CompanyFinancials:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Financial projections (often found in analysis or earnings estimates)
        # For simplicity, we'll take some growth estimates if available
        projections = f"Revenue Growth (YoY): {info.get('revenueGrowth', 'N/A')}. "
        projections += f"Earnings Growth (YoY): {info.get('earningsGrowth', 'N/A')}. "
        projections += f"Next fiscal year end: {info.get('nextFiscalYearEnd', 'N/A')}"

        return CompanyFinancials(
            cash=info.get('totalCash', 0.0),
            debt=info.get('totalDebt', 0.0),
            market_cap=info.get('marketCap', 0.0),
            pe_ratio=info.get('trailingPE'),
            pb_ratio=info.get('priceToBook'),
            revenue_growth=info.get('revenueGrowth'),
            profit_margins=info.get('profitMargins'),
            free_cash_flow=info.get('freeCashflow'),
            projections=projections
        )

    def get_technical_data(self, ticker: str) -> TechnicalLevels:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="6mo")
        if hist.empty:
            return TechnicalLevels(supports=[], resistances=[], current_price=0.0)
        
        current_price = hist['Close'].iloc[-1]
        
        # Simple support/resistance logic: local min/max
        # In a real app, we might use more sophisticated methods
        window = 20
        supports = []
        resistances = []
        
        for i in range(window, len(hist) - window):
            is_min = True
            is_max = True
            for j in range(i - window, i + window):
                if hist['Low'].iloc[j] < hist['Low'].iloc[i]:
                    is_min = False
                if hist['High'].iloc[j] > hist['High'].iloc[i]:
                    is_max = False
            
            if is_min:
                supports.append(round(float(hist['Low'].iloc[i]), 2))
            if is_max:
                resistances.append(round(float(hist['High'].iloc[i]), 2))
        
        # Filter and deduplicate near values
        def simplify(levels):
            if not levels: return []
            levels.sort()
            unique_levels = [levels[0]]
            for l in levels[1:]:
                if l > unique_levels[-1] * 1.02: # 2% difference
                    unique_levels.append(l)
            return unique_levels

        return TechnicalLevels(
            supports=simplify(supports),
            resistances=simplify(resistances),
            current_price=round(float(current_price), 2)
        )

    def get_news(self, ticker: str) -> List[NewsItem]:
        stock = yf.Ticker(ticker)
        news_data = stock.news
        items = []
        for n in news_data:
            items.append(NewsItem(
                title=n.get('title', ''),
                publisher=n.get('publisher', ''),
                link=n.get('link', ''),
                provider_publish_time=datetime.fromtimestamp(n.get('providerPublishTime', 0)),
                summary=None # yfinance news doesn't always have full text, just title/link
            ))
        return items
