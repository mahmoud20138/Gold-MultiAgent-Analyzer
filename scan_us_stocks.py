# -*- coding: utf-8 -*-
"""
US Stocks Scanner - Agent 3
Scans 7 US stocks with ICT Smart Money analysis
"""

import sys
import os
import json
import traceback
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))

OUTPUT_DIR = Path(
    r"C:\Users\Mamoud\Desktop\Claude-Skills-Collection\sessions\trading_20260305_194417\scans"
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Results storage
RESULTS = {}


def log(msg):
    print(f"[STOCK-SCAN] {msg}", flush=True)


def main():
    log("=" * 60)
    log("US STOCKS SCANNER - ICT SMART MONEY ANALYSIS")
    log(f"Timestamp: {datetime.utcnow().isoformat()}")
    log("=" * 60)

    # ── STEP 1: Initialize MT5 ──
    try:
        from tools.mt5_tools import (
            initialize_mt5,
            fetch_ohlcv_data,
            fetch_tick_data,
            get_open_positions,
        )
        from tools.structure_tools import (
            analyze_market_structure,
            find_premium_discount_zones,
        )
        from tools.indicator_tools import calculate_all_indicators
        from tools.volume_tools import (
            analyze_volume_profile,
            analyze_accumulation_distribution,
            analyze_volume_anomalies,
            volume_price_analysis,
        )
    except Exception as e:
        log(f"IMPORT ERROR: {e}")
        traceback.print_exc()
        return

    conn = initialize_mt5()
    log(f"MT5 Connection: {conn['status']}")
    if conn["status"] != "connected":
        log(f"FATAL: Cannot connect to MT5: {conn}")
        return

    log(
        f"Account Balance: ${conn.get('balance', 0):,.2f} | Equity: ${conn.get('equity', 0):,.2f}"
    )

    # ── Check open positions ──
    positions = get_open_positions()
    stock_positions = [
        p
        for p in positions.get("positions", [])
        if any(
            s in p["symbol"]
            for s in ["AAPL", "MSFT", "AMZN", "GOOGL", "TSLA", "NVDA", "META"]
        )
    ]
    log(f"\nOpen stock positions: {len(stock_positions)}")
    for p in stock_positions:
        log(
            f"  {p['symbol']} {p['type']} {p['volume']} lot @ {p['open_price']} | SL: {p['sl']} TP: {p['tp']} | P/L: ${p['profit']}"
        )

    # ── Symbols ──
    SYMBOLS = ["AAPLm", "MSFTm", "AMZNm", "GOOGLm", "TSLAm", "NVDAm", "METAm"]
    TIMEFRAMES = ["D1", "H4", "H1", "M15"]

    # ── STEP 1: Fetch data ──
    log("\n" + "=" * 60)
    log("STEP 1: FETCHING DATA FOR ALL STOCKS")
    log("=" * 60)

    all_data = {}
    for symbol in SYMBOLS:
        all_data[symbol] = {}
        for tf in TIMEFRAMES:
            data = fetch_ohlcv_data(symbol, tf, 200)
            all_data[symbol][tf] = data
            status = data["status"]
            count = data.get("candles_count", 0)
            latest = data.get("latest_close", "N/A")
            log(f"  {symbol} {tf}: {status} ({count} bars) Latest: {latest}")

        # Tick data
        tick = fetch_tick_data(symbol)
        all_data[symbol]["tick"] = tick
        if tick["status"] == "success":
            log(
                f"  {symbol} TICK: Bid={tick['bid']} Ask={tick['ask']} Spread={tick.get('spread_points', 'N/A')} pts"
            )

    # Also fetch SPX for relative strength
    spx_data = fetch_ohlcv_data("US500m", "D1", 200)
    log(f"  US500m D1: {spx_data['status']} ({spx_data.get('candles_count', 0)} bars)")

    # ── STEP 2: Full Analysis ──
    log("\n" + "=" * 60)
    log("STEP 2: FULL ANALYSIS (STRUCTURE + INDICATORS + VOLUME)")
    log("=" * 60)

    analysis_results = {}
    for symbol in SYMBOLS:
        analysis_results[symbol] = {}

        for tf in ["D1", "H4", "H1"]:
            tf_data = all_data[symbol][tf]
            if tf_data["status"] != "success" or tf_data.get("candles_count", 0) < 50:
                log(f"  {symbol} {tf}: SKIP (insufficient data)")
                analysis_results[symbol][tf] = {"status": "skipped"}
                continue

            ohlcv = tf_data["data"]

            # Market Structure
            try:
                structure = analyze_market_structure(ohlcv)
            except Exception as e:
                structure = {"status": "error", "message": str(e)}

            # Indicators
            try:
                if len(ohlcv) >= 200:
                    indicators = calculate_all_indicators(ohlcv)
                else:
                    indicators = {
                        "status": "error",
                        "message": f"Only {len(ohlcv)} candles, need 200",
                    }
            except Exception as e:
                indicators = {"status": "error", "message": str(e)}

            # Volume
            try:
                vol_profile = analyze_volume_profile(ohlcv)
            except Exception as e:
                vol_profile = {"status": "error", "message": str(e)}

            try:
                vol_ad = analyze_accumulation_distribution(ohlcv)
            except Exception as e:
                vol_ad = {"status": "error", "message": str(e)}

            try:
                vol_anomalies = analyze_volume_anomalies(ohlcv)
            except Exception as e:
                vol_anomalies = {"status": "error", "message": str(e)}

            try:
                vol_price = volume_price_analysis(ohlcv)
            except Exception as e:
                vol_price = {"status": "error", "message": str(e)}

            # Premium/Discount
            try:
                pd_zones = find_premium_discount_zones(ohlcv)
            except Exception as e:
                pd_zones = {"status": "error", "message": str(e)}

            analysis_results[symbol][tf] = {
                "structure": structure,
                "indicators": indicators,
                "volume_profile": vol_profile,
                "volume_ad": vol_ad,
                "volume_anomalies": vol_anomalies,
                "volume_price": vol_price,
                "premium_discount": pd_zones,
            }

            ms = structure.get("market_structure", "N/A")
            rsi_val = (
                indicators.get("rsi", {}).get("value", "N/A")
                if indicators.get("status") == "success"
                else "N/A"
            )
            macd_cross = (
                indicators.get("macd", {}).get("crossover", "N/A")
                if indicators.get("status") == "success"
                else "N/A"
            )
            flow = vol_ad.get("overall_flow", "N/A")
            zone = pd_zones.get("zone", "N/A")

            log(
                f"  {symbol} {tf}: Structure={ms} | RSI={rsi_val} | MACD={macd_cross} | Flow={flow} | Zone={zone}"
            )

    # ── STEP 3: Stock-Specific Analysis (Relative Strength + Gaps) ──
    log("\n" + "=" * 60)
    log("STEP 3: RELATIVE STRENGTH VS S&P 500 + GAP ANALYSIS")
    log("=" * 60)

    rel_strength = {}
    for symbol in SYMBOLS:
        stk_data = all_data[symbol]["D1"]
        if stk_data["status"] != "success" or spx_data["status"] != "success":
            rel_strength[symbol] = {"status": "error"}
            log(f"  {symbol}: SKIP (no data)")
            continue

        stk = stk_data["data"]
        spx = spx_data["data"]

        # 5-day performance
        if len(stk) >= 6 and len(spx) >= 6:
            stk_5d = (stk[-1]["close"] - stk[-6]["close"]) / stk[-6]["close"] * 100
            spx_5d = (spx[-1]["close"] - spx[-6]["close"]) / spx[-6]["close"] * 100
            rs_5d = stk_5d - spx_5d
        else:
            stk_5d = spx_5d = rs_5d = 0

        # 20-day performance
        if len(stk) >= 21 and len(spx) >= 21:
            stk_20d = (stk[-1]["close"] - stk[-21]["close"]) / stk[-21]["close"] * 100
            spx_20d = (spx[-1]["close"] - spx[-21]["close"]) / spx[-21]["close"] * 100
            rs_20d = stk_20d - spx_20d
        else:
            stk_20d = spx_20d = rs_20d = 0

        # Gap analysis
        if len(stk) >= 2:
            gap = stk[-1]["open"] - stk[-2]["close"]
            gap_pct = gap / stk[-2]["close"] * 100
            if gap > 0:
                gap_type = "GAP_UP"
            elif gap < 0:
                gap_type = "GAP_DOWN"
            else:
                gap_type = "NO_GAP"

            # Check if gap filled
            if gap_type == "GAP_UP":
                gap_filled = stk[-1]["low"] <= stk[-2]["close"]
            elif gap_type == "GAP_DOWN":
                gap_filled = stk[-1]["high"] >= stk[-2]["close"]
            else:
                gap_filled = True
        else:
            gap = gap_pct = 0
            gap_type = "NO_DATA"
            gap_filled = False

        rel_strength[symbol] = {
            "stk_5d_pct": round(stk_5d, 2),
            "spx_5d_pct": round(spx_5d, 2),
            "relative_strength_5d": round(rs_5d, 2),
            "stk_20d_pct": round(stk_20d, 2),
            "spx_20d_pct": round(spx_20d, 2),
            "relative_strength_20d": round(rs_20d, 2),
            "gap": round(gap, 2),
            "gap_pct": round(gap_pct, 3),
            "gap_type": gap_type,
            "gap_filled": gap_filled,
            "outperforming": rs_5d > 0,
        }

        log(
            f"  {symbol}: 5D={stk_5d:+.2f}% vs SPX {spx_5d:+.2f}% | RS={rs_5d:+.2f}% | Gap={gap_type} ({gap_pct:+.3f}%) | {'OUTPERFORMING' if rs_5d > 0 else 'UNDERPERFORMING'}"
        )

    # ── STEP 4: ICT Confluence Scoring ──
    log("\n" + "=" * 60)
    log("STEP 4: ICT CONFLUENCE SCORING (0-12)")
    log("=" * 60)

    scores = {}
    for symbol in SYMBOLS:
        score = 0
        score_breakdown = {}

        d1 = analysis_results.get(symbol, {}).get("D1", {})
        h4 = analysis_results.get(symbol, {}).get("H4", {})
        h1 = analysis_results.get(symbol, {}).get("H1", {})

        d1_struct = d1.get("structure", {})
        h4_struct = h4.get("structure", {})
        h1_struct = h1.get("structure", {})

        d1_ind = d1.get("indicators", {})
        h4_ind = h4.get("indicators", {})
        h1_ind = h1.get("indicators", {})

        d1_pd = d1.get("premium_discount", {})

        # Determine HTF bias
        d1_ms = d1_struct.get("market_structure", "UNKNOWN")
        h4_ms = h4_struct.get("market_structure", "UNKNOWN")

        if d1_ms in ["BULLISH"]:
            htf_bias = "BULLISH"
        elif d1_ms in ["BEARISH"]:
            htf_bias = "BEARISH"
        else:
            htf_bias = "NEUTRAL"

        # 1. HTF Bias alignment (+2)
        if htf_bias in ["BULLISH", "BEARISH"]:
            if h4_ms == d1_ms:
                score += 2
                score_breakdown["htf_bias_alignment"] = 2
            elif h4_ms != "RANGING":
                score += 1
                score_breakdown["htf_bias_alignment"] = 1
            else:
                score_breakdown["htf_bias_alignment"] = 0
        else:
            score_breakdown["htf_bias_alignment"] = 0

        # 2. Killzone timing (+2) - Stocks only trade NY session
        # Current time check (we assume NY session is active for stocks)
        import datetime as dt

        now_utc = dt.datetime.utcnow()
        hour_utc = now_utc.hour
        # NY session: 13:30-20:00 UTC
        if 13 <= hour_utc <= 20:
            score += 2
            score_breakdown["killzone"] = 2
        elif 8 <= hour_utc <= 13:
            score += 1
            score_breakdown["killzone"] = 1  # Pre-market
        else:
            score_breakdown["killzone"] = 0

        # 3. Liquidity sweep confirmed (+2)
        h1_liq = h1_struct.get("liquidity_levels", [])
        swept_count = sum(1 for l in h1_liq if l.get("swept", False))
        if swept_count > 0:
            score += 2
            score_breakdown["liquidity_sweep"] = 2
        else:
            h4_liq = h4_struct.get("liquidity_levels", [])
            swept_h4 = sum(1 for l in h4_liq if l.get("swept", False))
            if swept_h4 > 0:
                score += 1
                score_breakdown["liquidity_sweep"] = 1
            else:
                score_breakdown["liquidity_sweep"] = 0

        # 4. MSS/CHoCH confirmed (+2)
        h1_choch = h1_struct.get("choch_events", [])
        h1_bos = h1_struct.get("bos_events", [])
        if h1_choch:
            score += 2
            score_breakdown["mss_choch"] = 2
        elif h1_bos:
            score += 1
            score_breakdown["mss_choch"] = 1
        else:
            score_breakdown["mss_choch"] = 0

        # 5. FVG entry (+1)
        h1_fvg = h1_struct.get("fair_value_gaps", [])
        if h1_fvg:
            # Check if FVG aligns with bias
            bias_fvg = [
                f
                for f in h1_fvg
                if (htf_bias == "BULLISH" and f["type"] == "BULLISH_FVG")
                or (htf_bias == "BEARISH" and f["type"] == "BEARISH_FVG")
            ]
            if bias_fvg:
                score += 1
                score_breakdown["fvg_entry"] = 1
            else:
                score_breakdown["fvg_entry"] = 0
        else:
            score_breakdown["fvg_entry"] = 0

        # 6. Order Block entry (+1)
        h1_ob = h1_struct.get("order_blocks", [])
        if h1_ob:
            bias_ob = [
                ob
                for ob in h1_ob
                if (htf_bias == "BULLISH" and ob["type"] == "BULLISH_OB")
                or (htf_bias == "BEARISH" and ob["type"] == "BEARISH_OB")
            ]
            if bias_ob:
                score += 1
                score_breakdown["order_block"] = 1
            else:
                score_breakdown["order_block"] = 0
        else:
            score_breakdown["order_block"] = 0

        # 7. OTE zone 62-79% (+1)
        d1_zone = d1_pd.get("range_position", 50)
        if htf_bias == "BULLISH" and 21 <= d1_zone <= 38:  # Discount for buys
            score += 1
            score_breakdown["ote_zone"] = 1
        elif htf_bias == "BEARISH" and 62 <= d1_zone <= 79:  # Premium for sells
            score += 1
            score_breakdown["ote_zone"] = 1
        else:
            score_breakdown["ote_zone"] = 0

        # 8. Premium/Discount correct (+1)
        zone = d1_pd.get("zone", "EQUILIBRIUM")
        if (htf_bias == "BULLISH" and zone == "DISCOUNT") or (
            htf_bias == "BEARISH" and zone == "PREMIUM"
        ):
            score += 1
            score_breakdown["premium_discount"] = 1
        else:
            score_breakdown["premium_discount"] = 0

        # Determine direction and trade quality
        if score >= 8:
            trade_quality = "A+ SETUP (Full risk 1%)"
        elif score >= 5:
            trade_quality = "B SETUP (Half risk 0.5%)"
        else:
            trade_quality = "NO TRADE (Score < 5)"

        # Determine setup direction
        if htf_bias == "BULLISH" and score >= 5:
            setup_direction = "BUY"
        elif htf_bias == "BEARISH" and score >= 5:
            setup_direction = "SELL"
        else:
            setup_direction = "NONE"

        # Key levels for entry
        current_price = d1_struct.get("current_price", 0)

        # SL/TP calculation
        d1_atr = (
            d1_ind.get("atr", {}).get("value", 0)
            if d1_ind.get("status") == "success"
            else 0
        )

        if setup_direction == "BUY":
            sl = current_price - (d1_atr * 1.5) if d1_atr else 0
            tp1 = current_price + (d1_atr * 2) if d1_atr else 0
            tp2 = current_price + (d1_atr * 3) if d1_atr else 0
        elif setup_direction == "SELL":
            sl = current_price + (d1_atr * 1.5) if d1_atr else 0
            tp1 = current_price - (d1_atr * 2) if d1_atr else 0
            tp2 = current_price - (d1_atr * 3) if d1_atr else 0
        else:
            sl = tp1 = tp2 = 0

        rr_ratio = (
            round(abs(tp1 - current_price) / abs(sl - current_price), 2)
            if sl and current_price and sl != current_price
            else 0
        )

        scores[symbol] = {
            "score": score,
            "max_score": 12,
            "score_breakdown": score_breakdown,
            "htf_bias": htf_bias,
            "setup_direction": setup_direction,
            "trade_quality": trade_quality,
            "current_price": current_price,
            "sl": round(sl, 2) if sl else 0,
            "tp1": round(tp1, 2) if tp1 else 0,
            "tp2": round(tp2, 2) if tp2 else 0,
            "rr_ratio": rr_ratio,
            "atr_d1": round(d1_atr, 2) if d1_atr else 0,
        }

        log(
            f"  {symbol}: {score}/12 | Bias={htf_bias} | Direction={setup_direction} | Quality={trade_quality}"
        )
        for k, v in score_breakdown.items():
            log(f"    {k}: {v}")

    # ── STEP 5: Write JSON Results ──
    log("\n" + "=" * 60)
    log("STEP 5: WRITING RESULTS TO SCAN FILES")
    log("=" * 60)

    for symbol in SYMBOLS:
        d1_data = analysis_results.get(symbol, {}).get("D1", {})
        h4_data = analysis_results.get(symbol, {}).get("H4", {})
        h1_data = analysis_results.get(symbol, {}).get("H1", {})

        result = {
            "symbol": symbol,
            "asset_class": "US_STOCKS",
            "scan_timestamp": datetime.utcnow().isoformat(),
            "current_price": scores[symbol]["current_price"],
            "tick_data": all_data[symbol].get("tick", {}),
            "confluence_score": scores[symbol],
            "relative_strength_vs_spx": rel_strength.get(symbol, {}),
            "gap_analysis": {
                "gap": rel_strength.get(symbol, {}).get("gap", 0),
                "type": rel_strength.get(symbol, {}).get("gap_type", "N/A"),
                "gap_pct": rel_strength.get(symbol, {}).get("gap_pct", 0),
                "filled": rel_strength.get(symbol, {}).get("gap_filled", False),
            },
            "analysis": {
                "D1": {
                    "market_structure": d1_data.get("structure", {}).get(
                        "market_structure", "N/A"
                    ),
                    "bos_events": d1_data.get("structure", {}).get("bos_events", []),
                    "choch_events": d1_data.get("structure", {}).get(
                        "choch_events", []
                    ),
                    "fair_value_gaps": d1_data.get("structure", {}).get(
                        "fair_value_gaps", []
                    ),
                    "order_blocks": d1_data.get("structure", {}).get(
                        "order_blocks", []
                    ),
                    "liquidity_levels": d1_data.get("structure", {}).get(
                        "liquidity_levels", []
                    ),
                    "premium_discount": d1_data.get("premium_discount", {}),
                    "indicators": d1_data.get("indicators", {}),
                    "volume": {
                        "profile": d1_data.get("volume_profile", {}),
                        "ad": d1_data.get("volume_ad", {}),
                        "anomalies": d1_data.get("volume_anomalies", {}),
                        "price_analysis": d1_data.get("volume_price", {}),
                    },
                },
                "H4": {
                    "market_structure": h4_data.get("structure", {}).get(
                        "market_structure", "N/A"
                    ),
                    "bos_events": h4_data.get("structure", {}).get("bos_events", []),
                    "choch_events": h4_data.get("structure", {}).get(
                        "choch_events", []
                    ),
                    "fair_value_gaps": h4_data.get("structure", {}).get(
                        "fair_value_gaps", []
                    ),
                    "order_blocks": h4_data.get("structure", {}).get(
                        "order_blocks", []
                    ),
                    "liquidity_levels": h4_data.get("structure", {}).get(
                        "liquidity_levels", []
                    ),
                    "premium_discount": h4_data.get("premium_discount", {}),
                    "indicators": h4_data.get("indicators", {}),
                },
                "H1": {
                    "market_structure": h1_data.get("structure", {}).get(
                        "market_structure", "N/A"
                    ),
                    "bos_events": h1_data.get("structure", {}).get("bos_events", []),
                    "choch_events": h1_data.get("structure", {}).get(
                        "choch_events", []
                    ),
                    "fair_value_gaps": h1_data.get("structure", {}).get(
                        "fair_value_gaps", []
                    ),
                    "order_blocks": h1_data.get("structure", {}).get(
                        "order_blocks", []
                    ),
                    "liquidity_levels": h1_data.get("structure", {}).get(
                        "liquidity_levels", []
                    ),
                },
            },
            "sector_note": "Tech sector - monitor NAS100/US500 correlation",
            "trading_notes": {
                "session": "NY only (13:30-20:00 UTC)",
                "max_lot": "Check broker limits (typically 0.1-1.0 for stocks)",
                "spread_warning": "Wider spreads than forex - factor into SL placement",
            },
        }

        # Check position conflict
        symbol_positions = [
            p for p in stock_positions if symbol.replace("m", "") in p["symbol"]
        ]
        if symbol_positions:
            pos = symbol_positions[0]
            pos_direction = pos["type"]
            analysis_direction = scores[symbol]["setup_direction"]

            if analysis_direction == "NONE":
                conflict = "NEUTRAL - No clear setup"
            elif (pos_direction == "SELL" and analysis_direction == "BUY") or (
                pos_direction == "BUY" and analysis_direction == "SELL"
            ):
                conflict = f"CONFLICT! Position is {pos_direction} but analysis suggests {analysis_direction}"
            else:
                conflict = f"ALIGNED - Position {pos_direction} matches analysis {analysis_direction}"

            result["existing_position"] = {
                "direction": pos_direction,
                "volume": pos["volume"],
                "entry": pos["open_price"],
                "sl": pos["sl"],
                "tp": pos["tp"],
                "current_pnl": pos["profit"],
                "analysis_direction": analysis_direction,
                "conflict_status": conflict,
            }

        # Write JSON file
        filepath = OUTPUT_DIR / f"{symbol}.json"
        with open(filepath, "w") as f:
            json.dump(result, f, indent=2, default=str)
        log(f"  Written: {filepath}")

    # ── STEP 6: Summary Table ──
    log("\n" + "=" * 60)
    log("STEP 6: SUMMARY - US STOCKS RANKED BY ICT CONFLUENCE")
    log("=" * 60)

    ranked = sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True)

    log(
        f"\n{'Rank':<5} {'Symbol':<8} {'Score':<7} {'Bias':<10} {'Direction':<10} {'Price':<12} {'RS vs SPX':<12} {'Gap':<10} {'Quality'}"
    )
    log("-" * 100)

    for rank, (symbol, sc) in enumerate(ranked, 1):
        rs = rel_strength.get(symbol, {}).get("relative_strength_5d", 0)
        gap_type = rel_strength.get(symbol, {}).get("gap_type", "N/A")
        price = sc["current_price"]
        log(
            f"  {rank:<5} {symbol:<8} {sc['score']}/12   {sc['htf_bias']:<10} {sc['setup_direction']:<10} ${price:<11} {rs:+.2f}%      {gap_type:<10} {sc['trade_quality']}"
        )

    # Position conflict warnings
    log("\n" + "=" * 60)
    log("POSITION CONFLICT CHECK")
    log("=" * 60)

    for symbol in ["AMZNm", "MSFTm"]:
        sc = scores.get(symbol, {})
        direction = sc.get("setup_direction", "NONE")
        bias = sc.get("htf_bias", "NEUTRAL")

        if symbol == "AMZNm":
            pos_dir = "SELL"
            entry = 216.93
            log(f"\n  {symbol}: Open SELL 0.97 lot @ {entry}")
        elif symbol == "MSFTm":
            pos_dir = "SELL"
            entry = 408.38
            log(f"\n  {symbol}: Open SELL 0.56 lot @ {entry}")

        if direction == "BUY":
            log(
                f"    WARNING: Analysis suggests BUY but position is SELL - CONTRADICTION!"
            )
            log(f"    Consider: Close/reduce position or review higher TF")
        elif direction == "SELL":
            log(f"    ALIGNED: Analysis confirms SELL direction - position supported")
        else:
            log(f"    NEUTRAL: No clear directional signal - monitor closely")

        log(f"    HTF Bias: {bias} | Score: {sc.get('score', 0)}/12")

    # Top picks
    log("\n" + "=" * 60)
    log("TOP STOCK PICKS")
    log("=" * 60)

    tradeable = [(s, sc) for s, sc in ranked if sc["score"] >= 5]
    if tradeable:
        for symbol, sc in tradeable[:3]:
            log(f"\n  {symbol}:")
            log(f"    Direction: {sc['setup_direction']} | Score: {sc['score']}/12")
            log(
                f"    Entry: ${sc['current_price']} | SL: ${sc['sl']} | TP1: ${sc['tp1']} | TP2: ${sc['tp2']}"
            )
            log(f"    R:R = 1:{sc['rr_ratio']} | ATR(D1): {sc['atr_d1']}")
            rs = rel_strength.get(symbol, {})
            log(
                f"    RS vs SPX (5d): {rs.get('relative_strength_5d', 0):+.2f}% | 20d: {rs.get('relative_strength_20d', 0):+.2f}%"
            )
    else:
        log("  No stocks meet minimum confluence score of 5/12")
        log("  STAND ASIDE - Wait for better setups")

    log("\n" + "=" * 60)
    log("SCAN COMPLETE")
    log("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        traceback.print_exc()
