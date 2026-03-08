"""
Sentiment Master Agent - Coordinates sentiment analysis sub-agents.
For now, provides a simplified sentiment based on correlations and market context.
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logger import get_logger
from utils.time_utils import get_session_context

logger = get_logger("sentiment_agent")


class SentimentMasterAgent:
    """
    Coordinates sentiment analysis from multiple sources.
    In this version, uses correlation and session data as sentiment proxy.
    """
    
    def __init__(self):
        self.last_sentiment = None
    
    def analyze(
        self,
        correlation_analysis: Dict,
        session_context: Dict = None,
        news_headlines: List[str] = None
    ) -> Dict:
        """
        Analyze market sentiment.
        
        Args:
            correlation_analysis: Output from correlations agent
            session_context: Trading session info
            news_headlines: List of recent headlines (optional)
        
        Returns:
            Sentiment analysis with score (-100 to +100)
        """
        score = 0
        factors = []
        
        # Correlation-based sentiment
        overall_corr = correlation_analysis.get("overall_correlation_signal", "NEUTRAL")
        if overall_corr == "BULLISH":
            score += 30
            factors.append({"factor": "correlations", "impact": "BULLISH", "weight": 30})
        elif overall_corr == "BEARISH":
            score -= 30
            factors.append({"factor": "correlations", "impact": "BEARISH", "weight": -30})
        
        # DXY impact
        dxy = correlation_analysis.get("dxy_synthetic", {})
        dxy_impact = dxy.get("gold_implication", "NEUTRAL")
        if dxy_impact == "BULLISH":
            score += 20
            factors.append({"factor": "dxy", "impact": "BULLISH", "weight": 20})
        elif dxy_impact == "BEARISH":
            score -= 20
            factors.append({"factor": "dxy", "impact": "BEARISH", "weight": -20})
        
        # Safe haven flow
        safe_haven = correlation_analysis.get("safe_haven_flow", {})
        env = safe_haven.get("market_environment", "MIXED")
        if "RISK_OFF" in env:
            score += 25
            factors.append({"factor": "safe_haven", "impact": "BULLISH", "weight": 25})
        elif "RISK_ON" in env:
            score -= 15
            factors.append({"factor": "risk_appetite", "impact": "BEARISH", "weight": -15})
        
        # Session context
        if session_context is None:
            session_context = get_session_context()
        
        if session_context.get("session_overlap"):
            score += 10
            factors.append({"factor": "session_overlap", "impact": "BULLISH", "weight": 10})
        
        volatility = session_context.get("expected_volatility", "MEDIUM")
        if volatility == "HIGH":
            # High vol can be bullish for gold (uncertainty)
            score += 5
            factors.append({"factor": "volatility", "impact": "MILDLY_BULLISH", "weight": 5})
        
        # Determine direction
        if score > 40:
            direction = "STRONGLY_BULLISH"
        elif score > 20:
            direction = "BULLISH"
        elif score > 5:
            direction = "MILDLY_BULLISH"
        elif score > -5:
            direction = "NEUTRAL"
        elif score > -20:
            direction = "MILDLY_BEARISH"
        elif score > -40:
            direction = "BEARISH"
        else:
            direction = "STRONGLY_BEARISH"
        
        # Conviction
        abs_score = abs(score)
        if abs_score > 50:
            conviction = "HIGH"
        elif abs_score > 25:
            conviction = "MEDIUM"
        else:
            conviction = "LOW"
        
        result = {
            "status": "success",
            "composite_score": score,
            "direction": direction,
            "conviction": conviction,
            "factors": factors,
            "primary_driver": factors[0] if factors else None,
            "session": session_context,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self.last_sentiment = result
        logger.info(f"Sentiment: {direction} ({score})")
        
        return result
    
    def get_score(self, correlation_analysis: Dict) -> int:
        """Quick sentiment score."""
        sentiment = self.analyze(correlation_analysis)
        return sentiment.get("composite_score", 0)


def run_agent(action: str, **kwargs) -> Dict:
    """
    Run the sentiment master agent.
    
    Actions:
        - analyze: Full sentiment analysis
        - score: Quick score only
    """
    agent = SentimentMasterAgent()
    
    if action == "analyze":
        return agent.analyze(
            kwargs.get("correlation_analysis", {}),
            kwargs.get("session_context"),
            kwargs.get("news_headlines")
        )
    elif action == "score":
        return {"score": agent.get_score(kwargs.get("correlation_analysis", {}))}
    else:
        return {"status": "error", "message": f"Unknown action: {action}"}


if __name__ == "__main__":
    print("Sentiment Master Agent ready")
