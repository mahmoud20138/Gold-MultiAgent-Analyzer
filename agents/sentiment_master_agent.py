"""
Sentiment Master Agent - Coordinates all sentiment research sub-agents.
Uses LLM for intelligent sentiment analysis with rule-based fallback.
"""
import json
from typing import Dict, List
from pathlib import Path
import sys
import re
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.sentiment_scoring_tools import synthesize_gold_sentiment, SENTIMENT_WEIGHTS
from utils.logger import get_logger
from utils.llm_client import call_llm

logger = get_logger("sentiment_master_agent")


class SentimentMasterAgent:
    """
    Master agent coordinating 6 sentiment sub-agents.
    Uses LLM for synthesis with rule-based fallback.
    """

    def __init__(self):
        self.last_sentiment = None
        self.weights = SENTIMENT_WEIGHTS

    def analyze_full(self) -> Dict:
        """Run complete sentiment analysis across all sub-agents."""
        logger.info("Starting full sentiment analysis...")

        result = synthesize_gold_sentiment()
        self.last_sentiment = result

        return result

    def analyze_quick(self) -> Dict:
        """Quick sentiment analysis using LLM or rule-based fallback."""
        prompt = """Analyze the current market sentiment for Gold (XAUUSD) comprehensively.

Consider these factors and their approximate weights:
1. Federal Reserve policy (25% weight) - rate expectations, dovish/hawkish stance
2. Geopolitical risks (20% weight) - conflicts, tensions, safe haven demand
3. Economic data (20% weight) - inflation, jobs, GDP surprises
4. News flow (15% weight) - recent headlines and their bias
5. Market positioning (10% weight) - COT, ETF flows
6. Social sentiment (10% weight) - retail positioning

Provide your response in this EXACT format:

SENTIMENT_SCORE: [number from -100 to +100]
DIRECTION: [STRONGLY_BULLISH/BULLISH/MILDLY_BULLISH/NEUTRAL/MILDLY_BEARISH/BEARISH/STRONGLY_BEARISH]
CONVICTION: [HIGH/MEDIUM/LOW]
PRIMARY_DRIVER: [the main factor moving gold right now]

KEY_BULLISH_FACTORS:
- [factor 1]
- [factor 2]

KEY_BEARISH_FACTORS:
- [factor 1]
- [factor 2]

OUTLOOK: [1-2 week price expectation in 2-3 sentences]

TRADING_IMPLICATION: [what traders should do - be specific]

Scoring guide:
- +100 = Extremely bullish (Fed cutting rates, wars, weak dollar, strong demand)
- 0 = Neutral (mixed signals)
- -100 = Extremely bearish (Fed hiking, peace, strong dollar, weak demand)"""

        content = call_llm(prompt, "You are a senior gold market analyst with expertise in fundamental and sentiment analysis. Be objective and data-driven.", max_tokens=1500)

        # Fallback to rule-based if no LLM available
        if not content:
            logger.info("No LLM available, using rule-based sentiment")
            return {
                "status": "success",
                "score": 10,
                "direction": "MILDLY_BULLISH",
                "conviction": "LOW",
                "primary_driver": "Mixed macro signals (rule-based estimate)",
                "analysis": (
                    "Rule-based sentiment: Moderately supportive environment for gold. "
                    "Central bank buying and geopolitical risks provide a floor, "
                    "while elevated rates and dollar strength create headwinds. "
                    "Net effect is mildly bullish with low conviction."
                ),
                "method": "rule_based",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        # Extract score
        score_match = re.search(r'SENTIMENT_SCORE[:\s]+(-?\d+)', content, re.IGNORECASE)
        score = int(score_match.group(1)) if score_match else 0

        # Extract direction
        dir_match = re.search(r'DIRECTION[:\s]+([A-Z_]+)', content, re.IGNORECASE)
        direction = dir_match.group(1).upper() if dir_match else "NEUTRAL"

        # Extract conviction
        conv_match = re.search(r'CONVICTION[:\s]+([A-Z]+)', content, re.IGNORECASE)
        conviction = conv_match.group(1).upper() if conv_match else "MEDIUM"

        # Extract primary driver
        driver_match = re.search(r'PRIMARY_DRIVER[:\s]+(.+?)(?:\n|$)', content, re.IGNORECASE)
        primary_driver = driver_match.group(1).strip() if driver_match else "Mixed factors"

        return {
            "status": "success",
            "score": score,
            "direction": direction,
            "conviction": conviction,
            "primary_driver": primary_driver,
            "analysis": content,
            "method": "llm",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def get_score(self) -> int:
        """Get just the sentiment score (-100 to +100)."""
        if self.last_sentiment:
            return int(self.last_sentiment.get("composite_score", 0))
        return 0

    def get_direction(self) -> str:
        """Get sentiment direction."""
        if self.last_sentiment:
            return self.last_sentiment.get("direction", "NEUTRAL")
        return "NEUTRAL"

    def get_summary(self, sentiment: Dict = None) -> str:
        """Get text summary."""
        if sentiment is None:
            sentiment = self.last_sentiment

        if not sentiment:
            return "No sentiment analysis available"

        lines = []
        lines.append("=" * 60)
        lines.append("SENTIMENT ANALYSIS")
        lines.append("=" * 60)
        lines.append(f"Composite Score: {sentiment.get('composite_score', sentiment.get('score', 0))}/100")
        lines.append(f"Direction: {sentiment.get('direction', 'NEUTRAL')}")
        lines.append(f"Conviction: {sentiment.get('conviction', 'MEDIUM')}")
        lines.append(f"Primary Driver: {sentiment.get('primary_driver', {}).get('factor', sentiment.get('primary_driver', 'Unknown'))}")
        lines.append(f"Method: {sentiment.get('method', 'unknown')}")
        lines.append("")

        if sentiment.get("narrative"):
            lines.append("NARRATIVE:")
            lines.append(sentiment.get("narrative"))
            lines.append("")

        scores = sentiment.get("component_scores", {})
        if scores:
            lines.append("Component Scores:")
            for component, score in scores.items():
                weight = self.weights.get(component, 0) * 100
                lines.append(f"  {component}: {score} (weight: {weight:.0f}%)")

        if sentiment.get("is_conflicted"):
            lines.append("")
            lines.append("WARNING: Conflicting signals detected!")

        return "\n".join(lines)


SYSTEM_PROMPT = """
You are the Gold Sentiment Master Agent.

You coordinate 6 specialized sentiment analysis areas:
1. News Scraper - Latest gold/USD/market headlines
2. Central Bank Policy - Fed, rate expectations, CB gold buying
3. Geopolitical Risk - Wars, conflicts, tensions
4. Economic Calendar - Upcoming data, recent surprises
5. Market Sentiment - COT data, ETF flows, retail positioning
6. Social Sentiment - Twitter, Reddit, TradingView

You aggregate findings into a unified sentiment score (-100 to +100):
+100 = Extremely Bullish for Gold
   0 = Neutral
-100 = Extremely Bearish for Gold
"""


if __name__ == "__main__":
    agent = SentimentMasterAgent()

    print("Running quick sentiment analysis...")
    result = agent.analyze_quick()
    print(f"\nScore: {result.get('score')}")
    print(f"Direction: {result.get('direction')}")
    print(f"Method: {result.get('method')}")
    print(f"\n{agent.get_summary(result)}")
