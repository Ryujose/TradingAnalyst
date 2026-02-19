import pytest
from trading_analysis.domain.models import RunnerItem
from trading_analysis.infrastructure.engines.runners_scoring import MomentumScoringEngine

def test_scoring_logic():
    engine = MomentumScoringEngine()
    
    # Strong Runner
    strong_item = RunnerItem(
        ticker="STRG",
        price=100.0,
        change=15.0,
        pct_change=15.0,
        volume=1000000,
        relative_volume=10.0,
        range_expansion=3.0,
        volatility=0.2,
        volume_acceleration=5.0
    )
    
    score = engine.compute_score(strong_item)
    assert score > 50
    
    # Weak Runner
    weak_item = RunnerItem(
        ticker="WEAK",
        price=10.0,
        change=0.1,
        pct_change=1.0,
        volume=100000,
        relative_volume=0.5,
        range_expansion=0.5,
        volatility=0.01,
        volume_acceleration=0.5
    )
    
    weak_score = engine.compute_score(weak_item)
    assert weak_score < score

def test_breakdown():
    engine = MomentumScoringEngine()
    item = RunnerItem(
        ticker="TEST",
        price=10.0,
        change=0.5,
        pct_change=5.0,
        volume=100000,
        relative_volume=2.0,
        range_expansion=1.2,
        volatility=0.02,
        volume_acceleration=1.5
    )
    
    breakdown = engine.get_breakdown(item)
    assert breakdown.momentum_score > 0
    assert breakdown.liquidity_score > 0
    assert abs(breakdown.total_score - (
        breakdown.momentum_score * 0.4 +
        breakdown.liquidity_score * 0.3 +
        breakdown.volatility_score * 0.15 +
        breakdown.acceleration_score * 0.15
    )) < 0.001
