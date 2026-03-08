"""
Correlation Analysis Tools - Track gold correlations, divergences, safe haven flows.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_formatter import safe_float


def load_correlation_config() -> Dict:
    """Load correlation configuration."""
    config_path = Path(__file__).parent.parent / "config" / "correlation_config.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}


def calculate_rolling_correlations(all_data: Dict, windows: List[int] = [20, 50, 100]) -> Dict:
    """
    Calculate rolling correlations between Gold and each correlated instrument.
    
    Args:
        all_data: Dict with instrument data (from fetch_all_correlated_instruments)
        windows: Correlation window periods
    
    Returns:
        Correlation analysis for each instrument
    """
    if "XAUUSD" not in all_data and "XAUUSDm" not in all_data:
        return {"status": "error", "message": "Gold data not available"}
    
    # Get gold data
    gold_key = "XAUUSD" if "XAUUSD" in all_data else "XAUUSDm"
    gold_info = all_data.get(gold_key, {})
    
    if not gold_info.get("available"):
        return {"status": "error", "message": "Gold data not available"}
    
    gold_df = gold_info.get("data")
    if gold_df is None or len(gold_df) < 50:
        return {"status": "error", "message": "Insufficient gold data"}
    
    gold_returns = gold_df['close'].pct_change().dropna()
    
    correlations = {}
    
    for symbol, info in all_data.items():
        if symbol in ["XAUUSD", "XAUUSDm"] or not info.get("available"):
            continue
        
        other_df = info.get("data")
        if other_df is None or len(other_df) < 50:
            continue
        
        other_returns = other_df['close'].pct_change().dropna()
        
        # Align lengths
        min_len = min(len(gold_returns), len(other_returns))
        if min_len < 20:
            continue
        
        g = gold_returns.tail(min_len).reset_index(drop=True)
        o = other_returns.tail(min_len).reset_index(drop=True)
        
        symbol_corr = {
            "type": info.get("type", "unknown"),
            "expected_correlation": info.get("expected_corr", 0),
            "description": info.get("description", ""),
        }
        
        for window in windows:
            if min_len >= window:
                rolling_corr = g.rolling(window).corr(o)
                current_corr = float(rolling_corr.iloc[-1]) if not pd.isna(rolling_corr.iloc[-1]) else 0
                avg_corr = float(rolling_corr.tail(window).mean()) if not rolling_corr.tail(window).isna().all() else 0
                
                symbol_corr[f"corr_{window}"] = {
                    "current": round(current_corr, 4),
                    "average": round(avg_corr, 4),
                    "strength": "STRONG" if abs(current_corr) > 0.7 else "MODERATE" if abs(current_corr) > 0.4 else "WEAK",
                }
        
        # Detect divergence from expected
        current = symbol_corr.get("corr_20", {}).get("current", 0)
        expected = info.get("expected_corr", 0)
        divergence = abs(current - expected)
        
        symbol_corr["divergence_from_expected"] = round(divergence, 4)
        symbol_corr["correlation_anomaly"] = divergence > 0.4
        symbol_corr["regime_change"] = (current > 0) != (expected > 0) if current != 0 and expected != 0 else False
        
        correlations[symbol] = symbol_corr
    
    return {
        "status": "success",
        "correlations": correlations,
        "instruments_analyzed": len(correlations)
    }


def detect_correlation_divergences(all_data: Dict, lookback: int = 20) -> Dict:
    """
    Find divergences where correlated markets disagree with Gold.
    These are high-probability trade signals.
    """
    gold_key = None
    for k in ["XAUUSD", "XAUUSDm"]:
        if k in all_data and all_data[k].get("available"):
            gold_key = k
            break
    
    if not gold_key:
        return {"status": "error", "message": "Gold data not available"}
    
    gold_df = all_data[gold_key]["data"]
    gold_change = (gold_df['close'].iloc[-1] - gold_df['close'].iloc[-lookback]) / gold_df['close'].iloc[-lookback] * 100
    gold_direction = "UP" if gold_change > 0.1 else "DOWN" if gold_change < -0.1 else "FLAT"
    
    divergences = []
    confirmations = []
    
    for symbol, info in all_data.items():
        if symbol in ["XAUUSD", "XAUUSDm"] or not info.get("available"):
            continue
        
        other_df = info.get("data")
        if other_df is None or len(other_df) < lookback:
            continue
        
        other_change = (other_df['close'].iloc[-1] - other_df['close'].iloc[-lookback]) / other_df['close'].iloc[-lookback] * 100
        other_direction = "UP" if other_change > 0.1 else "DOWN" if other_change < -0.1 else "FLAT"
        
        expected_corr = info.get("expected_corr", 0)
        
        # Check for divergence
        if expected_corr > 0.3:  # Should move together
            if (gold_direction == "UP" and other_direction == "DOWN") or \
               (gold_direction == "DOWN" and other_direction == "UP"):
                divergences.append({
                    "symbol": symbol,
                    "type": "POSITIVE_CORRELATION_DIVERGENCE",
                    "gold_move": f"{gold_change:+.2f}%",
                    "other_move": f"{other_change:+.2f}%",
                    "expected": "Same direction",
                    "actual": "Opposite direction",
                    "significance": "HIGH" if abs(expected_corr) > 0.6 else "MEDIUM",
                    "implication": f"Either Gold or {symbol} will correct"
                })
            else:
                confirmations.append({
                    "symbol": symbol,
                    "aligned": True,
                    "gold_move": f"{gold_change:+.2f}%",
                    "other_move": f"{other_change:+.2f}%"
                })
        
        elif expected_corr < -0.3:  # Should move opposite
            if (gold_direction == "UP" and other_direction == "UP") or \
               (gold_direction == "DOWN" and other_direction == "DOWN"):
                divergences.append({
                    "symbol": symbol,
                    "type": "INVERSE_CORRELATION_DIVERGENCE",
                    "gold_move": f"{gold_change:+.2f}%",
                    "other_move": f"{other_change:+.2f}%",
                    "expected": "Opposite direction",
                    "actual": "Same direction",
                    "significance": "HIGH" if abs(expected_corr) > 0.6 else "MEDIUM",
                    "implication": f"Unusual alignment - possible regime shift"
                })
    
    if len(divergences) > 3:
        overall_signal = "DIVERGENCE_WARNING"
    elif len(confirmations) > len(divergences):
        overall_signal = "MOSTLY_ALIGNED"
    else:
        overall_signal = "MIXED"
    
    return {
        "status": "success",
        "gold_direction": gold_direction,
        "gold_change_pct": round(gold_change, 2),
        "divergences": divergences,
        "divergence_count": len(divergences),
        "confirmations_count": len(confirmations),
        "overall_signal": overall_signal
    }


def compute_dxy_synthetic(all_data: Dict) -> Dict:
    """
    Build a synthetic DXY from available forex pairs.
    DXY weights: EUR 57.6%, JPY 13.6%, GBP 11.9%, CAD 9.1%, CHF 3.6%
    """
    config = load_correlation_config()
    weights = config.get("dxy_weights", {
        "EURUSD": -0.576,
        "USDJPY": 0.136,
        "GBPUSD": -0.119,
        "USDCAD": 0.091,
        "USDCHF": 0.036
    })
    
    changes = {}
    for pair, weight in weights.items():
        # Try with m suffix first
        for test_pair in [f"{pair}m", pair]:
            if test_pair in all_data and all_data[test_pair].get("available"):
                df = all_data[test_pair]["data"]
                if len(df) >= 20:
                    pct_change = (df['close'].iloc[-1] - df['close'].iloc[-20]) / df['close'].iloc[-20] * 100
                    changes[pair] = {
                        "change_pct": round(float(pct_change), 3),
                        "weight": weight,
                        "weighted_impact": round(float(pct_change * weight), 4)
                    }
                break
    
    synthetic_dxy_change = sum(c["weighted_impact"] for c in changes.values())
    
    if synthetic_dxy_change > 0.1:
        dxy_direction = "STRENGTHENING"
        gold_implication = "BEARISH"
    elif synthetic_dxy_change < -0.1:
        dxy_direction = "WEAKENING"
        gold_implication = "BULLISH"
    else:
        dxy_direction = "STABLE"
        gold_implication = "NEUTRAL"
    
    strongest_pair = max(changes.items(), key=lambda x: abs(x[1]["weighted_impact"]))[0] if changes else None
    
    narrative = f"USD is {dxy_direction}. "
    if dxy_direction == "WEAKENING":
        narrative += "Dollar weakness supports higher Gold prices."
    elif dxy_direction == "STRENGTHENING":
        narrative += "Dollar strength pressures Gold lower."
    else:
        narrative += "Neutral dollar impact on Gold."
    
    return {
        "status": "success",
        "synthetic_dxy_change_20p": round(synthetic_dxy_change, 3),
        "dxy_direction": dxy_direction,
        "gold_implication": gold_implication,
        "component_analysis": changes,
        "strongest_usd_pair": strongest_pair,
        "narrative": narrative
    }


def analyze_safe_haven_flow(all_data: Dict, lookback: int = 10) -> Dict:
    """
    Detect risk-on vs risk-off environment.
    Checks safe havens (Gold, Silver, JPY, CHF) vs risk assets (Stocks, BTC, AUD).
    """
    config = load_correlation_config()
    safe_havens = config.get("safe_haven_assets", ["XAUUSD", "XAGUSD", "USDJPY", "USDCHF", "VIX"])
    risk_assets = config.get("risk_assets", ["US500", "US100", "BTCUSD", "AUDUSD"])
    
    safe_haven_score = 0
    risk_asset_score = 0
    details = {"safe_havens": {}, "risk_assets": {}}
    
    total_safe = 0
    for symbol in safe_havens:
        for test_symbol in [f"{symbol}m", symbol]:
            if test_symbol in all_data and all_data[test_symbol].get("available"):
                df = all_data[test_symbol]["data"]
                if len(df) >= lookback:
                    change = (df['close'].iloc[-1] - df['close'].iloc[-lookback]) / df['close'].iloc[-lookback] * 100
                    total_safe += 1
                    
                    # For USDJPY/USDCHF, drop = safe haven demand (JPY/CHF strengthening)
                    if symbol in ["USDJPY", "USDCHF"]:
                        safe_haven_demand = change < -0.1
                        display_change = -change
                    else:
                        safe_haven_demand = change > 0.1
                        display_change = change
                    
                    if safe_haven_demand:
                        safe_haven_score += 1
                    
                    details["safe_havens"][symbol] = {
                        "change_pct": round(display_change, 3),
                        "demand": "RISING" if safe_haven_demand else "FALLING"
                    }
                break
    
    total_risk = 0
    for symbol in risk_assets:
        for test_symbol in [f"{symbol}m", symbol]:
            if test_symbol in all_data and all_data[test_symbol].get("available"):
                df = all_data[test_symbol]["data"]
                if len(df) >= lookback:
                    change = (df['close'].iloc[-1] - df['close'].iloc[-lookback]) / df['close'].iloc[-lookback] * 100
                    total_risk += 1
                    risk_on = change > 0.1
                    
                    if risk_on:
                        risk_asset_score += 1
                    
                    details["risk_assets"][symbol] = {
                        "change_pct": round(change, 3),
                        "direction": "RISK_ON" if risk_on else "RISK_OFF"
                    }
                break
    
    # Determine environment
    if total_safe == 0:
        total_safe = 1
    if total_risk == 0:
        total_risk = 1
    
    safe_pct = safe_haven_score / total_safe * 100
    risk_pct = risk_asset_score / total_risk * 100
    
    if safe_pct > 60 and risk_pct < 40:
        environment = "RISK_OFF"
        gold_impact = "STRONGLY_BULLISH"
    elif safe_pct < 40 and risk_pct > 60:
        environment = "RISK_ON"
        gold_impact = "BEARISH"
    elif safe_pct > 50:
        environment = "MILD_RISK_OFF"
        gold_impact = "MILDLY_BULLISH"
    else:
        environment = "MIXED"
        gold_impact = "NEUTRAL"
    
    narrative = f"Market is in {environment} mode. "
    if "RISK_OFF" in environment:
        narrative += "Investors seeking safety → Gold demand rising."
    elif "RISK_ON" in environment:
        narrative += "Investors seeking yield → Gold demand lower."
    else:
        narrative += "Mixed signals across assets."
    
    return {
        "status": "success",
        "market_environment": environment,
        "gold_impact": gold_impact,
        "safe_haven_score": f"{safe_haven_score}/{total_safe}",
        "risk_asset_score": f"{risk_asset_score}/{total_risk}",
        "details": details,
        "narrative": narrative
    }


def full_correlation_analysis(all_data: Dict) -> Dict:
    """
    Complete correlation analysis combining all tools.
    """
    correlations = calculate_rolling_correlations(all_data)
    divergences = detect_correlation_divergences(all_data)
    dxy = compute_dxy_synthetic(all_data)
    safe_haven = analyze_safe_haven_flow(all_data)
    
    # Synthesize overall correlation signal
    bullish_signals = 0
    bearish_signals = 0
    
    if dxy.get("gold_implication") == "BULLISH":
        bullish_signals += 2
    elif dxy.get("gold_implication") == "BEARISH":
        bearish_signals += 2
    
    if safe_haven.get("gold_impact") in ["BULLISH", "STRONGLY_BULLISH", "MILDLY_BULLISH"]:
        bullish_signals += 2
    elif safe_haven.get("gold_impact") == "BEARISH":
        bearish_signals += 2
    
    if divergences.get("overall_signal") == "MOSTLY_ALIGNED":
        # Confirm the direction
        if divergences.get("gold_direction") == "UP":
            bullish_signals += 1
        elif divergences.get("gold_direction") == "DOWN":
            bearish_signals += 1
    
    if bullish_signals > bearish_signals + 1:
        overall = "BULLISH"
    elif bearish_signals > bullish_signals + 1:
        overall = "BEARISH"
    else:
        overall = "NEUTRAL"
    
    return {
        "status": "success",
        "overall_correlation_signal": overall,
        "bullish_signals": bullish_signals,
        "bearish_signals": bearish_signals,
        "rolling_correlations": correlations.get("correlations", {}),
        "divergences": divergences,
        "dxy_synthetic": dxy,
        "safe_haven_flow": safe_haven
    }
