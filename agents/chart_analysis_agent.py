"""
Chart Analysis Agent - Technical indicators, patterns, S/R levels.
"""
import json
from typing import Dict, List, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.indicator_tools import calculate_all_indicators, multi_timeframe_trend_analysis
from tools.pattern_tools import detect_candlestick_patterns, find_support_resistance, detect_trend, detect_chart_patterns
from utils.logger import get_logger

logger = get_logger("chart_analysis_agent")


class ChartAnalysisAgent:
    """
    Agent for comprehensive technical analysis.
    
    Responsibilities:
    - Calculate all technical indicators
    - Detect candlestick patterns
    - Find support/resistance levels
    - Analyze trends across timeframes
    - Detect chart patterns
    """
    
    def __init__(self):
        self.last_analysis = None
    
    def analyze(self, ohlcv_data: List[Dict], timeframe: str = "H1") -> Dict:
        """
        Run complete technical analysis on OHLCV data.
        
        Args:
            ohlcv_data: List of OHLCV candles
            timeframe: Timeframe being analyzed
        
        Returns:
            Complete technical analysis
        """
        if not ohlcv_data or len(ohlcv_data) < 50:
            return {"status": "error", "message": "Insufficient data for analysis"}
        
        logger.info(f"Running chart analysis for {timeframe}")
        
        # Calculate indicators
        indicators = calculate_all_indicators(ohlcv_data)
        
        # Detect patterns
        patterns = detect_candlestick_patterns(ohlcv_data)
        
        # Find S/R levels
        sr_levels = find_support_resistance(ohlcv_data)
        
        # Detect trend
        trend = detect_trend(ohlcv_data)
        
        # Chart patterns
        chart_patterns = detect_chart_patterns(ohlcv_data)
        
        analysis = {
            "status": "success",
            "timeframe": timeframe,
            "indicators": indicators,
            "candlestick_patterns": patterns,
            "support_resistance": sr_levels,
            "trend": trend,
            "chart_patterns": chart_patterns,
            "current_price": indicators.get("current_price"),
            "atr": indicators.get("atr", {}).get("value")
        }
        
        self.last_analysis = analysis
        return analysis
    
    def analyze_multi_timeframe(self, mtf_data: Dict) -> Dict:
        """
        Analyze trend alignment across multiple timeframes.
        
        Args:
            mtf_data: Dict with timeframe keys, each containing OHLCV data
        
        Returns:
            Multi-timeframe trend analysis
        """
        logger.info("Running multi-timeframe trend analysis")
        
        # Run MTF trend analysis
        mtf_trend = multi_timeframe_trend_analysis(mtf_data)
        
        # Run individual analyses
        individual = {}
        for tf, data in mtf_data.items():
            if data.get("status") == "success":
                ohlcv = data.get("data", [])
                if len(ohlcv) >= 50:
                    individual[tf] = self.analyze(ohlcv, tf)
        
        return {
            "status": "success",
            "mtf_trend": mtf_trend,
            "individual_analyses": individual
        }
    
    def get_summary(self, analysis: Dict = None) -> str:
        """Get a text summary of the analysis."""
        if analysis is None:
            analysis = self.last_analysis
        
        if not analysis:
            return "No analysis available"
        
        lines = []
        lines.append(f"CHART ANALYSIS ({analysis.get('timeframe', 'Unknown')})")
        lines.append("-" * 40)
        
        # Trend
        trend = analysis.get("trend", {})
        lines.append(f"Trend: {trend.get('trend', 'Unknown')}")
        
        # RSI
        rsi = analysis.get("indicators", {}).get("rsi", {})
        lines.append(f"RSI: {rsi.get('value', 'N/A')} ({rsi.get('condition', 'N/A')})")
        
        # MACD
        macd = analysis.get("indicators", {}).get("macd", {})
        lines.append(f"MACD: {macd.get('crossover', 'N/A')}")
        
        # ADX
        adx = analysis.get("indicators", {}).get("adx", {})
        lines.append(f"ADX: {adx.get('value', 'N/A')} ({adx.get('trend_strength', 'N/A')} trend)")
        
        # Patterns
        patterns = analysis.get("candlestick_patterns", {}).get("patterns", [])
        if patterns:
            lines.append(f"Patterns: {', '.join([p['pattern'] for p in patterns[:3]])}")
        
        # S/R
        sr = analysis.get("support_resistance", {})
        lines.append(f"Nearest Resistance: {sr.get('nearest_resistance', 'N/A')}")
        lines.append(f"Nearest Support: {sr.get('nearest_support', 'N/A')}")
        
        return "\n".join(lines)


# Agent system prompt
SYSTEM_PROMPT = """
You are the Chart Analysis Agent, an expert technical analyst. You receive
OHLCV data and compute technical indicators, identify chart patterns, 
find support/resistance levels, and determine trend direction across 
multiple timeframes.

You return structured analysis with confidence scores.
You are objective and data-driven. Always include the timeframe context.

Your analysis includes:
- Moving Averages (SMA 20/50/100/200, EMA 9/21/55)
- RSI (14) with overbought/oversold conditions
- MACD (12, 26, 9) with crossovers
- Bollinger Bands with squeeze detection
- ATR (14) for volatility
- Stochastic (14, 3, 3)
- ADX (14) for trend strength
- Ichimoku Cloud position
- Candlestick patterns (Doji, Hammer, Engulfing, etc.)
- Support/Resistance levels
- Trend direction and strength

Always provide:
1. Current indicator values
2. Signal interpretation (bullish/bearish/neutral)
3. Key levels to watch
4. Pattern alerts
"""


if __name__ == "__main__":
    # Test with sample data
    agent = ChartAnalysisAgent()
    
    # Create sample OHLCV data
    import pandas as pd
    import numpy as np
    
    np.random.seed(42)
    n = 200
    base_price = 2000
    
    sample_data = []
    for i in range(n):
        open_price = base_price + np.random.randn() * 10
        close_price = open_price + np.random.randn() * 5
        high_price = max(open_price, close_price) + abs(np.random.randn() * 3)
        low_price = min(open_price, close_price) - abs(np.random.randn() * 3)
        
        sample_data.append({
            "time": pd.Timestamp.now() - pd.Timedelta(hours=n-i),
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "tick_volume": int(np.random.rand() * 1000 + 100)
        })
        
        base_price = close_price
    
    result = agent.analyze(sample_data, "H1")
    print(agent.get_summary(result))
