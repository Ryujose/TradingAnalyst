import asyncio
from typing import List, Optional, Callable
from datetime import datetime
from ..domain.interfaces import RunnersProvider, ScoringEngine, RunnersService, RunnersPersistence
from ..domain.models import RunnerItem, RunnerSnapshot, ScoreBreakdown

class DefaultRunnersService(RunnersService):
    def __init__(
        self, 
        provider: RunnersProvider, 
        scoring_engine: ScoringEngine,
        persistence: Optional[RunnersPersistence] = None
    ):
        self.provider = provider
        self.scoring_engine = scoring_engine
        self.persistence = persistence

    def get_runners(self, mode: str = "live", top_n: int = 10) -> RunnerSnapshot:
        # 1. Get candidate tickers
        candidates = self.provider.get_top_movers()
        
        # 2. Pull market snapshot for candidates
        items = self.provider.get_market_snapshot(candidates)
        
        # 3. Apply universe filters (e.g. Price > 1)
        # In a real app, this would be more configurable
        filtered_items = [
            item for item in items 
            if item.price >= 1.0 and item.volume >= 500000
        ]
        
        # 4. Compute scores and classify
        for item in filtered_items:
            item.score = self.scoring_engine.compute_score(item)
            
            if item.score >= 70:
                item.classification = "Strong Runner"
            elif item.score >= 40:
                item.classification = "Developing Runner"
            else:
                item.classification = "Ignore"
        
        # 5. Sort by score
        sorted_runners = sorted(filtered_items, key=lambda x: x.score, reverse=True)
        
        snapshot = RunnerSnapshot(
            timestamp=datetime.now(),
            runners=sorted_runners[:top_n],
            universe_size=len(filtered_items)
        )

        # 6. Persist results
        if self.persistence:
            try:
                self.persistence.save_snapshot(snapshot)
            except Exception:
                # Log error but don't fail the request
                pass
        
        return snapshot

    async def run_live_scan(self, interval: int = 60, callback: Optional[Callable] = None):
        """Continuously scans for runners and persists/notifies."""
        while True:
            try:
                snapshot = self.get_runners(mode="live")
                if callback:
                    callback(snapshot)
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                # In a real app, use structured logging
                print(f"Error in live scan: {e}")
                await asyncio.sleep(interval)
