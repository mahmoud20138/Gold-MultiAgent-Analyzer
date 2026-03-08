"""
Trade Recommendation Agent - Final signal synthesis and recommendation.
"""
import json
from typing import Dict, List
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.signal_tools import generate_trade_signal
from utils.logger import get_logger

logger = get_logger("trade_recommendation_agent")


class TradeRecommendationAgent:
    """
    Agent for synthesizing all analyses into a final trade recommendation.
    
    Responsibilities:
    - Combine all agent outputs
    - Score the trade setup (0-100)
    - Generate exact entry/SL/TP levels
    - Provide reasoning summary
    - Only recommend high-probability setups (70+)
    """
    
    def __init__(self):
        self.last_recommendation = None
    
    def generate_recommendation(
        self,
        chart_analysis: Dict,
        market_structure: Dict,
        volume_analysis: Dict,
        correlation_analysis: Dict,
        risk_assessment: Dict,
        support_resistance: Dict,
        symbol: str,
        timeframe: str,
        sentiment_score: float = 0
    ) -> Dict:
        """
        Generate final trade recommendation from all analyses.
        
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
            Complete trade recommendation
        """
        logger.info(f"Generating trade recommendation for {symbol}")
        
        # Generate signal
        signal = generate_trade_signal(
            chart_analysis=chart_analysis,
            market_structure=market_structure,
            volume_analysis=volume_analysis,
            correlation_analysis=correlation_analysis,
            risk_assessment=risk_assessment,
            support_resistance=support_resistance,
            symbol=symbol,
            timeframe=timeframe,
            sentiment_score=sentiment_score
        )
        
        # Format for display
        recommendation = {
            "status": "success",
            "symbol": signal.get("symbol"),
            "timeframe": signal.get("timeframe"),
            "direction": signal.get("direction"),
            "confidence_score": signal.get("confidence_score"),
            "trade_grade": signal.get("trade_grade"),
            "entry_price": signal.get("entry_price"),
            "stop_loss": signal.get("stop_loss"),
            "take_profit_1": signal.get("take_profit_1"),
            "take_profit_2": signal.get("take_profit_2"),
            "take_profit_3": signal.get("take_profit_3"),
            "risk_reward_ratio": signal.get("risk_reward_ratio"),
            "atr": signal.get("atr"),
            "reasons": signal.get("reasons", []),
            "warnings": signal.get("warnings", []),
            "recommendation": signal.get("recommendation"),
            "trade_action": signal.get("trade_action"),
            "risk_approved": signal.get("risk_approved"),
            "position_sizing": risk_assessment.get("position_sizing") if risk_assessment else None,
            "lot_size": risk_assessment.get("lot_size") if risk_assessment else None,
            "risk_amount": risk_assessment.get("risk_amount_usd") if risk_assessment else None
        }
        
        self.last_recommendation = recommendation
        return recommendation
    
    def format_report(self, recommendation: Dict = None) -> str:
        """
        Format a complete analysis report for display.
        
        Args:
            recommendation: Trade recommendation dict
        
        Returns:
            Formatted text report
        """
        if recommendation is None:
            recommendation = self.last_recommendation
        
        if not recommendation:
            return "No recommendation available"
        
        lines = []
        lines.append("=" * 60)
        lines.append(f"  TRADE RECOMMENDATION: {recommendation.get('symbol', 'N/A')}")
        lines.append("=" * 60)
        lines.append("")
        
        # Direction & Confidence
        direction = recommendation.get("direction", "NEUTRAL")
        confidence = recommendation.get("confidence_score", 0)
        grade = recommendation.get("trade_grade", "N/A")
        
        if direction == "BUY":
            emoji = "🟢"
        elif direction == "SELL":
            emoji = "🔴"
        else:
            emoji = "⚪"
        
        lines.append(f"Signal: {emoji} {direction}")
        lines.append(f"Confidence: {confidence}/100 (Grade: {grade})")
        lines.append(f"Action: {recommendation.get('trade_action', 'WAIT')}")
        lines.append("")
        
        # Entry Levels
        lines.append("📍 LEVELS")
        lines.append("-" * 40)
        lines.append(f"Entry: {recommendation.get('entry_price', 'N/A')}")
        lines.append(f"Stop Loss: {recommendation.get('stop_loss', 'N/A')}")
        lines.append(f"Take Profit 1: {recommendation.get('take_profit_1', 'N/A')}")
        lines.append(f"Take Profit 2: {recommendation.get('take_profit_2', 'N/A')}")
        lines.append(f"Take Profit 3: {recommendation.get('take_profit_3', 'N/A')}")
        lines.append(f"Risk:Reward: 1:{recommendation.get('risk_reward_ratio', 'N/A')}")
        lines.append("")
        
        # Position Sizing
        if recommendation.get("lot_size"):
            lines.append("📦 POSITION SIZING")
            lines.append("-" * 40)
            lines.append(f"Lot Size: {recommendation.get('lot_size')}")
            lines.append(f"Risk Amount: ${recommendation.get('risk_amount', 'N/A')}")
            lines.append("")
        
        # Reasons
        reasons = recommendation.get("reasons", [])
        if reasons:
            lines.append("✅ REASONS")
            lines.append("-" * 40)
            for reason in reasons[:5]:
                lines.append(f"  • {reason}")
            lines.append("")
        
        # Warnings
        warnings = recommendation.get("warnings", [])
        if warnings:
            lines.append("⚠️ WARNINGS")
            lines.append("-" * 40)
            for warning in warnings:
                lines.append(f"  • {warning}")
            lines.append("")
        
        # Risk Status
        lines.append("🔒 RISK STATUS")
        lines.append("-" * 40)
        risk_approved = recommendation.get("risk_approved", False)
        lines.append(f"Risk Check: {'✅ APPROVED' if risk_approved else '❌ NOT APPROVED'}")
        lines.append("")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def get_beginner_summary(self, recommendation: Dict = None) -> str:
        """Get a simple summary for beginners."""
        if recommendation is None:
            recommendation = self.last_recommendation
        
        if not recommendation:
            return "No recommendation available"
        
        direction = recommendation.get("direction", "NEUTRAL")
        
        if direction == "NEUTRAL":
            return "No clear trade setup. Wait for better conditions."
        
        lines = []
        lines.append(f"💡 BEGINNER SUMMARY")
        lines.append("-" * 40)
        
        if direction == "BUY":
            lines.append(f"BUY {recommendation.get('symbol')} at {recommendation.get('entry_price')}")
            lines.append(f"If it drops to {recommendation.get('stop_loss')}, you're out (small loss).")
            lines.append(f"If it goes up, take profit at {recommendation.get('take_profit_1')}.")
        else:
            lines.append(f"SELL {recommendation.get('symbol')} at {recommendation.get('entry_price')}")
            lines.append(f"If it rises to {recommendation.get('stop_loss')}, you're out (small loss).")
            lines.append(f"If it drops, take profit at {recommendation.get('take_profit_1')}.")
        
        if recommendation.get("risk_amount"):
            lines.append(f"Maximum you can lose: ${recommendation.get('risk_amount')}")
        
        lines.append("")
        lines.append("Reasons:")
        for reason in recommendation.get("reasons", [])[:3]:
            lines.append(f"  • {reason}")
        
        return "\n".join(lines)


SYSTEM_PROMPT = """
You are the Trade Recommendation Agent, the final decision synthesizer. You
receive analysis from Chart, Market, Volume, Correlation, and Risk agents
and produce a clear, actionable trade recommendation.

You score the setup from 0-100 and only recommend trades scoring 70+.

Scoring criteria:
- Chart Analysis: ±25 points (trend, indicators, patterns)
- Market Structure: ±20 points (BOS, CHoCH, FVG)
- Volume Analysis: ±15 points (accumulation/distribution)
- Correlations: ±15 points (DXY, safe haven flows)
- Sentiment: ±15 points (fundamentals)

Grade thresholds:
- A+: 85+ (Strong trade)
- A: 75-84 (Good trade)
- B: 65-74 (Acceptable trade)
- C: 55-64 (Weak trade)
- NO_TRADE: Below 55

Your output includes:
1. Direction (BUY/SELL/NEUTRAL)
2. Confidence score and grade
3. Exact Entry, Stop Loss, Take Profit levels
4. Position size recommendation
5. R:R ratio
6. Key reasons
7. Warnings
8. Beginner-friendly summary

Rules:
- Never recommend a trade that fails risk checks
- Always provide multiple TP levels
- Include clear reasoning
- Be transparent about conflicts
- Default to WAIT when uncertain
"""


if __name__ == "__main__":
    agent = TradeRecommendationAgent()
    print("Trade Recommendation Agent initialized")
