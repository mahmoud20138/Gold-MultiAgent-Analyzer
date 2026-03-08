"""
MT5 Data Tools - All MetaTrader 5 connection and data retrieval functions.
"""
import MetaTrader5 as mt5
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json
from pathlib import Path

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger
from utils.data_formatter import df_to_records, safe_float, AnalysisResult

logger = get_logger("mt5_tools")


# ═══════════════════════════════════════════════════════════════════
# TIMEFRAME MAPPING
# ═══════════════════════════════════════════════════════════════════

TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}


# ═══════════════════════════════════════════════════════════════════
# CONNECTION TOOLS
# ═══════════════════════════════════════════════════════════════════

def initialize_mt5(account: int = None, password: str = None, 
                   server: str = None, path: str = None) -> Dict:
    """
    Initialize connection to MetaTrader 5 terminal.
    
    Args:
        account: MT5 account number
        password: MT5 password
        server: MT5 server name
        path: Path to MT5 terminal (optional)
    
    Returns:
        Connection status and account info
    """
    # Load credentials from config if not provided
    if account is None or password is None or server is None:
        config_path = Path(__file__).parent.parent / "config" / "mt5_credentials.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                creds = json.load(f)
                account = account or creds.get('account')
                password = password or creds.get('password')
                server = server or creds.get('server')
                path = path or creds.get('path')
    
    # Initialize MT5
    if path:
        if not mt5.initialize(path):
            logger.error(f"MT5 initialize() failed: {mt5.last_error()}")
            return {"status": "error", "message": f"Initialize failed: {mt5.last_error()}"}
    else:
        if not mt5.initialize():
            logger.error(f"MT5 initialize() failed: {mt5.last_error()}")
            return {"status": "error", "message": f"Initialize failed: {mt5.last_error()}"}
    
    # Login if credentials provided
    if account and password and server:
        authorized = mt5.login(account, password=password, server=server)
        if not authorized:
            mt5.shutdown()
            logger.error(f"MT5 login failed: {mt5.last_error()}")
            return {"status": "error", "message": f"Login failed: {mt5.last_error()}"}
    
    # Get account info
    account_info = mt5.account_info()
    if account_info is None:
        logger.warning("Could not retrieve account info")
        return {"status": "connected", "account": account, "message": "Connected but no account info"}
    
    info = account_info._asdict()
    
    logger.info(f"Connected to MT5 - Account: {info.get('login')}, Balance: {info.get('balance')}")
    
    return {
        "status": "connected",
        "account": info.get('login'),
        "balance": safe_float(info.get('balance')),
        "equity": safe_float(info.get('equity')),
        "margin": safe_float(info.get('margin')),
        "free_margin": safe_float(info.get('margin_free')),
        "leverage": info.get('leverage'),
        "server": info.get('server'),
        "currency": info.get('currency'),
        "company": info.get('company')
    }


def shutdown_mt5() -> Dict:
    """Shutdown MT5 connection."""
    mt5.shutdown()
    logger.info("MT5 connection closed")
    return {"status": "disconnected"}


def check_connection() -> Dict:
    """Check if MT5 is connected."""
    try:
        account_info = mt5.account_info()
        if account_info is None:
            return {"connected": False, "message": "Not connected"}
        return {"connected": True, "account": account_info.login}
    except Exception as e:
        return {"connected": False, "message": str(e)}


# ═══════════════════════════════════════════════════════════════════
# DATA FETCHING TOOLS
# ═══════════════════════════════════════════════════════════════════

def fetch_ohlcv_data(symbol: str, timeframe: str = "H1", 
                     num_candles: int = 500) -> Dict:
    """
    Fetch OHLCV candlestick data for a symbol.
    
    Args:
        symbol: Trading symbol (e.g., 'XAUUSDm', 'EURUSDm')
        timeframe: Timeframe string ('M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1')
        num_candles: Number of candles to fetch
    
    Returns:
        Dictionary with OHLCV data
    """
    tf = TIMEFRAME_MAP.get(timeframe)
    if tf is None:
        return {"status": "error", "message": f"Invalid timeframe: {timeframe}"}
    
    # Ensure symbol is visible
    if not mt5.symbol_select(symbol, True):
        logger.warning(f"Could not select symbol {symbol}")
    
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, num_candles)
    
    if rates is None or len(rates) == 0:
        error = mt5.last_error()
        logger.error(f"No data for {symbol} {timeframe}: {error}")
        return {"status": "error", "message": f"No data: {error}", "symbol": symbol}
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    latest = df.iloc[-1]
    
    logger.debug(f"Fetched {len(df)} candles for {symbol} {timeframe}")
    
    return {
        "status": "success",
        "symbol": symbol,
        "timeframe": timeframe,
        "candles_count": len(df),
        "data": df_to_records(df),
        "latest": {
            "time": str(latest['time']),
            "open": safe_float(latest['open']),
            "high": safe_float(latest['high']),
            "low": safe_float(latest['low']),
            "close": safe_float(latest['close']),
            "tick_volume": int(latest['tick_volume']),
            "real_volume": int(latest.get('real_volume', 0)),
            "spread": int(latest.get('spread', 0))
        },
        "latest_close": safe_float(latest['close']),
        "latest_time": str(latest['time'])
    }


def fetch_tick_data(symbol: str) -> Dict:
    """
    Get real-time tick data for a symbol.
    
    Args:
        symbol: Trading symbol
    
    Returns:
        Current bid/ask/spread data
    """
    # Ensure symbol is visible
    mt5.symbol_select(symbol, True)
    
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return {"status": "error", "message": f"No tick data for {symbol}"}
    
    return {
        "status": "success",
        "symbol": symbol,
        "bid": safe_float(tick.bid),
        "ask": safe_float(tick.ask),
        "last": safe_float(tick.last),
        "volume": int(tick.volume),
        "time": str(datetime.fromtimestamp(tick.time, tz=timezone.utc)),
        "spread": round(tick.ask - tick.bid, 6),
        "spread_points": round((tick.ask - tick.bid) * 100000, 1)  # Approximate points
    }


def fetch_symbol_info(symbol: str) -> Dict:
    """
    Get detailed symbol specifications.
    
    Args:
        symbol: Trading symbol
    
    Returns:
        Symbol specifications (lot sizes, digits, trading hours, etc.)
    """
    # Ensure symbol is visible
    mt5.symbol_select(symbol, True)
    
    info = mt5.symbol_info(symbol)
    if info is None:
        return {"status": "error", "message": f"No info for {symbol}"}
    
    return {
        "status": "success",
        "symbol": symbol,
        "description": info.description,
        "currency_base": info.currency_base,
        "currency_profit": info.currency_profit,
        "currency_margin": info.currency_margin,
        "point": safe_float(info.point),
        "digits": info.digits,
        "spread": info.spread,
        "spread_float": info.spread_float,
        "tick_size": safe_float(info.trade_tick_size),
        "tick_value": safe_float(info.trade_tick_value),
        "contract_size": safe_float(info.trade_contract_size),
        "volume_min": safe_float(info.volume_min),
        "volume_max": safe_float(info.volume_max),
        "volume_step": safe_float(info.volume_step),
        "swap_long": safe_float(info.swap_long),
        "swap_short": safe_float(info.swap_short),
        "swap_mode": info.swap_mode,
        "trade_mode": info.trade_mode,
        "trade_calc_mode": info.trade_calc_mode,
        "margin_initial": safe_float(info.margin_initial),
        "margin_maintenance": safe_float(info.margin_maintenance),
        "session_deals": info.session_deals,
        "session_buy_orders": info.session_buy_orders,
        "session_sell_orders": info.session_sell_orders,
    }


def fetch_multi_timeframe_data(symbol: str, timeframes: List[str] = None,
                                num_candles: int = 200) -> Dict:
    """
    Fetch data across multiple timeframes for one symbol.
    
    Args:
        symbol: Trading symbol
        timeframes: List of timeframes (default: M15, H1, H4, D1)
        num_candles: Candles per timeframe
    
    Returns:
        Dictionary with data for each timeframe
    """
    if timeframes is None:
        timeframes = ["M15", "H1", "H4", "D1"]
    
    result = {
        "status": "success",
        "symbol": symbol,
        "timeframes": {}
    }
    
    for tf in timeframes:
        data = fetch_ohlcv_data(symbol, tf, num_candles)
        result["timeframes"][tf] = data
    
    return result


def fetch_multiple_pairs(symbols: List[str], timeframe: str = "H1",
                         num_candles: int = 200) -> Dict:
    """
    Fetch latest data for multiple symbols at once.
    
    Args:
        symbols: List of trading symbols
        timeframe: Timeframe for all symbols
        num_candles: Number of candles
    
    Returns:
        Dictionary with data for each symbol
    """
    results = {
        "status": "success",
        "timeframe": timeframe,
        "symbols": {}
    }
    
    for symbol in symbols:
        data = fetch_ohlcv_data(symbol, timeframe, num_candles)
        results["symbols"][symbol] = {
            "status": data.get("status"),
            "latest_close": data.get("latest_close"),
            "candles_count": data.get("candles_count"),
            "data": data.get("data", [])[:50]  # Truncate for efficiency
        }
    
    return results


def fetch_all_correlated_instruments(timeframe: str = "H1",
                                      num_candles: int = 500) -> Dict:
    """
    Fetch data for ALL gold-correlated instruments.
    
    Loads correlation config and fetches each instrument.
    
    Args:
        timeframe: Timeframe for data
        num_candles: Number of candles
    
    Returns:
        Dictionary with all instrument data
    """
    # Load correlation config
    config_path = Path(__file__).parent.parent / "config" / "correlation_config.json"
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    instruments = config.get("correlated_instruments", {})
    results = {}
    
    # Try aliases with 'm' suffix first (broker convention), then without
    for symbol, meta in instruments.items():
        # Build candidate list: each alias tried with 'm' suffix then bare
        aliases = meta.get("aliases", [symbol])
        seen = set()
        test_symbols = []
        for alias in aliases:
            for candidate in [f"{alias}m", alias]:
                if candidate not in seen:
                    seen.add(candidate)
                    test_symbols.append(candidate)

        found = False
        for test_symbol in test_symbols:
            data = fetch_ohlcv_data(test_symbol, timeframe, num_candles)
            if data.get("status") == "success":
                results[symbol] = {
                    "data": pd.DataFrame(data["data"]),
                    "type": meta["type"],
                    "expected_corr": meta["expected_corr"],
                    "description": meta["description"],
                    "latest_close": data["latest_close"],
                    "available": True,
                    "resolved_symbol": test_symbol
                }
                found = True
                break

        if not found:
            results[symbol] = {
                "available": False,
                "type": meta["type"],
                "expected_corr": meta["expected_corr"]
            }
    
    return {
        "status": "success",
        "timeframe": timeframe,
        "instruments": results,
        "available_count": sum(1 for v in results.values() if v.get("available"))
    }


# ═══════════════════════════════════════════════════════════════════
# ACCOUNT & POSITION TOOLS
# ═══════════════════════════════════════════════════════════════════

def get_account_info() -> Dict:
    """Get current account information."""
    info = mt5.account_info()
    if info is None:
        return {"status": "error", "message": "Could not get account info"}
    
    return {
        "status": "success",
        "login": info.login,
        "server": info.server,
        "currency": info.currency,
        "balance": safe_float(info.balance),
        "equity": safe_float(info.equity),
        "margin": safe_float(info.margin),
        "free_margin": safe_float(info.margin_free),
        "margin_level": safe_float(info.margin_level) if info.margin_level > 0 else 0,
        "profit": safe_float(info.profit),
        "leverage": info.leverage,
        "company": info.company,
        "name": info.name
    }


def get_open_positions(symbol: str = None) -> Dict:
    """
    Get all open positions, optionally filtered by symbol.
    
    Args:
        symbol: Filter by symbol (optional)
    
    Returns:
        List of open positions
    """
    if symbol:
        positions = mt5.positions_get(symbol=symbol)
    else:
        positions = mt5.positions_get()
    
    if positions is None:
        return {"status": "success", "positions": [], "count": 0}
    
    result = []
    total_profit = 0
    total_margin = 0
    
    for pos in positions:
        pos_dict = pos._asdict()
        total_profit += safe_float(pos_dict.get('profit', 0))
        total_margin += safe_float(pos_dict.get('margin', 0))
        result.append({
            "ticket": pos_dict.get('ticket'),
            "symbol": pos_dict.get('symbol'),
            "type": "BUY" if pos_dict.get('type') == 0 else "SELL",
            "volume": safe_float(pos_dict.get('volume')),
            "open_price": safe_float(pos_dict.get('price_open')),
            "current_price": safe_float(pos_dict.get('price_current')),
            "sl": safe_float(pos_dict.get('sl')),
            "tp": safe_float(pos_dict.get('tp')),
            "profit": safe_float(pos_dict.get('profit')),
            "margin": safe_float(pos_dict.get('margin')),
            "swap": safe_float(pos_dict.get('swap')),
            "commission": safe_float(pos_dict.get('commission')),
            "comment": pos_dict.get('comment'),
            "open_time": str(pos_dict.get('time_setup'))
        })
    
    return {
        "status": "success",
        "positions": result,
        "count": len(result),
        "total_profit": round(total_profit, 2),
        "total_margin": round(total_margin, 2)
    }


def get_total_risk_exposure() -> Dict:
    """Calculate total risk exposure from open positions."""
    positions = get_open_positions()
    
    if positions["count"] == 0:
        return {"total_risk_usd": 0, "position_count": 0}
    
    account = get_account_info()
    equity = account.get("equity", 10000)
    
    # Estimate risk (simplified: use stop loss distance or 2% ATR)
    total_risk = 0
    for pos in positions["positions"]:
        if pos["sl"] > 0:
            sl_distance = abs(pos["current_price"] - pos["sl"])
            risk = sl_distance * pos["volume"] * 100000  # Approx for forex
            total_risk += risk
        else:
            # Assume 2% risk if no SL
            total_risk += equity * 0.02
    
    risk_pct = (total_risk / equity) * 100 if equity > 0 else 0
    
    return {
        "total_risk_usd": round(total_risk, 2),
        "risk_percent": round(risk_pct, 2),
        "position_count": positions["count"],
        "equity": equity
    }


# ═══════════════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Test connection
    print("Testing MT5 connection...")
    result = initialize_mt5()
    print(json.dumps(result, indent=2))
    
    if result["status"] == "connected":
        # Test data fetch
        print("\nFetching XAUUSDm H1 data...")
        data = fetch_ohlcv_data("XAUUSDm", "H1", 10)
        print(f"Status: {data['status']}")
        if data['status'] == 'success':
            print(f"Candles: {data['candles_count']}")
            print(f"Latest: {data['latest']}")
        
        # Test tick data
        print("\nFetching tick data...")
        tick = fetch_tick_data("XAUUSDm")
        print(json.dumps(tick, indent=2))
        
        # Test symbol info
        print("\nFetching symbol info...")
        info = fetch_symbol_info("XAUUSDm")
        print(f"Digits: {info.get('digits')}, Point: {info.get('point')}")
        
        # Shutdown
        shutdown_mt5()
