import json
import csv
import os
from datetime import datetime
from typing import List, Optional
from ..domain.models import ComprehensiveAnalysis, ExportData

class DataExporter:
    @staticmethod
    def to_json(analysis: ComprehensiveAnalysis, filename: str = "analysis_export.json"):
        export_data = ExportData(
            timestamp=datetime.now(),
            ticker=analysis.ticker,
            signal=analysis.final_decision.recommendation,
            conviction=analysis.final_decision.conviction_score,
            key_metrics={
                "volatility": analysis.risk_metrics.volatility_1y if analysis.risk_metrics else 0,
                "beta": analysis.risk_metrics.beta if analysis.risk_metrics else 1.0,
                "sharpe": analysis.risk_metrics.sharpe_ratio if analysis.risk_metrics else 0,
                "regime": analysis.market_regime.regime_type if analysis.market_regime else "Unknown",
                "suggested_size": analysis.final_decision.position_size_suggestion
            }
        )
        
        # We can append to a list or overwrite. Let's append to a list if exists.
        data_list = []
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    data_list = json.load(f)
                    if not isinstance(data_list, list):
                        data_list = [data_list]
            except Exception:
                data_list = []
        
        data_list.append(export_data.model_dump(mode='json'))
        
        with open(filename, 'w') as f:
            json.dump(data_list, f, indent=4)

    @staticmethod
    def to_csv(analysis: ComprehensiveAnalysis, filename: str = "analysis_export.csv"):
        file_exists = os.path.exists(filename)
        with open(filename, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "Ticker", "Signal", "Conviction", "Volatility", "Regime"])
            
            writer.writerow([
                datetime.now().isoformat(),
                analysis.ticker,
                analysis.final_decision.recommendation,
                analysis.final_decision.conviction_score,
                analysis.risk_metrics.volatility_1y if analysis.risk_metrics else "N/A",
                analysis.market_regime.regime_type if analysis.market_regime else "Unknown"
            ])
