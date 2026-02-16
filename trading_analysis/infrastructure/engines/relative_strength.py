import yfinance as yf
import pandas as pd
import numpy as np
from ...domain.interfaces import RelativeStrengthEngine
from ...domain.models import RelativeStrengthReport

SECTOR_ETF_MAP = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financial Services": "XLF",
    "Consumer Cyclical": "XLY",
    "Communication Services": "XLC",
    "Industrials": "XLI",
    "Consumer Defensive": "XLP",
    "Energy": "XLE",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Basic Materials": "XLB"
}

# Approximate sector averages for valuation comparison
SECTOR_PE_AVG = {
    "Technology": 35.0,
    "Healthcare": 22.0,
    "Financial Services": 14.0,
    "Consumer Cyclical": 28.0,
    "Communication Services": 25.0,
    "Industrials": 20.0,
    "Consumer Defensive": 24.0,
    "Energy": 11.0,
    "Utilities": 17.0,
    "Real Estate": 35.0,
    "Basic Materials": 16.0
}

SECTOR_GROWTH_AVG = {
    "Technology": 0.12,
    "Healthcare": 0.07,
    "Financial Services": 0.05,
    "Consumer Cyclical": 0.08,
    "Communication Services": 0.10,
    "Industrials": 0.06,
    "Consumer Defensive": 0.04,
    "Energy": 0.03,
    "Utilities": 0.03,
    "Real Estate": 0.05,
    "Basic Materials": 0.04
}

SECTOR_MARGIN_AVG = {
    "Technology": 0.20,
    "Healthcare": 0.15,
    "Financial Services": 0.25,
    "Consumer Cyclical": 0.10,
    "Communication Services": 0.18,
    "Industrials": 0.12,
    "Consumer Defensive": 0.06,
    "Energy": 0.15,
    "Utilities": 0.10,
    "Real Estate": 0.30,
    "Basic Materials": 0.12
}

class YFinanceRelativeStrengthEngine(RelativeStrengthEngine):
    def compute_report(self, ticker: str) -> RelativeStrengthReport:
        stock = yf.Ticker(ticker)
        info = stock.info
        sector = info.get('sector')
        
        # 1. Price performance vs SPY and Sector
        hist = stock.history(period="1y")['Close']
        spy_hist = yf.Ticker("SPY").history(period="1y")['Close']
        
        sector_etf = SECTOR_ETF_MAP.get(sector, "SPY")
        sector_hist = yf.Ticker(sector_etf).history(period="1y")['Close'] if sector_etf != "SPY" else spy_hist

        def calc_perf(series, days):
            if len(series) < 2: return 0.0
            idx = min(days, len(series) - 1)
            return (series.iloc[-1] / series.iloc[-idx]) - 1.0

        t_3m = calc_perf(hist, 63)
        t_6m = calc_perf(hist, 126)
        t_1y = calc_perf(hist, 252)

        s_3m = calc_perf(spy_hist, 63)
        s_6m = calc_perf(spy_hist, 126)
        s_1y = calc_perf(spy_hist, 252)

        sec_3m = calc_perf(sector_hist, 63)
        sec_6m = calc_perf(sector_hist, 126)
        sec_1y = calc_perf(sector_hist, 252)

        # 2. Valuation vs Sector
        pe = info.get('trailingPE') or info.get('forwardPE') or 0.0
        sector_pe = SECTOR_PE_AVG.get(sector, 20.0)
        pe_vs_sector = (pe / sector_pe) if sector_pe != 0 else 1.0

        # 3. Fundamentals vs Competitors (Industry/Sector average)
        rev_growth = info.get('revenueGrowth') or 0.0
        sector_growth = SECTOR_GROWTH_AVG.get(sector, 0.05)
        growth_vs_peers = rev_growth - sector_growth

        margin = info.get('profitMargins') or 0.0
        sector_margin = SECTOR_MARGIN_AVG.get(sector, 0.10)
        margin_vs_peers = margin - sector_margin

        # 4. Sector Ranking Estimate (Dummy logic or simplified based on sector performance)
        # Rank sectors by 3m performance relative to SPY
        sector_rank = 5 # Default middle rank
        if sec_3m > s_3m + 0.05: sector_rank = 1
        elif sec_3m > s_3m: sector_rank = 3
        elif sec_3m < s_3m - 0.05: sector_rank = 9

        return RelativeStrengthReport(
            perf_vs_spy_3m=t_3m - s_3m,
            perf_vs_spy_6m=t_6m - s_6m,
            perf_vs_spy_1y=t_1y - s_1y,
            perf_vs_sector_3m=t_3m - sec_3m,
            perf_vs_sector_6m=t_6m - sec_6m,
            perf_vs_sector_1y=t_1y - sec_1y,
            pe_vs_sector_avg=pe_vs_sector,
            rev_growth_vs_competitors=growth_vs_peers,
            margin_vs_competitors=margin_vs_peers,
            sector_ranking=sector_rank
        )
