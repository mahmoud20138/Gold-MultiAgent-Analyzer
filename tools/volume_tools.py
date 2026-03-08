"""
Volume Analysis Tools - Volume profile, money flow, accumulation/distribution.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_formatter import safe_float


def analyze_volume_profile(ohlcv_data: List[Dict], num_bins: int = 50) -> Dict:
    """
    Volume at Price analysis.
    - Point of Control (POC)
    - Value Area High/Low (VAH/VAL)
    - High/Low Volume Nodes
    """
    df = pd.DataFrame(ohlcv_data)
    
    if len(df) < 50:
        return {"status": "error", "message": "Need at least 50 candles"}
    
    price_min = df['low'].min()
    price_max = df['high'].max()
    bin_size = (price_max - price_min) / num_bins
    
    if bin_size == 0:
        return {"status": "error", "message": "Zero price range"}
    
    # Volume at Price calculation
    volume_at_price = {}
    for _, row in df.iterrows():
        bin_start = int((row['close'] - price_min) / bin_size)
        bin_price = round(price_min + bin_start * bin_size, 5)
        vol = row.get('tick_volume', row.get('volume', 1))
        volume_at_price[bin_price] = volume_at_price.get(bin_price, 0) + vol
    
    # Point of Control (highest volume price)
    poc_price = max(volume_at_price, key=volume_at_price.get)
    poc_volume = volume_at_price[poc_price]
    
    # Value Area (70% of volume)
    total_volume = sum(volume_at_price.values())
    sorted_levels = sorted(volume_at_price.items(), key=lambda x: x[1], reverse=True)
    
    cumulative = 0
    value_area_prices = []
    for price, vol in sorted_levels:
        cumulative += vol
        value_area_prices.append(price)
        if cumulative >= total_volume * 0.7:
            break
    
    vah = max(value_area_prices) if value_area_prices else poc_price
    val = min(value_area_prices) if value_area_prices else poc_price
    
    # High/Low Volume Nodes
    avg_volume = total_volume / num_bins
    hvn = sorted([p for p, v in volume_at_price.items() if v > avg_volume * 1.5])[-5:]
    lvn = sorted([p for p, v in volume_at_price.items() if v < avg_volume * 0.5])[:5]
    
    current_price = float(df['close'].iloc[-1])
    
    return {
        "status": "success",
        "current_price": current_price,
        "poc": round(float(poc_price), 5),
        "poc_volume": int(poc_volume),
        "value_area_high": round(float(vah), 5),
        "value_area_low": round(float(val), 5),
        "value_area_width": round(float(vah - val), 5),
        "high_volume_nodes": hvn,
        "low_volume_nodes": lvn,
        "price_vs_poc": "ABOVE" if current_price > poc_price else "BELOW" if current_price < poc_price else "AT_POC",
        "price_in_value_area": val <= current_price <= vah,
        "total_volume": int(total_volume),
        "volume_distribution": "NORMAL" if 0.5 < (poc_volume / avg_volume) < 2 else "SKEWED"
    }


def analyze_accumulation_distribution(ohlcv_data: List[Dict]) -> Dict:
    """
    Money flow analysis:
    - A/D Line
    - On Balance Volume (OBV)
    - Chaikin Money Flow (CMF)
    - VWAP
    """
    df = pd.DataFrame(ohlcv_data)
    
    if len(df) < 50:
        return {"status": "error", "message": "Need at least 50 candles"}
    
    # Handle volume column
    vol_col = 'tick_volume' if 'tick_volume' in df.columns else 'volume'
    
    # A/D Line
    high_low = df['high'] - df['low']
    high_low = high_low.replace(0, np.inf)
    clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / high_low
    clv = clv.fillna(0)
    df['ad_line'] = (clv * df[vol_col]).cumsum()
    
    # OBV
    obv = [0]
    for i in range(1, len(df)):
        if df['close'].iloc[i] > df['close'].iloc[i-1]:
            obv.append(obv[-1] + df[vol_col].iloc[i])
        elif df['close'].iloc[i] < df['close'].iloc[i-1]:
            obv.append(obv[-1] - df[vol_col].iloc[i])
        else:
            obv.append(obv[-1])
    df['obv'] = obv
    
    # CMF (20 period)
    mf_volume = clv * df[vol_col]
    df['cmf'] = mf_volume.rolling(20).sum() / df[vol_col].rolling(20).sum()
    
    # VWAP
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    df['vwap'] = (typical_price * df[vol_col]).cumsum() / df[vol_col].cumsum()
    
    latest = df.iloc[-1]
    
    # Trends
    ad_trend = "RISING" if df['ad_line'].iloc[-1] > df['ad_line'].iloc[-20] else "FALLING"
    obv_trend = "RISING" if df['obv'].iloc[-1] > df['obv'].iloc[-20] else "FALLING"
    price_trend = "RISING" if df['close'].iloc[-1] > df['close'].iloc[-20] else "FALLING"
    
    # Divergences
    price_ad_divergence = price_trend != ad_trend
    price_obv_divergence = price_trend != obv_trend
    
    # Overall flow
    cmf_val = safe_float(latest['cmf'])
    if ad_trend == "RISING" and cmf_val > 0:
        overall_flow = "ACCUMULATION"
    elif ad_trend == "FALLING" and cmf_val < 0:
        overall_flow = "DISTRIBUTION"
    else:
        overall_flow = "MIXED"
    
    return {
        "status": "success",
        "current_price": safe_float(latest['close']),
        "ad_line": {
            "current": round(safe_float(latest['ad_line']), 2),
            "trend": ad_trend,
            "divergence_with_price": price_ad_divergence
        },
        "obv": {
            "current": int(latest['obv']),
            "trend": obv_trend,
            "divergence_with_price": price_obv_divergence
        },
        "cmf": {
            "value": round(cmf_val, 4),
            "signal": "ACCUMULATION" if cmf_val > 0 else "DISTRIBUTION",
            "strength": "STRONG" if abs(cmf_val) > 0.2 else "MODERATE" if abs(cmf_val) > 0.1 else "WEAK"
        },
        "vwap": {
            "value": round(safe_float(latest['vwap']), 5),
            "price_vs_vwap": "ABOVE" if latest['close'] > latest['vwap'] else "BELOW",
            "distance_pct": round(safe_float((latest['close'] - latest['vwap']) / latest['vwap'] * 100), 3)
        },
        "overall_flow": overall_flow,
        "divergences": {
            "price_ad": price_ad_divergence,
            "price_obv": price_obv_divergence,
            "any_divergence": price_ad_divergence or price_obv_divergence
        }
    }


def analyze_volume_anomalies(ohlcv_data: List[Dict]) -> Dict:
    """
    Detect volume spikes, relative volume, climax/dry-up conditions.
    """
    df = pd.DataFrame(ohlcv_data)
    
    if len(df) < 50:
        return {"status": "error", "message": "Need at least 50 candles"}
    
    vol_col = 'tick_volume' if 'tick_volume' in df.columns else 'volume'
    
    avg_volume_20 = df[vol_col].tail(20).mean()
    avg_volume_50 = df[vol_col].tail(50).mean()
    current_volume = float(df[vol_col].iloc[-1])
    
    relative_volume = current_volume / avg_volume_20 if avg_volume_20 > 0 else 1
    
    # Volume spikes (last 20 candles)
    spikes = []
    for i in range(max(0, len(df)-20), len(df)):
        vol = df[vol_col].iloc[i]
        if vol > avg_volume_50 * 2:
            spikes.append({
                "candles_ago": len(df) - 1 - i,
                "volume": int(vol),
                "price": safe_float(df['close'].iloc[i]),
                "direction": "BULLISH" if df['close'].iloc[i] > df['open'].iloc[i] else "BEARISH"
            })
    
    # Climax / Dry-up
    is_climax = current_volume > avg_volume_20 * 3
    is_dryup = current_volume < avg_volume_20 * 0.3
    
    # Volume trend
    vol_sma_5 = df[vol_col].tail(5).mean()
    vol_sma_20 = avg_volume_20
    volume_trend = "INCREASING" if vol_sma_5 > vol_sma_20 else "DECREASING"
    
    # Relative volume label
    if relative_volume > 2:
        rv_label = "VERY_HIGH"
    elif relative_volume > 1.5:
        rv_label = "HIGH"
    elif relative_volume > 0.7:
        rv_label = "NORMAL"
    else:
        rv_label = "LOW"
    
    return {
        "status": "success",
        "current_volume": int(current_volume),
        "avg_volume_20": round(float(avg_volume_20), 0),
        "avg_volume_50": round(float(avg_volume_50), 0),
        "relative_volume": round(float(relative_volume), 2),
        "relative_volume_label": rv_label,
        "volume_spikes": spikes,
        "spike_count": len(spikes),
        "is_climax_volume": is_climax,
        "is_dryup_volume": is_dryup,
        "volume_trend": volume_trend,
        "volume_ma_5": round(float(vol_sma_5), 0),
        "volume_ma_20": round(float(vol_sma_20), 0)
    }


def volume_price_analysis(ohlcv_data: List[Dict]) -> Dict:
    """
    Wyckoff-style volume-price analysis.
    Evaluates each candle's volume vs price move relationship.
    """
    df = pd.DataFrame(ohlcv_data)
    
    if len(df) < 50:
        return {"status": "error", "message": "Need at least 50 candles"}
    
    vol_col = 'tick_volume' if 'tick_volume' in df.columns else 'volume'
    
    analyses = []
    avg_vol = df[vol_col].tail(50).mean()
    avg_range = (df['high'] - df['low']).tail(50).mean()
    
    for i in range(max(0, len(df)-10), len(df)):
        vol = df[vol_col].iloc[i]
        price_change = df['close'].iloc[i] - df['open'].iloc[i]
        candle_range = df['high'].iloc[i] - df['low'].iloc[i]
        
        high_vol = vol > avg_vol * 1.5
        low_vol = vol < avg_vol * 0.5
        big_range = candle_range > avg_range * 1.5
        small_range = candle_range < avg_range * 0.5
        bullish = price_change > 0
        
        # Signal determination
        if high_vol and bullish and big_range:
            signal = "STRONG_DEMAND"
        elif high_vol and not bullish and big_range:
            signal = "STRONG_SUPPLY"
        elif high_vol and small_range:
            signal = "ABSORPTION"
        elif low_vol and big_range:
            signal = "WEAK_MOVE"
        elif low_vol and small_range:
            signal = "NO_INTEREST"
        else:
            signal = "NORMAL"
        
        analyses.append({
            "candles_ago": len(df) - 1 - i,
            "signal": signal,
            "volume_relative": round(float(vol / avg_vol), 2) if avg_vol > 0 else 1,
            "direction": "BULLISH" if bullish else "BEARISH",
            "range_relative": round(float(candle_range / avg_range), 2) if avg_range > 0 else 1
        })
    
    # Summary
    recent_signals = [a['signal'] for a in analyses[-5:]]
    demand_count = recent_signals.count("STRONG_DEMAND")
    supply_count = recent_signals.count("STRONG_SUPPLY")
    absorption_count = recent_signals.count("ABSORPTION")
    
    if demand_count > supply_count:
        overall = "BUYERS_IN_CONTROL"
    elif supply_count > demand_count:
        overall = "SELLERS_IN_CONTROL"
    elif absorption_count > 0:
        overall = "ABSORPTION_PHASE"
    else:
        overall = "BATTLE_ZONE"
    
    return {
        "status": "success",
        "candle_by_candle": analyses,
        "summary": {
            "demand_signals": demand_count,
            "supply_signals": supply_count,
            "absorption_signals": absorption_count,
            "overall": overall
        },
        "interpretation": {
            "STRONG_DEMAND": "High volume + bullish move = institutions buying",
            "STRONG_SUPPLY": "High volume + bearish move = institutions selling",
            "ABSORPTION": "High volume + small range = absorption/reversal likely",
            "WEAK_MOVE": "Low volume + big range = weak move, may reverse",
            "NO_INTEREST": "Low volume + small range = market resting"
        }
    }
