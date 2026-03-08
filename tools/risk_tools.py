"""
Risk Management Tools - Position sizing, R:R, trade viability assessment.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.data_formatter import safe_float


def load_risk_config() -> Dict:
    """Load risk parameters from config file."""
    config_path = Path(__file__).parent.parent / "config" / "risk_parameters.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {
        "max_risk_per_trade_pct": 2.0,
        "max_total_risk_pct": 6.0,
        "max_open_trades": 5,
        "min_risk_reward_ratio": 1.5,
        "default_risk_pct": 1.5
    }


def calculate_position_size(
    account_equity: float,
    risk_percent: float,
    entry_price: float,
    stop_loss_price: float,
    symbol_info: Dict
) -> Dict:
    """
    Calculate optimal position size based on risk parameters.
    
    Args:
        account_equity: Current account equity
        risk_percent: Risk percentage (e.g., 1.5 for 1.5%)
        entry_price: Planned entry price
        stop_loss_price: Stop loss price
        symbol_info: Symbol specifications from MT5
    
    Returns:
        Position sizing details
    """
    config = load_risk_config()
    
    risk_amount = account_equity * (risk_percent / 100)
    stop_distance = abs(entry_price - stop_loss_price)
    
    # Calculate stop in pips/points
    point = symbol_info.get('point', 0.00001)
    digits = symbol_info.get('digits', 5)
    
    # Adjust for 3/5 digit pairs
    pip_multiplier = 10 if digits == 5 or digits == 3 else 1
    stop_pips = stop_distance / point / pip_multiplier
    
    # Pip value (simplified for forex/gold)
    # Gold: $1 per pip per 0.01 lot
    # Forex major: $10 per pip per 1 lot
    tick_value = symbol_info.get('tick_value', 1)
    tick_size = symbol_info.get('tick_size', point)
    contract_size = symbol_info.get('contract_size', 100000)
    
    # Calculate lot size
    pip_value_per_lot = tick_value / tick_size * point * pip_multiplier if tick_size > 0 else 10
    
    if pip_value_per_lot > 0 and stop_pips > 0:
        lot_size = risk_amount / (stop_pips * pip_value_per_lot)
    else:
        lot_size = 0.01
    
    # Constrain to symbol limits
    volume_min = symbol_info.get('volume_min', 0.01)
    volume_max = symbol_info.get('volume_max', 100)
    volume_step = symbol_info.get('volume_step', 0.01)
    
    lot_size = max(volume_min, min(volume_max, lot_size))
    lot_size = round(lot_size / volume_step) * volume_step
    
    # Recalculate actual risk
    actual_risk = lot_size * stop_pips * pip_value_per_lot
    actual_risk_pct = (actual_risk / account_equity) * 100 if account_equity > 0 else 0
    
    return {
        "status": "success",
        "recommended_lot_size": round(lot_size, 2),
        "risk_amount_usd": round(actual_risk, 2),
        "risk_percent_actual": round(actual_risk_pct, 2),
        "risk_percent_requested": risk_percent,
        "stop_distance_pips": round(stop_pips, 1),
        "stop_distance_price": round(stop_distance, 5),
        "entry_price": entry_price,
        "stop_loss": stop_loss_price,
        "account_equity": account_equity,
        "pip_value_per_lot": round(pip_value_per_lot, 2),
        "within_risk_limit": actual_risk_pct <= config['max_risk_per_trade_pct']
    }


def calculate_risk_reward(
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    direction: str = "BUY"
) -> Dict:
    """
    Calculate risk-reward ratio and multiple TP levels.
    
    Args:
        entry_price: Entry price
        stop_loss: Stop loss price
        take_profit: Primary take profit price
        direction: "BUY" or "SELL"
    
    Returns:
        R:R analysis with TP levels
    """
    if take_profit is None:
        return {"status": "error", "message": "No take profit provided", "risk_reward_ratio": 0, "grade": "N/A"}

    if direction == "BUY":
        risk = entry_price - stop_loss
        reward = take_profit - entry_price
    else:
        risk = stop_loss - entry_price
        reward = entry_price - take_profit

    if risk <= 0:
        return {"status": "error", "message": "Invalid stop loss for direction", "risk_reward_ratio": 0, "grade": "N/A"}
    
    rr_ratio = reward / risk if risk > 0 else 0
    breakeven_winrate = (1 / (1 + rr_ratio)) * 100 if rr_ratio > 0 else 100
    
    # Multiple TP levels
    tp_levels = {}
    for r in [1, 1.5, 2, 2.5, 3]:
        if direction == "BUY":
            tp_levels[f"TP_{r}R"] = round(entry_price + (risk * r), 5)
        else:
            tp_levels[f"TP_{r}R"] = round(entry_price - (risk * r), 5)
    
    # Grade the R:R
    if rr_ratio >= 3:
        grade = "EXCELLENT"
    elif rr_ratio >= 2:
        grade = "GOOD"
    elif rr_ratio >= 1.5:
        grade = "ACCEPTABLE"
    elif rr_ratio >= 1:
        grade = "FAIR"
    else:
        grade = "POOR"
    
    return {
        "status": "success",
        "risk_reward_ratio": round(rr_ratio, 2),
        "risk_pips": round(risk * 10000, 1),
        "reward_pips": round(reward * 10000, 1),
        "breakeven_winrate": round(breakeven_winrate, 1),
        "tp_levels": tp_levels,
        "grade": grade,
        "direction": direction,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "meets_minimum": rr_ratio >= 1.5
    }


def assess_trade_viability(
    risk_percent: float,
    rr_ratio: float,
    spread: float,
    atr: float,
    active_trades: int = 0,
    max_trades: int = 5,
    max_total_risk: float = 6.0,
    event_risk: str = "NONE"
) -> Dict:
    """
    Comprehensive trade viability check.
    
    Args:
        risk_percent: Risk percentage for this trade
        rr_ratio: Risk-reward ratio
        spread: Current spread
        atr: ATR value
        active_trades: Number of currently open trades
        max_trades: Maximum allowed open trades
        max_total_risk: Maximum total portfolio risk %
        event_risk: Event risk level (NONE, LOW, HIGH, CRITICAL)
    
    Returns:
        Viability assessment with pass/fail checks
    """
    config = load_risk_config()
    
    max_risk_per_trade = config.get('max_risk_per_trade_pct', 2.0)
    min_rr = config.get('min_risk_reward_ratio', 1.5)
    
    checks = {
        "risk_per_trade": {
            "status": "PASS" if risk_percent <= max_risk_per_trade else "FAIL",
            "value": risk_percent,
            "limit": max_risk_per_trade,
            "message": f"Risk {risk_percent}% is {'within' if risk_percent <= max_risk_per_trade else 'above'} limit of {max_risk_per_trade}%"
        },
        "risk_reward": {
            "status": "PASS" if rr_ratio >= min_rr else "FAIL",
            "value": rr_ratio,
            "limit": min_rr,
            "message": f"R:R of {rr_ratio} is {'acceptable' if rr_ratio >= min_rr else 'below minimum'} of {min_rr}"
        },
        "spread_vs_atr": {
            "status": "PASS" if atr > 0 and spread < atr * 0.15 else "WARNING",
            "value": round(spread / atr * 100, 1) if atr > 0 else 0,
            "limit": 15,
            "message": f"Spread is {round(spread/atr*100,1)}% of ATR" if atr > 0 else "Cannot calculate spread/ATR"
        },
        "max_open_trades": {
            "status": "PASS" if active_trades < max_trades else "FAIL",
            "current": active_trades,
            "limit": max_trades,
            "message": f"{active_trades}/{max_trades} trades open"
        },
        "total_portfolio_risk": {
            "status": "PASS" if (active_trades * risk_percent + risk_percent) <= max_total_risk else "FAIL",
            "projected": round((active_trades + 1) * risk_percent, 1),
            "limit": max_total_risk,
            "message": f"Total risk would be {round((active_trades + 1) * risk_percent, 1)}%"
        },
        "event_risk": {
            "status": "PASS" if event_risk == "NONE" else "WARNING" if event_risk == "LOW" else "FAIL",
            "value": event_risk,
            "message": f"Event risk: {event_risk}"
        }
    }
    
    all_pass = all(c["status"] == "PASS" for c in checks.values())
    has_fail = any(c["status"] == "FAIL" for c in checks.values())
    has_warning = any(c["status"] == "WARNING" for c in checks.values())
    
    if all_pass and not has_warning:
        overall = "APPROVED"
        recommendation = "PROCEED"
    elif has_fail:
        overall = "REJECTED"
        recommendation = "DO_NOT_TRADE"
    else:
        overall = "CAUTION"
        recommendation = "PROCEED_WITH_CAUTION"
    
    return {
        "status": "success",
        "checks": checks,
        "overall": overall,
        "recommendation": recommendation,
        "all_checks_pass": all_pass,
        "has_failures": has_fail,
        "has_warnings": has_warning
    }


def calculate_gold_specific_risk(
    account_equity: float,
    entry_price: float,
    stop_loss: float,
    risk_percent: float = 1.5
) -> Dict:
    """
    Gold-specific position sizing.
    Gold has ~$1/pip per 0.01 lot.
    """
    config = load_risk_config()
    gold_config = config.get('gold_specific', {})
    
    pip_value_per_001_lot = gold_config.get('pip_value_per_001_lot', 1.0)

    risk_amount = account_equity * (risk_percent / 100)
    stop_distance = abs(entry_price - stop_loss)  # In price units ($)

    # Dollar value per full lot per $1 move: pip_value_per_001_lot / 0.01
    # e.g. $1/pip per 0.01 lot → $100 per lot per $1 move
    dollar_per_lot = pip_value_per_001_lot / 0.01

    lot_size = risk_amount / (stop_distance * dollar_per_lot) if stop_distance > 0 else 0.01
    lot_size = max(0.01, round(lot_size, 2))

    actual_risk = lot_size * stop_distance * dollar_per_lot

    return {
        "status": "success",
        "symbol": "XAUUSD",
        "lot_size": lot_size,
        "stop_pips": round(stop_distance * 100, 1),
        "risk_usd": round(actual_risk, 2),
        "risk_percent": round((actual_risk / account_equity) * 100, 2),
        "pip_value": pip_value_per_001_lot,
        "entry": entry_price,
        "stop_loss": stop_loss
    }


def calculate_drawdown_metrics(equity_curve: List[float]) -> Dict:
    """
    Calculate drawdown metrics from equity curve.
    """
    if len(equity_curve) < 2:
        return {"status": "error", "message": "Need at least 2 equity points"}
    
    peak = equity_curve[0]
    max_dd = 0
    current_dd = 0
    dd_duration = 0
    max_dd_duration = 0
    
    for i, eq in enumerate(equity_curve):
        if eq > peak:
            peak = eq
            dd_duration = 0
        else:
            dd = (peak - eq) / peak * 100 if peak > 0 else 0
            current_dd = dd
            max_dd = max(max_dd, dd)
            dd_duration += 1
            max_dd_duration = max(max_dd_duration, dd_duration)
    
    return {
        "status": "success",
        "max_drawdown_pct": round(max_dd, 2),
        "current_drawdown_pct": round(current_dd, 2),
        "max_drawdown_duration": max_dd_duration,
        "current_equity": equity_curve[-1],
        "peak_equity": peak,
        "from_peak_pct": round((peak - equity_curve[-1]) / peak * 100, 2) if peak > 0 else 0
    }
