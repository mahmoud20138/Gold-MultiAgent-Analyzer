# -*- coding: utf-8 -*-
"""
Forex Majors & Minors Scanner - ICT Smart Money Analysis
Scans 8 forex instruments with full ICT analysis + SMT divergence
"""

import sys
import json
import os
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))

from tools.mt5_tools import (
    initialize_mt5,
    fetch_ohlcv_data,
    fetch_tick_data,
    shutdown_mt5,
)
from tools.structure_tools import analyze_market_structure, find_premium_discount_zones
from tools.indicator_tools import calculate_all_indicators
from tools.volume_tools import (
    analyze_volume_profile,
    analyze_accumulation_distribution,
    analyze_volume_anomalies,
)

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════
SYMBOLS = [
    "EURUSDm",
    "GBPUSDm",
    "USDJPYm",
    "USDCHFm",
    "AUDUSDm",
    "USDCADm",
    "NZDUSDm",
    "EURGBPm",
]
TIMEFRAMES = ["D1", "H4", "H1", "M15"]
OUTPUT_DIR = r"C:\Users\Mamoud\Desktop\Claude-Skills-Collection\sessions\trading_20260305_194417\scans"

# SMT correlation pairs
SMT_PAIRS = [
    ("EURUSDm", "GBPUSDm", "positive"),  # Should move together
    ("AUDUSDm", "NZDUSDm", "positive"),  # Commodity block
    ("EURUSDm", "USDCHFm", "inverse"),  # Inverse correlation
    ("GBPUSDm", "EURGBPm", "inverse"),  # Inverse via cross
]

# USD-quoted pairs (up = USD weak) vs USD-based (up = USD strong)
USD_WEAK_PAIRS = ["EURUSDm", "GBPUSDm", "AUDUSDm", "NZDUSDm"]  # XXX/USD - up = USD weak
USD_STRONG_PAIRS = ["USDJPYm", "USDCHFm", "USDCADm"]  # USD/XXX - up = USD strong


def safe_json(obj):
    """Make object JSON-serializable."""
    if isinstance(obj, (datetime,)):
        return str(obj)
    if isinstance(obj, float):
        if obj != obj:  # NaN
            return None
        return round(obj, 6)
    return obj


# ═══════════════════════════════════════════════════════════════
# STEP 1: CONNECT AND FETCH DATA
# ═══════════════════════════════════════════════════════════════
print("=" * 70)
print("FOREX MAJORS & MINORS SCANNER - ICT Smart Money Analysis")
print("=" * 70)
print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
print()

conn = initialize_mt5()
print(f"MT5 Connection: {conn['status']}")
if conn["status"] != "connected":
    print(f"ERROR: {conn.get('message', 'Unknown')}")
    sys.exit(1)

print(
    f"Account: {conn.get('account')} | Balance: ${conn.get('balance', 0):,.2f} | Equity: ${conn.get('equity', 0):,.2f}"
)
print()

# Store all raw data
all_data = {}  # {symbol: {timeframe: ohlcv_list}}
all_ticks = {}  # {symbol: tick_data}

print("--- STEP 1: Fetching OHLCV Data ---")
for sym in SYMBOLS:
    all_data[sym] = {}
    for tf in TIMEFRAMES:
        data = fetch_ohlcv_data(sym, tf, 200)
        if data["status"] == "success":
            all_data[sym][tf] = data["data"]
            latest = data["latest"]
            print(f"  {sym} {tf}: {data['candles_count']} bars | C={latest['close']}")
        else:
            all_data[sym][tf] = None
            print(f"  {sym} {tf}: ERROR - {data.get('message', 'unknown')}")

    tick = fetch_tick_data(sym)
    all_ticks[sym] = tick
    if tick["status"] == "success":
        print(
            f"  {sym} TICK: Bid={tick['bid']} Ask={tick['ask']} Spread={tick['spread_points']}pts"
        )
    print()

print("--- STEP 1 COMPLETE ---\n")


# ═══════════════════════════════════════════════════════════════
# STEP 2: MARKET STRUCTURE + INDICATORS + VOLUME
# ═══════════════════════════════════════════════════════════════
print("--- STEP 2: Market Structure + Indicators + Volume ---")

all_analysis = {}  # {symbol: {timeframe: {structure, indicators, volume, premium_discount}}}

for sym in SYMBOLS:
    all_analysis[sym] = {}
    print(f"\n  Analyzing {sym}...")

    for tf in ["D1", "H4", "H1"]:
        bars = all_data[sym].get(tf)
        if bars is None or len(bars) < 50:
            print(f"    {tf}: Insufficient data")
            all_analysis[sym][tf] = None
            continue

        # Market Structure (BOS, CHoCH, FVG, OB, Liquidity)
        struct = analyze_market_structure(bars)

        # Technical Indicators (RSI, MACD, BB, ATR, Stoch, ADX, Ichimoku)
        if len(bars) >= 200:
            indic = calculate_all_indicators(bars)
        else:
            indic = {"status": "error", "message": "Need 200+ bars"}

        # Volume Profile + Accumulation/Distribution + Anomalies
        vol_profile = analyze_volume_profile(bars)
        vol_ad = analyze_accumulation_distribution(bars)
        vol_anom = analyze_volume_anomalies(bars)

        # Premium/Discount zones
        pd_zones = find_premium_discount_zones(bars)

        all_analysis[sym][tf] = {
            "structure": struct,
            "indicators": indic,
            "volume_profile": vol_profile,
            "volume_ad": vol_ad,
            "volume_anomalies": vol_anom,
            "premium_discount": pd_zones,
        }

        ms = struct.get("market_structure", "N/A")
        bos_count = len(struct.get("bos_events", []))
        choch_count = len(struct.get("choch_events", []))
        fvg_count = len(struct.get("fair_value_gaps", []))
        ob_count = len(struct.get("order_blocks", []))

        rsi_val = (
            indic.get("rsi", {}).get("value", "N/A")
            if indic.get("status") == "success"
            else "N/A"
        )
        macd_cross = (
            indic.get("macd", {}).get("crossover", "N/A")
            if indic.get("status") == "success"
            else "N/A"
        )

        print(
            f"    {tf}: {ms} | BOS:{bos_count} CHoCH:{choch_count} FVG:{fvg_count} OB:{ob_count} | RSI:{rsi_val} MACD:{macd_cross}"
        )

print("\n--- STEP 2 COMPLETE ---\n")


# ═══════════════════════════════════════════════════════════════
# STEP 3: SMT DIVERGENCE CHECK
# ═══════════════════════════════════════════════════════════════
print("--- STEP 3: SMT Divergence Check ---")

smt_results = {}

for pair_a, pair_b, corr_type in SMT_PAIRS:
    bars_a = all_data.get(pair_a, {}).get("H1")
    bars_b = all_data.get(pair_b, {}).get("H1")

    if bars_a is None or bars_b is None:
        print(f"  {pair_a} vs {pair_b}: SKIPPED (missing data)")
        continue

    # Get last 20 bars for comparison
    import pandas as pd

    df_a = pd.DataFrame(bars_a[-20:])
    df_b = pd.DataFrame(bars_b[-20:])

    # For inverse pairs, flip pair_b's logic
    if corr_type == "inverse":
        # For inverse: when A makes new high, B should make new low
        a_new_high = df_a["high"].iloc[-1] >= df_a["high"].max() * 0.999
        a_new_low = df_a["low"].iloc[-1] <= df_a["low"].min() * 1.001
        b_new_high = df_b["high"].iloc[-1] >= df_b["high"].max() * 0.999
        b_new_low = df_b["low"].iloc[-1] <= df_b["low"].min() * 1.001

        # SMT: A makes new high but B doesn't make new low (inverse failed)
        bearish_smt = a_new_high and not b_new_low
        bullish_smt = a_new_low and not b_new_high
    else:
        # Positive correlation: should move together
        a_new_high = df_a["high"].iloc[-5:].max() >= df_a["high"].max() * 0.999
        a_new_low = df_a["low"].iloc[-5:].min() <= df_a["low"].min() * 1.001
        b_new_high = df_b["high"].iloc[-5:].max() >= df_b["high"].max() * 0.999
        b_new_low = df_b["low"].iloc[-5:].min() <= df_b["low"].min() * 1.001

        # SMT: A makes new high but B fails to make new high
        bearish_smt = a_new_high and not b_new_high
        bullish_smt = a_new_low and not b_new_low

    smt_detected = bearish_smt or bullish_smt
    smt_direction = "BEARISH" if bearish_smt else ("BULLISH" if bullish_smt else "NONE")

    key = f"{pair_a}_vs_{pair_b}"
    smt_results[key] = {
        "detected": smt_detected,
        "direction": smt_direction,
        "pair_a": pair_a,
        "pair_b": pair_b,
        "correlation_type": corr_type,
        "pair_a_high": round(float(df_a["high"].max()), 5),
        "pair_a_low": round(float(df_a["low"].min()), 5),
        "pair_a_close": round(float(df_a["close"].iloc[-1]), 5),
        "pair_b_high": round(float(df_b["high"].max()), 5),
        "pair_b_low": round(float(df_b["low"].min()), 5),
        "pair_b_close": round(float(df_b["close"].iloc[-1]), 5),
    }

    status = f"SMT {smt_direction}" if smt_detected else "No SMT"
    print(f"  {pair_a} vs {pair_b} ({corr_type}): {status}")
    if smt_detected:
        if bearish_smt:
            print(
                f"    -> {pair_a} made new high but {pair_b} failed = BEARISH divergence"
            )
        else:
            print(
                f"    -> {pair_a} made new low but {pair_b} failed = BULLISH divergence"
            )

# USD Strength Assessment
print("\n  USD Strength Assessment:")
usd_signals = []
for sym in USD_WEAK_PAIRS:
    bars = all_data.get(sym, {}).get("H4")
    if bars and len(bars) >= 20:
        df_t = pd.DataFrame(bars[-20:])
        if df_t["close"].iloc[-1] > df_t["close"].iloc[0]:
            usd_signals.append(f"{sym} UP (USD weak)")
        else:
            usd_signals.append(f"{sym} DOWN (USD strong)")

for sym in USD_STRONG_PAIRS:
    bars = all_data.get(sym, {}).get("H4")
    if bars and len(bars) >= 20:
        df_t = pd.DataFrame(bars[-20:])
        if df_t["close"].iloc[-1] > df_t["close"].iloc[0]:
            usd_signals.append(f"{sym} UP (USD strong)")
        else:
            usd_signals.append(f"{sym} DOWN (USD weak)")

for sig in usd_signals:
    print(f"    {sig}")

# Count USD direction
usd_weak_count = sum(1 for s in usd_signals if "USD weak" in s)
usd_strong_count = sum(1 for s in usd_signals if "USD strong" in s)
if usd_weak_count > usd_strong_count:
    usd_overall = "USD WEAK"
elif usd_strong_count > usd_weak_count:
    usd_overall = "USD STRONG"
else:
    usd_overall = "USD MIXED"
print(
    f"  Overall: {usd_overall} ({usd_weak_count} weak / {usd_strong_count} strong signals)"
)

print("\n--- STEP 3 COMPLETE ---\n")


# ═══════════════════════════════════════════════════════════════
# STEP 4: ICT CONFLUENCE SCORING
# ═══════════════════════════════════════════════════════════════
print("--- STEP 4: ICT Confluence Scoring ---")

# Current time check for killzone
now_utc = datetime.now(timezone.utc)
hour_utc = now_utc.hour
# Convert to EST (UTC-5)
hour_est = (hour_utc - 5) % 24

london_kz = 7 <= hour_utc <= 10  # London KZ: 2-5 AM EST = 7-10 UTC
ny_kz = 13 <= hour_utc <= 16  # NY KZ: 8:30-11 AM EST = 13:30-16 UTC
ny_lunch = 16 <= hour_utc <= 18  # 11AM-1PM EST
any_kz = london_kz or ny_kz

kz_name = (
    "London Killzone"
    if london_kz
    else (
        "NY Open Killzone"
        if ny_kz
        else ("NY Lunch - NO TRADE" if ny_lunch else "Off-Killzone")
    )
)
print(
    f"  Current Time: {now_utc.strftime('%H:%M')} UTC / {hour_est}:{now_utc.strftime('%M')} EST"
)
print(f"  Session: {kz_name}")
print()

all_scores = {}

for sym in SYMBOLS:
    score = 0
    score_breakdown = {}

    # --- Factor 1: HTF Bias (D1 + H4 aligned) [+2] ---
    d1_struct = None
    h4_struct = None
    h1_struct = None

    if (
        all_analysis[sym].get("D1")
        and all_analysis[sym]["D1"]["structure"].get("status") == "success"
    ):
        d1_struct = all_analysis[sym]["D1"]["structure"]["market_structure"]
    if (
        all_analysis[sym].get("H4")
        and all_analysis[sym]["H4"]["structure"].get("status") == "success"
    ):
        h4_struct = all_analysis[sym]["H4"]["structure"]["market_structure"]
    if (
        all_analysis[sym].get("H1")
        and all_analysis[sym]["H1"]["structure"].get("status") == "success"
    ):
        h1_struct = all_analysis[sym]["H1"]["structure"]["market_structure"]

    htf_aligned = False
    htf_bias = "NEUTRAL"
    if d1_struct and h4_struct:
        if d1_struct == h4_struct and d1_struct in ["BULLISH", "BEARISH"]:
            score += 2
            htf_aligned = True
            htf_bias = d1_struct
            score_breakdown["htf_bias"] = f"+2 ({d1_struct})"
        elif d1_struct in ["BULLISH", "BEARISH"]:
            score += 1
            htf_bias = d1_struct
            score_breakdown["htf_bias"] = f"+1 (D1={d1_struct}, H4={h4_struct})"
        else:
            score_breakdown["htf_bias"] = f"+0 (D1={d1_struct}, H4={h4_struct})"
    else:
        score_breakdown["htf_bias"] = "+0 (insufficient data)"

    # --- Factor 2: Session/Killzone active [+2] ---
    if any_kz:
        score += 2
        score_breakdown["killzone"] = f"+2 ({kz_name})"
    else:
        score_breakdown["killzone"] = f"+0 ({kz_name})"

    # --- Factor 3: Liquidity sweep confirmed [+2] ---
    liq_sweep = False
    h1_analysis = all_analysis[sym].get("H1", {})
    if h1_analysis:
        struct = h1_analysis.get("structure", {})
        liq_levels = struct.get("liquidity_levels", [])
        swept = [l for l in liq_levels if l.get("swept")]
        if swept:
            score += 2
            liq_sweep = True
            score_breakdown["liquidity_sweep"] = f"+2 ({len(swept)} levels swept)"
        else:
            score_breakdown["liquidity_sweep"] = "+0 (no sweep detected)"
    else:
        score_breakdown["liquidity_sweep"] = "+0 (no H1 data)"

    # --- Factor 4: MSS/CHoCH confirmed [+2] ---
    mss_confirmed = False
    if h1_analysis:
        struct = h1_analysis.get("structure", {})
        bos = struct.get("bos_events", [])
        choch = struct.get("choch_events", [])
        if choch:
            score += 2
            mss_confirmed = True
            score_breakdown["mss_choch"] = f"+2 (CHoCH: {choch[0]['type']})"
        elif bos:
            score += 1
            mss_confirmed = True
            score_breakdown["mss_choch"] = f"+1 (BOS: {bos[0]['type']})"
        else:
            score_breakdown["mss_choch"] = "+0 (no BOS/CHoCH)"
    else:
        score_breakdown["mss_choch"] = "+0 (no H1 data)"

    # --- Factor 5: FVG at entry [+1] ---
    fvg_present = False
    if h1_analysis:
        struct = h1_analysis.get("structure", {})
        fvgs = struct.get("fair_value_gaps", [])
        unfilled_fvgs = [f for f in fvgs if not f.get("filled", True)]
        if unfilled_fvgs:
            score += 1
            fvg_present = True
            score_breakdown["fvg"] = f"+1 ({len(unfilled_fvgs)} unfilled FVGs)"
        else:
            score_breakdown["fvg"] = "+0 (no unfilled FVGs)"
    else:
        score_breakdown["fvg"] = "+0 (no data)"

    # --- Factor 6: Order Block at entry [+1] ---
    ob_present = False
    if h1_analysis:
        struct = h1_analysis.get("structure", {})
        obs = struct.get("order_blocks", [])
        if obs:
            score += 1
            ob_present = True
            score_breakdown["order_block"] = f"+1 ({len(obs)} OBs)"
        else:
            score_breakdown["order_block"] = "+0 (no OBs)"
    else:
        score_breakdown["order_block"] = "+0 (no data)"

    # --- Factor 7: OTE zone (62-79% Fib) [+1] ---
    in_ote = False
    if h1_analysis:
        pd_data = h1_analysis.get("premium_discount", {})
        range_pos = pd_data.get("range_position", 50)
        # OTE is 62-79% for sells (premium) or 21-38% for buys (discount)
        if htf_bias == "BEARISH" and 62 <= range_pos <= 79:
            score += 1
            in_ote = True
            score_breakdown["ote"] = f"+1 (OTE sell zone: {range_pos}%)"
        elif htf_bias == "BULLISH" and 21 <= range_pos <= 38:
            score += 1
            in_ote = True
            score_breakdown["ote"] = f"+1 (OTE buy zone: {range_pos}%)"
        else:
            score_breakdown["ote"] = f"+0 (range pos: {range_pos}%)"
    else:
        score_breakdown["ote"] = "+0 (no data)"

    # --- Factor 8: Premium/Discount correct [+1] ---
    pd_correct = False
    if h1_analysis:
        pd_data = h1_analysis.get("premium_discount", {})
        zone = pd_data.get("zone", "EQUILIBRIUM")
        if (htf_bias == "BULLISH" and zone == "DISCOUNT") or (
            htf_bias == "BEARISH" and zone == "PREMIUM"
        ):
            score += 1
            pd_correct = True
            score_breakdown["premium_discount"] = f"+1 ({zone} for {htf_bias})"
        else:
            score_breakdown["premium_discount"] = f"+0 ({zone}, bias={htf_bias})"
    else:
        score_breakdown["premium_discount"] = "+0 (no data)"

    # --- BONUS: SMT Divergence [+1] ---
    smt_bonus = False
    smt_detail = None
    for key, smt in smt_results.items():
        if sym in key and smt["detected"]:
            # Check if SMT aligns with HTF bias
            if smt["direction"] == htf_bias or htf_bias == "NEUTRAL":
                score += 1
                smt_bonus = True
                smt_detail = smt
                score_breakdown["smt_divergence"] = (
                    f"+1 ({smt['direction']} SMT: {key})"
                )
                break
    if not smt_bonus:
        score_breakdown["smt_divergence"] = "+0 (no aligned SMT)"

    # --- BONUS: Correlated pair confirmation [+1] ---
    corr_confirm = False
    # Check if correlated pair has same bias
    corr_map = {
        "EURUSDm": "GBPUSDm",
        "GBPUSDm": "EURUSDm",
        "AUDUSDm": "NZDUSDm",
        "NZDUSDm": "AUDUSDm",
        "USDJPYm": "USDCHFm",
        "USDCHFm": "USDJPYm",
        "USDCADm": None,
        "EURGBPm": None,
    }
    corr_pair = corr_map.get(sym)
    if corr_pair and corr_pair in all_analysis:
        corr_h4 = all_analysis.get(corr_pair, {}).get("H4", {})
        if corr_h4:
            corr_struct = corr_h4.get("structure", {}).get("market_structure")
            if corr_struct == htf_bias and htf_bias in ["BULLISH", "BEARISH"]:
                score += 1
                corr_confirm = True
                score_breakdown["correlation"] = f"+1 ({corr_pair} also {htf_bias})"
            else:
                score_breakdown["correlation"] = f"+0 ({corr_pair}={corr_struct})"
        else:
            score_breakdown["correlation"] = "+0 (no corr data)"
    else:
        score_breakdown["correlation"] = "+0 (no correlated pair)"

    # Determine recommendation
    if score >= 8:
        recommendation = "FULL RISK (1%) - Strong setup"
        trade_grade = "A+"
    elif score >= 5:
        recommendation = "HALF RISK (0.5%) - Moderate setup"
        trade_grade = "B"
    else:
        recommendation = "NO TRADE - Insufficient confluence"
        trade_grade = "F"

    # Determine direction
    if htf_bias == "BULLISH" and score >= 5:
        direction = "BUY"
    elif htf_bias == "BEARISH" and score >= 5:
        direction = "SELL"
    else:
        direction = "WAIT"

    all_scores[sym] = {
        "score": score,
        "max_score": 14,
        "grade": trade_grade,
        "direction": direction,
        "htf_bias": htf_bias,
        "recommendation": recommendation,
        "breakdown": score_breakdown,
        "factors": {
            "htf_aligned": htf_aligned,
            "killzone_active": any_kz,
            "liquidity_swept": liq_sweep,
            "mss_confirmed": mss_confirmed,
            "fvg_present": fvg_present,
            "ob_present": ob_present,
            "in_ote": in_ote,
            "pd_correct": pd_correct,
            "smt_divergence": smt_bonus,
            "correlation_confirmed": corr_confirm,
        },
    }

    print(
        f"  {sym}: Score {score}/14 [{trade_grade}] | {htf_bias} | {direction} | {recommendation}"
    )
    for k, v in score_breakdown.items():
        print(f"    {k}: {v}")
    print()

print("--- STEP 4 COMPLETE ---\n")


# ═══════════════════════════════════════════════════════════════
# STEP 5: WRITE JSON RESULTS
# ═══════════════════════════════════════════════════════════════
print("--- STEP 5: Writing JSON Results ---")

for sym in SYMBOLS:
    tick = all_ticks.get(sym, {})
    scoring = all_scores.get(sym, {})

    # Get SMT info for this symbol
    sym_smt = {"detected": False, "pair": "N/A", "description": "No SMT divergence"}
    for key, smt in smt_results.items():
        if sym in key and smt["detected"]:
            sym_smt = {
                "detected": True,
                "pair": key.replace("_vs_", " vs "),
                "direction": smt["direction"],
                "description": f"{smt['pair_a']} vs {smt['pair_b']} - {smt['direction']} SMT divergence ({smt['correlation_type']} correlation)",
            }
            break

    # Build per-timeframe analysis summary
    tf_summaries = {}
    for tf in ["D1", "H4", "H1"]:
        analysis = all_analysis[sym].get(tf)
        if analysis is None:
            tf_summaries[tf] = {"status": "no_data"}
            continue

        struct = analysis.get("structure", {})
        indic = analysis.get("indicators", {})
        vol_ad = analysis.get("volume_ad", {})
        vol_anom = analysis.get("volume_anomalies", {})
        pd_zone = analysis.get("premium_discount", {})

        tf_summaries[tf] = {
            "market_structure": struct.get("market_structure", "N/A"),
            "current_price": struct.get("current_price"),
            "bos_events": struct.get("bos_events", []),
            "choch_events": struct.get("choch_events", []),
            "fair_value_gaps": struct.get("fair_value_gaps", []),
            "order_blocks": struct.get("order_blocks", []),
            "liquidity_levels": struct.get("liquidity_levels", []),
            "swing_highs": struct.get("swing_highs", []),
            "swing_lows": struct.get("swing_lows", []),
            "rsi": indic.get("rsi", {}),
            "macd": indic.get("macd", {}),
            "bollinger_bands": indic.get("bollinger_bands", {}),
            "atr": indic.get("atr", {}),
            "stochastic": indic.get("stochastic", {}),
            "adx": indic.get("adx", {}),
            "ichimoku": indic.get("ichimoku", {}),
            "moving_averages": indic.get("moving_averages", {}),
            "volume_flow": vol_ad.get("overall_flow", "N/A"),
            "volume_cmf": vol_ad.get("cmf", {}),
            "volume_divergences": vol_ad.get("divergences", {}),
            "relative_volume": vol_anom.get("relative_volume", "N/A"),
            "volume_trend": vol_anom.get("volume_trend", "N/A"),
            "premium_discount_zone": pd_zone.get("zone", "N/A"),
            "range_position_pct": pd_zone.get("range_position", "N/A"),
        }

    result = {
        "symbol": sym,
        "scan_time": datetime.now(timezone.utc).isoformat(),
        "agent": "forex_majors_minors_scanner",
        "current_price": {
            "bid": tick.get("bid"),
            "ask": tick.get("ask"),
            "spread_points": tick.get("spread_points"),
        },
        "confluence_score": {
            "score": scoring.get("score", 0),
            "max_score": 14,
            "grade": scoring.get("grade", "F"),
            "direction": scoring.get("direction", "WAIT"),
            "htf_bias": scoring.get("htf_bias", "NEUTRAL"),
            "recommendation": scoring.get("recommendation", "NO TRADE"),
            "breakdown": scoring.get("breakdown", {}),
            "factors": scoring.get("factors", {}),
        },
        "smt_divergence": sym_smt,
        "correlation_notes": usd_overall,
        "usd_assessment": {
            "overall": usd_overall,
            "weak_signals": usd_weak_count,
            "strong_signals": usd_strong_count,
            "details": usd_signals,
        },
        "timeframe_analysis": tf_summaries,
        "session_info": {
            "killzone": kz_name,
            "killzone_active": any_kz,
            "london_kz": london_kz,
            "ny_kz": ny_kz,
            "time_utc": now_utc.strftime("%H:%M"),
            "time_est": f"{hour_est}:{now_utc.strftime('%M')}",
        },
    }

    # Write JSON
    filepath = os.path.join(OUTPUT_DIR, f"{sym}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    print(f"  Written: {filepath}")

print("\n--- STEP 5 COMPLETE ---\n")


# ═══════════════════════════════════════════════════════════════
# STEP 6: SUMMARY TABLE
# ═══════════════════════════════════════════════════════════════
print("=" * 90)
print("FOREX SCAN SUMMARY - ICT Smart Money Analysis")
print("=" * 90)
print(
    f"{'Symbol':<12} {'Score':>6} {'Grade':>6} {'Bias':>10} {'Direction':>10} {'D1':>10} {'H4':>10} {'H1':>10} {'Recommendation'}"
)
print("-" * 90)

for sym in SYMBOLS:
    sc = all_scores.get(sym, {})
    d1_ms = "N/A"
    h4_ms = "N/A"
    h1_ms = "N/A"
    if all_analysis[sym].get("D1"):
        d1_ms = all_analysis[sym]["D1"]["structure"].get("market_structure", "N/A")[:8]
    if all_analysis[sym].get("H4"):
        h4_ms = all_analysis[sym]["H4"]["structure"].get("market_structure", "N/A")[:8]
    if all_analysis[sym].get("H1"):
        h1_ms = all_analysis[sym]["H1"]["structure"].get("market_structure", "N/A")[:8]

    score_str = f"{sc.get('score', 0)}/14"
    grade = sc.get("grade", "F")
    bias = sc.get("htf_bias", "N/A")
    direction = sc.get("direction", "WAIT")
    rec = sc.get("recommendation", "NO TRADE")[:30]

    print(
        f"{sym:<12} {score_str:>6} {grade:>6} {bias:>10} {direction:>10} {d1_ms:>10} {h4_ms:>10} {h1_ms:>10} {rec}"
    )

print("-" * 90)
print()

# SMT Summary
print("SMT DIVERGENCE SUMMARY:")
for key, smt in smt_results.items():
    status = f"SMT {smt['direction']}" if smt["detected"] else "No SMT"
    print(f"  {key.replace('_', ' ')}: {status}")

print(f"\nUSD OVERALL: {usd_overall}")
print(f"Session: {kz_name}")
print()

# Top picks
sorted_symbols = sorted(
    SYMBOLS, key=lambda s: all_scores.get(s, {}).get("score", 0), reverse=True
)
print("TOP PICKS (by confluence score):")
for i, sym in enumerate(sorted_symbols[:3], 1):
    sc = all_scores.get(sym, {})
    print(
        f"  {i}. {sym}: {sc.get('score', 0)}/14 [{sc.get('grade', 'F')}] - {sc.get('direction', 'WAIT')} ({sc.get('htf_bias', 'N/A')})"
    )

print()
print("=" * 90)
print("SCAN COMPLETE")
print("=" * 90)

# Shutdown MT5
shutdown_mt5()
