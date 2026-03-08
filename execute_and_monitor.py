# -*- coding: utf-8 -*-
"""
Trade Executor & Position Monitor
Reads scan results, identifies qualified trades, executes, and monitors.
"""

import sys
import os
import json
import time
import glob
from datetime import datetime, timezone
from pathlib import Path

# Fix encoding
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).parent))

import MetaTrader5 as mt5

# Configuration
SCANS_DIR = r"C:\Users\Mamoud\Desktop\Claude-Skills-Collection\sessions\trading_20260305_194417\scans"
TRADES_DIR = r"C:\Users\Mamoud\Desktop\Claude-Skills-Collection\sessions\trading_20260305_194417\trades"
DASHBOARD_FILE = r"C:\Users\Mamoud\Desktop\Claude-Skills-Collection\sessions\trading_20260305_194417\dashboard\live_data.json"
MAX_LOT = 0.1
MAX_POSITIONS = 5
MIN_SCORE = 5
FULL_RISK_SCORE = 8
MAX_DAILY_LOSS_PCT = 3.0
MAGIC_NUMBER = 202603


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def extract_score(scan):
    """Safely extract numeric score from scan data."""
    s = scan.get("confluence_score", 0)
    if isinstance(s, dict):
        return int(s.get("total", s.get("score", 0)))
    try:
        return int(s)
    except (TypeError, ValueError):
        return 0


def read_scan_results():
    """Read all scan JSON files and return sorted by score."""
    results = []
    for f in glob.glob(os.path.join(SCANS_DIR, "*.json")):
        try:
            with open(f, "r") as fh:
                data = json.load(fh)
                results.append(data)
        except Exception as e:
            log(f"  Error reading {f}: {e}")

    results.sort(key=lambda x: extract_score(x), reverse=True)
    return results


def get_account_status():
    """Get account info and open positions."""
    info = mt5.account_info()
    if not info:
        return None, []

    account = {
        "balance": info.balance,
        "equity": info.equity,
        "margin": info.margin,
        "free_margin": info.margin_free,
        "profit": info.equity - info.balance,
        "daily_pnl_pct": ((info.equity - info.balance) / info.balance * 100)
        if info.balance
        else 0,
    }

    positions = mt5.positions_get()
    pos_list = []
    if positions:
        for p in positions:
            sym_info = mt5.symbol_info(p.symbol)
            point = sym_info.point if sym_info else 0.0001
            digits = sym_info.digits if sym_info else 5
            raw_diff = (
                (p.price_current - p.price_open)
                if p.type == 0
                else (p.price_open - p.price_current)
            )
            pips = round(raw_diff / point) if point else 0
            sl_dist = abs(p.price_open - p.sl) if p.sl else 0
            r_mult = (raw_diff / sl_dist) if sl_dist > 0 else 0

            pos_list.append(
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
                    "r_multiple": round(r_mult, 2),
                    "time_open": datetime.fromtimestamp(p.time, tz=timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "comment": p.comment,
                    "magic": p.magic,
                }
            )

    return account, pos_list


def execute_trade(symbol, direction, lot, sl, tp, score, strategy):
    """Execute a trade via MT5."""
    if not mt5.symbol_select(symbol, True):
        log(f"  ERROR: Could not select {symbol}")
        return None

    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        log(f"  ERROR: No tick data for {symbol}")
        return None

    sym_info = mt5.symbol_info(symbol)
    if not sym_info:
        log(f"  ERROR: No symbol info for {symbol}")
        return None

    price = tick.ask if direction == "BUY" else tick.bid
    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL

    # Clamp lot size
    lot = min(lot, MAX_LOT)
    lot = max(lot, sym_info.volume_min)

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
        "comment": f"ICT_{strategy}_s{score}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result is None:
        log(f"  ERROR: order_send returned None for {symbol}")
        return None

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        log(
            f"  ERROR: {symbol} order rejected - {result.comment} (code {result.retcode})"
        )
        return None

    log(
        f"  SUCCESS: {symbol} {direction} {lot} lot @ {price} | SL:{sl} TP:{tp} | Ticket: {result.order}"
    )
    return {
        "ticket": result.order,
        "symbol": symbol,
        "direction": direction,
        "volume": lot,
        "entry": price,
        "sl": sl,
        "tp": tp,
        "score": score,
        "strategy": strategy,
        "timestamp": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def update_dashboard(account, positions, scans, signals, trades_executed):
    """Update the dashboard live_data.json with fresh data."""
    instruments = []
    for scan in scans:
        symbol = scan.get("symbol", "")
        if not symbol:
            continue
        tick = mt5.symbol_info_tick(symbol)
        sym_info = mt5.symbol_info(symbol)
        bid = tick.bid if tick else 0
        ask = tick.ask if tick else 0
        spread = (ask - bid) if tick else 0
        digits = sym_info.digits if sym_info else 5

        # Determine category
        cat = "Unknown"
        if "XAU" in symbol:
            cat = "Gold"
        elif any(
            x in symbol
            for x in ["EUR", "GBP", "USD", "AUD", "NZD", "CHF", "CAD", "JPY"]
        ):
            cat = "Forex"
        elif any(x in symbol for x in ["USTEC", "US30", "US500"]):
            cat = "Indices"
        elif any(x in symbol for x in ["BTC", "ETH"]):
            cat = "Crypto"
        else:
            cat = "Stocks"

        indicators = scan.get("indicators", {})
        instruments.append(
            {
                "symbol": symbol,
                "category": cat,
                "bid": round(bid, digits),
                "ask": round(ask, digits),
                "spread": round(spread, digits + 1),
                "change_pct": scan.get("change_pct", 0),
                "trend": scan.get("direction", "neutral").lower(),
                "rsi": indicators.get("rsi", {}).get("value", 50)
                if isinstance(indicators.get("rsi"), dict)
                else indicators.get("rsi", 50),
                "macd_signal": indicators.get("macd", {}).get("crossover", "neutral")
                if isinstance(indicators.get("macd"), dict)
                else indicators.get("macd", "neutral"),
                "ema_alignment": indicators.get("ema_alignment", "neutral"),
                "confluence_score": extract_score(scan),
                "atr": indicators.get("atr", {}).get("value", None)
                if isinstance(indicators.get("atr"), dict)
                else indicators.get("atr", None),
            }
        )

    # Build signals from high-score scans
    sigs = []
    for scan in scans:
        score = extract_score(scan)
        direction = scan.get("direction", "NEUTRAL")
        if score >= MIN_SCORE and direction not in ["NEUTRAL", "NONE", "WAIT"]:
            sigs.append(
                {
                    "timestamp": datetime.now(tz=timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "type": "SIGNAL",
                    "symbol": scan.get("symbol", ""),
                    "direction": direction,
                    "score": score,
                    "strategy": scan.get("strategy", "ICT Multi-Factor"),
                    "entry": scan.get("key_levels", {}).get("entry", 0),
                    "sl": scan.get("key_levels", {}).get("stop_loss", 0),
                    "tp": scan.get("key_levels", {}).get("take_profit", 0),
                    "factors": list(scan.get("ict_factors", {}).keys())[:8]
                    if isinstance(scan.get("ict_factors"), dict)
                    else [],
                }
            )

    # Add trade execution signals
    for t in trades_executed:
        sigs.append(
            {
                "timestamp": t["timestamp"],
                "type": "TRADE",
                "symbol": t["symbol"],
                "direction": t["direction"],
                "score": t["score"],
                "strategy": t["strategy"],
                "entry": t["entry"],
                "sl": t["sl"],
                "tp": t["tp"],
                "factors": ["EXECUTED"],
            }
        )

    sigs.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Session info
    h = datetime.now(tz=timezone.utc).hour
    if 8 <= h < 12:
        session = "London"
        kz = 8 <= h < 11
    elif 12 <= h < 13:
        session = "London/NY Overlap"
        kz = True
    elif 13 <= h < 22:
        session = "New York"
        kz = 13 <= h < 17
    else:
        session = "Asian"
        kz = h >= 23 or h < 3

    payload = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "account": account,
        "instruments": instruments,
        "positions": positions,
        "signals": sigs[:15],
        "session": {
            "current": session,
            "killzone_active": kz,
            "next_event": "None",
            "server_time": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        },
        "stats": {
            "win_rate": 0,
            "avg_rr": 0,
            "today_trades": len(positions),
            "total_signals_today": len(sigs),
        },
    }

    try:
        tmp = DASHBOARD_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
        os.replace(tmp, DASHBOARD_FILE)
        log(
            f"Dashboard updated: {len(instruments)} instruments, {len(positions)} positions, {len(sigs)} signals"
        )
    except Exception as e:
        log(f"Dashboard update error: {e}")


def monitor_positions():
    """Check positions and apply trailing stop logic."""
    positions = mt5.positions_get()
    if not positions:
        return

    for p in positions:
        if p.magic != MAGIC_NUMBER:
            continue

        sym_info = mt5.symbol_info(p.symbol)
        if not sym_info:
            continue

        point = sym_info.point
        sl_dist = abs(p.price_open - p.sl) if p.sl else 0

        if sl_dist <= 0:
            continue

        if p.type == 0:  # BUY
            raw_diff = p.price_current - p.price_open
        else:  # SELL
            raw_diff = p.price_open - p.price_current

        r_multiple = raw_diff / sl_dist

        # Move SL to breakeven at +1R
        if r_multiple >= 1.0:
            current_sl_distance = abs(p.price_open - p.sl) if p.sl else 0
            new_sl_distance = abs(p.price_open - p.price_open)  # breakeven = 0

            # Only modify if SL is not already at breakeven
            if p.sl and abs(p.sl - p.price_open) > point * 5:
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "symbol": p.symbol,
                    "position": p.ticket,
                    "sl": p.price_open,
                    "tp": p.tp,
                }
                result = mt5.order_send(request)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    log(
                        f"  TRAILING: {p.symbol} SL moved to breakeven ({p.price_open})"
                    )
                else:
                    comment = result.comment if result else "None"
                    log(f"  TRAILING FAILED: {p.symbol} - {comment}")


def main():
    log("=" * 70)
    log("TRADE EXECUTOR & POSITION MONITOR")
    log("=" * 70)

    # Phase 1: Connect to MT5
    log("\nPhase 1: Connecting to MT5...")
    if not mt5.initialize():
        log(f"MT5 connection failed: {mt5.last_error()}")
        return
    info = mt5.account_info()
    if not info:
        log("Could not get account info")
        return
    log(f"Connected: Account #{info.login} | Balance: ${info.balance:.2f}")

    # Phase 2: Read scan results
    log("\nPhase 2: Reading scan results...")
    scans = read_scan_results()
    log(f"Loaded {len(scans)} scan results")

    # Display ranked results
    log("\n--- ALL INSTRUMENTS RANKED BY SCORE ---")
    log(f"{'Rank':>4} {'Symbol':>10} {'Score':>6} {'Direction':>10} {'Quality':>15}")
    log("-" * 55)
    for i, s in enumerate(scans, 1):
        score = extract_score(s)
        direction = s.get("direction", "?")
        quality = (
            "FULL RISK"
            if score >= FULL_RISK_SCORE
            else "HALF RISK"
            if score >= MIN_SCORE
            else "NO TRADE"
        )
        log(
            f"{i:>4} {s.get('symbol', '?'):>10} {score:>4}/12 {direction:>10} {quality:>15}"
        )

    # Phase 3: Check account
    log("\nPhase 3: Checking account status...")
    account, positions = get_account_status()
    if not account:
        log("Could not get account info")
        return

    log(f"Balance: ${account['balance']:.2f} | Equity: ${account['equity']:.2f}")
    log(f"Daily P/L: ${account['profit']:.2f} ({account['daily_pnl_pct']:.2f}%)")
    log(f"Open positions: {len(positions)} / {MAX_POSITIONS}")

    for p in positions:
        log(
            f"  {p['symbol']} {p['type']} {p['volume']} @ {p['price_open']} | P/L: ${p['profit']:.2f} | R: {p['r_multiple']:.2f}"
        )

    # Check daily loss
    if abs(account["daily_pnl_pct"]) >= MAX_DAILY_LOSS_PCT:
        log(
            f"\n*** DAILY LOSS LIMIT REACHED ({account['daily_pnl_pct']:.2f}%) - NO NEW TRADES ***"
        )
        update_dashboard(account, positions, scans, [], [])
        return

    # Phase 4: Identify and execute qualified trades
    log("\nPhase 4: Evaluating trade candidates...")
    open_symbols = [p["symbol"] for p in positions]
    slots_available = MAX_POSITIONS - len(positions)
    trades_executed = []

    if slots_available <= 0:
        log(f"Max positions reached ({len(positions)}/{MAX_POSITIONS}) - no new trades")
    else:
        for scan in scans:
            if slots_available <= 0:
                break

            symbol = scan.get("symbol", "")
            score = extract_score(scan)
            direction = scan.get("direction", "NEUTRAL")

            if score < MIN_SCORE:
                continue
            if direction in ["NEUTRAL", "NONE", "WAIT"]:
                continue
            if symbol in open_symbols:
                log(f"  SKIP {symbol}: already have open position")
                continue

            # Get entry levels
            key_levels = scan.get("key_levels", {})
            entry = key_levels.get("entry", 0)
            sl = key_levels.get("stop_loss", 0)
            tp = key_levels.get("take_profit", 0)

            if not entry or not sl or not tp:
                # Calculate from ATR if levels missing
                indicators = scan.get("indicators", {})
                atr_data = indicators.get("atr", {})
                atr = atr_data.get("value", 0) if isinstance(atr_data, dict) else 0
                if not atr:
                    log(f"  SKIP {symbol}: no key levels or ATR data")
                    continue

                tick = mt5.symbol_info_tick(symbol)
                if not tick:
                    continue

                entry = tick.ask if direction == "BUY" else tick.bid
                if direction == "BUY":
                    sl = round(entry - 1.5 * atr, 5)
                    tp = round(entry + 3.0 * atr, 5)
                else:
                    sl = round(entry + 1.5 * atr, 5)
                    tp = round(entry - 3.0 * atr, 5)

            # Determine lot size
            lot = MAX_LOT if score >= FULL_RISK_SCORE else MAX_LOT / 2

            # Get strategy name
            strategy = scan.get("strategy", "ICT")
            if isinstance(strategy, dict):
                strategy = "ICT"

            log(f"\n  EXECUTING: {symbol} {direction} {lot} lot | Score: {score}")
            log(f"    Entry: {entry} | SL: {sl} | TP: {tp}")

            result = execute_trade(symbol, direction, lot, sl, tp, score, strategy)
            if result:
                trades_executed.append(result)
                open_symbols.append(symbol)
                slots_available -= 1

    # Phase 5: Save trade log
    log(f"\nPhase 5: Saving trade log ({len(trades_executed)} trades)...")
    os.makedirs(TRADES_DIR, exist_ok=True)
    trade_log_path = os.path.join(TRADES_DIR, "trade_log.json")
    existing_trades = []
    if os.path.exists(trade_log_path):
        with open(trade_log_path, "r") as f:
            existing_trades = json.load(f).get("trades", [])

    all_trades = existing_trades + trades_executed
    with open(trade_log_path, "w") as f:
        json.dump({"trades": all_trades}, f, indent=2, default=str)
    log(f"Trade log saved: {len(all_trades)} total trades")

    # Phase 6: Update dashboard
    log("\nPhase 6: Updating dashboard...")
    account, positions = get_account_status()
    update_dashboard(account, positions, scans, [], trades_executed)

    # Phase 7: Monitor loop
    log("\n" + "=" * 70)
    log("MONITORING MODE - Checking every 30 seconds")
    log("Press Ctrl+C to stop")
    log("=" * 70)

    iteration = 0
    while True:
        iteration += 1
        try:
            # Refresh account & positions
            account, positions = get_account_status()

            if positions:
                log(f"\n[Monitor #{iteration}] {len(positions)} positions:")
                for p in positions:
                    status = "PROFIT" if p["profit"] > 0 else "LOSS"
                    log(
                        f"  {p['symbol']} {p['type']} {p['volume']} | P/L: ${p['profit']:.2f} | R: {p['r_multiple']:.2f} [{status}]"
                    )

                # Apply trailing stops
                monitor_positions()
            else:
                log(f"\n[Monitor #{iteration}] No open positions")

            # Check daily loss
            if account and abs(account.get("daily_pnl_pct", 0)) >= MAX_DAILY_LOSS_PCT:
                log(
                    f"\n*** DAILY LOSS LIMIT HIT ({account['daily_pnl_pct']:.2f}%) - CLOSING ALL ***"
                )
                # Close all positions
                for p in mt5.positions_get() or []:
                    close_type = (
                        mt5.ORDER_TYPE_SELL if p.type == 0 else mt5.ORDER_TYPE_BUY
                    )
                    tick = mt5.symbol_info_tick(p.symbol)
                    close_price = tick.bid if p.type == 0 else tick.ask
                    request = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": p.symbol,
                        "volume": p.volume,
                        "type": close_type,
                        "position": p.ticket,
                        "price": close_price,
                        "deviation": 30,
                        "magic": MAGIC_NUMBER,
                        "comment": "DAILY_LOSS_LIMIT",
                        "type_filling": mt5.ORDER_FILLING_IOC,
                    }
                    result = mt5.order_send(request)
                    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                        log(f"  CLOSED: {p.symbol} ticket {p.ticket}")
                break

            # Update dashboard
            update_dashboard(account, positions, scans, [], trades_executed)

        except Exception as e:
            log(f"Monitor error: {e}")

        time.sleep(30)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\nMonitor stopped by user.")
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass
