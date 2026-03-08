"""
Risk Management Agent - Position sizing, R:R, trade viability.
"""
import json
from typing import Dict, List
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.risk_tools import (
    calculate_position_size,
    calculate_risk_reward,
    assess_trade_viability,
    calculate_gold_specific_risk,
    load_risk_config
)
from utils.logger import get_logger

logger = get_logger("risk_management_agent")


class RiskManagementAgent:
    """
    Agent for risk management and trade viability assessment.
    
    Responsibilities:
    - Calculate optimal position sizes
    - Assess risk-reward ratios
    - Check trade viability against risk rules
    - Manage portfolio risk exposure
    - Enforce risk limits
    """
    
    def __init__(self):
        self.config = load_risk_config()
        self.last_assessment = None
    
    def assess_trade(
        self,
        account_equity: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        direction: str,
        symbol_info: Dict,
        active_trades: int = 0,
        event_risk: str = "NONE",
        risk_percent: float = None
    ) -> Dict:
        """
        Complete trade risk assessment.
        
        Args:
            account_equity: Current account equity
            entry_price: Planned entry
            stop_loss: Stop loss price
            take_profit: Take profit price
            direction: BUY or SELL
            symbol_info: Symbol specifications
            active_trades: Number of open positions
            event_risk: NONE, LOW, HIGH, CRITICAL
            risk_percent: Desired risk percentage
        
        Returns:
            Complete risk assessment with position sizing
        """
        if risk_percent is None:
            risk_percent = self.config.get("default_risk_pct", 1.5)
        
        logger.info(f"Assessing trade risk: {direction} @ {entry_price}")
        
        # Position sizing
        if symbol_info.get("symbol", "").startswith("XAU"):
            # Gold-specific calculation
            sizing = calculate_gold_specific_risk(
                account_equity, entry_price, stop_loss, risk_percent
            )
        else:
            sizing = calculate_position_size(
                account_equity, risk_percent, entry_price, stop_loss, symbol_info
            )
        
        # R:R calculation
        rr = calculate_risk_reward(entry_price, stop_loss, take_profit, direction)
        
        # Spread (estimate)
        spread = symbol_info.get("spread", 0) * symbol_info.get("point", 0.00001)
        atr = abs(entry_price - stop_loss) / 1.5  # Estimate ATR from SL
        
        # Viability check
        viability = assess_trade_viability(
            risk_percent=sizing.get("risk_percent_actual", sizing.get("risk_percent", risk_percent)),
            rr_ratio=rr.get("risk_reward_ratio", 0),
            spread=spread,
            atr=atr,
            active_trades=active_trades,
            max_trades=self.config.get("max_open_trades", 5),
            max_total_risk=self.config.get("max_total_risk_pct", 6.0),
            event_risk=event_risk
        )
        
        is_gold = symbol_info.get("symbol", "").startswith("XAU")
        assessment = {
            "status": "success",
            "direction": direction,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "position_sizing": sizing,
            "risk_reward": rr,
            "viability": viability,
            "overall": viability.get("overall"),
            "recommendation": viability.get("recommendation"),
            "risk_approved": viability.get("overall") in ["APPROVED", "CAUTION"],
            "account_equity": account_equity,
            "risk_amount_usd": sizing.get("risk_usd") if is_gold else sizing.get("risk_amount_usd"),
            "lot_size": sizing.get("lot_size") if is_gold else sizing.get("recommended_lot_size"),
            "event_risk": event_risk
        }
        
        self.last_assessment = assessment
        return assessment
    
    def check_portfolio_risk(self, account_equity: float, 
                             open_positions: List[Dict]) -> Dict:
        """
        Check total portfolio risk exposure.
        
        Args:
            account_equity: Current equity
            open_positions: List of open positions
        
        Returns:
            Portfolio risk summary
        """
        total_risk = 0
        position_risks = []
        
        for pos in open_positions:
            if pos.get("sl", 0) > 0:
                sl_distance = abs(pos.get("current_price", 0) - pos.get("sl", 0))
                # Approximate risk
                risk = sl_distance * pos.get("volume", 0) * 100
                total_risk += risk
                position_risks.append({
                    "symbol": pos.get("symbol"),
                    "risk_usd": round(risk, 2)
                })
        
        risk_pct = (total_risk / account_equity) * 100 if account_equity > 0 else 0
        max_risk = self.config.get("max_total_risk_pct", 6.0)
        
        return {
            "total_risk_usd": round(total_risk, 2),
            "total_risk_pct": round(risk_pct, 2),
            "max_allowed_pct": max_risk,
            "within_limit": risk_pct <= max_risk,
            "position_count": len(open_positions),
            "position_risks": position_risks,
            "available_risk_pct": round(max_risk - risk_pct, 2)
        }
    
    def get_summary(self, assessment: Dict = None) -> str:
        """Get text summary."""
        if assessment is None:
            assessment = self.last_assessment
        
        if not assessment:
            return "No assessment available"
        
        lines = []
        lines.append("RISK ASSESSMENT")
        lines.append("-" * 40)
        lines.append(f"Direction: {assessment.get('direction')}")
        lines.append(f"Entry: {assessment.get('entry_price')} | SL: {assessment.get('stop_loss')} | TP: {assessment.get('take_profit')}")
        lines.append("")
        lines.append(f"Lot Size: {assessment.get('lot_size')}")
        lines.append(f"Risk: ${assessment.get('risk_amount_usd')}")
        lines.append(f"R:R Ratio: {assessment.get('risk_reward', {}).get('risk_reward_ratio')} ({assessment.get('risk_reward', {}).get('grade')})")
        lines.append("")
        lines.append(f"Overall: {assessment.get('overall')}")
        lines.append(f"Recommendation: {assessment.get('recommendation')}")
        
        return "\n".join(lines)


SYSTEM_PROMPT = """
You are the Risk Management Agent, a disciplined risk manager. You calculate
optimal position sizes, risk-reward ratios, stop loss and take profit levels,
maximum drawdown exposure, and assess whether a trade meets risk criteria.

You NEVER compromise on risk rules. Capital preservation is your #1 priority.

Default risk per trade: 1-2% of account equity.
Maximum total portfolio risk: 6%
Minimum risk-reward ratio: 1.5

Your rules:
1. Never risk more than 2% per trade
2. Reject trades with R:R below 1.5
3. Limit total open positions to 5
4. Avoid trading during high-impact events (NFP, CPI, FOMC)
5. Adjust position size to match risk percentage exactly
6. Always account for spread costs

Gold-specific considerations:
- Gold pip value: ~$1/pip per 0.01 lot
- Gold can move $50-100 on event days
- Gold spreads widen during news

You output:
- Recommended lot size
- Risk amount in USD
- R:R ratio with grade
- APPROVED/CAUTION/REJECTED status
"""


if __name__ == "__main__":
    agent = RiskManagementAgent()
    
    # Test assessment
    result = agent.assess_trade(
        account_equity=10000,
        entry_price=2650,
        stop_loss=2630,
        take_profit=2690,
        direction="BUY",
        symbol_info={"symbol": "XAUUSDm", "point": 0.01, "digits": 2, "spread": 25},
        active_trades=1,
        event_risk="NONE"
    )
    
    print(agent.get_summary(result))
