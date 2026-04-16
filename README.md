# 🥇 Gold MultiAgent Analyzer

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/MetaTrader-5-FF6B00?style=for-the-badge&logo=metatrader&logoColor=white" alt="MT5">
  <img src="https://img.shields.io/badge/Multi--Agent-AI-9333EA?style=for-the-badge&logoColor=white" alt="Multi-Agent AI">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</p>

<p align="center">
  <a href="https://github.com/mahmoud20138/Gold-MultiAgent-Analyzer/stargazers">
    <img src="https://img.shields.io/github/stars/mahmoud20138/Gold-MultiAgent-Analyzer?style=social" alt="Stars">
  </a>
  <a href="https://github.com/mahmoud20138/Gold-MultiAgent-Analyzer/issues">
    <img src="https://img.shields.io/github/issues/mahmoud20138/Gold-MultiAgent-Analyzer" alt="Issues">
  </a>
  <a href="https://github.com/mahmoud20138/Gold-MultiAgent-Analyzer/blob/master/LICENSE">
    <img src="https://img.shields.io/github/license/mahmoud20138/Gold-MultiAgent-Analyzer" alt="License">
  </a>
</p>

---

> 🤖 **8-Agent AI-Powered Gold Analysis System** — Smart Money Concepts — Multi-Provider LLM — MetaTrader 5

A comprehensive multi-agent gold trading analysis system that runs **8 specialized agents in parallel** — technical indicators (40+), Smart Money Concepts (BOS, CHoCH, FVG, Order Blocks), volume profiling, correlation tracking across 10+ instruments, LLM-powered sentiment analysis, and risk management — to produce **confidence-scored trade recommendations** with entry, stop loss, and 3 take-profit levels.

---

## 📑 Table of Contents

1. [🎯 Key Features](#-key-features)
2. [🏗️ System Architecture](#-system-architecture)
3. [🔄 Analysis Pipeline](#-analysis-pipeline)
4. [🤖 The 8 Agents](#-the-8-agents)
5. [🎯 Confidence Scoring](#-confidence-scoring)
6. [📊 Correlation Tracking](#-correlation-tracking)
7. [🧠 LLM Integration](#-llm-integration)
8. [📈 Technical Indicators](#-technical-indicators)
9. [💰 Risk Management](#-risk-management)
10. [🛠️ Technology Stack](#-technology-stack)
11. [📁 Project Structure](#-project-structure)
12. [🚀 Getting Started](#-getting-started)
13. [💻 Usage](#-usage)
14. [📊 Results Output](#-results-output)
15. [🤝 Contributing](#-contributing)
16. [📜 License](#-license)

---

## 🎯 Key Features

| Feature | Icon | Description |
|---------|------|-------------|
| **Multi-Agent Architecture** | 🤖 | 8 specialized agents running in parallel |
| **Smart Money Concepts** | 📊 | BOS, CHoCH, FVG, Order Blocks, Liquidity Zones |
| **40+ Technical Indicators** | 📈 | RSI, MACD, Bollinger, ADX, Ichimoku, Stochastic, CCI |
| **Volume Analysis** | 📉 | Volume Profile, CMF, OBV, Accumulation/Distribution |
| **Correlation Tracking** | 🔗 | Monitors 10+ instruments (DXY, Silver, Oil, EURUSD) |
| **LLM-Powered Sentiment** | 🧠 | Azure, Groq, Anthropic, OpenAI with auto-fallback |
| **Risk Management** | 🛡️ | Position sizing, R:R enforcement, portfolio limits |
| **Confidence Scoring** | 🎯 | 0-100 score with grades A+/A/B/C |
| **Multi-Timeframe** | ⏰ | M15, H1, H4, D1 alignment analysis |
| **MT5 Integration** | 📡 | Real-time data from MetaTrader 5 |

---

## 🏗️ System Architecture

```
╔═══════════════════════════════════════════════════════════════════════════════════════════════╗
║                                    GOLD MULTIAGENT ANALYZER                                     ║
║                                   Production-Ready Trading System                              ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════╣
║                                                                                                   ║
║  ┌────────────────────────────────────────────────────────────────────────────────────────────┐  ║
║  │                                      CLI INTERFACE                                           │  ║
║  │                        main.py ──► --quick --symbol --json --live                          │  ║
║  └────────────────────────────────────────────────────────────────────────────────────────────┘  ║
║                                            │                                                    ║
║                                            ▼                                                    ║
║  ╔══════════════════════════════════════════════════════════════════════════════════════════════╗  ║
║  ║                              ORCHESTRATOR (Command Center)                                   ║  ║
║  ║  ┌──────────────────────────────────────────────────────────────────────────────────────┐  ║  ║
║  ║  │  • Coordinates 8 agents in parallel                                                    │  ║  ║
║  ║  │  • Synthesizes all outputs into final recommendation                                 │  ║  ║
║  ║  │  • Multi-provider LLM fallback (Azure → Groq → Claude → OpenAI → Rule-based)        │  ║  ║
║  ║  └──────────────────────────────────────────────────────────────────────────────────────┘  ║  ║
║  ╚══════════════════════════════════════════════════════════════════════════════════════════════╝  ║
║                                            │                                                    ║
║        ┌─────────────────────────────────┼─────────────────────────────────────────────────┐    ║
║        │                                 │                                                 │    ║
║        ▼                                 ▼                                                 ▼    ║
║  ┌─────────────┐                  ┌─────────────┐                                   ┌─────────────┐
║  │    DATA     │                  │     LLM    │                                   │    RISK    │
║  │   FETCHER  │                  │  PROVIDERS  │                                   │   ENGINE   │
║  │   Agent    │                  │            │                                   │            │
║  │            │                  │  • Azure   │                                   │  • Sizing  │
║  │  MT5 Data  │                  │  • Groq    │                                   │  • R:R     │
║  │  OHLCV     │                  │  • Claude  │                                   │  • Limits  │
║  └─────────────┘                  │  • OpenAI  │                                   └─────────────┘
║        │                         └─────────────┘                                         │
║        │                               │                                                    │
║        ▼                               ▼                                                    │
║  ╔═══════════════════════════════════════════════════════════════════════════════════════╗    ║
║  ║                              8 SPECIALIZED AGENTS (PARALLEL)                              ║    ║
║  ╠═══════════════════════════════════════════════════════════════════════════════════════╣    ║
║  ║                                                                                         ║    ║
║  ║   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  ║    ║
║  ║   │    CHART    │  │   MARKET    │  │   VOLUME    │  │  CORRELATION│                  ║    ║
║  ║   │  ANALYSIS  │  │  STRUCTURE  │  │  ANALYSIS   │  │   ENGINE   │                  ║    ║
║  ║   │            │  │            │  │            │  │            │                  ║    ║
║  ║   │ RSI, MACD  │  │    BOS     │  │   Volume   │  │    DXY     │                  ║    ║
║  ║   │ Bollinger  │  │   CHoCH    │  │   Profile  │  │   Silver   │                  ║    ║
║  ║   │   ADX      │  │    FVG     │  │    CMF     │  │    Oil     │                  ║    ║
║  ║   │ Ichimoku   │  │  Order Blk │  │    OBV     │  │   EURUSD   │                  ║    ║
║  ║   │ Stochastic│  │  Liquidity │  │  Divergence│  │   Indices  │                  ║    ║
║  ║   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘                  ║    ║
║  ║                                                                                         ║    ║
║  ║   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  ║    ║
║  ║   │  SENTIMENT  │  │    RISK     │  │    TRADE   │  │            │                  ║    ║
║  ║   │   MASTER   │  │ MANAGEMENT  │  │RECOMMENDATION│  │            │                  ║    ║
║  ║   │            │  │            │  │            │  │            │                  ║    ║
║  ║   │ Fed Policy │  │  Position  │  │ Confidence │  │            │                  ║    ║
║  ║   │ Geopolitics│  │  Sizing   │  │    Score   │  │            │                  ║    ║
║  ║   │Economic   │  │  R:R      │  │    Grade   │  │            │                  ║    ║
║  ║   │   News    │  │  Limits   │  │ Entry/SL/TP│  │            │                  ║    ║
║  ║   │Positioning│  │  Blackout │  │   Trade    │  │            │                  ║    ║
║  ║   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘                  ║    ║
║  ╚═══════════════════════════════════════════════════════════════════════════════════════════════╝    ║
║        │                                                                                       │
║        ▼                                                                                       │
║  ╔══════════════════════════════════════════════════════════════════════════════════════════════╗  ║
║  ║                            FINAL OUTPUT                                                     ║  ║
║  ║  ┌─────────────────────────────────────────────────────────────────────────────────────┐  ║  ║
║  ║  │  BUY/SELL | Confidence: 82/100 | Grade: A | Entry | SL | TP1 | TP2 | R:R | Lot Size  │  ║  ║
║  ║  └─────────────────────────────────────────────────────────────────────────────────────┘  ║  ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## 🔄 Analysis Pipeline

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                              ANALYSIS PIPELINE                                              │
├──────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                  │
│  │    MT5     │    │  CORRELATED │    │    LLM      │    │   CONFIG    │                  │
│  │   DATA     │    │ INSTRUMENTS │    │   PROVIDERS │    │   FILES     │                  │
│  │            │    │             │    │             │    │             │                  │
│  │ XAUUSD     │    │ DXY        │    │ Azure      │    │ Risk Params │                  │
│  │ M15/H1/H4  │    │ Silver     │    │ Groq       │    │ Gold Config │                  │
│  │ D1         │    │ Oil        │    │ Claude     │    │ LLM Config  │                  │
│  │            │    │ EURUSD     │    │ OpenAI     │    │ Credentials│                  │
│  │            │    │ Indices    │    │             │    │             │                  │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                  │
│         │                  │                  │                  │                          │
│         └──────────────────┴──────────────────┴──────────────────┘                          │
│                                        │                                                   │
│                                        ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                    8 AGENTS RUN IN PARALLEL                                             │  │
│  │                                                                                       │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐         │  │
│  │  │   Chart    │ │   Market   │ │  Volume    │ │   Corr    │ │ Sentiment  │         │  │
│  │  │   Agent    │ │ Structure  │ │   Agent    │ │   Agent   │ │   Agent    │         │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘         │  │
│  │                                                                                       │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐                                      │  │
│  │  │   Risk    │ │   Trade    │ │   Data     │                                      │  │
│  │  │   Agent   │ │   Rec      │ │  Fetcher   │                                      │  │
│  │  └────────────┘ └────────────┘ └────────────┘                                      │  │
│  └──────────────────────────────────────────────────────────────────────────────────────┘  │
│                                        │                                                   │
│                                        ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                      TRADE RECOMMENDATION SYNTHESIS                                      │  │
│  │                                                                                       │  │
│  │   ┌────────────────────────────────────────────────────────────────────────────┐    │  │
│  │   │  CONFIDENCE SCORING (0-100)                                                     │    │  │
│  │   │  ┌────────────────────┬───────────┬─────────────────────────────────────┐    │    │  │
│  │   │  │ Component         │ Max Pts   │ Calculation                          │    │    │  │
│  │   │  ├────────────────────┼───────────┼─────────────────────────────────────┤    │    │  │
│  │   │  │ Chart Analysis    │   +/-25   │ Trend + Indicators                  │    │    │  │
│  │   │  │ Market Structure │   +/-20   │ BOS + CHoCH + OBs + FVG            │    │    │  │
│  │   │  │ Volume Analysis  │   +/-15   │ Flow + Profile + Divergence         │    │    │  │
│  │   │  │ Correlations    │   +/-15   │ DXY + Safe Haven                    │    │    │  │
│  │   │  │ Sentiment        │   +/-15   │ LLM Fundamental                   │    │    │  │
│  │   │  └────────────────────┴───────────┴─────────────────────────────────────┘    │    │  │
│  │   └────────────────────────────────────────────────────────────────────────────┘    │  │
│  │                                                                                       │  │
│  │   ┌────────────────────────────────────────────────────────────────────────────┐    │  │
│  │   │  GRADE ASSIGNMENT                                                            │    │  │
│  │   │  ┌───────────┬────────────────┬─────────────────────────────────────┐    │    │  │
│  │   │  │ Grade    │    Score       │            Action                    │    │    │  │
│  │   │  ├───────────┼────────────────┼─────────────────────────────────────┤    │    │  │
│  │   │  │   A+     │     85-100     │ Full position size                  │    │    │  │
│  │   │  │   A      │     70-84      │ Standard position size              │    │    │  │
│  │   │  │   B      │     55-69      │ Reduced position size               │    │    │  │
│  │   │  │   C      │      <55       │ Skip or paper trade only           │    │    │  │
│  │   │  └───────────┴────────────────┴─────────────────────────────────────┘    │    │  │
│  │   └────────────────────────────────────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────────────────────────────────┘  │
│                                        │                                                   │
│                                        ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                            FINAL OUTPUT                                                 │  │
│  │                                                                                       │  │
│  │   Direction: BUY/SELL    Confidence: 82/100    Grade: A    Action: TRADE             │  │
│  │                                                                                       │  │
│  │   Entry: 2658.40    Stop Loss: 2639.50    Take Profit 1: 2677.30                        │  │
│  │   Take Profit 2: 2696.20    Take Profit 3: 2715.10    R:R: 1:2.6    Lot: 0.05          │  │
│  │                                                                                       │  │
│  └──────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                              │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 The 8 Agents

| # | Agent | Icon | Role | Key Functions |
|---|-------|------|------|--------------|
| 1 | **Data Fetcher** | 📡 | Connects to MT5, retrieves multi-TF OHLCV | XAUUSD, DXY, Silver, Oil, EURUSD |
| 2 | **Chart Analysis** | 📈 | 40+ technical indicators | RSI, MACD, Bollinger, ADX, Ichimoku, Stochastic, CCI, ATR |
| 3 | **Market Structure** | 🏗️ | Smart Money Concepts | BOS, CHoCH, FVG, Order Blocks, Liquidity Zones, Premium/Discount |
| 4 | **Volume Analysis** | 📉 | Money flow analysis | Volume Profile (POC, VAH, VAL), CMF, OBV, Accumulation/Distribution |
| 5 | **Correlations Engine** | 🔗 | Cross-market analysis | DXY, Silver, Oil, EURUSD, Bonds, VIX, Indices |
| 6 | **Sentiment Master** | 🧠 | LLM-powered fundamentals | Fed Policy, Geopolitics, Economic Data, News, Positioning |
| 7 | **Risk Management** | 🛡️ | Position sizing & limits | Lot sizing, R:R enforcement, Portfolio limits, Event blackout |
| 8 | **Trade Recommendation** | 🎯 | Final signal synthesis | Confidence scoring, Grade assignment, Entry/SL/TP levels |

---

## 🎯 Confidence Scoring

### Score Components

| Component | Max Points | Description |
|-----------|------------|-------------|
| **Chart Analysis** | +/-25 | Trend direction, indicator alignment, signal strength |
| **Market Structure** | +/-20 | BOS confirmation, CHoCH, Order Blocks, FVG quality |
| **Volume Analysis** | +/-15 | Money flow direction, profile position, divergence |
| **Correlations** | +/-15 | DXY correlation, safe-haven flow, cross-market alignment |
| **Sentiment** | +/-15 | LLM fundamental score, news sentiment, positioning |

### Grade Thresholds

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              GRADE THRESHOLDS                                               │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│   Grade A+  ═══════════════════════════════════════  85-100  ═══  Full position size       │
│   Grade A   ═════════════════════════════════════════  70-84   ═══  Standard position      │
│   Grade B   ═════════════════════════════════════════  55-69   ═══  Reduced position        │
│   Grade C   ═════════════════════════════════════════   <55    ═══  Skip / Paper trade     │
│                                                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Correlation Tracking

### Monitored Instruments

| Instrument | Symbol | Expected Correlation | Type | Analysis |
|------------|--------|---------------------|------|----------|
| **US Dollar Index** | DXY | -0.85 | Inverse | Gold moves opposite to USD |
| **Silver** | XAGUSD | +0.90 | Positive | Strong correlation with gold |
| **EUR/USD** | EURUSD | +0.80 | Positive | Currency impact on gold |
| **US 10Y Bonds** | US10Y | -0.70 | Inverse | Real rates affect gold |
| **Real Rates** | - | -0.80 | Inverse | Negative correlation |
| **VIX Index** | VIX | +0.60 | Positive | Risk sentiment |
| **S&P 500** | SPX | -0.30 | Weak Inverse | Stock market correlation |
| **Crude Oil** | USOIL | +0.40 | Positive | Commodity correlation |

### Correlation Alerts

- **Divergence Detection**: Alerts when current correlation diverges from expected
- **Safe Haven Flow**: Tracks gold vs risk assets (stocks, crypto)
- **Currency Impact**: DXY impact on gold pricing
- **Momentum Confirmation**: Cross-asset momentum alignment

---

## 🧠 LLM Integration

### Multi-Provider Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              LLM PROVIDER FALLBACK                                           │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                             │
│                           ┌─────────────────┐                                              │
│                           │   User Request  │                                              │
│                           └────────┬────────┘                                              │
│                                    │                                                        │
│                                    ▼                                                        │
│                     ┌──────────────────────────────────────────┐                           │
│                     │           PRIORITY QUEUE                 │                           │
│                     │                                          │                           │
│                     │   1️⃣  Azure AI  (GPT-4o, Llama-3.1)    │◄── Primary              │
│                     │   2️⃣  Groq       (Llama-3.3-70B)        │◄── Free tier            │
│                     │   3️⃣  Anthropic  (Claude Sonnet)        │◄── Cloud                │
│                     │   4️⃣  OpenAI     (GPT-4o-mini)         │◄── Fallback             │
│                     │   5️⃣  Rule-based  (No API needed)        │◄── Always available     │
│                     └──────────────────────────────────────────┘                           │
│                                    │                                                        │
│                           ┌────────┴────────┐                                             │
│                           │   AUTO FALLBACK  │                                             │
│                           │                   │                                             │
│                           │  If provider N   │                                             │
│                           │  fails or times   │                                             │
│                           │  out → try N+1    │                                             │
│                           │                   │                                             │
│                           │  Timeout: 30s     │                                             │
│                           │  Max retries: 2   │                                             │
│                           └───────────────────┘                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Provider Details

| Priority | Provider | Models | Latency | Cost | Notes |
|----------|----------|--------|---------|------|-------|
| 1 | **Azure AI** | GPT-4o, Llama-3.1 | ~1s | $$ | Primary production |
| 2 | **Groq** | Llama-3.3-70B | ~200ms | Free | Fast inference |
| 3 | **Anthropic** | Claude Sonnet | ~1.5s | $$ | High quality |
| 4 | **OpenAI** | GPT-4o-mini | ~500ms | $ | Fallback |
| 5 | **Rule-based** | - | Instant | Free | Always available |

### LLM Use Cases

- 📰 **Sentiment Analysis**: Fed policy, geopolitical risk, economic data
- 📊 **Report Generation**: Daily analysis summary
- 💬 **Analyst Commentary**: Natural language trade rationale
- 🔍 **News Analysis**: Real-time news impact assessment

---

## 📈 Technical Indicators

### Implemented Indicators

| Category | Indicators |
|----------|-----------|
| **Trend** | EMA (9, 21, 50, 200), SMA (20, 50, 100, 200), ADX, Ichimoku |
| **Momentum** | RSI (14), MACD (12,26,9), Stochastic (14,3), CCI (14), Williams %R (14) |
| **Volatility** | Bollinger Bands (20,2), ATR (14), Keltner Channels |
| **Volume** | Volume SMA, OBV, CMF, Accumulation/Distribution |
| **Patterns** | Doji, Hammer, Engulfing, Morning/Evening Star, Harami, Pin Bar |

### Multi-Timeframe Analysis

| Timeframe | Purpose | Indicators Used |
|-----------|---------|-----------------|
| **M15** | Entry timing | All fast indicators |
| **H1** | Intraday trend | EMA 21/50, MACD, RSI |
| **H4** | Swing direction | EMA 50/200, ADX, ATR |
| **D1** | Long-term bias | EMA 200, trend structure |

---

## 💰 Risk Management

### Position Sizing Formula

```
Position Size = (Account Balance × Risk%) / (SL Distance × Point Value)
```

### Risk Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| **Max Risk per Trade** | 2.0% | Maximum risk per position |
| **Max Portfolio Risk** | 6.0% | Total risk across all positions |
| **Min R:R Ratio** | 1:1.5 | Minimum reward to risk |
| **Max Open Trades** | 3 | Maximum concurrent positions |
| **Consecutive Loss Pause** | 3 | Pause after 3 losses |

### Event Blackout

| Event | Blackout Duration |
|-------|-------------------|
| **NFP (Non-Farm Payrolls)** | +/- 1 hour |
| **CPI (Inflation)** | +/- 1 hour |
| **FOMC (Fed Rate Decision)** | +/- 2 hours |
| **Major Geopolitical** | Until resolved |

---

## 🛠️ Technology Stack

| Category | Technology | Version | Purpose |
|----------|------------|---------|---------|
| **Runtime** | Python | 3.10+ | Core language |
| **Trading** | MetaTrader5 | 5.0.45+ | Market data & execution |
| **Data** | Pandas | 2.0+ | Data manipulation |
| **NumPy** | NumPy | 1.24+ | Numerical computing |
| **HTTP** | Requests | 2.31+ | API calls |
| **Async** | aiohttp | 3.9+ | Async operations |
| **LLM** | OpenAI | 1.0+ | LLM integration |
| **LLM** | Anthropic | 0.18+ | Claude integration |
| **Logging** | Loguru | 0.7+ | Structured logging |
| **Rich** | Rich | 13.0+ | Terminal output |

---

## 📁 Project Structure

```
Gold-MultiAgent-Analyzer/
│
├── 📜 LICENSE                         # MIT License
├── 🤝 CONTRIBUTING.md                 # Contribution guidelines
├── 📖 README.md                       # This file
│
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── 🐛 bug_report.md
│   │   └── ✨ feature_request.md
│   └── 📝 PULL_REQUEST_TEMPLATE.md
│
├── main.py                            # 🎯 CLI entry point
├── unified_executor.py                # 🔄 Unified execution
├── execute_and_monitor.py             # 📊 Live monitoring
├── forex_scan.py                      # 💱 Forex scanning
├── scan_group1.py                    # 📈 Group scanning
├── scan_us_stocks.py                  # 🏦 US stock scanning
├── check_time.py                     # ⏰ Time utilities
├── test_full.py                      # 🧪 Full system test
│
├── agents/                            # 🤖 Agent modules
│   ├── __init__.py
│   ├── orchestrator.py              # 🎯 Command center
│   ├── data_fetcher_agent.py        # 📡 MT5 data retrieval
│   ├── chart_analysis_agent.py      # 📈 Technical indicators
│   ├── market_structure_agent.py    # 🏗️ SMC analysis
│   ├── volume_analysis_agent.py    # 📉 Volume profiling
│   ├── correlations_engine_agent.py# 🔗 Cross-market
│   ├── sentiment_master_agent.py   # 🧠 LLM sentiment
│   ├── risk_management_agent.py    # 🛡️ Risk controls
│   ├── sentiment/
│   │   └── sentiment_master_agent.py
│   └── trade_recommendation_agent.py# 🎯 Final signal
│
├── tools/                            # 🛠️ Tool modules
│   ├── __init__.py
│   ├── mt5_tools.py                 # MetaTrader5 wrapper
│   ├── indicator_tools.py           # Technical calculations
│   ├── pattern_tools.py             # Candlestick patterns
│   ├── structure_tools.py           # SMC functions
│   ├── volume_tools.py              # Volume analysis
│   ├── correlation_tools.py         # Cross-market
│   ├── signal_tools.py              # Signal scoring
│   ├── risk_tools.py               # Risk calculations
│   ├── sentiment_scoring_tools.py   # Sentiment analysis
│   ├── web_search_tools.py          # News scraping
│   └── __init__.py
│
├── utils/                            # 🔧 Utilities
│   ├── __init__.py
│   ├── llm_client.py               # Multi-provider LLM
│   ├── data_formatter.py           # Data conversion
│   ├── logger.py                   # Structured logging
│   └── time_utils.py               # Session context
│
├── config/                           # ⚙️ Configuration
│   ├── __init__.py
│   ├── gold_config.json             # Gold parameters
│   ├── risk_parameters.json         # Risk thresholds
│   ├── correlation_config.json      # Correlation settings
│   └── (mt5_credentials.json)        # MT5 login (gitignored)
│
├── tests/                            # 🧪 Test suite
│   └── test_system.py
│
└── requirements.txt                  # 📦 Dependencies
```

---

## 🚀 Getting Started

### Prerequisites

| Requirement | Description |
|-------------|-------------|
| 🐍 Python | 3.10+ |
| 🖥️ MT5 Terminal | Running on Windows |
| 💾 RAM | 4GB+ recommended |

### Installation

```bash
# Clone repository
git clone https://github.com/mahmoud20138/Gold-MultiAgent-Analyzer.git
cd Gold-MultiAgent-Analyzer

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# 1. Configure MT5 credentials
# Edit config/mt5_credentials.json
{
  "account": 12345678,
  "password": "your_password",
  "server": "YourBroker-Server",
  "path": "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
}

# 2. Configure LLM (optional - rule-based fallback available)
# Edit config/llm_config.json
{
  "azure_api_key": "your-key",
  "groq_api_key": "your-key",
  "anthropic_api_key": "sk-ant-...",
  "openai_api_key": "sk-..."
}

# 3. Adjust risk parameters (optional)
# Edit config/risk_parameters.json
```

---

## 💻 Usage

### Command Line Options

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

# Help
python main.py --help
```

### Example Output

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                          FINAL TRADE RECOMMENDATION                          ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  BUY   Confidence: 82/100   Grade: A   Action: TRADE                        ║
║                                                                               ║
║  LEVELS                                                                     ║
║  Entry              2658.40                                                 ║
║  Stop Loss          2639.50                                                 ║
║  Take Profit 1      2677.30                                                 ║
║  Take Profit 2      2696.20                                                 ║
║  Take Profit 3      2715.10                                                 ║
║  R:R                1:2.6                                                    ║
║  Lot Size           0.05                                                     ║
║  Risk Amount        $94.50                                                   ║
║                                                                               ║
║  Reasons:                                                                     ║
║    - Strong bullish trend (ADX > 25)                                        ║
║    - Bullish market structure (HH, HL)                                       ║
║    - Volume shows accumulation                                              ║
║    - DXY weakening -> Bullish for Gold                                      ║
║    - Sentiment score positive (7/10 bullish)                               ║
║                                                                               ║
║  Warnings:                                                                    ║
║    ! RSI overbought - watch for pullback                                     ║
║    ! Price extended above POC - consolidation likely                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝

   Overall Bias      BULLISH
   Alignment         ALIGNED (all TFs bullish)
     M15            BULLISH  strength=STRONG
     H1             BULLISH  strength=STRONG
     H4             BULLISH  strength=MEDIUM
     D1             BULLISH  strength=MEDIUM
```

---

## 📊 Results Output

### Trade Recommendation

| Field | Description |
|-------|-------------|
| **Direction** | BUY or SELL |
| **Confidence** | 0-100 score |
| **Grade** | A+, A, B, or C |
| **Action** | TRADE, SKIP, or PAPER |
| **Entry** | Recommended entry price |
| **Stop Loss** | Protective stop loss |
| **Take Profit 1/2/3** | Target levels |
| **R:R** | Risk:Reward ratio |
| **Lot Size** | Position size |
| **Risk Amount** | Dollar risk |

### Multi-Timeframe Alignment

| Timeframe | Bias | Strength |
|-----------|------|----------|
| M15 | BULLISH | STRONG |
| H1 | BULLISH | STRONG |
| H4 | BULLISH | MEDIUM |
| D1 | BULLISH | MEDIUM |

### Smart Money Concepts

| Element | Status |
|---------|--------|
| Structure | BULLISH (HH, HL) |
| Price Zone | DISCOUNT (62% of range) |
| BOS Events | 3 (latest=BULLISH_BOS @ 2645.20) |
| CHoCH Events | 1 |
| FVGs Unfilled | 2 / 5 |
| Order Blocks | 4 |

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📜 License

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) for details.

---

## ⚠️ Disclaimer

**⚠️ WARNING: Trading financial instruments carries significant risk.**

- This system is for **educational and research purposes only**
- Past performance does not guarantee future results
- Always use proper risk management
- Test on demo accounts before live trading
- The authors assume no liability for trading losses

---

<p align="center">
  Made with 🤖 for algorithmic gold trading
</p>