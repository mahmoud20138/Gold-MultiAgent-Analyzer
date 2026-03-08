"""
Market Structure Tools - Smart Money Concepts analysis.
BOS, CHoCH, Order Blocks, Fair Value Gaps, Liquidity levels.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_formatter import safe_float


def analyze_market_structure(ohlcv_data: List[Dict]) -> Dict:
    """
    Smart Money Concepts analysis:
    - Break of Structure (BOS)
    - Change of Character (CHoCH)
    - Order Blocks
    - Fair Value Gaps (FVG)
    - Liquidity levels
    """
    df = pd.DataFrame(ohlcv_data)
    
    if len(df) < 50:
        return {"status": "error", "message": "Need at least 50 candles"}
    
    # Identify swing points
    window = 5
    swing_highs = []
    swing_lows = []
    
    for i in range(window, len(df) - window):
        if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
            swing_highs.append({"index": i, "price": float(df['high'].iloc[i]), "time": str(df['time'].iloc[i]) if 'time' in df.columns else i})
        if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
            swing_lows.append({"index": i, "price": float(df['low'].iloc[i]), "time": str(df['time'].iloc[i]) if 'time' in df.columns else i})
    
    # BOS / CHoCH Detection
    bos_events = []
    choch_events = []
    
    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        # Check for bullish BOS (breaking above previous swing high)
        if swing_highs[-1]['price'] > swing_highs[-2]['price']:
            bos_events.append({
                "type": "BULLISH_BOS",
                "broken_level": swing_highs[-2]['price'],
                "current_price": float(df['close'].iloc[-1]),
                "candles_ago": len(df) - 1 - swing_highs[-2]['index']
            })
        
        # Check for bearish BOS
        if swing_lows[-1]['price'] < swing_lows[-2]['price']:
            bos_events.append({
                "type": "BEARISH_BOS",
                "broken_level": swing_lows[-2]['price'],
                "current_price": float(df['close'].iloc[-1]),
                "candles_ago": len(df) - 1 - swing_lows[-2]['index']
            })
        
        # CHoCH - trend change (downtrend breaking to upside, or vice versa)
        if len(swing_highs) >= 3 and len(swing_lows) >= 3:
            # Bullish CHoCH in downtrend
            if (swing_lows[-1]['price'] > swing_lows[-2]['price'] and 
                swing_highs[-2]['price'] < swing_highs[-3]['price']):
                choch_events.append({
                    "type": "BULLISH_CHoCH",
                    "level": swing_lows[-2]['price'],
                    "candles_ago": len(df) - 1 - swing_lows[-2]['index']
                })
            
            # Bearish CHoCH in uptrend
            if (swing_highs[-1]['price'] < swing_highs[-2]['price'] and 
                swing_lows[-2]['price'] > swing_lows[-3]['price']):
                choch_events.append({
                    "type": "BEARISH_CHoCH",
                    "level": swing_highs[-2]['price'],
                    "candles_ago": len(df) - 1 - swing_highs[-2]['index']
                })
    
    # Fair Value Gap Detection
    fvgs = []
    for i in range(2, min(50, len(df))):
        idx = len(df) - i
        if idx < 2:
            break
        
        # Bullish FVG: gap between candle 2's high and candle 0's low
        if df['low'].iloc[idx] > df['high'].iloc[idx-2]:
            fvgs.append({
                "type": "BULLISH_FVG",
                "top": round(float(df['low'].iloc[idx]), 5),
                "bottom": round(float(df['high'].iloc[idx-2]), 5),
                "midpoint": round(float((df['low'].iloc[idx] + df['high'].iloc[idx-2]) / 2), 5),
                "candles_ago": i,
                "filled": df['low'].iloc[-1] <= df['high'].iloc[idx-2] if len(df) > idx else False
            })
        
        # Bearish FVG: gap between candle 0's high and candle 2's low
        if df['high'].iloc[idx] < df['low'].iloc[idx-2]:
            fvgs.append({
                "type": "BEARISH_FVG",
                "top": round(float(df['low'].iloc[idx-2]), 5),
                "bottom": round(float(df['high'].iloc[idx]), 5),
                "midpoint": round(float((df['low'].iloc[idx-2] + df['high'].iloc[idx]) / 2), 5),
                "candles_ago": i,
                "filled": df['high'].iloc[-1] >= df['low'].iloc[idx-2] if len(df) > idx else False
            })
    
    # Order Block Detection
    order_blocks = []
    for i in range(max(0, len(df)-50), len(df)-1):
        if i < 1:
            continue
        
        # Bullish OB: bearish candle followed by bullish move breaking its high
        if (df['close'].iloc[i] < df['open'].iloc[i] and  # bearish candle
            i + 1 < len(df) and
            df['close'].iloc[i+1] > df['open'].iloc[i+1] and  # bullish candle follows
            df['high'].iloc[i+1:i+5].max() > df['high'].iloc[i]):  # breaks above OB high
            
            order_blocks.append({
                "type": "BULLISH_OB",
                "top": round(float(df['high'].iloc[i]), 5),
                "bottom": round(float(df['low'].iloc[i]), 5),
                "midpoint": round(float((df['high'].iloc[i] + df['low'].iloc[i]) / 2), 5),
                "candles_ago": len(df) - 1 - i,
                "tested": df['low'].iloc[-1] <= df['high'].iloc[i]  # Price returned to OB
            })
        
        # Bearish OB: bullish candle followed by bearish move breaking its low
        if (df['close'].iloc[i] > df['open'].iloc[i] and  # bullish candle
            i + 1 < len(df) and
            df['close'].iloc[i+1] < df['open'].iloc[i+1] and  # bearish candle follows
            df['low'].iloc[i+1:i+5].min() < df['low'].iloc[i]):  # breaks below OB low
            
            order_blocks.append({
                "type": "BEARISH_OB",
                "top": round(float(df['high'].iloc[i]), 5),
                "bottom": round(float(df['low'].iloc[i]), 5),
                "midpoint": round(float((df['high'].iloc[i] + df['low'].iloc[i]) / 2), 5),
                "candles_ago": len(df) - 1 - i,
                "tested": df['high'].iloc[-1] >= df['low'].iloc[i]  # Price returned to OB
            })
    
    # Liquidity levels (equal highs/lows where stops likely cluster)
    liquidity_levels = []
    
    # Equal highs (sell-side liquidity)
    for i in range(len(swing_highs) - 1):
        if abs(swing_highs[i]['price'] - swing_highs[i+1]['price']) / swing_highs[i]['price'] < 0.003:
            liquidity_levels.append({
                "type": "SELL_SIDE_LIQUIDITY",
                "level": round(float(swing_highs[i]['price']), 5),
                "swept": df['high'].iloc[-1] > swing_highs[i]['price']
            })
    
    # Equal lows (buy-side liquidity)
    for i in range(len(swing_lows) - 1):
        if abs(swing_lows[i]['price'] - swing_lows[i+1]['price']) / swing_lows[i]['price'] < 0.003:
            liquidity_levels.append({
                "type": "BUY_SIDE_LIQUIDITY",
                "level": round(float(swing_lows[i]['price']), 5),
                "swept": df['low'].iloc[-1] < swing_lows[i]['price']
            })
    
    # Determine market structure
    current_price = float(df['close'].iloc[-1])
    
    if len(swing_highs) >= 2 and len(swing_lows) >= 2:
        hh = swing_highs[-1]['price'] > swing_highs[-2]['price']
        hl = swing_lows[-1]['price'] > swing_lows[-2]['price']
        ll = swing_lows[-1]['price'] < swing_lows[-2]['price']
        lh = swing_highs[-1]['price'] < swing_highs[-2]['price']
        
        if hh and hl:
            structure = "BULLISH"
        elif ll and lh:
            structure = "BEARISH"
        else:
            structure = "RANGING"
    else:
        structure = "INSUFFICIENT_DATA"
    
    return {
        "status": "success",
        "market_structure": structure,
        "current_price": current_price,
        "bos_events": bos_events[-3:] if bos_events else [],
        "choch_events": choch_events[-3:] if choch_events else [],
        "fair_value_gaps": [f for f in fvgs if not f['filled']][:5],  # Unfilled FVGs
        "order_blocks": order_blocks[:5],
        "liquidity_levels": liquidity_levels[-5:],
        "swing_highs": [{"price": s['price'], "index": s['index']} for s in swing_highs[-5:]],
        "swing_lows": [{"price": s['price'], "index": s['index']} for s in swing_lows[-5:]],
        "latest_swing_high": swing_highs[-1] if swing_highs else None,
        "latest_swing_low": swing_lows[-1] if swing_lows else None
    }


def find_premium_discount_zones(ohlcv_data: List[Dict], lookback: int = 50) -> Dict:
    """
    Identify premium (expensive) and discount (cheap) price zones.
    Based on current range - buy in discount, sell in premium.
    """
    df = pd.DataFrame(ohlcv_data)
    
    if len(df) < lookback:
        return {"status": "error", "message": f"Need at least {lookback} candles"}
    
    recent = df.tail(lookback)
    range_high = recent['high'].max()
    range_low = recent['low'].min()
    range_size = range_high - range_low
    
    current_price = float(df['close'].iloc[-1])
    
    # Calculate position in range (0 = bottom, 1 = top)
    range_position = (current_price - range_low) / range_size if range_size > 0 else 0.5
    
    # Equilibrium (50% level)
    equilibrium = (range_high + range_low) / 2
    
    # Premium zone: top 30% of range
    premium_threshold = range_low + range_size * 0.7
    
    # Discount zone: bottom 30% of range
    discount_threshold = range_low + range_size * 0.3
    
    if current_price > premium_threshold:
        zone = "PREMIUM"
        recommendation = "Look for shorts, avoid longs"
    elif current_price < discount_threshold:
        zone = "DISCOUNT"
        recommendation = "Look for longs, avoid shorts"
    else:
        zone = "EQUILIBRIUM"
        recommendation = "Neutral zone - wait for extension"
    
    return {
        "status": "success",
        "current_price": current_price,
        "zone": zone,
        "range_position": round(range_position * 100, 1),
        "range_high": round(float(range_high), 5),
        "range_low": round(float(range_low), 5),
        "equilibrium": round(float(equilibrium), 5),
        "premium_threshold": round(float(premium_threshold), 5),
        "discount_threshold": round(float(discount_threshold), 5),
        "recommendation": recommendation,
        "lookback_periods": lookback
    }
