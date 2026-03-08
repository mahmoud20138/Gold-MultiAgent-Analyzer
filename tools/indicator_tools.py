"""
Technical Indicator Tools - All major indicators for chart analysis.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_formatter import safe_float

# ═══════════════════════════════════════════════════════════════════
# MAIN INDICATOR CALCULATOR
# ═══════════════════════════════════════════════════════════════════

def calculate_all_indicators(ohlcv_data: List[Dict]) -> Dict:
    """
    Compute all major technical indicators from OHLCV data.
    
    Returns structured analysis with current values and conditions.
    """
    df = pd.DataFrame(ohlcv_data)
    
    if len(df) < 200:
        return {"status": "error", "message": "Need at least 200 candles for full analysis"}
    
    # --- Moving Averages ---
    for period in [20, 50, 100, 200]:
        df[f'sma_{period}'] = df['close'].rolling(period).mean()
    for period in [9, 21, 55]:
        df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
    
    # --- RSI ---
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.inf)
    df['rsi'] = 100 - (100 / (1 + rs))
    df['rsi'] = df['rsi'].fillna(50)
    
    # --- MACD ---
    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    df['macd_histogram'] = df['macd'] - df['macd_signal']
    
    # --- Bollinger Bands ---
    df['bb_middle'] = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_middle'] + (2 * bb_std)
    df['bb_lower'] = df['bb_middle'] - (2 * bb_std)
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    
    # --- ATR ---
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = true_range.rolling(14).mean()
    
    # --- Stochastic ---
    low14 = df['low'].rolling(14).min()
    high14 = df['high'].rolling(14).max()
    range14 = high14 - low14
    range14 = range14.replace(0, np.inf)
    df['stoch_k'] = ((df['close'] - low14) / range14) * 100
    df['stoch_d'] = df['stoch_k'].rolling(3).mean()
    df['stoch_k'] = df['stoch_k'].fillna(50)
    df['stoch_d'] = df['stoch_d'].fillna(50)
    
    # --- ADX ---
    plus_dm = df['high'].diff().clip(lower=0)
    minus_dm = (-df['low'].diff()).clip(lower=0)
    atr14 = true_range.rolling(14).mean()
    atr14_safe = atr14.replace(0, np.inf)
    plus_di = 100 * (plus_dm.rolling(14).mean() / atr14_safe)
    minus_di = 100 * (minus_dm.rolling(14).mean() / atr14_safe)
    di_sum = plus_di + minus_di
    di_sum = di_sum.replace(0, np.inf)
    dx = 100 * ((plus_di - minus_di).abs() / di_sum)
    df['adx'] = dx.rolling(14).mean()
    df['plus_di'] = plus_di.fillna(0)
    df['minus_di'] = minus_di.fillna(0)
    
    # --- Ichimoku (simplified) ---
    df['tenkan'] = (df['high'].rolling(9).max() + df['low'].rolling(9).min()) / 2
    df['kijun'] = (df['high'].rolling(26).max() + df['low'].rolling(26).min()) / 2
    df['senkou_a'] = ((df['tenkan'] + df['kijun']) / 2).shift(26)
    df['senkou_b'] = ((df['high'].rolling(52).max() + df['low'].rolling(52).min()) / 2).shift(26)
    
    # --- CCI ---
    tp = (df['high'] + df['low'] + df['close']) / 3
    df['cci'] = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).std())
    
    # --- Williams %R ---
    df['williams_r'] = ((high14 - df['close']) / range14) * -100
    df['williams_r'] = df['williams_r'].fillna(-50)
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    return {
        "status": "success",
        "current_price": safe_float(latest['close']),
        
        "moving_averages": {
            "sma_20": safe_float(latest['sma_20']),
            "sma_50": safe_float(latest['sma_50']),
            "sma_100": safe_float(latest['sma_100']),
            "sma_200": safe_float(latest['sma_200']),
            "ema_9": safe_float(latest['ema_9']),
            "ema_21": safe_float(latest['ema_21']),
            "ema_55": safe_float(latest['ema_55']),
            "price_vs_sma200": "ABOVE" if latest['close'] > latest['sma_200'] else "BELOW",
            "price_vs_sma50": "ABOVE" if latest['close'] > latest['sma_50'] else "BELOW",
            "sma_cross": "GOLDEN_CROSS" if latest['sma_50'] > latest['sma_200'] else "DEATH_CROSS"
        },
        
        "rsi": {
            "value": round(safe_float(latest['rsi']), 2),
            "condition": "OVERBOUGHT" if latest['rsi'] > 70 else "OVERSOLD" if latest['rsi'] < 30 else "NEUTRAL",
            "trend": "RISING" if latest['rsi'] > prev['rsi'] else "FALLING"
        },
        
        "macd": {
            "macd_line": round(safe_float(latest['macd']), 6),
            "signal_line": round(safe_float(latest['macd_signal']), 6),
            "histogram": round(safe_float(latest['macd_histogram']), 6),
            "crossover": "BULLISH" if latest['macd'] > latest['macd_signal'] else "BEARISH",
            "histogram_trend": "EXPANDING" if abs(latest['macd_histogram']) > abs(prev['macd_histogram']) else "CONTRACTING"
        },
        
        "bollinger_bands": {
            "upper": safe_float(latest['bb_upper']),
            "middle": safe_float(latest['bb_middle']),
            "lower": safe_float(latest['bb_lower']),
            "width": round(safe_float(latest['bb_width']), 4),
            "position": "UPPER" if latest['close'] > latest['bb_upper'] else "LOWER" if latest['close'] < latest['bb_lower'] else "MIDDLE",
            "percent_b": round(safe_float((latest['close'] - latest['bb_lower']) / (latest['bb_upper'] - latest['bb_lower'])), 2) if latest['bb_upper'] != latest['bb_lower'] else 0.5,
            "squeeze": "SQUEEZE" if latest['bb_width'] < df['bb_width'].tail(50).mean() * 0.7 else "NORMAL"
        },
        
        "atr": {
            "value": round(safe_float(latest['atr']), 2),
            "percent_of_price": round(safe_float(latest['atr'] / latest['close'] * 100), 3),
            "volatility_regime": "HIGH" if latest['atr'] > df['atr'].tail(100).mean() * 1.2 else "LOW" if latest['atr'] < df['atr'].tail(100).mean() * 0.8 else "NORMAL"
        },
        
        "stochastic": {
            "k": round(safe_float(latest['stoch_k']), 2),
            "d": round(safe_float(latest['stoch_d']), 2),
            "condition": "OVERBOUGHT" if latest['stoch_k'] > 80 else "OVERSOLD" if latest['stoch_k'] < 20 else "NEUTRAL",
            "crossover": "BULLISH" if latest['stoch_k'] > latest['stoch_d'] else "BEARISH"
        },
        
        "adx": {
            "value": round(safe_float(latest['adx']), 2),
            "trend_strength": "STRONG" if latest['adx'] > 25 else "WEAK",
            "plus_di": round(safe_float(latest['plus_di']), 2),
            "minus_di": round(safe_float(latest['minus_di']), 2),
            "direction": "BULLISH" if latest['plus_di'] > latest['minus_di'] else "BEARISH"
        },
        
        "ichimoku": {
            "tenkan": safe_float(latest['tenkan']),
            "kijun": safe_float(latest['kijun']),
            "cloud_top": safe_float(max(latest['senkou_a'], latest['senkou_b'])) if pd.notna(latest['senkou_a']) else None,
            "cloud_bottom": safe_float(min(latest['senkou_a'], latest['senkou_b'])) if pd.notna(latest['senkou_a']) else None,
            "price_vs_cloud": "ABOVE" if latest['close'] > max(latest['senkou_a'], latest['senkou_b']) else "BELOW" if latest['close'] < min(latest['senkou_a'], latest['senkou_b']) else "INSIDE" if pd.notna(latest['senkou_a']) else "UNKNOWN",
            "tk_cross": "BULLISH" if latest['tenkan'] > latest['kijun'] else "BEARISH"
        },
        
        "cci": {
            "value": round(safe_float(latest['cci']), 2),
            "condition": "OVERBOUGHT" if latest['cci'] > 100 else "OVERSOLD" if latest['cci'] < -100 else "NEUTRAL"
        },
        
        "williams_r": {
            "value": round(safe_float(latest['williams_r']), 2),
            "condition": "OVERBOUGHT" if latest['williams_r'] > -20 else "OVERSOLD" if latest['williams_r'] < -80 else "NEUTRAL"
        }
    }


# ═══════════════════════════════════════════════════════════════════
# INDIVIDUAL INDICATORS (for granular use)
# ═══════════════════════════════════════════════════════════════════

def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI for a price series."""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.inf)
    return 100 - (100 / (1 + rs))


def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
    """Calculate MACD components."""
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram
    }


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate ATR from OHLC data."""
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(period).mean()


def calculate_bollinger(prices: pd.Series, period: int = 20, std_dev: float = 2) -> Dict:
    """Calculate Bollinger Bands."""
    middle = prices.rolling(period).mean()
    std = prices.rolling(period).std()
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    return {
        "upper": upper,
        "middle": middle,
        "lower": lower,
        "width": (upper - lower) / middle
    }


# ═══════════════════════════════════════════════════════════════════
# MULTI-TIMEFRAME TREND ANALYSIS
# ═══════════════════════════════════════════════════════════════════

def multi_timeframe_trend_analysis(mtf_data: Dict) -> Dict:
    """
    Analyze trend alignment across multiple timeframes.
    
    Args:
        mtf_data: Dict with timeframe keys, each containing OHLCV data
    
    Returns:
        Trend consensus and alignment score
    """
    trends = {}
    
    for tf, data in mtf_data.items():
        if data.get("status") != "success":
            continue
            
        ohlcv = data.get("data", [])
        if len(ohlcv) < 50:
            continue
        
        df = pd.DataFrame(ohlcv)
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        
        current = df['close'].iloc[-1]
        sma20 = df['sma_20'].iloc[-1]
        sma50 = df['sma_50'].iloc[-1]
        
        if pd.isna(sma50):
            continue
        
        if current > sma20 > sma50:
            trends[tf] = "STRONG_BULLISH"
        elif current > sma20:
            trends[tf] = "BULLISH"
        elif current < sma20 < sma50:
            trends[tf] = "STRONG_BEARISH"
        elif current < sma20:
            trends[tf] = "BEARISH"
        else:
            trends[tf] = "NEUTRAL"
    
    if not trends:
        return {"status": "error", "message": "Insufficient data for MTF analysis"}
    
    bullish_count = sum(1 for t in trends.values() if "BULLISH" in t)
    bearish_count = sum(1 for t in trends.values() if "BEARISH" in t)
    total = len(trends)
    
    if total == 0:
        alignment = "UNKNOWN"
        alignment_score = 0
    elif bullish_count == total:
        alignment = "ALIGNED_BULLISH"
        alignment_score = 100
    elif bearish_count == total:
        alignment = "ALIGNED_BEARISH"
        alignment_score = 100
    else:
        alignment = "MIXED"
        alignment_score = max(bullish_count, bearish_count) / total * 100
    
    return {
        "status": "success",
        "timeframe_trends": trends,
        "alignment": alignment,
        "alignment_score": round(alignment_score, 1),
        "dominant_direction": "BULLISH" if bullish_count > bearish_count else "BEARISH" if bearish_count > bullish_count else "NEUTRAL",
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "total_timeframes": total
    }
