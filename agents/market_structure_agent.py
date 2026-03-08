"""
Market Structure Agent - Smart Money Concepts analysis.
"""
import json
from typing import Dict, List
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.structure_tools import analyze_market_structure, find_premium_discount_zones
from utils.logger import get_logger

logger = get_logger("market_structure_agent")


class MarketStructureAgent:
    """
    Agent for Smart Money Concepts analysis.
    
    Responsibilities:
    - Identify Break of Structure (BOS)
    - Detect Change of Character (CHoCH)
    - Find Order Blocks
    - Detect Fair Value Gaps (FVG)
    - Map liquidity levels
    - Determine premium/discount zones
    """
    
    def __init__(self):
        self.last_analysis = None
    
    def analyze(self, ohlcv_data: List[Dict]) -> Dict:
        """
        Run complete market structure analysis.
        
        Args:
            ohlcv_data: List of OHLCV candles
        
        Returns:
            SMC analysis results
        """
        if not ohlcv_data or len(ohlcv_data) < 50:
            return {"status": "error", "message": "Insufficient data for SMC analysis"}
        
        logger.info("Running market structure analysis")
        
        # Main SMC analysis
        structure = analyze_market_structure(ohlcv_data)
        
        # Premium/Discount zones
        zones = find_premium_discount_zones(ohlcv_data)
        
        analysis = {
            "status": "success",
            "market_structure": structure.get("market_structure"),
            "current_price": structure.get("current_price"),
            "bos_events": structure.get("bos_events", []),
            "choch_events": structure.get("choch_events", []),
            "fair_value_gaps": structure.get("fair_value_gaps", []),
            "order_blocks": structure.get("order_blocks", []),
            "liquidity_levels": structure.get("liquidity_levels", []),
            "swing_highs": structure.get("swing_highs", []),
            "swing_lows": structure.get("swing_lows", []),
            "premium_discount": zones,
            "narrative": self._generate_narrative(structure, zones)
        }
        
        self.last_analysis = analysis
        return analysis
    
    def _generate_narrative(self, structure: Dict, zones: Dict) -> str:
        """Generate a narrative summary of the market structure."""
        lines = []
        
        # Structure
        ms = structure.get("market_structure", "Unknown")
        lines.append(f"Market Structure: {ms}")
        
        # BOS
        bos = structure.get("bos_events", [])
        if bos:
            latest = bos[-1]
            lines.append(f"Latest BOS: {latest.get('type')} at {latest.get('broken_level')}")
        
        # FVGs
        fvgs = structure.get("fair_value_gaps", [])
        if fvgs:
            unfilled = [f for f in fvgs if not f.get("filled")]
            lines.append(f"Unfilled FVGs: {len(unfilled)}")
        
        # Zone
        zone = zones.get("zone", "Unknown")
        lines.append(f"Price Zone: {zone} ({zones.get('range_position')}% of range)")
        
        # Recommendation
        if zone == "DISCOUNT" and ms == "BULLISH":
            lines.append("→ Ideal zone for longs (discount + bullish structure)")
        elif zone == "PREMIUM" and ms == "BEARISH":
            lines.append("→ Ideal zone for shorts (premium + bearish structure)")
        elif zone == "PREMIUM" and ms == "BULLISH":
            lines.append("→ Caution: Price extended in premium - wait for pullback")
        elif zone == "DISCOUNT" and ms == "BEARISH":
            lines.append("→ Caution: Price in discount but structure bearish")
        
        return " | ".join(lines)
    
    def get_summary(self, analysis: Dict = None) -> str:
        """Get text summary."""
        if analysis is None:
            analysis = self.last_analysis
        
        if not analysis:
            return "No analysis available"
        
        lines = []
        lines.append("MARKET STRUCTURE ANALYSIS")
        lines.append("-" * 40)
        lines.append(f"Structure: {analysis.get('market_structure')}")
        lines.append(f"Current Price: {analysis.get('current_price')}")
        lines.append(f"Zone: {analysis.get('premium_discount', {}).get('zone')}")
        lines.append("")
        lines.append(analysis.get('narrative', ''))
        
        return "\n".join(lines)


SYSTEM_PROMPT = """
You are the Market Structure Agent, specializing in Smart Money Concepts (SMC).

You analyze:
- Break of Structure (BOS) - trend continuation signals
- Change of Character (CHoCH) - trend reversal signals
- Order Blocks - institutional entry zones
- Fair Value Gaps (FVG) - imbalance zones to be filled
- Liquidity levels - where stops are clustered
- Premium/Discount zones - expensive vs cheap areas

Your analysis helps identify:
1. Where institutions are likely positioned
2. Optimal entry zones (discount for longs, premium for shorts)
3. High-probability reversal areas
4. Liquidity pools that may be targeted

Rules:
- Only trade in direction of market structure
- Enter in discount zones for longs, premium for shorts
- Use order blocks as entry zones
- Target unfilled FVGs
- Be aware of liquidity sweeps
"""


if __name__ == "__main__":
    agent = MarketStructureAgent()
    print("Market Structure Agent initialized")
