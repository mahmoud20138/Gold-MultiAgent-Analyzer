"""
Signal Synthesis Tools - Generate final trade signals from all analysis.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_formatter import safe_float


def generate_trade_signal(
    chart_analysis: Dict,
    market_structure: Dict,
    volume_analysis: Dict,
    correlation_analysis: Dict,
    risk_assessment: Dict,
    support_resistance: Dict,
    symbol: str,
    timeframe: str,
    sentiment_score: float = 0  # -100 to +100
) -> Dict:
    """
    Score and synthesize all analyses into a final trade signal.
    
    Args:
        chart_analysis: Technical indicators output
        market_structure: SMC analysis output
        volume_analysis: Volume analysis output
        correlation_analysis: Correlations output
        risk_assessment: Risk viability output
        support_resistance: S/R levels
        symbol: Trading symbol
        timeframe: Primary timeframe
        sentiment_score: Fundamental sentiment (-100 to +100)
    
    Returns:
        Complete trade recommendation with scoring
    """
    score = 50  # Start neutral
    reasons = []
    warnings = []
    
    # ═══════════════════════════════════════════════════════════════
    # CHART ANALYSIS SCORING (max ±25)
    # ═══════════════════════════════════════════════════════════════
    
    if chart_analysis.get("status") == "success":
        indicators = chart_analysis.get("indicators", {})

        # Trend alignment via ADX
        adx = indicators.get("adx", {})
        if adx.get("trend_strength") == "STRONG":
            if adx.get("direction") == "BULLISH":
                score += 10
                reasons.append("Strong bullish trend (ADX > 25)")
            else:
                score -= 10
                reasons.append("Strong bearish trend (ADX > 25)")

        # RSI
        rsi = indicators.get("rsi", {})
        rsi_val = rsi.get("value", 50)
        if rsi.get("condition") == "OVERSOLD":
            score += 5
            reasons.append(f"RSI oversold ({rsi_val}) - potential bounce")
        elif rsi.get("condition") == "OVERBOUGHT":
            score -= 5
            reasons.append(f"RSI overbought ({rsi_val}) - potential pullback")

        # MACD
        macd = indicators.get("macd", {})
        if macd.get("crossover") == "BULLISH" and macd.get("histogram", 0) > 0:
            score += 5
            reasons.append("MACD bullish crossover")
        elif macd.get("crossover") == "BEARISH" and macd.get("histogram", 0) < 0:
            score -= 5
            reasons.append("MACD bearish crossover")

        # Price vs SMA200
        ma = indicators.get("moving_averages", {})
        if ma.get("price_vs_sma200") == "ABOVE":
            score += 3
            reasons.append("Price above SMA200 - bullish bias")
        else:
            score -= 3
            reasons.append("Price below SMA200 - bearish bias")

        # Bollinger position
        bb = indicators.get("bollinger_bands", {})
        if bb.get("squeeze") == "SQUEEZE":
            warnings.append("Bollinger squeeze - breakout imminent")
    
    # ═══════════════════════════════════════════════════════════════
    # MARKET STRUCTURE SCORING (max ±20)
    # ═══════════════════════════════════════════════════════════════
    
    if market_structure.get("status") == "success":
        structure = market_structure.get("market_structure", "")
        if structure == "BULLISH":
            score += 12
            reasons.append("Bullish market structure (HH, HL)")
        elif structure == "BEARISH":
            score -= 12
            reasons.append("Bearish market structure (LH, LL)")
        
        # BOS events
        bos = market_structure.get("bos_events", [])
        if bos:
            latest_bos = bos[-1]
            if "BULLISH" in latest_bos.get("type", ""):
                score += 5
                reasons.append(f"Bullish BOS at {latest_bos.get('broken_level')}")
            elif "BEARISH" in latest_bos.get("type", ""):
                score -= 5
                reasons.append(f"Bearish BOS at {latest_bos.get('broken_level')}")
        
        # FVG
        fvgs = market_structure.get("fair_value_gaps", [])
        unfilled_bull_fvg = [f for f in fvgs if f.get("type") == "BULLISH_FVG" and not f.get("filled")]
        if unfilled_bull_fvg:
            score += 3
            reasons.append(f"Bullish FVG at {unfilled_bull_fvg[0].get('bottom')}-{unfilled_bull_fvg[0].get('top')}")
    
    # ═══════════════════════════════════════════════════════════════
    # VOLUME SCORING (max ±15)
    # ═══════════════════════════════════════════════════════════════
    
    if volume_analysis.get("status") == "success":
        flow = volume_analysis.get("overall_flow", "")
        if flow == "ACCUMULATION":
            score += 10
            reasons.append("Volume shows accumulation")
        elif flow == "DISTRIBUTION":
            score -= 10
            reasons.append("Volume shows distribution")
        
        cmf = volume_analysis.get("cmf", {})
        if cmf.get("signal") == "ACCUMULATION":
            score += 5
            reasons.append("Positive Chaikin Money Flow")
        elif cmf.get("signal") == "DISTRIBUTION":
            score -= 5
            reasons.append("Negative Chaikin Money Flow")
        
        # Divergences
        divergences = volume_analysis.get("divergences", {})
        if divergences.get("any_divergence"):
            warnings.append("Volume divergence detected - caution")
    
    # ═══════════════════════════════════════════════════════════════
    # CORRELATION SCORING (max ±15)
    # ═══════════════════════════════════════════════════════════════
    
    if correlation_analysis.get("status") == "success":
        overall_corr = correlation_analysis.get("overall_correlation_signal", "")
        if overall_corr == "BULLISH":
            score += 10
            reasons.append("Correlations aligned bullish (DXY weak, risk-off)")
        elif overall_corr == "BEARISH":
            score -= 10
            reasons.append("Correlations aligned bearish (DXY strong, risk-on)")
        
        # Safe haven flow
        safe_haven = correlation_analysis.get("safe_haven_flow", {})
        if safe_haven.get("gold_impact") in ["BULLISH", "STRONGLY_BULLISH"]:
            score += 5
            reasons.append("Safe haven demand rising")
        elif safe_haven.get("gold_impact") == "BEARISH":
            score -= 5
            reasons.append("Risk-on environment - safe haven demand low")
    
    # ═══════════════════════════════════════════════════════════════
    # SENTIMENT SCORING (max ±15)
    # ═══════════════════════════════════════════════════════════════
    
    if sentiment_score > 40:
        score += 10
        reasons.append(f"Strong bullish sentiment ({sentiment_score}/100)")
    elif sentiment_score > 20:
        score += 5
        reasons.append(f"Bullish sentiment ({sentiment_score}/100)")
    elif sentiment_score < -40:
        score -= 10
        reasons.append(f"Strong bearish sentiment ({sentiment_score}/100)")
    elif sentiment_score < -20:
        score -= 5
        reasons.append(f"Bearish sentiment ({sentiment_score}/100)")
    
    # ═══════════════════════════════════════════════════════════════
    # DETERMINE DIRECTION
    # ═══════════════════════════════════════════════════════════════
    
    if score >= 60:
        direction = "BUY"
    elif score <= 40:
        direction = "SELL"
    else:
        direction = "NEUTRAL"
    
    # ═══════════════════════════════════════════════════════════════
    # ENTRY, SL, TP CALCULATION
    # ═══════════════════════════════════════════════════════════════
    
    current_price = chart_analysis.get("current_price", 0) if chart_analysis else 0
    atr = (chart_analysis.get("atr") or 0) if chart_analysis else 0
    
    if direction == "BUY" and current_price > 0:
        entry = current_price
        stop_loss = round(current_price - (atr * 1.5), 5) if atr > 0 else round(current_price * 0.985, 5)
        tp1 = round(current_price + (atr * 2), 5) if atr > 0 else round(current_price * 1.02, 5)
        tp2 = round(current_price + (atr * 3), 5) if atr > 0 else round(current_price * 1.03, 5)
        tp3 = round(current_price + (atr * 4.5), 5) if atr > 0 else round(current_price * 1.045, 5)
        
        # Adjust to S/R
        if support_resistance.get("nearest_support"):
            sl_support = round(support_resistance["nearest_support"] - atr * 0.2, 5)
            stop_loss = min(stop_loss, sl_support)
        if support_resistance.get("nearest_resistance"):
            tp1 = min(tp1, support_resistance["nearest_resistance"])
    
    elif direction == "SELL" and current_price > 0:
        entry = current_price
        stop_loss = round(current_price + (atr * 1.5), 5) if atr > 0 else round(current_price * 1.015, 5)
        tp1 = round(current_price - (atr * 2), 5) if atr > 0 else round(current_price * 0.98, 5)
        tp2 = round(current_price - (atr * 3), 5) if atr > 0 else round(current_price * 0.97, 5)
        tp3 = round(current_price - (atr * 4.5), 5) if atr > 0 else round(current_price * 0.955, 5)
        
        # Adjust to S/R
        if support_resistance.get("nearest_resistance"):
            sl_resistance = round(support_resistance["nearest_resistance"] + atr * 0.2, 5)
            stop_loss = max(stop_loss, sl_resistance)
        if support_resistance.get("nearest_support"):
            tp1 = max(tp1, support_resistance["nearest_support"])
    
    else:
        entry = stop_loss = tp1 = tp2 = tp3 = None
    
    # Calculate R:R
    if entry and stop_loss and tp1 and direction != "NEUTRAL":
        risk = abs(entry - stop_loss)
        reward = abs(tp1 - entry)
        rr_ratio = round(reward / risk, 2) if risk > 0 else 0
    else:
        rr_ratio = 0
    
    # ═══════════════════════════════════════════════════════════════
    # FINAL CONFIDENCE
    # ═══════════════════════════════════════════════════════════════
    
    confidence = min(max(score, 0), 100)
    
    if confidence >= 85:
        grade = "A+"
    elif confidence >= 75:
        grade = "A"
    elif confidence >= 65:
        grade = "B"
    elif confidence >= 55:
        grade = "C"
    else:
        grade = "NO_TRADE"
    
    # Check risk approval
    risk_approved = risk_assessment.get("overall") == "APPROVED" if risk_assessment else True
    
    # Final recommendation
    if direction == "NEUTRAL" or grade == "NO_TRADE":
        recommendation = "WAIT - No clear setup"
        trade_action = "DO_NOT_TRADE"
    elif not risk_approved:
        recommendation = f"{direction} setup but risk check failed"
        trade_action = "CAUTION"
    elif confidence >= 70:
        recommendation = f"STRONG {direction}"
        trade_action = "TRADE"
    else:
        recommendation = direction
        trade_action = "CAUTION"
    
    return {
        "status": "success",
        "symbol": symbol,
        "timeframe": timeframe,
        "direction": direction,
        "confidence_score": confidence,
        "trade_grade": grade,
        "entry_price": entry,
        "stop_loss": stop_loss,
        "take_profit_1": tp1,
        "take_profit_2": tp2,
        "take_profit_3": tp3,
        "risk_reward_ratio": rr_ratio,
        "atr": atr,
        "reasons": reasons,
        "warnings": warnings,
        "recommendation": recommendation,
        "trade_action": trade_action,
        "risk_approved": risk_approved,
        "analysis_components": {
            "chart_score": "analyzed",
            "structure_score": "analyzed",
            "volume_score": "analyzed",
            "correlation_score": "analyzed",
            "sentiment_score": sentiment_score
        }
    }
