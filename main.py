#!/usr/bin/env python3
"""
MT5 Gold Trading System - Multi-Agent Analysis Platform

A comprehensive multi-agent trading analysis system for Gold (XAUUSD)
using MetaTrader 5 data and GLM-5 AI for sentiment analysis.

Usage:
    python main.py                          # Full analysis with sentiment
    python main.py --quick                  # Quick analysis (no sentiment)
    python main.py --symbol EURUSDm         # Analyze different symbol
    python main.py --help                   # Show help

Environment Variables:
    MT5_ACCOUNT     - MT5 account number
    MT5_PASSWORD    - MT5 password
    MT5_SERVER      - MT5 server name
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime, timezone

# Fix Windows console encoding for unicode output
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.orchestrator import GoldTradingOrchestrator
from utils.logger import get_logger
from utils.time_utils import get_session_context

logger = get_logger("main")


def load_credentials() -> dict:
    """Load MT5 credentials from config or environment."""
    # Try environment variables first
    creds = {
        "account": os.environ.get("MT5_ACCOUNT"),
        "password": os.environ.get("MT5_PASSWORD"),
        "server": os.environ.get("MT5_SERVER")
    }
    
    # If not in env, try config file
    if not all(creds.values()):
        config_path = Path(__file__).parent / "config" / "mt5_credentials.json"
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                creds["account"] = creds["account"] or config.get("account")
                creds["password"] = creds["password"] or config.get("password")
                creds["server"] = creds["server"] or config.get("server")
    
    # Convert account to int if string
    if creds["account"]:
        creds["account"] = int(creds["account"])
    
    return creds


def print_banner():
    """Print system banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║     🥇 MT5 GOLD TRADING SYSTEM - Multi-Agent Analysis           ║
║                                                                  ║
║     Agents: Data | Chart | Structure | Volume | Correlations    ║
║             Sentiment | Risk | Recommendation                   ║
║                                                                  ║
║     AI: Multi-provider LLM + Rule-based Fallback                ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_session_info():
    """Print current trading session info."""
    session = get_session_context()
    print(f"\n📅 Session: {', '.join(session['active_sessions']) or 'Closed'}")
    print(f"⏰ UTC Time: {session['utc_time'][:19]}")
    print(f"📊 Expected Volatility: {session['expected_volatility']}")
    print()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="MT5 Gold Trading Multi-Agent Analysis System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    Full analysis with sentiment
  python main.py --quick            Quick technical analysis
  python main.py --symbol EURUSDm   Analyze EURUSD
  python main.py --sentiment-only   Only sentiment analysis
        """
    )
    
    parser.add_argument("--symbol", default="XAUUSDm", 
                        help="Trading symbol (default: XAUUSDm)")
    parser.add_argument("--quick", action="store_true",
                        help="Quick analysis without web sentiment")
    parser.add_argument("--no-sentiment", action="store_true",
                        help="Skip sentiment analysis")
    parser.add_argument("--sentiment-only", action="store_true",
                        help="Only run sentiment analysis")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output")
    parser.add_argument("--live", action="store_true",
                        help="Run continuously, re-analyzing at each interval")
    parser.add_argument("--interval", type=int, default=60,
                        help="Seconds between live re-checks (default: 60)")
    
    args = parser.parse_args()
    
    # Print banner
    if not args.json:
        print_banner()
        print_session_info()
    
    # Sentiment only mode
    if args.sentiment_only:
        from agents.sentiment_master_agent import SentimentMasterAgent
        sentiment = SentimentMasterAgent()
        result = sentiment.analyze_quick()
        
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(sentiment.get_summary(result))
        return 0
    
    # Load credentials
    creds = load_credentials()
    
    # Initialize orchestrator
    orchestrator = GoldTradingOrchestrator(
        mt5_account=creds.get("account"),
        mt5_password=creds.get("password"),
        mt5_server=creds.get("server")
    )
    
    def run_once() -> dict:
        logger.info(f"Starting analysis for {args.symbol}")
        if args.quick or args.no_sentiment:
            return orchestrator.get_quick_analysis(args.symbol)
        return orchestrator.analyze(args.symbol, include_sentiment=True)

    try:
        if args.live:
            # ── LIVE continuous loop ───────────────────────────────────
            if not args.json:
                print(f"🔄  LIVE MODE  |  interval={args.interval}s  |  Ctrl+C to stop\n")
            cycle = 0
            while True:
                cycle += 1
                if not args.json:
                    print(f"\n{'─'*70}")
                    print(f"  CYCLE {cycle}  |  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
                    print(f"{'─'*70}")
                result = run_once()
                if args.json:
                    output = {
                        "cycle": cycle,
                        "symbol": result.get("symbol"),
                        "timestamp": result.get("timestamp"),
                        "status": result.get("status"),
                        "recommendation": result.get("recommendation"),
                        "elapsed_seconds": result.get("elapsed_seconds")
                    }
                    print(json.dumps(output, indent=2, default=str), flush=True)
                else:
                    orchestrator.print_report(result)
                    if args.verbose:
                        print(json.dumps(result, indent=2, default=str)[:5000])
                    print(f"\n⏳  Next update in {args.interval}s  (Ctrl+C to stop)")
                time.sleep(args.interval)
        else:
            # ── Single run ────────────────────────────────────────────
            result = run_once()
            if args.json:
                output = {
                    "symbol": result.get("symbol"),
                    "timestamp": result.get("timestamp"),
                    "status": result.get("status"),
                    "recommendation": result.get("recommendation"),
                    "elapsed_seconds": result.get("elapsed_seconds")
                }
                print(json.dumps(output, indent=2, default=str))
            else:
                orchestrator.print_report(result)
                if args.verbose:
                    print("\n" + "=" * 70)
                    print("FULL ANALYSIS DATA")
                    print("=" * 70)
                    print(json.dumps(result, indent=2, default=str)[:5000])
            return 0 if result.get("status") == "success" else 1

    except KeyboardInterrupt:
        print("\n\nAnalysis interrupted by user.")
        return 130

    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"\n❌ Error: {e}")
        return 1

    finally:
        orchestrator.disconnect()


if __name__ == "__main__":
    sys.exit(main())
