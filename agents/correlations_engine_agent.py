"""
Correlations Engine Agent - Track gold correlations, divergences, safe haven flows.
"""
import json
from typing import Dict, List
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.correlation_tools import (
    calculate_rolling_correlations,
    detect_correlation_divergences,
    compute_dxy_synthetic,
    analyze_safe_haven_flow,
    full_correlation_analysis
)
from utils.logger import get_logger

logger = get_logger("correlations_agent")


class CorrelationsEngineAgent:
    """
    Agent for tracking and analyzing all Gold correlations.
    
    Responsibilities:
    - Calculate rolling correlations with all related instruments
    - Detect correlation divergences
    - Build synthetic DXY
    - Analyze safe haven flows
    - Identify leading signals
    """
    
    def __init__(self):
        self.last_analysis = None
    
    def analyze(self, all_data: Dict) -> Dict:
        """
        Run complete correlation analysis.
        
        Args:
            all_data: Dict with all instrument data from data fetcher
        
        Returns:
            Complete correlation analysis
        """
        if not all_data:
            return {"status": "error", "message": "No data provided"}
        
        logger.info("Running correlation analysis")
        
        # Run full analysis
        full_analysis = full_correlation_analysis(all_data)
        
        if full_analysis.get("status") != "success":
            return full_analysis
        
        analysis = {
            "status": "success",
            "overall_signal": full_analysis.get("overall_correlation_signal"),
            "bullish_signals": full_analysis.get("bullish_signals", 0),
            "bearish_signals": full_analysis.get("bearish_signals", 0),
            "rolling_correlations": full_analysis.get("rolling_correlations", {}),
            "divergences": full_analysis.get("divergences", {}),
            "dxy_synthetic": full_analysis.get("dxy_synthetic", {}),
            "safe_haven_flow": full_analysis.get("safe_haven_flow", {}),
            "narrative": self._generate_narrative(full_analysis)
        }
        
        self.last_analysis = analysis
        return analysis
    
    def _generate_narrative(self, analysis: Dict) -> str:
        """Generate narrative summary."""
        lines = []
        
        # Overall
        signal = analysis.get("overall_correlation_signal", "NEUTRAL")
        lines.append(f"Correlation Signal: {signal}")
        
        # DXY
        dxy = analysis.get("dxy_synthetic", {})
        lines.append(f"DXY: {dxy.get('dxy_direction')} → {dxy.get('gold_implication')} for Gold")
        
        # Safe Haven
        safe = analysis.get("safe_haven_flow", {})
        lines.append(f"Environment: {safe.get('market_environment')} → {safe.get('gold_impact')}")
        
        # Divergences
        div = analysis.get("divergences", {})
        if div.get("divergence_count", 0) > 0:
            lines.append(f"⚠️ {div.get('divergence_count')} correlation divergences detected")
        
        return " | ".join(lines)
    
    def get_summary(self, analysis: Dict = None) -> str:
        """Get text summary."""
        if analysis is None:
            analysis = self.last_analysis
        
        if not analysis:
            return "No analysis available"
        
        lines = []
        lines.append("CORRELATIONS ANALYSIS")
        lines.append("-" * 40)
        lines.append(f"Overall Signal: {analysis.get('overall_signal')}")
        lines.append(f"Bullish: {analysis.get('bullish_signals')} | Bearish: {analysis.get('bearish_signals')}")
        lines.append("")
        lines.append(analysis.get("narrative", ""))
        
        return "\n".join(lines)


SYSTEM_PROMPT = """
You are the Gold Correlations Engine Agent. You specialize in tracking
every market that influences Gold (XAUUSD) prices.

INVERSE correlations (Gold moves opposite):
- DXY (US Dollar Index) -0.85
- US Bond Yields (10Y, 2Y) -0.70
- Real Interest Rates -0.80
- S&P 500 -0.30

POSITIVE correlations (Gold moves together):
- Silver (XAGUSD) +0.90
- VIX (Fear Index) +0.60
- EURUSD +0.80
- JPY/CHF pairs +0.50
- Inflation expectations +0.65

COMPLEX correlations:
- Oil (WTI/Brent) +0.35
- Bitcoin varies
- Copper +0.40

You detect:
- Divergences (Gold moving opposite to expected correlation)
- Leading signals (correlated market moved first)
- Correlation breakdowns (relationship changing)
- Regime changes (correlation flipping sign)

Return correlation scores, divergence alerts, and directional bias.
"""


if __name__ == "__main__":
    agent = CorrelationsEngineAgent()
    print("Correlations Engine Agent initialized")
