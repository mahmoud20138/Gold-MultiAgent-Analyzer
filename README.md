# Gold MultiAgent Analyzer

**8-Agent AI-Powered Gold Analysis System -- Smart Money Concepts -- Multi-Provider LLM -- MetaTrader 5**

A multi-agent gold trading analysis system that runs 8 specialized agents in parallel -- technical indicators (40+), Smart Money Concepts (BOS, CHoCH, FVG, Order Blocks), volume profiling, correlation tracking across 10+ instruments, LLM-powered sentiment analysis, and risk management -- to produce confidence-scored trade recommendations with entry, stop loss, and 3 take-profit levels. Supports Azure, Groq, Anthropic, and OpenAI with automatic fallback.

---

## Architecture

```
+------------------+
|    main.py       |
|  CLI Interface   |
+--------+---------+
         |
+--------+---------+
|   Orchestrator   |
| (Command Center) |
+--------+---------+
         |
    +----+----+----+----+----+----+----+----+
    |    |    |    |    |    |    |    |    |
  Data Chart  SMC  Vol  Corr Sent Risk Trade
  Fetch Anlys Struct Anlys Engine Mstr Mgr  Rec
    |    |    |    |    |    |    |    |    |
    +----+----+----+----+----+----+----+----+
         |              |              |
    MT5 Data      LLM Providers    Risk Engine
    (OHLCV)    (Azure/Groq/Claude) (Sizing/Limits)
```

### Analysis Pipeline

```
MT5 OHLCV (M15/H1/H4/D1) + Correlated Instruments
        |
        v
  8 Specialized Agents (parallel)
    ├── Chart Analysis (40+ indicators)
    ├── Market Structure (BOS, CHoCH, FVG, OBs)
    ├── Volume Analysis (profile, CMF, OBV)
    ├── Correlations (DXY, Silver, Oil, indices)
    ├── Sentiment (LLM-powered, 6 components)
    └── Risk Management (sizing, portfolio limits)
        |
        v
  Trade Recommendation (confidence 0-100, grade A+/A/B/C)
        |
        v
  Entry + SL + TP1/TP2/TP3 + Risk Approval
```

---

## The 8 Agents

| # | Agent | Role |
|---|-------|------|
| 1 | **Data Fetcher** | Connects to MT5, retrieves multi-TF OHLCV for gold and 10+ correlated instruments |
| 2 | **Chart Analysis** | 40+ technical indicators: RSI, MACD, Bollinger, ADX, Ichimoku, Stochastic, CCI, ATR, 10+ candlestick patterns |
| 3 | **Market Structure** | Smart Money Concepts: BOS/CHoCH detection, Order Blocks, Fair Value Gaps, liquidity mapping, premium/discount zones |
| 4 | **Volume Analysis** | Volume profile (POC, VAH, VAL), CMF, OBV, accumulation/distribution, relative volume, divergence |
| 5 | **Correlations Engine** | Rolling correlations with DXY, Silver, Oil, EURUSD, indices, bonds. Divergence alerts, safe haven flow analysis |
| 6 | **Sentiment Master** | LLM-powered fundamental analysis: Fed policy (25%), geopolitical risk (20%), economic data (20%), news (15%), positioning (10%), social (10%) |
| 7 | **Risk Management** | Position sizing, R:R enforcement, portfolio risk tracking, event blackout (NFP, CPI, FOMC), max 2% per trade / 6% total |
| 8 | **Trade Recommendation** | Synthesizes all agents into confidence score (0-100), grade (A+/A/B/C), entry/SL/TP levels |

---

## Confidence Scoring

The Trade Recommendation agent scores each analysis:

| Component | Max Points |
|-----------|-----------|
| Chart Analysis (trend, indicators) | +/-25 |
| Market Structure (BOS, CHoCH, OBs) | +/-20 |
| Volume (flow, profile) | +/-15 |
| Correlations (DXY, safe haven) | +/-15 |
| Sentiment (LLM fundamental) | +/-15 |

**Grades:**
- **A+** (85+): Highest confidence, full position
- **A** (70-84): Strong setup, standard position
- **B** (55-69): Acceptable, reduced position
- **C** (<55): Low confidence, skip or paper trade

---

## Correlation Tracking

Monitors 10+ instruments correlated with gold:

| Instrument | Expected Correlation | Type |
|-----------|---------------------|------|
| DXY (US Dollar Index) | -0.85 | Inverse |
| XAGUSD (Silver) | +0.90 | Positive |
| EURUSD | +0.80 | Positive |
| US10Y (Bonds) | -0.70 | Inverse |
| Real Rates | -0.80 | Inverse |
| VIX | +0.60 | Positive |
| S&P 500 | -0.30 | Weak Inverse |
| Oil | +0.40 | Positive |

Alerts when current correlations diverge from expected values.

---

## LLM Integration (4 Providers)

Multi-provider with automatic fallback:

| Priority | Provider | Model | Notes |
|----------|----------|-------|-------|
| 1 | Azure AI | GPT-4o, Llama-3.1 | Primary |
| 2 | Groq | Llama-3.3-70B | Free tier |
| 3 | Anthropic | Claude Sonnet | Cloud |
| 4 | OpenAI | GPT-4o-mini | Fallback |
| 5 | Rule-based | -- | No API needed |

Used for sentiment analysis, report generation, and analyst commentary.

---

## Installation

### Prerequisites

- Python 3.10+
- MetaTrader 5 terminal running on Windows
- At least one LLM API key (optional -- rule-based fallback available)

### Setup

```bash
cd mt5-gold-trading-system
pip install -r requirements.txt
```

### Configuration

1. Edit `config/mt5_credentials.json`:
   ```json
   {
     "account": 12345678,
     "password": "your_password",
     "server": "YourBroker-Server",
     "path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
   }
   ```

2. Edit `config/llm_config.json` with your API keys (optional).

3. Edit `config/risk_parameters.json` to adjust risk limits.

---

## Usage

```bash
# Full analysis (technical + sentiment)
python main.py

# Quick technical only (no LLM, faster)
python main.py --quick

# Analyze different symbol
python main.py --symbol EURUSDm

# JSON output for API integration
python main.py --json

# Live monitoring (re-analyze every 60s)
python main.py --live --interval 60

# Sentiment analysis only
python main.py --sentiment-only

# Verbose debug output
python main.py --verbose
```

---

## Results & Output

### Trade Recommendation

```
══════════════════════════════════════════════════════
  FINAL TRADE RECOMMENDATION

  BUY   Confidence: 82/100   Grade: A   Action: TRADE

  LEVELS
  Entry              2658.40
  Stop Loss          2639.50
  Take Profit 1      2677.30
  Take Profit 2      2696.20
  Take Profit 3      2715.10
  R:R                1:2.6
  Lot Size           0.05
  Risk Amount        $94.50

  Reasons:
    - Strong bullish trend (ADX > 25)
    - Bullish market structure (HH, HL)
    - Volume shows accumulation
    - DXY weakening -> Bullish for Gold
    - Sentiment score positive (7/10 bullish)

  Warnings:
    ! RSI overbought - watch for pullback
    ! Price extended above POC - consolidation likely
══════════════════════════════════════════════════════
```

### Multi-Timeframe Alignment

```
  Overall Bias      BULLISH
  Alignment         ALIGNED (all TFs bullish)
    M15            BULLISH  strength=STRONG
    H1             BULLISH  strength=STRONG
    H4             BULLISH  strength=MEDIUM
    D1             BULLISH  strength=MEDIUM
```

### Smart Money Concepts

```
  Structure         BULLISH (HH, HL)
  Price Zone        DISCOUNT (62% of range)
  BOS events        3  latest=BULLISH_BOS @ 2645.20
  CHoCH events      1
  FVGs unfilled     2 / 5
  Order Blocks      4
```

---

## Project Structure

```
mt5-gold-trading-system/
  main.py                          # CLI entry point
  agents/
    orchestrator.py                # Command center (coordinates all agents)
    data_fetcher_agent.py          # MT5 data retrieval
    chart_analysis_agent.py        # 40+ technical indicators
    market_structure_agent.py      # BOS, CHoCH, FVG, Order Blocks
    volume_analysis_agent.py       # Volume profile, CMF, OBV
    correlations_engine_agent.py   # Gold correlation tracking
    sentiment_master_agent.py      # LLM-powered sentiment
    risk_management_agent.py       # Position sizing, limits
    trade_recommendation_agent.py  # Final signal synthesis
  tools/
    mt5_tools.py                   # MetaTrader5 API wrapper
    indicator_tools.py             # Technical indicator calculations
    pattern_tools.py               # Candlestick pattern detection
    structure_tools.py             # SMC analysis functions
    volume_tools.py                # Volume analysis algorithms
    correlation_tools.py           # Correlation calculations
    signal_tools.py                # Signal synthesis scoring
    risk_tools.py                  # Risk calculations
    sentiment_scoring_tools.py     # Sentiment analysis
    web_search_tools.py            # Web scraping for news
  utils/
    llm_client.py                  # Multi-provider LLM client
    data_formatter.py              # Data conversion
    logger.py                      # Structured logging
    time_utils.py                  # Session context & timezones
  config/
    gold_config.json               # Gold trading parameters
    risk_parameters.json           # Risk thresholds
    llm_config.json                # LLM provider settings (gitignored)
    mt5_credentials.json           # MT5 login (gitignored)
  tests/                           # Test suite
  requirements.txt
```
