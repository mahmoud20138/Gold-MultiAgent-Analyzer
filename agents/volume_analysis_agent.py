"""
Volume Analysis Agent - Volume profile, money flow, accumulation/distribution.
"""
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.volume_tools import (
    analyze_volume_profile,
    analyze_accumulation_distribution,
    analyze_volume_anomalies,
    volume_price_analysis
)
from utils.logger import get_logger

logger = get_logger("volume_analysis_agent")


class VolumeAnalysisAgent:
    """
    Volume analysis specialist.
    Analyzes volume profile, money flow, and accumulation/distribution.
    """
    
    def __init__(self):
        self.last_analysis = None
    
    def analyze(self, ohlcv_data: List[Dict]) -> Dict:
        """
        Perform complete volume analysis.
        
        Args:
            ohlcv_data: OHLCV candle data
        
        Returns:
            Complete volume analysis
        """
        if not ohlcv_data or len(ohlcv_data) < 50:
            return {"status": "error", "message": "Insufficient data"}
        
        result = {
            "status": "success",
            "profile": analyze_volume_profile(ohlcv_data),
            "flow": analyze_accumulation_distribution(ohlcv_data),
            "anomalies": analyze_volume_anomalies(ohlcv_data),
            "vpa": volume_price_analysis(ohlcv_data)
        }

        # Flatten key flow fields to top level (for signal_tools / orchestrator consumers)
        flow = result.get("flow", {})
        result["overall_flow"] = flow.get("overall_flow", "MIXED")
        result["cmf"] = flow.get("cmf", {})
        result["obv"] = flow.get("obv", {})
        result["divergences"] = flow.get("divergences", {})

        # Create summary
        result["summary"] = self._create_summary(result)
        
        self.last_analysis = result
        logger.info("Volume analysis complete")
        
        return result
    
    def _create_summary(self, analysis: Dict) -> Dict:
        """Create volume analysis summary."""
        profile = analysis.get("profile", {})
        flow = analysis.get("flow", {})
        anomalies = analysis.get("anomalies", {})
        vpa = analysis.get("vpa", {})
        
        summary = {
            "overall_flow": flow.get("overall_flow", "MIXED"),
            "price_vs_poc": profile.get("price_vs_poc", "UNKNOWN"),
            "price_in_va": profile.get("price_in_value_area", False),
            "relative_volume": anomalies.get("relative_volume", 1),
            "rv_label": anomalies.get("relative_volume_label", "NORMAL"),
            "vpa_overall": vpa.get("summary", {}).get("overall", "UNKNOWN"),
            "divergences": flow.get("divergences", {}).get("any_divergence", False)
        }
        
        # Volume signal
        signals = []
        if summary["overall_flow"] == "ACCUMULATION":
            signals.append("ACCUMULATION")
        elif summary["overall_flow"] == "DISTRIBUTION":
            signals.append("DISTRIBUTION")
        
        if summary["price_vs_poc"] == "ABOVE":
            signals.append("ABOVE_POC")
        elif summary["price_vs_poc"] == "BELOW":
            signals.append("BELOW_POC")
        
        if summary["rv_label"] in ["HIGH", "VERY_HIGH"]:
            signals.append("HIGH_VOLUME")
        elif summary["rv_label"] == "LOW":
            signals.append("LOW_VOLUME")
        
        if summary["divergences"]:
            signals.append("DIVERGENCE")
        
        summary["signals"] = signals
        
        # Bias
        if "ACCUMULATION" in signals and "ABOVE_POC" in signals:
            summary["bias"] = "BULLISH"
        elif "DISTRIBUTION" in signals and "BELOW_POC" in signals:
            summary["bias"] = "BEARISH"
        elif summary["divergences"]:
            summary["bias"] = "CAUTION"
        else:
            summary["bias"] = "NEUTRAL"
        
        return summary
    
    def get_flow(self, ohlcv_data: List[Dict]) -> str:
        """Get overall money flow (ACCUMULATION/DISTRIBUTION/MIXED)."""
        analysis = self.analyze(ohlcv_data)
        return analysis.get("summary", {}).get("overall_flow", "MIXED")


def run_agent(action: str, **kwargs) -> Dict:
    """
    Run the volume analysis agent.
    
    Actions:
        - analyze: Full volume analysis
        - flow: Get money flow only
    """
    agent = VolumeAnalysisAgent()
    
    if action == "analyze":
        return agent.analyze(kwargs.get("ohlcv_data", []))
    elif action == "flow":
        return {"flow": agent.get_flow(kwargs.get("ohlcv_data", []))}
    else:
        return {"status": "error", "message": f"Unknown action: {action}"}


if __name__ == "__main__":
    print("Volume Analysis Agent ready")
