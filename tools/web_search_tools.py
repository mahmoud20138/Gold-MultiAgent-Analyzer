"""
Web Search Tools - Search the web for news, sentiment, and research.
Uses LLM for intelligent search and analysis with rule-based fallback.
"""
import json
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.logger import get_logger
from utils.llm_client import call_llm

logger = get_logger("web_search_tools")


def search_web(query: str, max_results: int = 10) -> Dict:
    """Search the web using LLM or return rule-based fallback."""
    prompt = f"""Research the following topic: {query}

Provide a structured response with:
1. Key findings (bullet points)
2. Important facts and figures
3. Relevant context
4. Sentiment assessment (bullish/bearish/neutral for financial topics)

Be factual and objective."""

    system = "You are a financial research assistant. Provide accurate, well-sourced information."

    content = call_llm(prompt, system, max_tokens=2000)

    if not content:
        content = f"No LLM available for research query: {query}. Using technical analysis only."

    return {
        "status": "success" if content else "fallback",
        "query": query,
        "results": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "llm"
    }


def search_gold_news(max_results: int = 20) -> Dict:
    """Search for latest Gold-related news."""
    prompt = """Analyze the current state of the Gold (XAUUSD) market:

1. Recent price action and key levels
2. Federal Reserve policy impact
3. Central bank gold activity
4. Dollar strength context
5. Key support/resistance levels

Provide a comprehensive market overview with trading implications."""

    results = call_llm(prompt, "You are a gold market analyst.", max_tokens=2500)

    if not results:
        results = "No LLM available. Relying on technical analysis for gold market assessment."

    return {
        "status": "success",
        "news_results": [{"query": "gold market", "content": results}],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def search_fed_policy() -> Dict:
    """Research current Federal Reserve policy."""
    prompt = """Analyze current Federal Reserve monetary policy:
1. Current Fed funds rate
2. Recent FOMC decisions
3. Forward guidance
4. Implications for Gold prices

Provide SENTIMENT_SCORE from -100 to +100 where positive is bullish for gold."""
    return search_web(prompt)


def search_central_bank_gold() -> Dict:
    """Research central bank gold purchases."""
    prompt = """Analyze central bank gold purchases:
1. Major buyers (China, Russia, India, etc.)
2. Purchase trends
3. De-dollarization impact
4. Implications for Gold

Provide SENTIMENT_SCORE from -100 to +100."""
    return search_web(prompt)


def search_geopolitical_risks() -> Dict:
    """Research current geopolitical risks."""
    prompt = """Analyze geopolitical risks affecting Gold:
1. Active conflicts
2. Trade tensions
3. Safe haven demand
4. Implications for Gold

Provide SENTIMENT_SCORE from -100 to +100 where positive = higher safe haven demand."""
    return search_web(prompt)


def search_economic_calendar() -> Dict:
    """Research upcoming economic events."""
    prompt = """Analyze upcoming economic events affecting Gold:
1. Key data releases (CPI, NFP, GDP)
2. FOMC meetings
3. Market expectations
4. Implications for Gold

Provide SENTIMENT_SCORE from -100 to +100."""
    return search_web(prompt)


def search_cot_data() -> Dict:
    """Research COT positioning data."""
    prompt = """Analyze COT positioning for Gold:
1. Managed money positioning
2. Commercial hedgers
3. Recent changes
4. Contrarian signals

Provide SENTIMENT_SCORE from -100 to +100."""
    return search_web(prompt)


def search_gold_etf_flows() -> Dict:
    """Research Gold ETF holdings and flows."""
    prompt = """Analyze Gold ETF flows:
1. GLD holdings
2. Recent flows
3. Institutional demand
4. Implications for Gold

Provide SENTIMENT_SCORE from -100 to +100."""
    return search_web(prompt)


def search_social_sentiment() -> Dict:
    """Research social media sentiment for Gold."""
    prompt = """Analyze retail sentiment for Gold:
1. Social media trends
2. Retail positioning
3. Sentiment extremes
4. Contrarian signals

Provide SENTIMENT_SCORE from -100 to +100."""
    return search_web(prompt)


def analyze_news_with_claude(news_items: List[str]) -> Dict:
    """Use LLM to analyze news items."""
    if not news_items:
        return {"status": "error", "message": "No news items provided"}

    combined_news = "\n\n".join([f"News {i+1}: {item}" for i, item in enumerate(news_items[:10])])

    prompt = f"""Analyze these gold-related news items:

{combined_news}

Provide:
1. OVERALL_SENTIMENT
2. SENTIMENT_SCORE (-100 to +100)
3. KEY_THEMES
4. TRADING_IMPLICATIONS"""

    content = call_llm(prompt, "You are a financial sentiment analyst.", max_tokens=1500)

    if not content:
        content = "No LLM available for news analysis. Using technical signals only."

    return {
        "status": "success",
        "analysis": content,
        "items_analyzed": len(news_items),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
