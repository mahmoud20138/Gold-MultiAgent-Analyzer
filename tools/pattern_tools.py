"""
Pattern Recognition Tools - Candlestick and chart pattern detection.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_formatter import safe_float


def detect_candlestick_patterns(ohlcv_data: List[Dict]) -> Dict:
    """
    Detect candlestick patterns in recent price data.
    
    Returns patterns found in the last 10 candles with significance ratings.
    """
    df = pd.DataFrame(ohlcv_data)
    
    if len(df) < 20:
        return {"status": "error", "message": "Need at least 20 candles"}
    
    patterns = []
    
    # Analyze last 10 candles
    for i in range(max(0, len(df) - 10), len(df)):
        if i < 1:
            continue
        
        candle = df.iloc[i]
        prev = df.iloc[i - 1]
        
        body = abs(candle['close'] - candle['open'])
        upper_wick = candle['high'] - max(candle['close'], candle['open'])
        lower_wick = min(candle['close'], candle['open']) - candle['low']
        candle_range = candle['high'] - candle['low']
        avg_range = (df['high'] - df['low']).tail(50).mean()
        avg_body = abs(df['close'] - df['open']).tail(50).mean()
        
        is_bullish = candle['close'] > candle['open']
        candles_ago = len(df) - 1 - i
        
        # Doji
        if candle_range > 0 and body < candle_range * 0.1:
            patterns.append({
                "candle": candles_ago,
                "pattern": "DOJI",
                "type": "reversal",
                "significance": "medium",
                "direction": "NEUTRAL",
                "description": "Indecision - potential reversal"
            })
        
        # Hammer (bullish)
        if lower_wick > body * 2 and upper_wick < body * 0.5 and candle_range > 0 and is_bullish:
            patterns.append({
                "candle": candles_ago,
                "pattern": "HAMMER",
                "type": "bullish_reversal",
                "significance": "high",
                "direction": "BULLISH",
                "description": "Bullish reversal hammer at support"
            })
        
        # Inverted Hammer
        if upper_wick > body * 2 and lower_wick < body * 0.5 and candle_range > 0 and is_bullish:
            patterns.append({
                "candle": candles_ago,
                "pattern": "INVERTED_HAMMER",
                "type": "bullish_reversal",
                "significance": "medium",
                "direction": "BULLISH",
                "description": "Potential bullish reversal"
            })
        
        # Shooting Star (bearish)
        if upper_wick > body * 2 and lower_wick < body * 0.5 and candle_range > 0 and not is_bullish:
            patterns.append({
                "candle": candles_ago,
                "pattern": "SHOOTING_STAR",
                "type": "bearish_reversal",
                "significance": "high",
                "direction": "BEARISH",
                "description": "Bearish reversal signal"
            })
        
        # Hanging Man
        if lower_wick > body * 2 and upper_wick < body * 0.5 and candle_range > 0 and not is_bullish:
            patterns.append({
                "candle": candles_ago,
                "pattern": "HANGING_MAN",
                "type": "bearish_reversal",
                "significance": "medium",
                "direction": "BEARISH",
                "description": "Bearish reversal at resistance"
            })
        
        # Bullish Engulfing
        if i >= 1:
            prev_body = abs(prev['close'] - prev['open'])
            if (prev['close'] < prev['open'] and 
                is_bullish and
                candle['close'] > prev['open'] and 
                candle['open'] < prev['close'] and
                body > prev_body):
                patterns.append({
                    "candle": candles_ago,
                    "pattern": "BULLISH_ENGULFING",
                    "type": "bullish_reversal",
                    "significance": "high",
                    "direction": "BULLISH",
                    "description": "Strong bullish engulfing pattern"
                })
        
        # Bearish Engulfing
        if i >= 1:
            prev_body = abs(prev['close'] - prev['open'])
            if (prev['close'] > prev['open'] and 
                not is_bullish and
                candle['close'] < prev['open'] and 
                candle['open'] > prev['close'] and
                body > prev_body):
                patterns.append({
                    "candle": candles_ago,
                    "pattern": "BEARISH_ENGULFING",
                    "type": "bearish_reversal",
                    "significance": "high",
                    "direction": "BEARISH",
                    "description": "Strong bearish engulfing pattern"
                })
        
        # Morning Star (3 candle bullish)
        if i >= 2:
            first = df.iloc[i - 2]
            second = df.iloc[i - 1]
            first_body = abs(first['close'] - first['open'])
            second_body = abs(second['close'] - second['open'])
            
            if (first['close'] < first['open'] and  # First bearish
                second_body < first_body * 0.3 and  # Second small body (gap)
                is_bullish and  # Third bullish
                candle['close'] > (first['open'] + first['close']) / 2):
                patterns.append({
                    "candle": candles_ago,
                    "pattern": "MORNING_STAR",
                    "type": "bullish_reversal",
                    "significance": "very_high",
                    "direction": "BULLISH",
                    "description": "Strong bullish morning star"
                })
        
        # Evening Star (3 candle bearish)
        if i >= 2:
            first = df.iloc[i - 2]
            second = df.iloc[i - 1]
            first_body = abs(first['close'] - first['open'])
            second_body = abs(second['close'] - second['open'])
            
            if (first['close'] > first['open'] and  # First bullish
                second_body < first_body * 0.3 and  # Second small body
                not is_bullish and  # Third bearish
                candle['close'] < (first['open'] + first['close']) / 2):
                patterns.append({
                    "candle": candles_ago,
                    "pattern": "EVENING_STAR",
                    "type": "bearish_reversal",
                    "significance": "very_high",
                    "direction": "BEARISH",
                    "description": "Strong bearish evening star"
                })
        
        # Three White Soldiers
        if i >= 2:
            prev2 = df.iloc[i - 2]
            prev1 = df.iloc[i - 1]
            if (prev2['close'] > prev2['open'] and
                prev1['close'] > prev1['open'] and
                is_bullish and
                prev1['close'] > prev2['close'] and
                candle['close'] > prev1['close']):
                patterns.append({
                    "candle": candles_ago,
                    "pattern": "THREE_WHITE_SOLDIERS",
                    "type": "bullish_continuation",
                    "significance": "high",
                    "direction": "BULLISH",
                    "description": "Strong bullish continuation"
                })
        
        # Three Black Crows
        if i >= 2:
            prev2 = df.iloc[i - 2]
            prev1 = df.iloc[i - 1]
            if (prev2['close'] < prev2['open'] and
                prev1['close'] < prev1['open'] and
                not is_bullish and
                prev1['close'] < prev2['close'] and
                candle['close'] < prev1['close']):
                patterns.append({
                    "candle": candles_ago,
                    "pattern": "THREE_BLACK_CROWS",
                    "type": "bearish_continuation",
                    "significance": "high",
                    "direction": "BEARISH",
                    "description": "Strong bearish continuation"
                })
    
    # Remove duplicates (keep most recent)
    seen = set()
    unique_patterns = []
    for p in patterns:
        key = p['pattern']
        if key not in seen:
            seen.add(key)
            unique_patterns.append(p)
    
    return {
        "status": "success",
        "patterns": unique_patterns,
        "pattern_count": len(unique_patterns),
        "bullish_patterns": sum(1 for p in unique_patterns if "BULLISH" in p.get("direction", "")),
        "bearish_patterns": sum(1 for p in unique_patterns if "BEARISH" in p.get("direction", "")),
        "most_recent": unique_patterns[0] if unique_patterns else None
    }


def find_support_resistance(ohlcv_data: List[Dict], window: int = 20) -> Dict:
    """
    Identify key support and resistance levels.
    
    Uses swing highs/lows and pivot points.
    """
    df = pd.DataFrame(ohlcv_data)
    
    if len(df) < window * 2:
        return {"status": "error", "message": f"Need at least {window * 2} candles"}
    
    # Swing highs and lows
    swing_highs = []
    swing_lows = []
    
    for i in range(window, len(df) - window):
        if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
            swing_highs.append(float(df['high'].iloc[i]))
        if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
            swing_lows.append(float(df['low'].iloc[i]))
    
    # Cluster nearby levels
    def cluster_levels(levels, threshold=0.002):
        if not levels:
            return []
        levels = sorted(levels)
        clusters = [[levels[0]]]
        for level in levels[1:]:
            if (level - clusters[-1][-1]) / clusters[-1][-1] < threshold:
                clusters[-1].append(level)
            else:
                clusters.append([level])
        return [round(np.mean(c), 5) for c in clusters]
    
    # Pivot Points (Classic)
    last = df.iloc[-1]
    pivot = (last['high'] + last['low'] + last['close']) / 3
    r1 = 2 * pivot - last['low']
    s1 = 2 * pivot - last['high']
    r2 = pivot + (last['high'] - last['low'])
    s2 = pivot - (last['high'] - last['low'])
    r3 = last['high'] + 2 * (pivot - last['low'])
    s3 = last['low'] - 2 * (last['high'] - pivot)
    
    current_price = float(last['close'])
    
    # Get nearest levels
    resistance_levels = cluster_levels(swing_highs)
    support_levels = cluster_levels(swing_lows)
    
    # Filter: resistance above price, support below
    resistance_levels = [r for r in resistance_levels if r > current_price]
    support_levels = [s for s in support_levels if s < current_price]
    
    return {
        "status": "success",
        "current_price": current_price,
        "resistance_levels": resistance_levels[-5:] if resistance_levels else [],
        "support_levels": support_levels[-5:] if support_levels else [],
        "pivot_points": {
            "pivot": round(float(pivot), 5),
            "r1": round(float(r1), 5),
            "r2": round(float(r2), 5),
            "r3": round(float(r3), 5),
            "s1": round(float(s1), 5),
            "s2": round(float(s2), 5),
            "s3": round(float(s3), 5)
        },
        "nearest_resistance": resistance_levels[0] if resistance_levels else round(float(r1), 5),
        "nearest_support": support_levels[-1] if support_levels else round(float(s1), 5),
        "swing_high_count": len(swing_highs),
        "swing_low_count": len(swing_lows)
    }


def detect_trend(ohlcv_data: List[Dict]) -> Dict:
    """
    Detect current trend direction and strength.
    """
    df = pd.DataFrame(ohlcv_data)
    
    if len(df) < 50:
        return {"status": "error", "message": "Need at least 50 candles"}
    
    # SMA-based trend
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    df['sma_200'] = df['close'].rolling(200).mean() if len(df) >= 200 else None
    
    current = df['close'].iloc[-1]
    sma20 = df['sma_20'].iloc[-1]
    sma50 = df['sma_50'].iloc[-1]
    sma200 = df['sma_200'].iloc[-1] if df['sma_200'] is not None else None
    
    # Higher highs / higher lows check
    recent = df.tail(50)
    highs = recent['high'].values
    lows = recent['low'].values
    
    higher_highs = sum(1 for i in range(len(highs)-5, len(highs)-1) if highs[i] < highs[i+1])
    lower_lows = sum(1 for i in range(len(lows)-5, len(lows)-1) if lows[i] > lows[i+1])
    
    # Determine trend
    if current > sma20 > sma50:
        if sma200 is not None and current > sma200:
            trend = "STRONG_UPTREND"
        else:
            trend = "UPTREND"
    elif current < sma20 < sma50:
        if sma200 is not None and current < sma200:
            trend = "STRONG_DOWNTREND"
        else:
            trend = "DOWNTREND"
    else:
        trend = "SIDEWAYS"
    
    strength = "STRONG" if "STRONG" in trend else ("WEAK" if trend == "SIDEWAYS" else "MODERATE")

    return {
        "status": "success",
        "trend": trend,
        "strength": strength,
        "current_price": safe_float(current),
        "sma_20": safe_float(sma20),
        "sma_50": safe_float(sma50),
        "sma_200": safe_float(sma200) if sma200 else None,
        "price_vs_sma20": "ABOVE" if current > sma20 else "BELOW",
        "price_vs_sma50": "ABOVE" if current > sma50 else "BELOW",
        "sma_cross": "BULLISH" if sma20 > sma50 else "BEARISH",
        "higher_highs_count": higher_highs,
        "lower_lows_count": lower_lows
    }


def detect_chart_patterns(ohlcv_data: List[Dict]) -> Dict:
    """
    Detect larger chart patterns (double tops/bottoms, head & shoulders, etc.)
    """
    df = pd.DataFrame(ohlcv_data)
    
    if len(df) < 100:
        return {"status": "error", "message": "Need at least 100 candles for chart patterns"}
    
    patterns = []
    
    # Find swing points
    window = 10
    swing_highs_idx = []
    swing_lows_idx = []
    
    for i in range(window, len(df) - window):
        if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
            swing_highs_idx.append(i)
        if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
            swing_lows_idx.append(i)
    
    # Double Top (M pattern)
    if len(swing_highs_idx) >= 2:
        recent_highs = swing_highs_idx[-3:] if len(swing_highs_idx) >= 3 else swing_highs_idx
        if len(recent_highs) >= 2:
            h1 = df['high'].iloc[recent_highs[-2]]
            h2 = df['high'].iloc[recent_highs[-1]]
            if abs(h1 - h2) / h1 < 0.01:  # Within 1%
                neckline = min(df['low'].iloc[recent_highs[-2]:recent_highs[-1]+1])
                patterns.append({
                    "pattern": "DOUBLE_TOP",
                    "type": "bearish_reversal",
                    "significance": "high",
                    "level": round(float((h1 + h2) / 2), 5),
                    "neckline": round(float(neckline), 5)
                })
    
    # Double Bottom (W pattern)
    if len(swing_lows_idx) >= 2:
        recent_lows = swing_lows_idx[-3:] if len(swing_lows_idx) >= 3 else swing_lows_idx
        if len(recent_lows) >= 2:
            l1 = df['low'].iloc[recent_lows[-2]]
            l2 = df['low'].iloc[recent_lows[-1]]
            if abs(l1 - l2) / l1 < 0.01:  # Within 1%
                neckline = max(df['high'].iloc[recent_lows[-2]:recent_lows[-1]+1])
                patterns.append({
                    "pattern": "DOUBLE_BOTTOM",
                    "type": "bullish_reversal",
                    "significance": "high",
                    "level": round(float((l1 + l2) / 2), 5),
                    "neckline": round(float(neckline), 5)
                })
    
    return {
        "status": "success",
        "chart_patterns": patterns,
        "pattern_count": len(patterns),
        "swing_points": {
            "recent_highs": [round(float(df['high'].iloc[i]), 5) for i in swing_highs_idx[-5:]],
            "recent_lows": [round(float(df['low'].iloc[i]), 5) for i in swing_lows_idx[-5:]]
        }
    }
