"""
Test script for MT5 Gold Trading System.
Run to verify all components are working.
"""
import sys
import os
from pathlib import Path

# Fix Windows console encoding for unicode output
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test all imports work."""
    print("Testing imports...")
    
    try:
        from utils.logger import get_logger
        from utils.time_utils import get_session_context
        from utils.data_formatter import safe_float, AnalysisResult
        print("  ✅ Utils")
    except Exception as e:
        print(f"  ❌ Utils: {e}")
        return False
    
    try:
        from tools.mt5_tools import initialize_mt5, fetch_ohlcv_data
        from tools.indicator_tools import calculate_all_indicators
        from tools.pattern_tools import detect_candlestick_patterns
        from tools.structure_tools import analyze_market_structure
        from tools.volume_tools import analyze_volume_profile
        from tools.correlation_tools import full_correlation_analysis
        from tools.risk_tools import calculate_position_size
        from tools.signal_tools import generate_trade_signal
        from tools.web_search_tools import search_web
        from tools.sentiment_scoring_tools import synthesize_gold_sentiment
        print("  ✅ Tools")
    except Exception as e:
        print(f"  ❌ Tools: {e}")
        return False
    
    try:
        from agents.data_fetcher_agent import MT5DataFetcherAgent
        from agents.chart_analysis_agent import ChartAnalysisAgent
        from agents.market_structure_agent import MarketStructureAgent
        from agents.volume_analysis_agent import VolumeAnalysisAgent
        from agents.correlations_engine_agent import CorrelationsEngineAgent
        from agents.sentiment_master_agent import SentimentMasterAgent
        from agents.risk_management_agent import RiskManagementAgent
        from agents.trade_recommendation_agent import TradeRecommendationAgent
        from agents.orchestrator import GoldTradingOrchestrator
        print("  ✅ Agents")
    except Exception as e:
        print(f"  ❌ Agents: {e}")
        return False
    
    return True


def test_config():
    """Test config files exist."""
    import json
    
    print("\nTesting config files...")
    
    config_dir = Path(__file__).parent.parent / "config"
    
    configs = [
        "mt5_credentials.json",
        "risk_parameters.json", 
        "gold_config.json",
        "correlation_config.json"
    ]
    
    all_ok = True
    for cfg in configs:
        path = config_dir / cfg
        if path.exists():
            try:
                with open(path) as f:
                    json.load(f)
                print(f"  ✅ {cfg}")
            except Exception as e:
                print(f"  ❌ {cfg}: {e}")
                all_ok = False
        else:
            print(f"  ⚠️  {cfg}: Not found")
    
    return all_ok


def test_indicators():
    """Test indicator calculations with sample data."""
    import pandas as pd
    import numpy as np
    from tools.indicator_tools import calculate_all_indicators
    
    print("\nTesting indicator calculations...")
    
    # Generate sample OHLCV data
    np.random.seed(42)
    n = 250
    base_price = 2000
    
    data = []
    for i in range(n):
        open_price = base_price + np.random.randn() * 10
        close_price = open_price + np.random.randn() * 5
        high_price = max(open_price, close_price) + abs(np.random.randn() * 3)
        low_price = min(open_price, close_price) - abs(np.random.randn() * 3)
        
        data.append({
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "tick_volume": int(np.random.rand() * 1000 + 100)
        })
        base_price = close_price
    
    try:
        result = calculate_all_indicators(data)
        
        checks = [
            ("RSI", result.get("rsi", {}).get("value")),
            ("MACD", result.get("macd", {}).get("macd_line")),
            ("ATR", result.get("atr", {}).get("value")),
            ("ADX", result.get("adx", {}).get("value")),
        ]
        
        all_ok = True
        for name, value in checks:
            if value is not None:
                print(f"  ✅ {name}: {value:.2f}")
            else:
                print(f"  ❌ {name}: None")
                all_ok = False
        
        return all_ok
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def test_llm_client():
    """Test LLM client with multi-provider fallback."""
    print("\nTesting LLM client...")

    try:
        from utils.llm_client import call_llm, is_llm_available

        if is_llm_available():
            result = call_llm("Say 'API OK' in exactly 2 words", max_tokens=10)
            if result:
                print(f"  ✅ LLM API: {result.strip()[:50]}")
                return True
            else:
                print("  ⚠️  LLM API: Configured but not responding")
                return None
        else:
            print("  ⚠️  LLM API: No provider configured (using rule-based fallback)")
            return None
    except Exception as e:
        print(f"  ❌ LLM Client: {e}")
        return False


def test_mt5_connection():
    """Test MT5 connection (optional - requires MT5 running)."""
    print("\nTesting MT5 connection...")
    
    try:
        import MetaTrader5 as mt5
        
        if not mt5.initialize():
            print(f"  ⚠️  MT5 not available: {mt5.last_error()}")
            return None
        
        account_info = mt5.account_info()
        if account_info:
            print(f"  ✅ MT5 Connected: Account {account_info.login}")
            mt5.shutdown()
            return True
        else:
            print("  ⚠️  MT5 initialized but no account")
            mt5.shutdown()
            return None
    except ImportError:
        print("  ⚠️  MetaTrader5 package not installed")
        return None
    except Exception as e:
        print(f"  ⚠️  MT5 error: {e}")
        return None


def main():
    """Run all tests."""
    print("=" * 60)
    print("  MT5 GOLD TRADING SYSTEM - Test Suite")
    print("=" * 60)
    
    results = {
        "Imports": test_imports(),
        "Config": test_config(),
        "Indicators": test_indicators(),
        "LLM Client": test_llm_client(),
        "MT5": test_mt5_connection()
    }
    
    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)
    
    for test, result in results.items():
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️  SKIP"
        print(f"  {test}: {status}")
    
    # Overall
    failed = [k for k, v in results.items() if v is False]
    if failed:
        print(f"\n❌ Failed tests: {', '.join(failed)}")
        return 1
    else:
        print("\n✅ All tests passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
