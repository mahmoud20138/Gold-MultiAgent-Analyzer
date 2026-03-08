"""
MT5 Data Fetcher Agent - Retrieves market data from MetaTrader 5.
"""
import json
from typing import Dict, List, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.mt5_tools import (
    initialize_mt5, shutdown_mt5, check_connection,
    fetch_ohlcv_data, fetch_tick_data, fetch_symbol_info,
    fetch_multi_timeframe_data, fetch_multiple_pairs,
    fetch_all_correlated_instruments, get_account_info,
    get_open_positions, get_total_risk_exposure
)
from utils.logger import get_logger
from utils.data_formatter import AnalysisResult

logger = get_logger("data_fetcher_agent")


class MT5DataFetcherAgent:
    """
    Agent responsible for fetching all market data from MetaTrader 5.
    
    Responsibilities:
    - Connect to MT5 terminal
    - Fetch OHLCV data for any symbol/timeframe
    - Fetch tick data and symbol info
    - Fetch multi-timeframe data
    - Fetch correlated instruments
    - Get account and position info
    """
    
    def __init__(self):
        self.connected = False
        self.last_fetch = None
    
    def connect(self, account: int = None, password: str = None, 
                server: str = None) -> Dict:
        """Initialize connection to MT5."""
        result = initialize_mt5(account, password, server)
        self.connected = result.get("status") == "connected"
        return result
    
    def disconnect(self) -> Dict:
        """Shutdown MT5 connection."""
        self.connected = False
        return shutdown_mt5()
    
    def check_status(self) -> Dict:
        """Check connection status."""
        return check_connection()
    
    def fetch_gold_data(self, symbol: str = "XAUUSDm", 
                        timeframes: List[str] = None,
                        num_candles: int = 500) -> Dict:
        """
        Fetch complete Gold data across multiple timeframes.
        
        Args:
            symbol: Gold symbol (default XAUUSDm for broker with m suffix)
            timeframes: List of timeframes (default M15, H1, H4, D1)
            num_candles: Candles per timeframe
        
        Returns:
            Multi-timeframe Gold data
        """
        if not self.connected:
            return {"status": "error", "message": "Not connected to MT5"}
        
        if timeframes is None:
            timeframes = ["M15", "H1", "H4", "D1"]
        
        logger.info(f"Fetching Gold data for {symbol} across {timeframes}")
        
        result = fetch_multi_timeframe_data(symbol, timeframes, num_candles)
        
        # Add tick data
        tick = fetch_tick_data(symbol)
        result["tick_data"] = tick
        
        # Add symbol info
        info = fetch_symbol_info(symbol)
        result["symbol_info"] = info
        
        self.last_fetch = result
        return result
    
    def fetch_correlated_data(self, timeframe: str = "H1",
                               num_candles: int = 500) -> Dict:
        """
        Fetch data for all Gold-correlated instruments.
        
        Returns:
            Data for DXY pairs, Silver, Oil, Indices, etc.
        """
        if not self.connected:
            return {"status": "error", "message": "Not connected to MT5"}
        
        logger.info(f"Fetching correlated instruments data ({timeframe})")
        
        return fetch_all_correlated_instruments(timeframe, num_candles)
    
    def fetch_pair_data(self, symbol: str, timeframe: str = "H1",
                        num_candles: int = 500) -> Dict:
        """Fetch data for a single pair."""
        if not self.connected:
            return {"status": "error", "message": "Not connected to MT5"}
        
        return fetch_ohlcv_data(symbol, timeframe, num_candles)
    
    def get_account_status(self) -> Dict:
        """Get current account information."""
        if not self.connected:
            return {"status": "error", "message": "Not connected to MT5"}
        
        account = get_account_info()
        positions = get_open_positions()
        risk = get_total_risk_exposure()
        
        return {
            "status": "success",
            "account": account,
            "positions": positions,
            "risk_exposure": risk
        }
    
    def run_full_fetch(self, symbol: str = "XAUUSDm") -> Dict:
        """
        Run complete data fetch for analysis pipeline.
        
        Returns all data needed for full analysis.
        """
        logger.info(f"Starting full data fetch for {symbol}")
        
        # Check connection
        if not self.connected:
            conn = self.connect()
            if conn.get("status") != "connected":
                return {"status": "error", "message": "Failed to connect to MT5"}
        
        results = {
            "symbol": symbol,
            "status": "success"
        }
        
        # 1. Gold multi-timeframe data
        results["gold_data"] = self.fetch_gold_data(symbol)
        
        # 2. Correlated instruments
        results["correlated_data"] = self.fetch_correlated_data()
        
        # 3. Account status
        results["account"] = self.get_account_status()
        
        logger.info("Full data fetch complete")
        
        return results


# Agent system prompt for OpenClaw orchestration
SYSTEM_PROMPT = """
You are the MT5 Data Fetcher Agent. Your sole responsibility is to connect
to MetaTrader 5, retrieve requested market data, and return it in clean
structured format.

You handle:
- OHLCV data for any symbol and timeframe
- Tick data (bid, ask, spread)
- Symbol specifications (lot sizes, digits, etc.)
- Multi-timeframe data (M15, H1, H4, D1)
- Correlated instruments (DXY pairs, Silver, Oil, Indices)
- Account info and open positions

You NEVER analyze — you only fetch and format data.

Available tools:
- connect(): Initialize MT5 connection
- fetch_gold_data(): Get multi-TF Gold data
- fetch_correlated_data(): Get all correlated instruments
- get_account_status(): Get account/position info
- run_full_fetch(): Complete data fetch for analysis

Always verify connection status before fetching.
Return data in structured format ready for analysis agents.
"""


# For direct testing
if __name__ == "__main__":
    agent = MT5DataFetcherAgent()
    
    print("Connecting to MT5...")
    result = agent.connect()
    print(json.dumps(result, indent=2, default=str))
    
    if result.get("status") == "connected":
        print("\nFetching Gold data...")
        data = agent.fetch_gold_data("XAUUSDm", ["H1", "H4"], 100)
        print(f"Status: {data.get('status')}")
        print(f"Timeframes: {list(data.get('timeframes', {}).keys())}")
        
        print("\nDisconnecting...")
        agent.disconnect()
