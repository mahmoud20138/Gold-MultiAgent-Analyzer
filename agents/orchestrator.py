"""
Main Orchestrator Agent - Gold Trading Command Center.
Coordinates all agents with LLM-powered synthesis and rule-based fallback.
"""
import json
from typing import Dict, List, Optional
from pathlib import Path
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logger import get_logger
from utils.time_utils import get_session_context
from utils.llm_client import call_llm

# Import all agents
from agents.data_fetcher_agent import MT5DataFetcherAgent
from agents.chart_analysis_agent import ChartAnalysisAgent
from agents.market_structure_agent import MarketStructureAgent
from agents.volume_analysis_agent import VolumeAnalysisAgent
from agents.correlations_engine_agent import CorrelationsEngineAgent
from agents.sentiment_master_agent import SentimentMasterAgent
from agents.risk_management_agent import RiskManagementAgent
from agents.trade_recommendation_agent import TradeRecommendationAgent

logger = get_logger("orchestrator")


class GoldTradingOrchestrator:
    """
    Main Orchestrator - Gold Trading Command Center.
    
    Coordinates 8 specialized agents:
    1. MT5 Data Fetcher - Market data
    2. Chart Analysis - Technical indicators
    3. Market Structure - SMC analysis
    4. Volume Analysis - Money flow
    5. Correlations Engine - Related markets
    6. Sentiment Master - Fundamentals
    7. Risk Management - Position sizing
    8. Trade Recommendation - Final signal
    
    Uses Claude for synthesis and natural language generation.
    """
    
    def __init__(self, mt5_account: int = None, mt5_password: str = None, 
                 mt5_server: str = None):
        """Initialize all agents."""
        logger.info("Initializing Gold Trading Command Center...")
        
        # Initialize agents
        self.data_fetcher = MT5DataFetcherAgent()
        self.chart_analyst = ChartAnalysisAgent()
        self.market_structure = MarketStructureAgent()
        self.volume_analyst = VolumeAnalysisAgent()
        self.correlations = CorrelationsEngineAgent()
        self.sentiment = SentimentMasterAgent()
        self.risk_manager = RiskManagementAgent()
        self.trade_recommender = TradeRecommendationAgent()
        
        # MT5 credentials
        self.mt5_account = mt5_account
        self.mt5_password = mt5_password
        self.mt5_server = mt5_server
        
        # State
        self.connected = False
        self.last_analysis = None
    
    def connect(self) -> Dict:
        """Connect to MT5."""
        result = self.data_fetcher.connect(
            self.mt5_account, self.mt5_password, self.mt5_server
        )
        self.connected = result.get("status") == "connected"
        return result
    
    def disconnect(self) -> Dict:
        """Disconnect from MT5."""
        self.connected = False
        return self.data_fetcher.disconnect()
    
    def analyze(self, symbol: str = "XAUUSDm", 
                include_sentiment: bool = True) -> Dict:
        """
        Run complete analysis pipeline.
        """
        logger.info(f"Starting complete analysis for {symbol}")
        start_time = datetime.now()
        
        results = {
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "running"
        }
        
        try:
            # Ensure connection
            if not self.connected:
                conn = self.connect()
                if conn.get("status") != "connected":
                    return {"status": "error", "message": "Failed to connect to MT5"}
            
            # ═════════════════════════════════════════════════════════
            # STEP 1: DATA COLLECTION
            # ═════════════════════════════════════════════════════════
            logger.info("Step 1: Fetching data...")
            data = self.data_fetcher.run_full_fetch(symbol)
            results["data"] = {"status": data.get("status")}
            
            if data.get("status") != "success":
                return {"status": "error", "message": "Data fetch failed"}
            
            # ═════════════════════════════════════════════════════════
            # STEP 2: PARALLEL TECHNICAL ANALYSIS
            # ═════════════════════════════════════════════════════════
            logger.info("Step 2: Running technical analysis...")
            
            gold_data = data.get("gold_data", {})
            
            # Chart Analysis (H1 primary)
            h1_data = gold_data.get("timeframes", {}).get("H1", {}).get("data", [])
            chart_analysis = self.chart_analyst.analyze(h1_data, "H1")
            results["chart_analysis"] = chart_analysis
            
            # Market Structure
            structure_analysis = self.market_structure.analyze(h1_data)
            results["market_structure"] = structure_analysis
            
            # Volume Analysis
            volume_analysis = self.volume_analyst.analyze(h1_data)
            results["volume_analysis"] = volume_analysis
            
            # MTF Analysis
            mtf_analysis = self.chart_analyst.analyze_multi_timeframe(
                gold_data.get("timeframes", {})
            )
            results["mtf_analysis"] = mtf_analysis
            
            # ═════════════════════════════════════════════════════════
            # STEP 3: CORRELATIONS
            # ═════════════════════════════════════════════════════════
            logger.info("Step 3: Analyzing correlations...")
            correlated_data = data.get("correlated_data", {}).get("instruments", {})
            correlation_analysis = self.correlations.analyze(correlated_data)
            results["correlation_analysis"] = correlation_analysis
            
            # ═════════════════════════════════════════════════════════
            # STEP 4: SENTIMENT (Claude)
            # ═════════════════════════════════════════════════════════
            sentiment_score = 0
            if include_sentiment:
                logger.info("Step 4: Analyzing sentiment...")
                try:
                    sentiment_result = self.sentiment.analyze_quick()
                    if sentiment_result.get("status") == "success":
                        sentiment_score = sentiment_result.get("score", 0)
                    results["sentiment"] = sentiment_result
                except Exception as e:
                    logger.warning(f"Sentiment analysis failed: {e}")
                    results["sentiment"] = {"status": "error", "message": str(e)}
            
            # ═════════════════════════════════════════════════════════
            # STEP 5: RISK ASSESSMENT
            # ═════════════════════════════════════════════════════════
            logger.info("Step 5: Assessing risk...")
            
            account = data.get("account", {}).get("account", {})
            equity = account.get("equity", 10000) if isinstance(account, dict) else 10000
            positions = data.get("account", {}).get("positions", {}).get("count", 0)
            
            # Get levels from analysis - handle both dict and float cases
            current_price = chart_analysis.get("current_price", 0) if isinstance(chart_analysis, dict) else 0
            
            # Handle ATR - could be dict or float
            atr_raw = chart_analysis.get("atr", 0) if isinstance(chart_analysis, dict) else 0
            if isinstance(atr_raw, dict):
                atr = atr_raw.get("value", 0)
            else:
                atr = float(atr_raw) if atr_raw else 0
            
            initial_risk = self.risk_manager.check_portfolio_risk(
                equity, data.get("account", {}).get("positions", {}).get("positions", [])
            )
            results["portfolio_risk"] = initial_risk
            
            # ═════════════════════════════════════════════════════════
            # STEP 6: TRADE RECOMMENDATION
            # ═════════════════════════════════════════════════════════
            logger.info("Step 6: Generating trade recommendation...")
            
            # Get support/resistance safely
            sr_data = chart_analysis.get("support_resistance", {}) if isinstance(chart_analysis, dict) else {}
            
            recommendation = self.trade_recommender.generate_recommendation(
                chart_analysis=chart_analysis if isinstance(chart_analysis, dict) else {},
                market_structure=structure_analysis if isinstance(structure_analysis, dict) else {},
                volume_analysis=volume_analysis if isinstance(volume_analysis, dict) else {},
                correlation_analysis=correlation_analysis if isinstance(correlation_analysis, dict) else {},
                risk_assessment={"equity": equity, "active_trades": positions},
                support_resistance=sr_data,
                symbol=symbol,
                timeframe="H1",
                sentiment_score=sentiment_score
            )
            
            # Full risk assessment with signal levels
            if recommendation.get("entry_price") and recommendation.get("stop_loss"):
                try:
                    full_risk = self.risk_manager.assess_trade(
                        account_equity=equity,
                        entry_price=recommendation.get("entry_price"),
                        stop_loss=recommendation.get("stop_loss"),
                        take_profit=recommendation.get("take_profit_1"),
                        direction=recommendation.get("direction"),
                        symbol_info=gold_data.get("symbol_info", {}),
                        active_trades=positions
                    )
                    recommendation["position_sizing"] = full_risk.get("position_sizing")
                    recommendation["lot_size"] = full_risk.get("lot_size")
                    recommendation["risk_amount"] = full_risk.get("risk_amount_usd")
                    recommendation["risk_approved"] = full_risk.get("risk_approved")
                except Exception as e:
                    logger.warning(f"Risk assessment failed: {e}")
            
            results["recommendation"] = recommendation
            
            # ═════════════════════════════════════════════════════════
            # STEP 7: GENERATE REPORT WITH Claude
            # ═════════════════════════════════════════════════════════
            logger.info("Step 7: Generating final report...")
            results["report"] = self._generate_report_with_claude(results)
            
            # Timing
            elapsed = (datetime.now() - start_time).total_seconds()
            results["elapsed_seconds"] = round(elapsed, 2)
            results["status"] = "success"
            
            self.last_analysis = results
            logger.info(f"Analysis complete in {elapsed:.2f}s")
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            import traceback
            traceback.print_exc()
            results["status"] = "error"
            results["message"] = str(e)
        
        return results
    
    def _generate_report_with_claude(self, analysis: Dict) -> str:
        """Generate a natural language report using LLM or rule-based fallback."""

        rec = analysis.get('recommendation', {})
        if not isinstance(rec, dict):
            rec = {}

        chart = analysis.get('chart_analysis', {})
        if not isinstance(chart, dict):
            chart = {}

        structure = analysis.get('market_structure', {})
        if not isinstance(structure, dict):
            structure = {}

        volume = analysis.get('volume_analysis', {})
        if not isinstance(volume, dict):
            volume = {}

        corr = analysis.get('correlation_analysis', {})
        if not isinstance(corr, dict):
            corr = {}

        prompt = f"""Generate a comprehensive trading report for Gold (XAUUSD) based on the following analysis:

RECOMMENDATION:
- Direction: {rec.get('direction', 'NEUTRAL')}
- Confidence: {rec.get('confidence_score', 0)}/100
- Grade: {rec.get('trade_grade', 'N/A')}
- Entry: {rec.get('entry_price', 'N/A')}
- Stop Loss: {rec.get('stop_loss', 'N/A')}
- Take Profit 1: {rec.get('take_profit_1', 'N/A')}
- R:R Ratio: {rec.get('risk_reward_ratio', 'N/A')}

KEY REASONS:
{chr(10).join(['• ' + r for r in rec.get('reasons', [])[:5]]) if rec.get('reasons') else 'No specific reasons'}

TECHNICAL:
- Trend: {chart.get('trend', {}).get('trend', 'Unknown') if isinstance(chart.get('trend'), dict) else 'Unknown'}
- RSI: {chart.get('indicators', {}).get('rsi', {}).get('value', 'N/A') if isinstance(chart.get('indicators'), dict) else 'N/A'}
- MACD: {chart.get('indicators', {}).get('macd', {}).get('crossover', 'N/A') if isinstance(chart.get('indicators'), dict) else 'N/A'}
- Structure: {structure.get('market_structure', 'Unknown')}

VOLUME:
- Flow: {volume.get('overall_flow', 'Unknown')}

CORRELATIONS:
- Signal: {corr.get('overall_signal', 'Unknown')}

Generate a professional trading report with:
1. Executive Summary (2-3 sentences)
2. Technical Analysis Summary
3. Trade Setup Details
4. Risk Management Notes
5. Action Recommendation

Keep it concise and actionable."""

        try:
            result = call_llm(prompt, "You are a professional gold trading analyst. Generate clear, actionable trading reports.", max_tokens=2000)
            if result:
                return result
            # Fallback to structured report
            return self.trade_recommender.format_report(rec)
        except Exception as e:
            logger.error(f"Report generation error: {e}")
            return self.trade_recommender.format_report(rec)
    
    def get_quick_analysis(self, symbol: str = "XAUUSDm") -> Dict:
        """Quick analysis without web sentiment (faster)."""
        return self.analyze(symbol, include_sentiment=False)
    
    def print_report(self, analysis: Dict = None):
        """Print full report: all sub-agent results + final recommendation."""
        if analysis is None:
            analysis = self.last_analysis

        if not analysis:
            print("No analysis available")
            return

        W = 70

        def _hdr(title):
            pad = (W - len(title) - 2) // 2
            print(f"\n{'═' * pad} {title} {'═' * max(0, W - pad - len(title) - 2)}")

        def _row(label, value, width=28):
            print(f"  {label:<{width}} {value}")

        symbol  = analysis.get("symbol", "?")
        ts      = analysis.get("timestamp", "")[:19]
        elapsed = analysis.get("elapsed_seconds", "?")
        print(f"\n{'═' * W}")
        print(f"  MT5 GOLD TRADING SYSTEM  |  {symbol}  |  {ts}  |  {elapsed}s")
        print(f"{'═' * W}")

        # ── 1. CHART ANALYSIS ────────────────────────────────────────────
        _hdr("1 · CHART ANALYSIS (H1)")
        chart = analysis.get("chart_analysis", {})
        if isinstance(chart, dict) and chart.get("status") == "success":
            ind   = chart.get("indicators", {})
            rsi   = ind.get("rsi", {})
            macd  = ind.get("macd", {})
            adx   = ind.get("adx", {})
            ma    = ind.get("moving_averages", {})
            bb    = ind.get("bollinger_bands", {})
            atr   = ind.get("atr", {})
            trend = chart.get("trend", {})
            sr    = chart.get("support_resistance", {})
            pats  = chart.get("candlestick_patterns", {}).get("patterns", [])
            _row("Price",        f"{chart.get('current_price', 'N/A')}")
            _row("Trend",        f"{trend.get('trend','?')}  strength={trend.get('strength','?')}")
            _row("RSI (14)",     f"{rsi.get('value','?')}  → {rsi.get('condition','?')}")
            _row("MACD",         f"cross={macd.get('crossover','?')}  hist={macd.get('histogram','?')}")
            _row("ADX (14)",     f"{adx.get('value','?')}  {adx.get('trend_strength','?')}  dir={adx.get('direction','?')}")
            _row("SMA200",       f"price {ma.get('price_vs_sma200','?')} SMA200")
            _row("BB",           f"pos={bb.get('position','?')}  {bb.get('squeeze','NORMAL')}")
            _row("ATR (14)",     f"{atr.get('value','?')}")
            _row("Resistance",   f"{sr.get('nearest_resistance','N/A')}")
            _row("Support",      f"{sr.get('nearest_support','N/A')}")
            if pats:
                _row("Patterns", ", ".join(p.get("pattern","?") for p in pats[:4]))
        else:
            print(f"  Status: {chart.get('message','error')}")

        # ── 2. MULTI-TIMEFRAME ───────────────────────────────────────────
        _hdr("2 · MULTI-TIMEFRAME TREND")
        mtf = analysis.get("mtf_analysis", {})
        if isinstance(mtf, dict) and mtf.get("status") == "success":
            mtf_trend = mtf.get("mtf_trend", {})
            _row("Overall Bias",   mtf_trend.get("dominant_direction", "?"))
            _row("Alignment",      mtf_trend.get("alignment", "?"))
            for tf, tf_data in mtf.get("individual_analyses", {}).items():
                if isinstance(tf_data, dict):
                    t = tf_data.get("trend", {})
                    _row(f"  {tf}", f"{t.get('trend','?')}  strength={t.get('strength','?')}")
        else:
            print("  No MTF data")

        # ── 3. MARKET STRUCTURE ──────────────────────────────────────────
        _hdr("3 · MARKET STRUCTURE  (Smart Money)")
        ms = analysis.get("market_structure", {})
        if isinstance(ms, dict) and ms.get("status") == "success":
            zone = ms.get("premium_discount", {})
            bos  = ms.get("bos_events", [])
            choc = ms.get("choch_events", [])
            fvgs = ms.get("fair_value_gaps", [])
            obs  = ms.get("order_blocks", [])
            _row("Structure",     ms.get("market_structure", "?"))
            _row("Price Zone",    f"{zone.get('zone','?')}  ({zone.get('range_position','?')}% of range)")
            bos_txt = (f"  latest={bos[-1].get('type','?')} @ {bos[-1].get('broken_level','?')}"
                       if bos else "")
            _row("BOS events",    f"{len(bos)}{bos_txt}")
            _row("CHoCH events",  f"{len(choc)}")
            unfilled = [f for f in fvgs if not f.get("filled")]
            _row("FVGs unfilled", f"{len(unfilled)} / {len(fvgs)}")
            _row("Order Blocks",  f"{len(obs)}")
            if ms.get("narrative"):
                print(f"  → {ms['narrative']}")
        else:
            print(f"  Status: {ms.get('message','error')}")

        # ── 4. VOLUME ANALYSIS ───────────────────────────────────────────
        _hdr("4 · VOLUME ANALYSIS")
        vol = analysis.get("volume_analysis", {})
        if isinstance(vol, dict) and vol.get("status") == "success":
            profile = vol.get("profile", {})
            cmf     = vol.get("cmf", {})
            obv     = vol.get("obv", {})
            anom    = vol.get("anomalies", {})
            summ    = vol.get("summary", {})
            rv      = anom.get("relative_volume")
            rv_lbl  = anom.get("relative_volume_label", "?")
            _row("Overall Flow",   vol.get("overall_flow", "?"))
            _row("Bias",           summ.get("bias", "?"))
            _row("CMF",            f"{cmf.get('value','?')}  → {cmf.get('signal','?')}  ({cmf.get('strength','?')})")
            _row("OBV trend",      obv.get("trend", "?"))
            _row("POC",            f"{profile.get('poc','?')}  price {profile.get('price_vs_poc','?')} POC")
            _row("Value Area",     f"{profile.get('value_area_low','?')} – {profile.get('value_area_high','?')}")
            _row("Rel. Volume",    f"{rv:.2f}x  ({rv_lbl})" if isinstance(rv, (int, float)) else "?")
            if vol.get("divergences", {}).get("any_divergence"):
                print("  ⚠ Volume divergence detected")
        else:
            print(f"  Status: {vol.get('message','error')}")

        # ── 5. CORRELATIONS ──────────────────────────────────────────────
        _hdr("5 · CORRELATIONS ENGINE")
        corr = analysis.get("correlation_analysis", {})
        if isinstance(corr, dict) and corr.get("status") == "success":
            dxy  = corr.get("dxy_synthetic", {})
            safe = corr.get("safe_haven_flow", {})
            divs = corr.get("divergences", {})
            _row("Overall Signal",   corr.get("overall_signal", "?"))
            _row("Bull / Bear score", f"{corr.get('bullish_signals',0)} / {corr.get('bearish_signals',0)}")
            _row("DXY direction",    f"{dxy.get('dxy_direction','?')}  → Gold: {dxy.get('gold_implication','?')}")
            _row("Safe Haven env",   f"{safe.get('market_environment','?')}  → {safe.get('gold_impact','?')}")
            _row("Safe Haven score", safe.get("safe_haven_score", "?"))
            if divs.get("divergence_count", 0):
                _row("Divergences",  f"⚠ {divs['divergence_count']} detected")
            rc = corr.get("rolling_correlations", {})
            if rc:
                print("  Key correlations (20-bar):")
                for sym, cdata in list(rc.items())[:6]:
                    c20  = cdata.get("corr_20", {}).get("current", "?")
                    exp  = cdata.get("expected_correlation", "?")
                    anom = " ⚠ANOMALY" if cdata.get("correlation_anomaly") else ""
                    print(f"    {sym:<10}  current={c20:>7}  expected={exp}{anom}")
        else:
            print(f"  Status: {corr.get('message','error')}")

        # ── 6. SENTIMENT ─────────────────────────────────────────────────
        _hdr("6 · SENTIMENT ANALYSIS")
        sent = analysis.get("sentiment", {})
        if isinstance(sent, dict) and sent.get("status") == "success":
            _row("Score",          f"{sent.get('score', 0)} / 100")
            _row("Direction",      sent.get("direction", "?"))
            _row("Conviction",     sent.get("conviction", "?"))
            _row("Primary Driver", sent.get("primary_driver", "?"))
            _row("Method",         sent.get("method", "?"))
        else:
            print("  Sentiment unavailable (rule-based fallback used)")

        # ── 7. PORTFOLIO RISK ────────────────────────────────────────────
        _hdr("7 · PORTFOLIO RISK")
        prisk = analysis.get("portfolio_risk", {})
        if isinstance(prisk, dict):
            within = prisk.get("within_limit", True)
            _row("Open Positions", prisk.get("position_count", 0))
            _row("Total Risk",     f"${prisk.get('total_risk_usd',0):.2f}  ({prisk.get('total_risk_pct',0):.2f}%)")
            _row("Max Allowed",    f"{prisk.get('max_allowed_pct',6)}%")
            _row("Available Risk", f"{prisk.get('available_risk_pct',0):.2f}%")
            _row("Within Limit",   "✅ YES" if within else "❌ NO – risk limit breached")

        # ── 8. FINAL RECOMMENDATION ──────────────────────────────────────
        _hdr("8 · FINAL TRADE RECOMMENDATION")
        rec = analysis.get("recommendation", {})
        if isinstance(rec, dict):
            direction  = rec.get("direction", "NEUTRAL")
            confidence = rec.get("confidence_score", 0)
            grade      = rec.get("trade_grade", "?")
            action     = rec.get("trade_action", "?")
            marker = "🟢" if direction == "BUY" else "🔴" if direction == "SELL" else "⚪"
            print(f"\n  {marker}  {direction}   Confidence: {confidence}/100   Grade: {grade}   Action: {action}")
            print()
            _row("Entry",          rec.get("entry_price", "N/A"))
            _row("Stop Loss",      rec.get("stop_loss", "N/A"))
            _row("Take Profit 1",  rec.get("take_profit_1", "N/A"))
            _row("Take Profit 2",  rec.get("take_profit_2", "N/A"))
            _row("Take Profit 3",  rec.get("take_profit_3", "N/A"))
            _row("R:R",            f"1:{rec.get('risk_reward_ratio','N/A')}")
            _row("Lot Size",       rec.get("lot_size", "N/A"))
            _row("Risk Amount",    f"${rec.get('risk_amount','N/A')}")
            _row("Risk Approved",  "✅ YES" if rec.get("risk_approved") else "❌ NO")
            reasons = rec.get("reasons", [])
            if reasons:
                print("\n  Reasons:")
                for r in reasons:
                    print(f"    • {r}")
            warnings = rec.get("warnings", [])
            if warnings:
                print("\n  Warnings:")
                for w in warnings:
                    print(f"    ⚠ {w}")

        # ── LLM ANALYST REPORT (only when LLM generated, not fallback) ───
        report = analysis.get("report", "")
        if report and not report.strip().startswith("==="):
            _hdr("ANALYST REPORT  (LLM)")
            print(report)

        print(f"\n{'═' * W}\n")


# CLI entry point
def main():
    """Main entry point for CLI usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Gold Trading Analysis System")
    parser.add_argument("--symbol", default="XAUUSDm", help="Trading symbol")
    parser.add_argument("--no-sentiment", action="store_true", help="Skip web sentiment")
    parser.add_argument("--quick", action="store_true", help="Quick analysis")
    args = parser.parse_args()
    
    orchestrator = GoldTradingOrchestrator()
    
    try:
        if args.quick:
            result = orchestrator.get_quick_analysis(args.symbol)
        else:
            result = orchestrator.analyze(args.symbol, include_sentiment=not args.no_sentiment)
        
        orchestrator.print_report(result)
        
    finally:
        orchestrator.disconnect()


if __name__ == "__main__":
    main()
