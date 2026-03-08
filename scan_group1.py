"""
Group 1 Scanner: Indices, Gold & Crypto
Full ICT Smart Money analysis for 6 instruments.
"""

import sys, json, os
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, ".")
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
    volume_price_analysis,
)
from tools.pattern_tools import detect_candlestick_patterns

SYMBOLS = ["USTECm", "US30m", "US500m", "XAUUSDm", "BTCUSDm", "ETHUSDm"]
OUTPUT_DIR = r"C:\Users\Mamoud\Desktop\Claude-Skills-Collection\sessions\trading_20260305_194417\scans"
TIMEFRAMES_STRUCTURE = ["D1", "H4", "H1"]
TIMEFRAMES_INDICATORS = ["H4", "H1", "M15"]
TIMEFRAMES_DATA = ["D1", "H4", "H1", "M15"]

os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_full_scan():
    # Step 1: Connect
    print("=" * 80)
    print("STEP 1: CONNECTING TO MT5")
    print("=" * 80)
    init = initialize_mt5()
    print(json.dumps(init, indent=2, default=str))
    if init.get("status") != "connected":
        print("FATAL: Cannot connect to MT5")
        return

    all_results = {}

    for symbol in SYMBOLS:
        print("\n" + "=" * 80)
        print(f"SCANNING: {symbol}")
        print("=" * 80)

        result = {
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "group1_indices_gold_crypto",
            "data": {},
            "structure": {},
            "indicators": {},
            "volume": {},
            "patterns": {},
            "premium_discount": {},
        }

        # Step 1: Fetch data for all timeframes
        print(f"\n--- {symbol}: Fetching OHLCV Data ---")
        for tf in TIMEFRAMES_DATA:
            data = fetch_ohlcv_data(symbol, tf, 200)
            if data.get("status") == "success":
                result["data"][tf] = data
                latest = data.get("latest", {})
                print(
                    f"  {tf}: {data['candles_count']} bars | Last close: {latest.get('close')} | Time: {latest.get('time')}"
                )
            else:
                print(f"  {tf}: FAILED - {data.get('message', 'unknown error')}")
                result["data"][tf] = data

        # Get current tick
        tick = fetch_tick_data(symbol)
        result["tick"] = tick
        if tick.get("status") == "success":
            print(
                f"  TICK: Bid={tick['bid']} Ask={tick['ask']} Spread={tick.get('spread_points', 'N/A')}pts"
            )

        # Step 2: Market Structure Analysis
        print(f"\n--- {symbol}: Market Structure Analysis ---")
        for tf in TIMEFRAMES_STRUCTURE:
            if result["data"].get(tf, {}).get("status") == "success":
                bars = result["data"][tf]["data"]
                struct = analyze_market_structure(bars)
                result["structure"][tf] = struct
                if struct.get("status") == "success":
                    print(
                        f"  {tf}: Structure={struct['market_structure']} | BOS={len(struct.get('bos_events', []))} | CHoCH={len(struct.get('choch_events', []))} | FVG={len(struct.get('fair_value_gaps', []))} | OB={len(struct.get('order_blocks', []))}"
                    )
                else:
                    print(f"  {tf}: {struct.get('message', 'error')}")
            else:
                print(f"  {tf}: No data available")

        # Premium/Discount zones on H4
        if result["data"].get("H4", {}).get("status") == "success":
            pd_zones = find_premium_discount_zones(result["data"]["H4"]["data"])
            result["premium_discount"] = pd_zones
            if pd_zones.get("status") == "success":
                print(
                    f"  Premium/Discount: Zone={pd_zones['zone']} | Position={pd_zones['range_position']}% | EQ={pd_zones['equilibrium']}"
                )

        # Step 3: Indicator Analysis
        print(f"\n--- {symbol}: Indicator Analysis ---")
        for tf in TIMEFRAMES_INDICATORS:
            if result["data"].get(tf, {}).get("status") == "success":
                bars = result["data"][tf]["data"]
                indics = calculate_all_indicators(bars)
                result["indicators"][tf] = indics
                if indics.get("status") == "success":
                    rsi = indics["rsi"]
                    macd = indics["macd"]
                    adx = indics["adx"]
                    bb = indics["bollinger_bands"]
                    ma = indics["moving_averages"]
                    print(
                        f"  {tf}: RSI={rsi['value']}({rsi['condition']}) | MACD={macd['crossover']}({macd['histogram_trend']}) | ADX={adx['value']}({adx['trend_strength']},{adx['direction']}) | BB={bb['position']}({bb['squeeze']}) | SMA200={ma['price_vs_sma200']} | Cross={ma['sma_cross']}"
                    )
                else:
                    print(f"  {tf}: {indics.get('message', 'error')}")
            else:
                print(f"  {tf}: No data available")

        # Step 4: Volume Analysis
        print(f"\n--- {symbol}: Volume Analysis ---")
        if result["data"].get("H1", {}).get("status") == "success":
            bars = result["data"]["H1"]["data"]

            vol_profile = analyze_volume_profile(bars)
            result["volume"]["profile"] = vol_profile
            if vol_profile.get("status") == "success":
                print(
                    f"  Profile: POC={vol_profile['poc']} | VAH={vol_profile['value_area_high']} | VAL={vol_profile['value_area_low']} | Price vs POC: {vol_profile['price_vs_poc']}"
                )

            vol_ad = analyze_accumulation_distribution(bars)
            result["volume"]["accumulation"] = vol_ad
            if vol_ad.get("status") == "success":
                print(
                    f"  A/D: Flow={vol_ad['overall_flow']} | CMF={vol_ad['cmf']['value']}({vol_ad['cmf']['signal']}) | OBV trend={vol_ad['obv']['trend']} | VWAP={vol_ad['vwap']['value']}({vol_ad['vwap']['price_vs_vwap']})"
                )
                if vol_ad["divergences"]["any_divergence"]:
                    print(
                        f"  *** DIVERGENCE DETECTED: Price-A/D={vol_ad['divergences']['price_ad']} Price-OBV={vol_ad['divergences']['price_obv']}"
                    )

            vol_anom = analyze_volume_anomalies(bars)
            result["volume"]["anomalies"] = vol_anom
            if vol_anom.get("status") == "success":
                print(
                    f"  Anomalies: RelVol={vol_anom['relative_volume']}({vol_anom['relative_volume_label']}) | Spikes={vol_anom['spike_count']} | Trend={vol_anom['volume_trend']} | Climax={vol_anom['is_climax_volume']} | DryUp={vol_anom['is_dryup_volume']}"
                )

            vol_vpa = volume_price_analysis(bars)
            result["volume"]["vpa"] = vol_vpa
            if vol_vpa.get("status") == "success":
                summary = vol_vpa["summary"]
                print(
                    f"  VPA: {summary['overall']} | Demand={summary['demand_signals']} | Supply={summary['supply_signals']} | Absorption={summary['absorption_signals']}"
                )

        # Step 5: Candlestick Patterns
        print(f"\n--- {symbol}: Candlestick Patterns ---")
        for tf in ["H4", "H1"]:
            if result["data"].get(tf, {}).get("status") == "success":
                bars = result["data"][tf]["data"]
                pats = detect_candlestick_patterns(bars)
                result["patterns"][tf] = pats
                if pats.get("status") == "success":
                    recent = pats.get("recent_patterns", [])
                    if recent:
                        print(
                            f"  {tf}: {len(recent)} patterns - {[p.get('pattern', '?') for p in recent[:5]]}"
                        )
                    else:
                        print(f"  {tf}: No recent patterns")

        all_results[symbol] = result
        print(f"\n{'=' * 40} {symbol} DATA COLLECTION COMPLETE {'=' * 40}")

    # Now output the raw data as JSON for AI analysis
    print("\n\n" + "=" * 80)
    print("FULL DATA DUMP FOR AI ANALYSIS")
    print("=" * 80)

    for symbol, result in all_results.items():
        print(f"\n{'#' * 80}")
        print(f"# {symbol} - COMPLETE ANALYSIS DATA")
        print(f"{'#' * 80}")

        # Structure summary
        print(f"\n## {symbol} STRUCTURE:")
        for tf in TIMEFRAMES_STRUCTURE:
            s = result["structure"].get(tf, {})
            if s.get("status") == "success":
                print(
                    json.dumps(
                        {
                            "timeframe": tf,
                            "market_structure": s["market_structure"],
                            "current_price": s["current_price"],
                            "bos_events": s["bos_events"],
                            "choch_events": s["choch_events"],
                            "fair_value_gaps": s["fair_value_gaps"],
                            "order_blocks": s["order_blocks"],
                            "liquidity_levels": s["liquidity_levels"],
                            "swing_highs": s["swing_highs"],
                            "swing_lows": s["swing_lows"],
                        },
                        indent=2,
                        default=str,
                    )
                )

        # Premium/Discount
        pd_z = result.get("premium_discount", {})
        if pd_z.get("status") == "success":
            print(f"\n## {symbol} PREMIUM/DISCOUNT:")
            print(json.dumps(pd_z, indent=2, default=str))

        # Indicators summary
        print(f"\n## {symbol} INDICATORS:")
        for tf in TIMEFRAMES_INDICATORS:
            ind = result["indicators"].get(tf, {})
            if ind.get("status") == "success":
                print(f"\n### {tf}:")
                print(
                    json.dumps(
                        {k: v for k, v in ind.items() if k != "status"},
                        indent=2,
                        default=str,
                    )
                )

        # Volume
        print(f"\n## {symbol} VOLUME:")
        for k, v in result.get("volume", {}).items():
            if v.get("status") == "success":
                print(f"\n### {k}:")
                compact = {key: val for key, val in v.items() if key != "status"}
                print(json.dumps(compact, indent=2, default=str))

        # Patterns
        print(f"\n## {symbol} PATTERNS:")
        for tf, p in result.get("patterns", {}).items():
            if p.get("status") == "success":
                print(
                    f"  {tf}: {json.dumps(p.get('recent_patterns', []), default=str)}"
                )

    shutdown_mt5()
    print("\n\nMT5 disconnected. Data collection complete.")
    print("AI will now perform ICT Confluence Scoring on all collected data.")


if __name__ == "__main__":
    run_full_scan()
