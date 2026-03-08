# -*- coding: utf-8 -*-
"""
Unified Trade Executor — ICT Multi-Agent Scan Processor
========================================================
Reads 21 scan JSONs (3 different formats), normalises them into a unified
schema, re-analyses top candidates with live MT5 data, executes qualified
trades, and enters a monitoring loop.

Author: Claude Code  |  Session: trading_20260305_194417
"""

import sys
import os
import json
import time
import glob
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ──────────────────────────────────────────────────────────────────────────────
# 0. ENCODING & PATH SETUP
# ──────────────────────────────────────────────────────────────────────────────
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Project root (mt5-gold-trading-system)
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import MetaTrader5 as mt5

# Import tools library
try:
    from tools.mt5_tools import (
        initialize_mt5,
        fetch_ohlcv_data,
        fetch_tick_data,
        get_account_info,
        get_open_positions,
    )
    from tools.structure_tools import analyze_market_structure
    from tools.indicator_tools import calculate_all_indicators

    TOOLS_AVAILABLE = True
except ImportError as _tools_err:
    TOOLS_AVAILABLE = False
    print(
        f"[WARN] tools library import failed: {_tools_err} — will use raw MT5 API only"
    )


# ──────────────────────────────────────────────────────────────────────────────
# 1. CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────
SESSION_DIR = Path(
    r"C:\Users\Mamoud\Desktop\Claude-Skills-Collection\sessions\trading_20260305_194417"
)
SCANS_DIR = SESSION_DIR / "scans"
TRADES_DIR = SESSION_DIR / "trades"
DASHBOARD_FILE = SESSION_DIR / "dashboard" / "live_data.json"
TRADE_LOG_FILE = TRADES_DIR / "trade_log.json"

MAX_LOT = 0.1  # Hard limit per position
HALF_LOT = 0.05
MAX_POSITIONS = 5  # Maximum concurrent positions
MAX_DAILY_LOSS_PCT = 3.0  # Close all at -3 %
MIN_SCORE = 5  # Below this → no trade
FULL_RISK_SCORE = 8  # At/above → 0.1 lot
MIN_RR = 1.5  # Minimum risk:reward ratio
MAGIC_NUMBER = 202603  # Our trades only
MONITOR_INTERVAL = 30  # seconds

# Symbols that already have open positions (not ours — different magic)
LEGACY_POSITIONS = {"AMZNm", "MSFTm"}

# Category detection helpers
FOREX_CURRENCIES = {"EUR", "GBP", "USD", "AUD", "NZD", "CHF", "CAD", "JPY"}
INDEX_SYMBOLS = {"USTEC", "US30", "US500"}
CRYPTO_SYMBOLS = {"BTC", "ETH"}


# ──────────────────────────────────────────────────────────────────────────────
# 2. LOGGING
# ──────────────────────────────────────────────────────────────────────────────
def log(msg: str, level: str = "INFO") -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    tag = {
        "INFO": "·",
        "OK": "✓",
        "WARN": "!",
        "ERR": "✗",
        "TRADE": "▶",
        "MON": "⟳",
    }.get(level, "·")
    print(f"[{ts}] {tag} {msg}", flush=True)


def log_section(title: str) -> None:
    print(f"\n{'═' * 70}\n  {title}\n{'═' * 70}", flush=True)


# ──────────────────────────────────────────────────────────────────────────────
# 3. SCAN NORMALISER  (handles all 3 agent formats)
# ──────────────────────────────────────────────────────────────────────────────


def _get_price(raw: dict) -> float:
    """Extract a usable float price from any scan format."""
    cp = raw.get("current_price", 0)
    if isinstance(cp, dict):
        return float(cp.get("bid", cp.get("ask", 0)))
    return float(cp or 0)


def _extract_structure_flags(struct: dict) -> Tuple[bool, bool, bool, bool, bool]:
    """Return (has_bos, has_choch, has_fvg, has_ob, has_liquidity_sweep)."""
    bos = bool(struct.get("bos_events"))
    choch = bool(struct.get("choch_events"))
    fvg = any(
        not (f.get("filled") in (True, "True"))
        for f in struct.get("fair_value_gaps", [])
    )
    ob = bool(struct.get("order_blocks"))
    liq = any(
        lv.get("swept") in (True, "True") for lv in struct.get("liquidity_levels", [])
    )
    return bos, choch, fvg, ob, liq


def _best_structure(scan_data: dict) -> dict:
    """Pick the most useful structure block from a scan."""
    # Format 1: market_structure (H1) + h4_structure
    if "h4_structure" in scan_data:
        return scan_data["h4_structure"]
    # Format 2: timeframe_analysis.D1
    if "timeframe_analysis" in scan_data:
        tf = scan_data["timeframe_analysis"]
        return tf.get("D1", tf.get("H4", {}))
    # Format 3: analysis.D1
    if "analysis" in scan_data:
        an = scan_data["analysis"]
        return an.get("D1", an.get("H4", {}))
    # Format 1 fallback: market_structure
    return scan_data.get("market_structure", {})


def _best_atr(scan_data: dict) -> float:
    """Extract ATR (D1 preferred) from any scan format."""
    # Format 3: confluence_score.atr_d1
    cs = scan_data.get("confluence_score", {})
    if isinstance(cs, dict) and cs.get("atr_d1"):
        return float(cs["atr_d1"])
    # Format 1: indicators.atr.value
    ind = scan_data.get("indicators", {})
    if isinstance(ind, dict):
        atr_block = ind.get("atr", {})
        if isinstance(atr_block, dict):
            return float(atr_block.get("value", 0) or 0)
    # Format 2 / 3: timeframe_analysis/analysis D1 indicators
    for key in ("timeframe_analysis", "analysis"):
        section = scan_data.get(key, {})
        if isinstance(section, dict):
            d1 = section.get("D1", {})
            if isinstance(d1, dict):
                atr_block = d1.get("atr", {})
                if isinstance(atr_block, dict):
                    val = atr_block.get("value", 0)
                    if val:
                        return float(val)
                ind2 = d1.get("indicators", {})
                if isinstance(ind2, dict):
                    atr_block = ind2.get("atr", {})
                    if isinstance(atr_block, dict):
                        val = atr_block.get("value", 0)
                        if val:
                            return float(val)
    return 0.0


def _best_sl_tp(scan_data: dict) -> Tuple[float, float]:
    """Extract pre-calculated SL/TP if available (Format 3 stocks)."""
    cs = scan_data.get("confluence_score", {})
    if isinstance(cs, dict):
        sl = cs.get("sl", 0)
        tp = cs.get("tp1", cs.get("tp", 0))
        return float(sl or 0), float(tp or 0)
    return 0.0, 0.0


def _determine_direction(scan_data: dict) -> str:
    """Resolve trade direction from any format to BUY / SELL / NEUTRAL."""
    cs = scan_data.get("confluence_score", {})
    if isinstance(cs, dict):
        # Format 2: confluence_score.direction → "SELL"
        d = cs.get("direction", "")
        if d in ("BUY", "SELL"):
            return d
        # Format 3: setup_direction
        d = cs.get("setup_direction", "")
        if d in ("BUY", "SELL"):
            return d
        # Format 3: htf_bias BEARISH → SELL
        htf = cs.get("htf_bias", "")
        if htf == "BEARISH":
            return "SELL"
        if htf == "BULLISH":
            return "BUY"
    # Format 1: mtf_trends.dominant_direction
    mtf = scan_data.get("mtf_trends", {})
    if isinstance(mtf, dict):
        dom = mtf.get("dominant_direction", "")
        if dom == "BEARISH":
            return "SELL"
        if dom == "BULLISH":
            return "BUY"
    # Format 2: confluence_score.htf_bias
    htf = scan_data.get("confluence_score", {})
    if isinstance(htf, dict):
        bias = htf.get("htf_bias", "")
        if bias == "BEARISH":
            return "SELL"
        if bias == "BULLISH":
            return "BUY"
    return "NEUTRAL"


def normalise_scan(raw: dict) -> Optional[dict]:
    """
    Convert any of the 3 scan formats into the unified schema:
    {
      symbol, score, direction, htf_bias,
      has_bos, has_choch, has_fvg, has_ob, has_liquidity_sweep,
      sl, tp, atr, current_price,
      hard_htf, hard_liquidity, hard_mss,   ← hard requirement flags
      scan_format,                           ← "F1" / "F2" / "F3"
    }
    Returns None if the scan is structurally invalid.
    """
    symbol = raw.get("symbol", "")
    if not symbol:
        return None

    current_price = _get_price(raw)

    # ── Detect format ──
    if "mtf_trends" in raw:
        fmt = "F1"
    elif "agent" in raw and "timeframe_analysis" in raw:
        fmt = "F2"
    elif "asset_class" in raw and "analysis" in raw:
        fmt = "F3"
    else:
        # Fallback: try to handle gracefully
        fmt = "F1"

    # ── Score ──
    cs = raw.get("confluence_score", {})
    if isinstance(cs, int):
        score = cs
        htf_bias = "UNKNOWN"
        hard_htf = False
        hard_liq = False
        hard_mss = False
    elif isinstance(cs, dict):
        score = int(cs.get("score", 0))
        htf_bias = cs.get("htf_bias", cs.get("direction", "UNKNOWN"))
        # Hard requirements from score breakdown / factors
        hr = cs.get("hard_requirements", {})
        factors = cs.get("factors", {})
        breakdown = cs.get("score_breakdown", {})
        hard_htf = bool(
            hr.get("htf_bias")
            or factors.get("htf_aligned", False)
            or breakdown.get("htf_bias_alignment", 0) >= 2
        )
        hard_liq = bool(
            hr.get("liquidity")
            or factors.get("liquidity_swept", False)
            or breakdown.get("liquidity_sweep", 0) >= 2
        )
        hard_mss = bool(
            hr.get("mss")
            or factors.get("mss_confirmed", False)
            or breakdown.get("mss_choch", 0) >= 2
        )
    else:
        score = 0
        htf_bias = "UNKNOWN"
        hard_htf = False
        hard_liq = False
        hard_mss = False

    direction = _determine_direction(raw)

    # ── Structure flags (check ALL timeframes, not just the "best" one) ──
    struct = _best_structure(raw)
    has_bos, has_choch, has_fvg, has_ob, has_liquidity_sweep = _extract_structure_flags(
        struct
    )

    # Also scan ALL timeframe blocks for swept liquidity (many scans have it in H4/H1)
    for tf_key in ("timeframe_analysis", "analysis"):
        tf_section = raw.get(tf_key, {})
        if isinstance(tf_section, dict):
            for tf_name, tf_data in tf_section.items():
                if isinstance(tf_data, dict):
                    for lv in tf_data.get("liquidity_levels", []):
                        if lv.get("swept") in (True, "True"):
                            has_liquidity_sweep = True
                            break
    # Format 1: check market_structure and h4_structure directly
    for struct_key in ("market_structure", "h4_structure"):
        s = raw.get(struct_key, {})
        if isinstance(s, dict):
            for lv in s.get("liquidity_levels", []):
                if lv.get("swept") in (True, "True"):
                    has_liquidity_sweep = True
                    break

    # ── Pre-calculated levels ──
    sl_pre, tp_pre = _best_sl_tp(raw)

    # ── ATR ──
    atr = _best_atr(raw)

    return {
        "symbol": symbol,
        "score": score,
        "direction": direction,
        "htf_bias": htf_bias,
        "has_bos": has_bos,
        "has_choch": has_choch,
        "has_fvg": has_fvg,
        "has_ob": has_ob,
        "has_liquidity_sweep": has_liquidity_sweep,
        "sl": sl_pre,
        "tp": tp_pre,
        "atr": atr,
        "current_price": current_price,
        "hard_htf": hard_htf,
        "hard_liquidity": hard_liq,
        "hard_mss": hard_mss,
        "scan_format": fmt,
        "_raw": raw,  # keep original for dashboard
    }


# ──────────────────────────────────────────────────────────────────────────────
# 4. FRESH RE-ANALYSIS
# ──────────────────────────────────────────────────────────────────────────────


def _ohlcv_to_list(result: dict) -> List[dict]:
    """Convert fetch_ohlcv_data result to list of dicts for tools."""
    if result.get("status") != "success":
        return []
    data = result.get("data", [])
    if isinstance(data, list):
        return data
    return []


def _score_structure(struct: dict, direction: str) -> int:
    """
    Re-score a fresh market structure analysis.
    Returns points: bos=2, choch=2, fvg=1, ob=1, liq=2  → max 8.
    """
    points = 0
    bos_events = struct.get("bos_events", [])
    choch_events = struct.get("choch_events", [])
    fvg_list = struct.get("fair_value_gaps", [])
    ob_list = struct.get("order_blocks", [])
    liq_list = struct.get("liquidity_levels", [])

    if direction == "SELL":
        if any("BEARISH" in e.get("type", "") for e in bos_events):
            points += 2
        if any("BEARISH" in e.get("type", "") for e in choch_events):
            points += 2
        if any(
            "BEARISH" in f.get("type", "") and not (f.get("filled") in (True, "True"))
            for f in fvg_list
        ):
            points += 1
        if any(
            "BEARISH" in o.get("type", "") and not (o.get("tested") in (True, "True"))
            for o in ob_list
        ):
            points += 1
        if any(lv.get("swept") in (True, "True") for lv in liq_list):
            points += 2
    else:  # BUY
        if any("BULLISH" in e.get("type", "") for e in bos_events):
            points += 2
        if any("BULLISH" in e.get("type", "") for e in choch_events):
            points += 2
        if any(
            "BULLISH" in f.get("type", "") and not (f.get("filled") in (True, "True"))
            for f in fvg_list
        ):
            points += 1
        if any(
            "BULLISH" in o.get("type", "") and not (o.get("tested") in (True, "True"))
            for o in ob_list
        ):
            points += 1
        if any(lv.get("swept") in (True, "True") for lv in liq_list):
            points += 2

    return points


def _score_indicators(ind: dict, direction: str) -> int:
    """
    Score indicator alignment.
    Returns points: htf_bias=2, macd=1, rsi=1  → max 4.
    """
    points = 0
    # HTF bias from MA alignment (already baked into direction for re-analysis — give 2 if consistent)
    ma = ind.get("moving_averages", {})
    if direction == "SELL":
        if ma.get("price_vs_sma200") == "BELOW":
            points += 1
        if ma.get("sma_cross") == "DEATH_CROSS":
            points += 1
        macd = ind.get("macd", {})
        if isinstance(macd, dict) and macd.get("crossover") == "BEARISH":
            points += 1
        rsi = ind.get("rsi", {})
        if isinstance(rsi, dict) and rsi.get("value", 50) < 50:
            points += 1
    else:
        if ma.get("price_vs_sma200") == "ABOVE":
            points += 1
        if ma.get("sma_cross") == "GOLDEN_CROSS":
            points += 1
        macd = ind.get("macd", {})
        if isinstance(macd, dict) and macd.get("crossover") == "BULLISH":
            points += 1
        rsi = ind.get("rsi", {})
        if isinstance(rsi, dict) and rsi.get("value", 50) > 50:
            points += 1

    return points


def re_analyse_candidate(unified: dict) -> dict:
    """
    Fetch live H4 + D1 data, re-run structure & indicator analysis,
    recalculate confluence score.

    Returns updated `unified` dict with fresh fields:
      fresh_score, fresh_atr, fresh_struct_d1, fresh_struct_h4,
      fresh_indicators, re_analysis_ok
    """
    symbol = unified["symbol"]
    direction = unified["direction"]

    log(f"  Re-analysing {symbol} ({direction}) …")

    result = dict(unified)
    result["re_analysis_ok"] = False

    try:
        # Fetch D1 data (500 bars for full indicators)
        d1_raw = (
            fetch_ohlcv_data(symbol, "D1", 500)
            if TOOLS_AVAILABLE
            else {"status": "error"}
        )
        h4_raw = (
            fetch_ohlcv_data(symbol, "H4", 300)
            if TOOLS_AVAILABLE
            else {"status": "error"}
        )

        d1_data = _ohlcv_to_list(d1_raw)
        h4_data = _ohlcv_to_list(h4_raw)

        if not d1_data and not h4_data:
            log(f"    {symbol}: no data from MT5", "WARN")
            return result

        # Structure analysis
        struct_d1 = (
            analyze_market_structure(d1_data) if d1_data and TOOLS_AVAILABLE else {}
        )
        struct_h4 = (
            analyze_market_structure(h4_data) if h4_data and TOOLS_AVAILABLE else {}
        )

        # Indicator analysis (prefer D1 for trend, H4 for entry)
        indicators = (
            calculate_all_indicators(d1_data) if d1_data and TOOLS_AVAILABLE else {}
        )

        # ATR — prefer live D1 ATR
        fresh_atr = 0.0
        if isinstance(indicators, dict) and indicators.get("status") == "success":
            atr_block = indicators.get("atr", {})
            fresh_atr = float(atr_block.get("value", 0) or 0)
        if not fresh_atr:
            fresh_atr = unified.get("atr", 0.0)

        # Re-score: structure (max 8) + indicators (max 4) = max 12
        struct_points = _score_structure(struct_d1, direction)
        # Bonus for H4 confirming
        h4_struct_pts = _score_structure(struct_h4, direction)
        struct_points = min(8, struct_points + (1 if h4_struct_pts >= 4 else 0))

        ind_points = _score_indicators(indicators, direction) if indicators else 0

        # Killzone bonus: NY session is active (12-21 UTC) — relaxed
        utc_hour = datetime.now(tz=timezone.utc).hour
        in_ny_session = 12 <= utc_hour < 21
        kz_bonus = 1 if in_ny_session else 0

        fresh_score = min(12, struct_points + ind_points + kz_bonus)

        result.update(
            {
                "fresh_score": fresh_score,
                "fresh_atr": fresh_atr,
                "fresh_struct_d1": struct_d1,
                "fresh_struct_h4": struct_h4,
                "fresh_indicators": indicators,
                "re_analysis_ok": True,
                # Update flags from fresh structure
                "has_bos": bool(
                    struct_d1.get("bos_events") or struct_h4.get("bos_events")
                ),
                "has_choch": bool(
                    struct_d1.get("choch_events") or struct_h4.get("choch_events")
                ),
                "has_fvg": bool(
                    struct_d1.get("fair_value_gaps") or struct_h4.get("fair_value_gaps")
                ),
                "has_ob": bool(
                    struct_d1.get("order_blocks") or struct_h4.get("order_blocks")
                ),
                "has_liquidity_sweep": any(
                    lv.get("swept") in (True, "True")
                    for lv in struct_d1.get("liquidity_levels", [])
                    + struct_h4.get("liquidity_levels", [])
                ),
            }
        )
        log(
            f"    {symbol}: fresh score = {fresh_score}/12 (struct={struct_points}, ind={ind_points}, kz={kz_bonus})",
            "OK",
        )

    except Exception as exc:
        log(f"    {symbol}: re-analysis error — {exc}", "ERR")
        traceback.print_exc()

    return result


# ──────────────────────────────────────────────────────────────────────────────
# 5. ENTRY / SL / TP CALCULATION
# ──────────────────────────────────────────────────────────────────────────────


def _nearest_unfilled_fvg(
    fvgs: List[dict], direction: str, current_price: float
) -> Optional[float]:
    """
    For SELL: find nearest unfilled BEARISH FVG bottom that is above current price.
    For BUY:  find nearest unfilled BULLISH FVG top that is below current price.
    """
    targets = []
    for fvg in fvgs:
        if fvg.get("filled") in (True, "True"):
            continue
        if direction == "SELL" and "BEARISH" in fvg.get("type", ""):
            lvl = float(fvg.get("bottom", 0))
            if lvl < current_price:  # TP is below entry for SELL
                targets.append(lvl)
        elif direction == "BUY" and "BULLISH" in fvg.get("type", ""):
            lvl = float(fvg.get("top", 0))
            if lvl > current_price:  # TP is above entry for BUY
                targets.append(lvl)
    if not targets:
        return None
    # Nearest to current price
    return min(targets, key=lambda x: abs(x - current_price))


def _nearest_ob_level(
    obs: List[dict], direction: str, current_price: float
) -> Optional[float]:
    """
    For SELL: find nearest untested BEARISH OB top above current price (use as SL).
    For BUY:  find nearest untested BULLISH OB bottom below current price (use as SL).
    """
    targets = []
    for ob in obs:
        tested = ob.get("tested") in (True, "True")
        if direction == "SELL" and "BEARISH" in ob.get("type", "") and not tested:
            lvl = float(ob.get("top", 0))
            if lvl > current_price:
                targets.append(lvl)
        elif direction == "BUY" and "BULLISH" in ob.get("type", "") and not tested:
            lvl = float(ob.get("bottom", 0))
            if lvl < current_price:
                targets.append(lvl)
    if not targets:
        return None
    return min(targets, key=lambda x: abs(x - current_price))


def calculate_entry_sl_tp(
    unified: dict,
    tick_bid: float,
    tick_ask: float,
    digits: int,
) -> Tuple[float, float, float, float]:
    """
    Calculate entry, SL, TP and lot size.

    SL/TP rules:
      SELL:
        entry  = bid
        SL     = nearest untested BEARISH OB top + 0.5*ATR, or entry + 1.5*ATR
        TP     = nearest unfilled BEARISH FVG bottom, or entry - 2.5*ATR
      BUY:
        entry  = ask
        SL     = nearest untested BULLISH OB bottom - 0.5*ATR, or entry - 1.5*ATR
        TP     = nearest unfilled BULLISH FVG top, or entry + 2.5*ATR

    Minimum R:R = 1.5 (returns (0,0,0,0) if not met).
    Returns: (entry, sl, tp, lot)
    """
    direction = unified["direction"]
    current_price = tick_bid if direction == "SELL" else tick_ask
    entry = current_price

    score = unified.get("fresh_score", unified.get("score", 0))
    atr = unified.get("fresh_atr", unified.get("atr", 0.0))
    if not atr or atr <= 0:
        atr = current_price * 0.005  # 0.5% fallback

    # Gather fresh structures for level picking
    struct_d1 = unified.get("fresh_struct_d1", {})
    struct_h4 = unified.get("fresh_struct_h4", {})

    # Use pre-computed levels from Format-3 scans if re-analysis wasn't run
    if unified.get("sl") and unified.get("tp") and not unified.get("re_analysis_ok"):
        sl_pre = float(unified["sl"])
        tp_pre = float(unified["tp"])
        sl_dist = abs(entry - sl_pre)
        tp_dist = abs(entry - tp_pre)
        rr = tp_dist / sl_dist if sl_dist > 0 else 0
        if rr >= MIN_RR:
            lot = MAX_LOT if score >= FULL_RISK_SCORE else HALF_LOT
            return (
                round(entry, digits),
                round(sl_pre, digits),
                round(tp_pre, digits),
                lot,
            )

    # Merge FVGs / OBs from both timeframes
    all_fvgs = struct_d1.get("fair_value_gaps", []) + struct_h4.get(
        "fair_value_gaps", []
    )
    all_obs = struct_d1.get("order_blocks", []) + struct_h4.get("order_blocks", [])

    if direction == "SELL":
        ob_top = _nearest_ob_level(all_obs, "SELL", entry)
        sl = ob_top + 0.5 * atr if ob_top else entry + 1.5 * atr

        fvg_bottom = _nearest_unfilled_fvg(all_fvgs, "SELL", entry)
        tp = fvg_bottom if fvg_bottom else entry - 2.5 * atr
    else:  # BUY
        ob_bot = _nearest_ob_level(all_obs, "BUY", entry)
        sl = ob_bot - 0.5 * atr if ob_bot else entry - 1.5 * atr

        fvg_top = _nearest_unfilled_fvg(all_fvgs, "BUY", entry)
        tp = fvg_top if fvg_top else entry + 2.5 * atr

    # Validate SL/TP direction
    if direction == "SELL":
        if sl <= entry or tp >= entry:
            sl = entry + 1.5 * atr
            tp = entry - 2.5 * atr
    else:
        if sl >= entry or tp <= entry:
            sl = entry - 1.5 * atr
            tp = entry + 2.5 * atr

    sl_dist = abs(entry - sl)
    tp_dist = abs(entry - tp)
    rr = tp_dist / sl_dist if sl_dist > 0 else 0

    if rr < MIN_RR:
        log(f"    R:R = {rr:.2f} < {MIN_RR} — skipping {unified['symbol']}", "WARN")
        return 0.0, 0.0, 0.0, 0.0

    lot = MAX_LOT if score >= FULL_RISK_SCORE else HALF_LOT
    return (
        round(entry, digits),
        round(sl, digits),
        round(tp, digits),
        lot,
    )


# ──────────────────────────────────────────────────────────────────────────────
# 6. TRADE EXECUTION
# ──────────────────────────────────────────────────────────────────────────────


def execute_trade(
    unified: dict, lot: float, sl: float, tp: float, entry: float
) -> Optional[dict]:
    """
    Send a market order via MT5 API.
    Returns a trade-record dict on success, None on failure.
    """
    symbol = unified["symbol"]
    direction = unified["direction"]
    score = unified.get("fresh_score", unified.get("score", 0))

    if not mt5.symbol_select(symbol, True):
        log(f"  {symbol}: symbol_select failed", "ERR")
        return None

    sym_info = mt5.symbol_info(symbol)
    if not sym_info:
        log(f"  {symbol}: no symbol info", "ERR")
        return None

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        log(f"  {symbol}: no tick data", "ERR")
        return None

    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
    price = tick.ask if direction == "BUY" else tick.bid

    # Clamp lot to broker limits
    lot = min(lot, MAX_LOT, sym_info.volume_max)
    lot = max(lot, sym_info.volume_min)
    # Round to volume_step
    step = sym_info.volume_step
    lot = round(round(lot / step) * step, 8)

    comment = f"ICT_UX_s{score}"

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 30,
        "magic": MAGIC_NUMBER,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)

    if result is None:
        log(f"  {symbol}: order_send returned None — {mt5.last_error()}", "ERR")
        return None

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        log(f"  {symbol}: REJECTED — {result.comment} (code {result.retcode})", "ERR")
        return None

    digits = sym_info.digits
    log(
        f"  {symbol} {direction} {lot} lot @ {round(price, digits)} | "
        f"SL:{round(sl, digits)} TP:{round(tp, digits)} | Ticket:{result.order}",
        "TRADE",
    )

    return {
        "ticket": result.order,
        "symbol": symbol,
        "direction": direction,
        "volume": lot,
        "entry": round(price, digits),
        "sl": round(sl, digits),
        "tp": round(tp, digits),
        "score": score,
        "comment": comment,
        "timestamp": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
    }


# ──────────────────────────────────────────────────────────────────────────────
# 7. ACCOUNT & POSITION HELPERS
# ──────────────────────────────────────────────────────────────────────────────


def get_account_status() -> Tuple[Optional[dict], List[dict]]:
    """Returns (account_dict, positions_list) directly from MT5 API."""
    info = mt5.account_info()
    if not info:
        return None, []

    account = {
        "balance": round(info.balance, 2),
        "equity": round(info.equity, 2),
        "margin": round(info.margin, 2),
        "free_margin": round(info.margin_free, 2),
        "margin_level": round(info.margin_level, 2) if info.margin_level > 0 else 0.0,
        "profit": round(info.equity - info.balance, 2),
        "daily_pnl": round(info.equity - info.balance, 2),
        "daily_pnl_pct": round((info.equity - info.balance) / info.balance * 100, 6)
        if info.balance
        else 0.0,
    }

    positions_raw = mt5.positions_get()
    positions = []

    if positions_raw:
        for p in positions_raw:
            sym_info = mt5.symbol_info(p.symbol)
            point = sym_info.point if sym_info else 0.0001
            digits = sym_info.digits if sym_info else 5
            raw_diff = (
                (p.price_current - p.price_open)
                if p.type == 0
                else (p.price_open - p.price_current)
            )
            pips = round(raw_diff / point) if point else 0
            sl_d = abs(p.price_open - p.sl) if p.sl else 0
            r_mul = round(raw_diff / sl_d, 2) if sl_d > 0 else 0.0

            positions.append(
                {
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "type": "BUY" if p.type == 0 else "SELL",
                    "volume": round(p.volume, 2),
                    "price_open": round(p.price_open, digits),
                    "price_current": round(p.price_current, digits),
                    "sl": round(p.sl, digits) if p.sl else None,
                    "tp": round(p.tp, digits) if p.tp else None,
                    "profit": round(p.profit, 2),
                    "pips": pips,
                    "r_multiple": r_mul,
                    "time_open": datetime.fromtimestamp(p.time, tz=timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "comment": p.comment or "",
                    "magic": p.magic,
                }
            )

    return account, positions


def close_position(pos: dict) -> bool:
    """Market-close a position. Returns True on success."""
    symbol = pos["symbol"]
    ptype = pos["type"]
    ticket = pos["ticket"]

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return False

    close_type = mt5.ORDER_TYPE_SELL if ptype == "BUY" else mt5.ORDER_TYPE_BUY
    close_price = tick.bid if ptype == "BUY" else tick.ask

    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": pos["volume"],
        "type": close_type,
        "position": ticket,
        "price": close_price,
        "deviation": 30,
        "magic": MAGIC_NUMBER,
        "comment": "DAILY_LOSS_LIMIT",
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    res = mt5.order_send(req)
    if res and res.retcode == mt5.TRADE_RETCODE_DONE:
        log(f"  CLOSED {symbol} ticket {ticket}", "OK")
        return True
    comment = res.comment if res else str(mt5.last_error())
    log(f"  CLOSE FAILED {symbol}: {comment}", "ERR")
    return False


# ──────────────────────────────────────────────────────────────────────────────
# 8. TRAILING STOP LOGIC
# ──────────────────────────────────────────────────────────────────────────────


def apply_trailing_stops() -> None:
    """
    For every position with MAGIC_NUMBER:
      • At +1R → move SL to breakeven
      • At +2R → trail SL 0.5*initial_sl_dist behind price
    """
    positions_raw = mt5.positions_get()
    if not positions_raw:
        return

    for p in positions_raw:
        if p.magic != MAGIC_NUMBER:
            continue

        sym_info = mt5.symbol_info(p.symbol)
        if not sym_info:
            continue

        point = sym_info.point
        digits = sym_info.digits
        sl_d = abs(p.price_open - p.sl) if p.sl else 0.0
        if sl_d <= 0:
            continue

        is_buy = p.type == 0
        raw_diff = (
            (p.price_current - p.price_open)
            if is_buy
            else (p.price_open - p.price_current)
        )
        r_mult = raw_diff / sl_d

        new_sl = None

        if r_mult >= 2.0:
            # Trail at 0.5 * initial SL distance behind current price
            trail_dist = sl_d * 0.5
            candidate = (
                (p.price_current - trail_dist)
                if is_buy
                else (p.price_current + trail_dist)
            )
            candidate = round(candidate, digits)
            # Only move in the profit direction
            if is_buy and candidate > (p.sl or 0) + point * 5:
                new_sl = candidate
            elif not is_buy and candidate < (p.sl or 999999) - point * 5:
                new_sl = candidate

        elif r_mult >= 1.0:
            # Move to breakeven
            be = round(p.price_open, digits)
            if is_buy and (not p.sl or p.sl < be - point * 5):
                new_sl = be
            elif not is_buy and (not p.sl or p.sl > be + point * 5):
                new_sl = be

        if new_sl is not None:
            req = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": p.symbol,
                "position": p.ticket,
                "sl": new_sl,
                "tp": p.tp,
            }
            res = mt5.order_send(req)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                log(
                    f"  TRAIL {p.symbol} ticket={p.ticket} SL → {new_sl} (R={r_mult:.2f})",
                    "MON",
                )
            else:
                comment = res.comment if res else str(mt5.last_error())
                log(f"  TRAIL FAILED {p.symbol}: {comment}", "WARN")


# ──────────────────────────────────────────────────────────────────────────────
# 9. DASHBOARD UPDATE
# ──────────────────────────────────────────────────────────────────────────────


def _symbol_category(symbol: str) -> str:
    if "XAU" in symbol:
        return "Gold"
    if any(x in symbol for x in INDEX_SYMBOLS):
        return "Indices"
    if any(x in symbol for x in CRYPTO_SYMBOLS):
        return "Crypto"
    if any(c in symbol for c in FOREX_CURRENCIES) and len(symbol) <= 9:
        return "Forex"
    return "Stocks"


def update_dashboard(
    account: dict,
    positions: List[dict],
    normalised_scans: List[dict],
    trades_executed: List[dict],
) -> None:
    """
    Write live_data.json in exactly the format the running dashboard bridge expects.
    """
    # ── Instruments ──
    instruments = []
    for u in normalised_scans:
        symbol = u["symbol"]
        raw = u.get("_raw", {})
        tick = mt5.symbol_info_tick(symbol)
        sym_i = mt5.symbol_info(symbol)
        bid = tick.bid if tick else u.get("current_price", 0)
        ask = tick.ask if tick else bid
        digits = sym_i.digits if sym_i else 5
        spread = round(ask - bid, digits + 1)

        # Extract RSI / MACD from original scan data (any format)
        ind = raw.get("indicators", {})
        rsi_val = 50.0
        macd_sig = "neutral"

        if isinstance(ind, dict):
            rsi_block = ind.get("rsi", {})
            macd_block = ind.get("macd", {})
            if isinstance(rsi_block, dict):
                rsi_val = float(rsi_block.get("value", 50) or 50)
            if isinstance(macd_block, dict):
                macd_sig = macd_block.get("crossover", "neutral").lower()
        else:
            # Format 2/3 — look inside timeframe_analysis or analysis
            for key in ("timeframe_analysis", "analysis"):
                sec = raw.get(key, {})
                if isinstance(sec, dict):
                    d1 = sec.get("D1", sec.get("H4", {}))
                    if isinstance(d1, dict):
                        rsi_block = d1.get("rsi", {})
                        macd_block = d1.get("macd", {})
                        if isinstance(rsi_block, dict):
                            rsi_val = float(rsi_block.get("value", 50) or 50)
                        if isinstance(macd_block, dict):
                            macd_sig = macd_block.get("crossover", "neutral").lower()
                        break

        # Trend from direction
        direction = u["direction"]
        trend = (
            "bearish"
            if direction == "SELL"
            else "bullish"
            if direction == "BUY"
            else "neutral"
        )
        ema_align = trend

        instruments.append(
            {
                "symbol": symbol,
                "category": _symbol_category(symbol),
                "bid": round(bid, digits),
                "ask": round(ask, digits),
                "spread": spread,
                "change_pct": raw.get("change_pct", 0),
                "trend": trend,
                "rsi": round(rsi_val, 2),
                "macd_signal": macd_sig,
                "ema_alignment": ema_align,
                "confluence_score": u["score"],
                "atr": u.get("fresh_atr", u.get("atr", None)),
            }
        )

    # ── Signals ──
    signals = []
    for u in normalised_scans:
        score = u.get("fresh_score", u.get("score", 0))
        direction = u["direction"]
        if score < MIN_SCORE or direction not in ("BUY", "SELL"):
            continue
        signals.append(
            {
                "timestamp": datetime.now(tz=timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                "type": "SIGNAL",
                "symbol": u["symbol"],
                "direction": direction,
                "score": score,
                "strategy": "ICT-UX",
                "entry": u.get("current_price", 0),
                "sl": u.get("sl", 0),
                "tp": u.get("tp", 0),
                "factors": [
                    f
                    for f, v in {
                        "HTF_Bias": u.get("hard_htf"),
                        "Liquidity": u.get("has_liquidity_sweep"),
                        "BOS": u.get("has_bos"),
                        "CHoCH": u.get("has_choch"),
                        "FVG": u.get("has_fvg"),
                        "OB": u.get("has_ob"),
                    }.items()
                    if v
                ],
            }
        )

    for t in trades_executed:
        signals.append(
            {
                "timestamp": t["timestamp"],
                "type": "TRADE",
                "symbol": t["symbol"],
                "direction": t["direction"],
                "score": t["score"],
                "strategy": "ICT-UX",
                "entry": t["entry"],
                "sl": t["sl"],
                "tp": t["tp"],
                "factors": ["EXECUTED"],
            }
        )

    signals.sort(key=lambda x: x.get("score", 0), reverse=True)

    # ── Session ──
    h = datetime.now(tz=timezone.utc).hour
    if 8 <= h < 12:
        session, kz = "London", 8 <= h < 11
    elif 12 <= h < 13:
        session, kz = "London/NY Overlap", True
    elif 13 <= h < 22:
        session, kz = "New York", 13 <= h < 17
    else:
        session, kz = "Asian", h >= 23 or h < 3

    our_trades_today = [p for p in positions if p.get("magic") == MAGIC_NUMBER]

    payload = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "account": account or {},
        "instruments": instruments,
        "positions": positions,
        "signals": signals[:15],
        "session": {
            "current": session,
            "killzone_active": kz,
            "next_event": "None",
            "server_time": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        },
        "stats": {
            "win_rate": 0,
            "avg_rr": 0,
            "today_trades": len(our_trades_today),
            "total_signals_today": len(signals),
        },
    }

    try:
        tmp = str(DASHBOARD_FILE) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
        os.replace(tmp, str(DASHBOARD_FILE))
        log(
            f"Dashboard updated: {len(instruments)} instruments, {len(positions)} positions, {len(signals)} signals",
            "OK",
        )
    except Exception as exc:
        log(f"Dashboard write error: {exc}", "ERR")


# ──────────────────────────────────────────────────────────────────────────────
# 10. TRADE LOG
# ──────────────────────────────────────────────────────────────────────────────


def save_trade_log(trades: List[dict]) -> None:
    TRADES_DIR.mkdir(parents=True, exist_ok=True)
    existing = []
    if TRADE_LOG_FILE.exists():
        try:
            existing = json.loads(TRADE_LOG_FILE.read_text(encoding="utf-8")).get(
                "trades", []
            )
        except Exception:
            pass
    all_trades = existing + trades
    tmp = str(TRADE_LOG_FILE) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"trades": all_trades}, f, indent=2, default=str)
    os.replace(tmp, str(TRADE_LOG_FILE))
    log(f"Trade log saved: {len(all_trades)} total trades", "OK")


# ──────────────────────────────────────────────────────────────────────────────
# 11. QUALIFICATION CHECK
# ──────────────────────────────────────────────────────────────────────────────


def is_qualified(u: dict) -> Tuple[bool, str]:
    """
    Apply ICT hard requirements to decide if a setup qualifies.
    Returns (qualified: bool, reason: str).

    Hard requirements:
      1. HTF bias alignment (from analysis or scan score)
      2. Liquidity sweep detected
      3. MSS / CHoCH confirmed
      4. Direction must be BUY or SELL (not NEUTRAL/WAIT)
      5. Score >= MIN_SCORE after re-analysis
    """
    score = u.get("fresh_score", u.get("score", 0))
    direction = u.get("direction", "NEUTRAL")

    if direction not in ("BUY", "SELL"):
        return False, f"direction={direction}"

    if score < MIN_SCORE:
        return False, f"score={score} < {MIN_SCORE}"

    # Hard requirement 1: HTF bias
    htf_ok = (
        u.get("hard_htf")
        or u.get("has_bos")
        or u.get("has_choch")
        # If fresh analysis confirmed structure, treat as OK
        or bool(u.get("fresh_struct_d1", {}).get("bos_events"))
        or bool(u.get("fresh_struct_d1", {}).get("choch_events"))
    )
    if not htf_ok:
        return False, "no HTF bias confirmation"

    # Hard requirement 2: Liquidity sweep (from structure analysis OR scan score)
    liq_ok = (
        u.get("has_liquidity_sweep")
        or u.get("hard_liquidity")
        # If fresh analysis found swept levels
        or any(
            lv.get("swept") in (True, "True")
            for lv in u.get("fresh_struct_d1", {}).get("liquidity_levels", [])
            + u.get("fresh_struct_h4", {}).get("liquidity_levels", [])
        )
    )
    if not liq_ok:
        return False, "no liquidity sweep"

    # Hard requirement 3: MSS (BOS or CHoCH)
    mss_ok = u.get("hard_mss") or u.get("has_bos") or u.get("has_choch")
    if not mss_ok:
        return False, "no BOS/CHoCH confirmation"

    return True, "OK"


# ──────────────────────────────────────────────────────────────────────────────
# 12. MAIN FLOW
# ──────────────────────────────────────────────────────────────────────────────


def main() -> None:
    log_section("UNIFIED EXECUTOR  —  ICT Multi-Agent  |  Session 20260305_194417")

    # ═══ PHASE 1: Connect to MT5 ═══════════════════════════════════════════
    log_section("Phase 1: MT5 Connection")
    if not mt5.initialize():
        log(f"MT5 init failed: {mt5.last_error()}", "ERR")
        sys.exit(1)

    info = mt5.account_info()
    if not info:
        log("Could not retrieve account info", "ERR")
        mt5.shutdown()
        sys.exit(1)

    log(f"Account #{info.login} | Server: {info.server}", "OK")
    log(f"Balance: ${info.balance:,.2f} | Equity: ${info.equity:,.2f}", "OK")
    log(f"Daily P/L: ${info.equity - info.balance:+,.2f}", "OK")

    # ═══ PHASE 2: Read & Normalise All Scans ════════════════════════════════
    log_section("Phase 2: Reading & Normalising 21 Scan Files")

    scan_files = sorted(SCANS_DIR.glob("*.json"))
    log(f"Found {len(scan_files)} scan files in {SCANS_DIR}")

    raw_scans = []
    normalised = []
    parse_errors = 0

    for fp in scan_files:
        try:
            with open(fp, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            raw_scans.append(raw)
            u = normalise_scan(raw)
            if u:
                normalised.append(u)
        except Exception as exc:
            log(f"  Error parsing {fp.name}: {exc}", "ERR")
            parse_errors += 1

    normalised.sort(key=lambda x: x["score"], reverse=True)

    log(f"Normalised: {len(normalised)} scans  ({parse_errors} errors)", "OK")
    log("")
    log(
        f"{'Rank':>4} {'Symbol':>12} {'Score':>7} {'Dir':>6} {'HTF':>8} {'Liq':>5} {'MSS':>5} {'Fmt':>4}"
    )
    log("─" * 60)
    for i, u in enumerate(normalised, 1):
        q, reason = is_qualified(u)
        marker = "✓" if q else "·"
        log(
            f"{i:>4} {u['symbol']:>12} {u['score']:>4}/12  "
            f"{u['direction']:>6}  {str(u['hard_htf']):>5}  "
            f"{str(u['has_liquidity_sweep']):>5}  {str(u['has_bos'] or u['has_choch']):>5}  "
            f"{u['scan_format']:>3}  {marker}"
        )

    # ═══ PHASE 3: Account Status ════════════════════════════════════════════
    log_section("Phase 3: Account & Position Status")

    account, positions = get_account_status()
    if not account:
        log("Account data unavailable", "ERR")
        mt5.shutdown()
        sys.exit(1)

    log(
        f"Equity: ${account['equity']:,.2f} | Daily P/L: ${account['daily_pnl']:+,.2f} ({account['daily_pnl_pct']:+.3f}%)"
    )
    log(f"Open positions: {len(positions)} / {MAX_POSITIONS}")

    for p in positions:
        own = "(ours)" if p["magic"] == MAGIC_NUMBER else "(legacy)"
        log(
            f"  {p['symbol']:>8} {p['type']} {p['volume']} lot | "
            f"open={p['price_open']} cur={p['price_current']} | "
            f"P/L=${p['profit']:+.2f} R={p['r_multiple']:.2f} {own}"
        )

    # Daily loss guard (daily_pnl_pct is already %, e.g. -0.4 means -0.4%)
    if abs(account["daily_pnl_pct"]) >= MAX_DAILY_LOSS_PCT:
        log(
            f"*** DAILY LOSS LIMIT HIT ({account['daily_pnl_pct']:.3f}%) — CLOSING ALL OUR POSITIONS ***",
            "ERR",
        )
        for p in positions:
            if p["magic"] == MAGIC_NUMBER:
                close_position(p)
        update_dashboard(account, positions, normalised, [])
        mt5.shutdown()
        return

    # Currently occupied symbols (skip re-entry on open symbols)
    occupied_symbols = {p["symbol"] for p in positions}
    log(f"Occupied symbols: {occupied_symbols}")

    slots_available = MAX_POSITIONS - len(positions)
    log(f"Slots available: {slots_available}")

    # ═══ PHASE 4: Re-analyse Top Candidates ═════════════════════════════════
    log_section("Phase 4: Re-Analysing Top 8 Candidates with Live MT5 Data")

    top_candidates = [
        u
        for u in normalised
        if u["score"] >= MIN_SCORE
        and u["direction"] in ("BUY", "SELL")
        and u["symbol"] not in occupied_symbols
    ][:8]

    log(f"Candidates for re-analysis: {len(top_candidates)}")

    re_analysed = []
    for u in top_candidates:
        refreshed = re_analyse_candidate(u)
        re_analysed.append(refreshed)

    # Re-sort by fresh score
    re_analysed.sort(
        key=lambda x: x.get("fresh_score", x.get("score", 0)), reverse=True
    )

    # Also keep the rest (not re-analysed) for dashboard completeness
    reanalysed_symbols = {u["symbol"] for u in re_analysed}
    rest = [u for u in normalised if u["symbol"] not in reanalysed_symbols]
    all_normalised_updated = re_analysed + rest

    # ═══ PHASE 5: Execute Qualified Trades ══════════════════════════════════
    log_section("Phase 5: Trade Execution")

    trades_executed = []

    if slots_available <= 0:
        log(
            f"No slots available ({len(positions)}/{MAX_POSITIONS}) — skipping execution"
        )
    else:
        for u in re_analysed:
            if slots_available <= 0:
                break

            symbol = u["symbol"]
            score = u.get("fresh_score", u.get("score", 0))
            direction = u["direction"]

            # Skip already-open symbols
            if symbol in occupied_symbols:
                log(f"  {symbol}: already open — skip")
                continue

            qualified, reason = is_qualified(u)
            if not qualified:
                log(f"  {symbol}: disqualified — {reason}", "WARN")
                continue

            log(f"\n  [{symbol}] Score={score}/12 Dir={direction}")

            # Get live tick and symbol info
            if not mt5.symbol_select(symbol, True):
                log(f"  {symbol}: symbol_select failed", "ERR")
                continue

            tick = mt5.symbol_info_tick(symbol)
            sym_info = mt5.symbol_info(symbol)
            if not tick or not sym_info:
                log(f"  {symbol}: no tick/info data", "ERR")
                continue

            digits = sym_info.digits
            bid = round(tick.bid, digits)
            ask = round(tick.ask, digits)

            entry, sl, tp, lot = calculate_entry_sl_tp(u, bid, ask, digits)

            if not entry:
                log(
                    f"  {symbol}: SL/TP calculation failed (R:R too low) — skip", "WARN"
                )
                continue

            sl_dist = abs(entry - sl)
            tp_dist = abs(entry - tp)
            rr = tp_dist / sl_dist if sl_dist > 0 else 0
            log(f"  Entry={entry} SL={sl} TP={tp} Lot={lot} R:R={rr:.2f}")

            trade = execute_trade(u, lot, sl, tp, entry)
            if trade:
                trades_executed.append(trade)
                occupied_symbols.add(symbol)
                slots_available -= 1

        log(f"\nTrades executed this session: {len(trades_executed)}")

    # ═══ PHASE 6: Save Trade Log ═════════════════════════════════════════════
    log_section("Phase 6: Saving Trade Log")
    save_trade_log(trades_executed)

    # ═══ PHASE 7: Update Dashboard ═══════════════════════════════════════════
    log_section("Phase 7: Updating Dashboard")
    account, positions = get_account_status()
    update_dashboard(account, positions, all_normalised_updated, trades_executed)

    # ═══ PHASE 8: Monitoring Loop ════════════════════════════════════════════
    log_section("Phase 8: Monitoring Loop  (Ctrl+C to stop)")
    log(f"Interval: {MONITOR_INTERVAL}s | Daily loss limit: {MAX_DAILY_LOSS_PCT}%")
    log(f"Trailing: Breakeven at +1R, Trail at +2R")
    log(f"Tracking {len(occupied_symbols)} occupied symbols")
    log(f"Legacy positions ({LEGACY_POSITIONS}) are monitored but NOT modified")

    iteration = 0
    while True:
        iteration += 1
        try:
            time.sleep(MONITOR_INTERVAL)

            account, positions = get_account_status()
            if not account:
                log("Monitor: lost MT5 connection — attempting reinit …", "WARN")
                mt5.shutdown()
                time.sleep(5)
                if not mt5.initialize():
                    log("Reinit failed — sleeping 60s", "ERR")
                    time.sleep(60)
                continue

            pct = account["daily_pnl_pct"]
            our_pos = [p for p in positions if p["magic"] == MAGIC_NUMBER]
            other_pos = [p for p in positions if p["magic"] != MAGIC_NUMBER]
            total_pnl = account["daily_pnl"]

            log(
                f"[#{iteration}] Equity=${account['equity']:,.2f} | "
                f"P/L=${total_pnl:+,.2f} ({pct:+.3f}%) | "
                f"Our:{len(our_pos)}  Legacy:{len(other_pos)}",
                "MON",
            )

            for p in positions:
                tag = "OUR" if p["magic"] == MAGIC_NUMBER else "LEG"
                log(
                    f"  [{tag}] {p['symbol']:>8} {p['type']} {p['volume']}lot | "
                    f"P/L=${p['profit']:+.2f} R={p['r_multiple']:+.2f}",
                    "MON",
                )

            # Daily loss check (pct is already %, e.g. -0.4 means -0.4%)
            if abs(pct) >= MAX_DAILY_LOSS_PCT:
                log(
                    f"*** DAILY LOSS LIMIT HIT ({pct:.3f}%) — CLOSING ALL OUR POSITIONS ***",
                    "ERR",
                )
                for p in our_pos:
                    close_position(p)
                account, positions = get_account_status()
                update_dashboard(account, positions, all_normalised_updated, [])
                log("All our positions closed. Exiting monitor.", "OK")
                break

            # Apply trailing stops (our positions only — MAGIC_NUMBER filter inside)
            apply_trailing_stops()

            # Refresh dashboard
            update_dashboard(
                account, positions, all_normalised_updated, trades_executed
            )

        except KeyboardInterrupt:
            log("\nMonitor stopped by user.", "WARN")
            break
        except Exception as exc:
            log(f"Monitor error: {exc}", "ERR")
            traceback.print_exc()
            time.sleep(5)


# ──────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Executor stopped by user.", "WARN")
    except Exception as fatal:
        log(f"FATAL: {fatal}", "ERR")
        traceback.print_exc()
    finally:
        try:
            mt5.shutdown()
            log("MT5 connection closed.", "OK")
        except Exception:
            pass
