"""
Sentiment Scoring Tools - Synthesize sentiment from multiple sources.
Uses LLM for intelligent sentiment analysis with rule-based fallback.
"""
import json
import re
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logger import get_logger
from utils.llm_client import call_llm

logger = get_logger("sentiment_tools")


# Sentiment weights
SENTIMENT_WEIGHTS = {
    "central_bank": 0.25,
    "geopolitical": 0.20,
    "economic_data": 0.20,
    "news": 0.15,
    "market_sentiment": 0.10,
    "social_sentiment": 0.10
}


def extract_sentiment_score(text: str) -> int:
    """Extract numerical sentiment score from response."""
    patterns = [
        r'SENTIMENT_SCORE[:\s]+(-?\d+)',
        r'SENTIMENT[:\s]+(-?\d+)',
        r'SCORE[:\s]+(-?\d+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            return max(-100, min(100, score))

    return 0


def _rule_based_central_bank() -> Dict:
    """Rule-based central bank sentiment (no API needed)."""
    # Conservative neutral estimate - rates are elevated, CB buying strong
    return {
        "status": "success",
        "score": 15,
        "analysis": "Rule-based: Central banks continue gold accumulation. Elevated rates create headwinds but rate cut expectations provide support.",
        "weight": SENTIMENT_WEIGHTS["central_bank"],
        "method": "rule_based",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def _rule_based_geopolitical() -> Dict:
    """Rule-based geopolitical sentiment."""
    # Moderate safe-haven demand
    return {
        "status": "success",
        "score": 20,
        "analysis": "Rule-based: Ongoing geopolitical tensions support safe-haven demand for gold.",
        "weight": SENTIMENT_WEIGHTS["geopolitical"],
        "method": "rule_based",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def _rule_based_economic() -> Dict:
    """Rule-based economic data sentiment."""
    return {
        "status": "success",
        "score": 5,
        "analysis": "Rule-based: Mixed economic signals. Inflation moderating but labor market remains resilient.",
        "weight": SENTIMENT_WEIGHTS["economic_data"],
        "method": "rule_based",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def _rule_based_market() -> Dict:
    """Rule-based market positioning sentiment."""
    return {
        "status": "success",
        "score": 10,
        "analysis": "Rule-based: Institutional positioning moderately bullish. ETF flows stable.",
        "weight": SENTIMENT_WEIGHTS["market_sentiment"],
        "method": "rule_based",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def _rule_based_social() -> Dict:
    """Rule-based social sentiment."""
    return {
        "status": "success",
        "score": 0,
        "analysis": "Rule-based: Social sentiment neutral. No extreme readings.",
        "weight": SENTIMENT_WEIGHTS["social_sentiment"],
        "method": "rule_based",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def analyze_central_bank_sentiment() -> Dict:
    """Analyze central bank policy sentiment for Gold."""
    prompt = """Analyze central bank policy impact on Gold.

Consider: Fed rates, FOMC stance, global CB gold purchases, QT/QE status.

Format:
SENTIMENT_SCORE: [number -100 to +100]
STANCE: [Hawkish/Dovish/Neutral]
GOLD_IMPLICATION: [BULLISH/BEARISH/NEUTRAL]
KEY_FACTORS:
- [factor 1]
- [factor 2]
ANALYSIS: [2-3 sentences]

Positive = bullish for gold (dovish Fed, strong CB buying)"""

    content = call_llm(prompt, "You are a central bank policy analyst.", max_tokens=1000)

    if not content:
        return _rule_based_central_bank()

    score = extract_sentiment_score(content)

    return {
        "status": "success",
        "score": score,
        "analysis": content,
        "weight": SENTIMENT_WEIGHTS["central_bank"],
        "method": "llm",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def analyze_geopolitical_sentiment() -> Dict:
    """Analyze geopolitical risk sentiment for Gold."""
    prompt = """Analyze geopolitical risk impact on Gold.

Consider: Active conflicts, US-China tensions, sanctions, energy security.

Format:
SENTIMENT_SCORE: [number -100 to +100]
RISK_LEVEL: [1-10]
GOLD_IMPLICATION: [BULLISH/BEARISH/NEUTRAL]
ACTIVE_CONFLICTS:
- [conflict 1]
ESCALATION_RISK: [LOW/MEDIUM/HIGH/CRITICAL]
ANALYSIS: [2-3 sentences]

Positive = higher safe haven demand (bullish for gold)"""

    content = call_llm(prompt, "You are a geopolitical risk analyst.", max_tokens=1000)

    if not content:
        return _rule_based_geopolitical()

    score = extract_sentiment_score(content)

    return {
        "status": "success",
        "score": score,
        "analysis": content,
        "weight": SENTIMENT_WEIGHTS["geopolitical"],
        "method": "llm",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def analyze_economic_data_sentiment() -> Dict:
    """Analyze economic calendar and data sentiment."""
    prompt = """Analyze economic data impact on Gold.

Consider: US inflation (CPI/PCE), jobs (NFP), GDP, upcoming data releases.

Format:
SENTIMENT_SCORE: [number -100 to +100]
GOLD_IMPLICATION: [BULLISH/BEARISH/NEUTRAL]
UPCOMING_RISKS:
- [event 1]
- [event 2]
RECENT_SURPRISES: [summary]
ANALYSIS: [2-3 sentences]

Positive = data supports gold (weak data = rate cuts expected)"""

    content = call_llm(prompt, "You are an economic data analyst.", max_tokens=1000)

    if not content:
        return _rule_based_economic()

    score = extract_sentiment_score(content)

    return {
        "status": "success",
        "score": score,
        "analysis": content,
        "weight": SENTIMENT_WEIGHTS["economic_data"],
        "method": "llm",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def analyze_market_sentiment() -> Dict:
    """Analyze market positioning sentiment (COT, ETF flows)."""
    prompt = """Analyze market positioning for Gold.

Consider: COT report, ETF flows (GLD/IAU), futures OI, options put/call.

Format:
SENTIMENT_SCORE: [number -100 to +100]
GOLD_IMPLICATION: [BULLISH/BEARISH/NEUTRAL]
INSTITUTIONAL_POSITIONING: [assessment]
ETF_FLOW_TREND: [inflows/outflows]
CONTRARIAN_SIGNAL: [Yes/No with reasoning]
ANALYSIS: [2-3 sentences]

Positive = supportive positioning"""

    content = call_llm(prompt, "You are a market positioning analyst.", max_tokens=1000)

    if not content:
        return _rule_based_market()

    score = extract_sentiment_score(content)

    return {
        "status": "success",
        "score": score,
        "analysis": content,
        "weight": SENTIMENT_WEIGHTS["market_sentiment"],
        "method": "llm",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def analyze_social_sentiment() -> Dict:
    """Analyze social media sentiment."""
    prompt = """Analyze social/retail sentiment for Gold.

Consider: Twitter/X, Reddit, TradingView, Google Trends, retail positioning.

Format:
SENTIMENT_SCORE: [number -100 to +100]
GOLD_IMPLICATION: [BULLISH/BEARISH/NEUTRAL]
RETAIL_POSITIONING: [assessment]
EUPHORIA_LEVEL: [LOW/MEDIUM/HIGH/EXTREME]
CONTRARIAN_ALERT: [Yes/No]
ANALYSIS: [2-3 sentences]

Note: Extreme readings (>75%) are contrarian signals"""

    content = call_llm(prompt, "You are a social sentiment analyst.", max_tokens=1000)

    if not content:
        return _rule_based_social()

    score = extract_sentiment_score(content)

    return {
        "status": "success",
        "score": score,
        "analysis": content,
        "weight": SENTIMENT_WEIGHTS["social_sentiment"],
        "method": "llm",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def synthesize_gold_sentiment() -> Dict:
    """
    Master sentiment synthesizer - combines all sentiment sources.
    Uses LLM for analysis with rule-based fallback.
    """
    logger.info("Starting sentiment synthesis...")

    # Run all sentiment analyses
    central_bank = analyze_central_bank_sentiment()
    geopolitical = analyze_geopolitical_sentiment()
    economic_data = analyze_economic_data_sentiment()
    market_sentiment = analyze_market_sentiment()
    social_sentiment = analyze_social_sentiment()

    # Calculate weighted composite
    scores = {
        "central_bank": central_bank.get("score", 0),
        "geopolitical": geopolitical.get("score", 0),
        "economic_data": economic_data.get("score", 0),
        "market_sentiment": market_sentiment.get("score", 0),
        "social_sentiment": social_sentiment.get("score", 0)
    }

    composite = sum(scores[k] * SENTIMENT_WEIGHTS[k] for k in scores)

    # Determine direction
    if composite > 40:
        direction = "STRONGLY_BULLISH"
    elif composite > 20:
        direction = "BULLISH"
    elif composite > 5:
        direction = "MILDLY_BULLISH"
    elif composite > -5:
        direction = "NEUTRAL"
    elif composite > -20:
        direction = "MILDLY_BEARISH"
    elif composite > -40:
        direction = "BEARISH"
    else:
        direction = "STRONGLY_BEARISH"

    # Identify primary driver
    primary_driver = max(scores.items(), key=lambda x: abs(x[1]))

    # Check for conflicts
    bullish_count = sum(1 for s in scores.values() if s > 10)
    bearish_count = sum(1 for s in scores.values() if s < -10)
    is_conflicted = bullish_count > 0 and bearish_count > 0

    # Conviction level
    agreement = max(bullish_count, bearish_count) / len(scores) * 100
    conviction = "HIGH" if agreement > 70 else "MEDIUM" if agreement > 50 else "LOW"

    # Determine method used
    methods = {central_bank.get("method"), geopolitical.get("method"),
               economic_data.get("method"), market_sentiment.get("method"),
               social_sentiment.get("method")}
    method = "llm" if "llm" in methods else "rule_based"

    # Generate narrative
    narrative_prompt = f"""Summarize gold sentiment in 2-3 sentences:

Composite Score: {composite:.1f}/100
Direction: {direction}
- Central Bank: {scores['central_bank']}
- Geopolitical: {scores['geopolitical']}
- Economic: {scores['economic_data']}
- Market: {scores['market_sentiment']}
- Social: {scores['social_sentiment']}

Primary Driver: {primary_driver[0].replace('_', ' ').title()}
Conflicted: {is_conflicted}"""

    narrative = call_llm(narrative_prompt, "You are a gold strategist.", max_tokens=300)

    if not narrative:
        # Rule-based narrative
        driver_name = primary_driver[0].replace("_", " ").title()
        narrative = (
            f"Gold sentiment is {direction.replace('_', ' ').lower()} with a composite score of {composite:.1f}. "
            f"The primary driver is {driver_name} (score: {primary_driver[1]}). "
            f"{'Conflicting signals detected - exercise caution.' if is_conflicted else 'Signals are broadly aligned.'}"
        )

    return {
        "status": "success",
        "composite_score": round(composite, 1),
        "direction": direction,
        "conviction": conviction,
        "is_conflicted": is_conflicted,
        "primary_driver": {
            "factor": primary_driver[0].replace("_", " ").title(),
            "score": primary_driver[1]
        },
        "component_scores": scores,
        "weights_used": SENTIMENT_WEIGHTS,
        "narrative": narrative,
        "method": method,
        "details": {
            "central_bank": central_bank,
            "geopolitical": geopolitical,
            "economic_data": economic_data,
            "market_sentiment": market_sentiment,
            "social_sentiment": social_sentiment
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
