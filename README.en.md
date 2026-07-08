<div align="center">

# ⚜️ Gold Investment Assistant

**Gold Investment Assistant** — A multi-dimensional gold investment analysis tool based on real-time data

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Dependencies: Zero](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)](requirements.txt)
[![Platform: Cross-Platform](https://img.shields.io/badge/platform-windows%20%7C%20macos%20%7C%20linux-lightgrey.svg)](#-quick-start)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#-contributing)
[![Made with ❤️](https://img.shields.io/badge/made%20with-%E2%9D%A4-red.svg)](#-acknowledgements)

Combines **Technical · Fundamental · Sentiment** three dimensions, outputting clear trading signals and actionable advice via a quantitative scoring system.

> 📘 中文版: [README.md](README.md)

[Features](#-features) · [Project Structure](#-project-structure) · [Quick Start](#-quick-start) · [Analysis Framework](#-analysis-framework) · [Fundamental Analysis Details](#-fundamental-analysis-details) · [Data Source Architecture](#-data-source-architecture) · [Custom Configuration](#-custom-configuration) · [Technical Indicators](#-technical-indicators) · [Output Examples](#-output-examples) · [Backtesting Framework](#-backtesting-framework) · [Testing](#-testing) · [FAQ](#-faq) · [Roadmap](#-roadmap) · [Contributing](#-contributing) · [Disclaimer](#-disclaimer) · [License](#-license) · [Acknowledgements](#-acknowledgements) · [Star History](#-star-history)

</div>

---

## ✨ Features

- 📈 **Technical Analysis Engine**: RSI, MACD, Bollinger Bands, moving-average system, support/resistance, trend, momentum, divergence detection, OBV
- 🏦 **Fundamental Analysis**: Fed policy (news sentiment + real yield), USD index, inflation, yield curve, structural factors (central-bank buying, fiscal deficit, de-dollarization)
- 💭 **Sentiment Analysis**: VIX, oil price transmission, gold-silver ratio, multi-source news scraping & sentiment scoring
- 🎯 **Three-dimensional Composite Score**: weighted score (0-100), clear trading signals
- 💡 **Smart Investment Advice**: direction, position sizing, risk control, key watchpoints
- 🔄 **Multi-source Hybrid Data**: FRED API + East Money + Sina Finance + Tencent, with automatic fallback
- 📉 **Backtesting Framework**: validate the scoring system on historical data
- 🪶 **Zero Hard Dependencies**: core logic implemented with the Python standard library, works out of the box

---

## 📁 Project Structure

```
gold_assistant/
├── gold_assistant.py       # Main entry point
├── config.py               # Central config (weights, params, dictionaries, data sources)
├── hybrid_data_fetcher.py  # Hybrid data fetcher (FRED / Sina / East Money / Tencent)
├── fundamental.py          # Fundamental analysis engine
├── technical.py            # Technical analysis engine
├── sentiment.py            # Sentiment analysis engine
├── scoring.py              # Composite scoring & recommendation engine
├── report.py               # HTML report generator (Plotly charts loaded via CDN)
├── backtest.py             # Backtesting framework
├── utils.py                # Utilities (HTTP requests, logging, caching)
├── tests/
│   └── test_core.py        # Unit tests
├── docs/
│   └── screenshots/        # Report screenshots used in the README
├── reports/                # HTML report output dir (auto-generated at runtime, empty initially)
├── requirements.txt        # Dependency list (only python-dotenv is optional)
├── .env.example            # Environment variable template
├── .gitignore
├── LICENSE                 # MIT License
└── README.md
```

---

## 🚀 Quick Start

### Requirements

- **Python 3.8+**
- **Zero hard external dependencies** (core logic uses the standard library)
- FRED API Key (optional, free申请: <https://fred.stlouisfed.org/docs/api/api_key.html>)
  - Without it, the program automatically falls back to East Money + Sina Finance data sources

### 1. Clone the repository

```bash
git clone https://github.com/houguofei/gold_assistant.git
cd gold_assistant
```

### 2. Create a virtual environment (recommended)

**Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
# Core logic uses the Python standard library, no packages required to run
# Optional: install python-dotenv to auto-load FRED_API_KEY from .env
pip install -r requirements.txt
```

> 📌 The Plotly charts in the HTML report are loaded via CDN (`cdn.plot.ly`); no local Plotly package is needed. An internet connection is required when opening the HTML report.

### 4. Configure environment variables (optional)

```bash
cp .env.example .env
# Edit .env and fill in your FRED_API_KEY
```

Or set it directly as an environment variable:

**Linux / macOS:**

```bash
export FRED_API_KEY="your-key-here"
```

**Windows (PowerShell):**

```powershell
$env:FRED_API_KEY = "your-key-here"
```

### 5. Run

```bash
# Standard run (terminal report + HTML report)
python gold_assistant.py --html

# Terminal report only (default behavior, without --html)
python gold_assistant.py

# Quick mode (key indicators only)
python gold_assistant.py --quick

# Run backtest
python gold_assistant.py --backtest
```

> 💡 Command-line flags can be combined, e.g. `python gold_assistant.py --html --quick`.

After running with `--html`, the generated visual report can be found in the `reports/` directory.

---

## 📊 Analysis Framework

### Three-dimensional Scoring System

| Dimension      | Weight | Core Indicators                                                              |
| -------------- | ------ | --------------------------------------------------------------------------- |
| **Technical**  | 25%    | RSI, MACD, Bollinger Bands, MA alignment, support/resistance, momentum, divergence, OBV |
| **Fundamental**| 35%    | Fed policy, USD index, inflation, real yield, yield curve, structural factors |
| **Sentiment**  | 40%    | VIX, news sentiment, oil volatility, gold-silver ratio                       |

> Weights are configured centrally in [`config.py`](config.py) and automatically synced by `scoring.py`.

### Score → Signal Mapping

| Score Range | Signal           | Suggestion                          |
| ----------- | ---------------- | ---------------------------------- |
| 75-100      | 🟢 Strongly Bullish | Aggressive build-up/add, 30-40% position |
| 65-75       | 🟢 Bullish        | Phased build-up, 20-30% position        |
| 55-65       | 🟡 Lean Bullish   | Small试探 position, 10-15% position     |
| 45-55       | ⚪ Neutral         | Hold / maintain current position        |
| 35-45       | 🟡 Lean Bearish   | Reduce/Take profit, below 10%           |
| 25-35       | 🔴 Bearish        | Sharp reduction, below 5%               |
| 0-25        | 🔴 Strongly Bearish | Close out / exit                    |

---

## 🔧 Fundamental Analysis Details

### 1. Fed Policy Analysis

[`fundamental.py`](fundamental.py)'s `analyze_fed_policy()` decides by the following priority (use the higher-priority source when available, otherwise fall back):

| Priority | Data Source                | Description                                                                                       |
| -------- | ------------------------- | ------------------------------------------------------------------------------------------------- |
| 1️⃣       | FedWatch rate expectations (connected) | CME Fed funds futures implied cut/hike probabilities, fetched live by [`hybrid_data_fetcher.py`](hybrid_data_fetcher.py)'s `_fetch_fedwatch_rates()` |
| 2️⃣       | News sentiment + Fed funds rate    | Scan multi-source news keywords to quantify hawkish/dovish bias (`fed_news_sentiment`, **auto-computed** by the data fetcher), combined with the absolute rate level |
| 3️⃣       | Real yield (always added)         | `US10Y - CPI`; <1% bullish for gold, >2% bearish for gold (applied on top of either branch above) |

**Hawkish/Dovish keyword scoring**:

News headlines are scanned and scored by weighted keywords (positive = dovish/bullish, negative = hawkish/bearish). The full dictionaries are in [`config.py`](config.py) as `KEYWORD_SENTIMENT` (Chinese) and `KEYWORD_SENTIMENT_EN` (English). Examples:

| Type            | Keywords (ZH)                                      | Keywords (EN)                                                       | Score  |
| --------------- | -------------------------------------------------- | ------------------------------------------------------------------ | ------ |
| **Hawkish**     | 加息(-8), 加息预期(-7), 鹰派(-7), 紧缩(-6)           | rate hike(-8), hawkish(-7), tightening(-6), higher for longer(-7)  | Negative |
| **Dovish**      | 降息(+8), 降息预期(+7), 鸽派(+7), 宽松(+6)           | rate cut(+8), dovish(+7), easing(+6), pivot(+6)                    | Positive |
| **Safe-haven/Geo** | 避险需求(+5), 地缘政治(+4), 央行购金(+7), 战争(+5) | safe haven(+6), geopolitical(+4), central bank buy(+7), war(+6)   | Positive |
| **Recession/Crisis** | 衰退(+5), 硬着陆(+5), 银行危机(+6), 滞胀(+7)    | recession(+5), hard landing(+5), banking crisis(+6), stagflation(+7) | Positive |

**Per-news cap**: a single news item's impact is clamped to `-10 ~ +10` (`max(-10, min(10, total_score))`) to prevent one extreme headline from dominating.

**News sentiment → hawkish/dovish thresholds** (`fundamental.py::_fed_policy_from_news`):

| `fed_news_sentiment` | Judgment      | Impact on gold | Score adj. |
| -------------------- | ------------- | -------------- | ---------- |
| `< -5`               | Strong hawkish| Bearish        | -15        |
| `-5 ~ -2`            | Lean hawkish  | Bearish        | -10        |
| `-2 ~ +2`            | Neutral       | Neutral        | 0          |
| `+2 ~ +5`            | Lean dovish   | Bullish        | +10        |
| `> +5`               | Strong dovish | Bullish        | +15        |

> 📌 `fed_news_sentiment` is auto-computed by the data fetcher (scanning Fed-related news sources); no manual setting is required. To override, set it in `USER_MACRO_OVERRIDES` in `gold_assistant.py`, or extend `hybrid_data_fetcher.py` with more real-time news sources.

### 2. USD Index Analysis

- Data source: FRED `DTWEXBGS` (Broad trade-weighted USD index, scale ~120; not the traditional ICE DXY ~100)
- **Level thresholds**: >125 strongly bearish (-20), >119 mildly bearish (-10), <113 bullish (+15)
- **3-month trend**: rise >5% strong pressure (-15), >2% pressure (-8), fall >3% supportive (+12)
- **1-year trend**: rise >5% bearish (-8), fall >5% bullish (+8)

> ⚠️ Note: `DTWEXBGS` is a trade-weighted broad USD index whose range differs from the traditional DXY. The thresholds in code are calibrated for this scale.

### 3. Inflation Analysis

- Data source: FRED `CPIAUCSL` (CPI index), `CPILFESL` (core CPI index); fallback: East Money CPI YoY interface
- YoY auto-computed: `(current - 12 months ago) / 12 months ago * 100`
- Trend derivation: compare the mean of the last 3 months vs the prior 3 months (`rising` / `cooling` / `stable`)
- **CPI YoY thresholds**: >5% strong bullish (+15), >3% mild support (+8), <2% weakens demand (-8)
- **Core CPI thresholds**: >4% supports inflation premium (+8), <2% mildly bearish (-5)
- **Inflation trend**: `rising` +10, `cooling` -5, `stable` 0

### 4. Yield Curve

- Data source: FRED `DGS10` / `DGS2`; fallback: East Money bond yield interface
- **2s10s spread thresholds**:
  - `< -0.5%` deep inversion → strong bullish (+15, strong recession expectation)
  - `-0.5% ~ -0.1%` inversion → supports gold (+8)
  - `-0.1% ~ 0.3%` flat → neutral (+2)
  - `> 0.3%` steep → mildly bearish (-3, better economic outlook)

### 5. Structural Factors

Long-term structural factors are quantified in [`fundamental.py`](fundamental.py)'s `analyze_structural()`, weighing 30% of the fundamental dimension (the highest).

| Factor                      | Threshold    | Score adj. |
| --------------------------- | ------------ | ---------- |
| **US fiscal deficit / GDP** | >6%          | +18        |
| <br />                     | >4%          | +10        |
| <br />                     | <3%          | -5         |
| **US debt / GDP**          | >130%        | +12        |
| <br />                     | >100%        | +6         |
| **Central banks planning to increase gold** | >40% | +10        |
| <br />                     | >25%         | +5         |
| **Central-bank buying trend**     | `rising` | +5         |
| **De-dollarization momentum**     | >0.7    | +8         |
| <br />                     | >0.4         | +3         |

> 📌 Data source: default values reference the World Gold Council 2024 report and can be updated in [`config.py`](config.py)'s `MACRO_PARAMS`. Geopolitical risk is not scored directly in this dimension; it is reflected indirectly in the sentiment dimension via news keywords ("地缘政治"/geopolitical, "战争"/war, "中东"/Middle East, "制裁"/sanctions, etc.).

---

## 📡 Data Source Architecture

### Macro Data Priority

```
East Money datacenter → FRED API (requires Key) → Sina Finance → Tencent US-ETF proxy (UUP→DXY, TLT→Treasury yields) → default-value fallback
```

> 📌 The real-time **gold price** chain prioritizes **Sina Finance** (see next section), while the **macro data** chain prioritizes **East Money**, with FRED as a precise supplement (requires `FRED_API_KEY`). Missing the FRED Key auto-degrades without affecting operation.

| Item              | Primary source           | Fallback source                          | Notes                                                  |
| ----------------- | ------------------------ | ---------------------------------------- | ------------------------------------------------------ |
| Fed funds rate    | East Money datacenter    | FRED FEDFUNDS                           | Current policy rate                                   |
| CPI YoY           | East Money datacenter    | FRED CPIAUCSL                           | YoY auto-computed                                    |
| US10Y / US2Y      | East Money bond interface| Tencent TLT proxy / FRED DGS10·DGS2     | Real-time yields                                     |
| DXY               | East Money global index  | Tencent UUP proxy / FRED DTWEXBGS       | East Money/UUP proxy scale ~100, FRED DTWEXBGS scale ~120 |
| Core CPI          | FRED `CPILFESL`          | —                                        | YoY computed from history                            |
| Inflation trend   | FRED `CPIAUCSL`          | —                                        | Last 3-month mean vs prior 3-month mean              |

### News Data Sources

News sources are configured in [`config.py`](config.py)'s `NEWS_SOURCES` and scraped by [`sentiment.py`](sentiment.py)'s `fetch_news_from_rss()`:

| Source               | Type          | Content                                |
| -------------------- | ------------- | -------------------------------------- |
| Sina Finance - US stocks | sina\_api | Global financial market headlines      |
| Sina 7x24 flash news | html\_parse  | Real-time market moves                |
| Sina Finance - Gold  | sina\_api    | Precious metals / gold (keyword filter) |
| Sina Finance - Fed   | sina\_api    | Monetary policy / central bank (keyword filter) |
| Reuters              | rss          | International financial news           |

### Real-time Prices & Historical K-lines

Gold price uses a multi-tier fallback chain ([`hybrid_data_fetcher.py`](hybrid_data_fetcher.py)'s `fetch_gold_data()`):

```
Spot price:   Sina spot hf_XAU (XAU/USD) → East Money futures hf_GC → Tencent futures hf_GC → manual price → reference $4,000 fallback
History K-line: Sina COMEX futures hf_GC (full history) → Sina Shanghai gold AU0 (CNY/gram, auto-scaled) → East Money 113.aum → simulated history based on the real current price
```

> ⚠️ When all real K-line sources are unavailable, the program generates a segment of simulated history based on the **real current price** (for technical-indicator computation only) and explicitly marks it `data_quality=simulated` in logs and reports; technical indicators are for reference only in that case.

| Instrument                | Real-time source                                                  | Notes                  |
| ------------------------- | ---------------------------------------------------------------- | ---------------------- |
| Gold (spot/futures)       | Sina `hf_XAU` / East Money `hf_GC` / Tencent `hf_GC`            | Multi-source fallback  |
| Silver / Oil / VIX / S&P | Sina futures (`hf_SI` / `hf_CL` / `hf_VX` / `hf_ES`)            | `hq.sinajs.cn`         |
| USD index / Treasuries (fallback) | East Money global index / Tencent US-ETF (`UUP` / `TLT`) proxy | `qt.gtimg.cn`          |

---

## 🛠️ Custom Configuration

All configuration lives in [`config.py`](config.py) to avoid scattered maintenance.

### Update macro parameters

Edit `MACRO_PARAMS` in `config.py` (these are fallback defaults, overwritten at runtime by live data):

```python
MACRO_PARAMS = {
    "fed_rate_upper": 3.75,            # Upper bound of fed funds rate (%)
    "dxy_current": 120.89,             # USD index (DTWEXBGS scale, ~120)
    "cpi_yoy": 4.2,                    # CPI YoY (%)
    "core_cpi_yoy": 2.82,              # Core CPI YoY (%)
    "us10y_yield": 4.38,               # 10Y Treasury yield (%)
    "us2y_yield": 4.10,                # 2Y Treasury yield (%)
    "us10y_real": 0.18,                # Real yield (%)
    "yield_curve_2s10s": 0.28,         # 2s10s spread (%)
    "inflation_trend": "rising",       # Inflation trend: rising / cooling / stable
    "fed_policy_tone": "neutral",      # Fed policy tone: hawkish / dovish / neutral
    "us_fiscal_deficit_gdp": 6.0,      # Fiscal deficit / GDP (%)
    "us_debt_gdp": 125.0,              # Debt / GDP (%)
    "cb_buying_pct_plan_increase": 45, # % of central banks planning to increase gold
    "dedollarization_momentum": 0.7,   # De-dollarization momentum (0-1)
}
```

> 💡 The program automatically fetches the latest data from FRED / East Money to override defaults. To force custom values, set them in `USER_MACRO_OVERRIDES` in `gold_assistant.py`.

### Adjust scoring weights

Edit `SCORING["weights"]` in `config.py`:

```python
SCORING = {
    "weights": {
        "technical":   25,   # Technical
        "fundamental": 35,   # Fundamental
        "sentiment":   40,   # Sentiment
    },
}
```

> 📌 The sum of weights need not equal 100; `scoring.py` normalizes automatically. At runtime, weights are also dynamically adjusted by the market regime (bull/bear/sideways) detected from the technical side — see `ScoringEngine._adjust_weights_by_regime()`.

### Adjust the sentiment dictionary

Edit `KEYWORD_SENTIMENT` (Chinese) and `KEYWORD_SENTIMENT_EN` (English) in `config.py`:

```python
KEYWORD_SENTIMENT = {
    "加息": -8, "降息": +8, "鹰派": -7, "鸽派": +7,
    "央行购金": +7, "地缘政治": +4, "衰退": +5,
    # ... more keywords
}
```

---

## 📋 Technical Indicators

| Indicator       | Description                              | Buy signal                  | Sell signal                        |
| --------------- | ---------------------------------------- | --------------------------- | --------------------------------- |
| RSI(14)         | Relative Strength Index                 | <30 oversold                | >70 overbought                    |
| MACD            | Trend & momentum                        | Golden cross / histogram turns positive | Death cross / histogram turns negative |
| Bollinger Bands | Volatility channel                      | Touches lower band          | Touches upper band                |
| MA              | Trend direction                         | Short > long (bullish alignment) | Short < long (bearish alignment) |
| ATR             | Volatility (display only, not scored)   | High vol = more opportunity | High vol = more risk              |
| OBV             | On-Balance Volume                       | Price up + volume up        | Price down + volume up (divergence) |
| Divergence      | Price vs indicator divergence            | Bullish divergence          | Bearish divergence               |
| Support/Resistance | Key price levels (display only, not scored) | Pullback to support holds (bullish) | Breakdown of support / breakout (bearish) |

---

## 📄 Output Examples

### Terminal Output

> The actual terminal output includes **market snapshots, factor-level detail of each dimension's scoring process, the composite score formula & weights, investment advice, risk control, key watchpoints, and risk level**. The following is an excerpt:

```
======================================================================
  ⚜️  Gold Investment Analysis Assistant  |  Gold Investment Assistant
  📅 2026-07-01 18:00:00
======================================================================

  💰 Gold Spot Price (XAU/USD):  $3,350.00/oz
  📊 Intraday change:      +15.20 (+0.46%)

  📈 Technical Analysis
  Market regime: Sideways (confidence 60%) (60d change: +1.20%)
  Score dimensions: RSI(20%) + MACD(15%) + Bollinger(10%) + MA trend(20%) + Divergence(15%) + Momentum(10%) + Volume(10%)
    RSI(14): 54.3 → Neutral
    MACD: 2.15 / 1.98 → Golden cross
    ...
    Final score: 58.2/100  ████████████████████░░░░░░░░░░

  🏦 Fundamental Analysis
  Score dimensions: Fed policy(25%) + USD(20%) + Inflation(15%) + Yield curve(10%) + Structural(30%)
    🏛️ Fed policy: score +12 × weight 25% = +3.0 → Bullish
    ...
    Final score: 52.4/100  █████████████████░░░░░░░░░░░░░

  💭 Sentiment Analysis
  ...

  🎯 Composite Conclusion
  Composite weights: Tech×25% + Fundamental×35% + Sentiment×40%
  Final score: 55.1/100  ████████████████████░░░░░░░░░░
  Composite signal: 🟡 Lean Bullish
  Suggestion: small试探 position
  Position: 10-15%
  💡 Risk control: Stop-loss 3-5% | Take-profit 10-15% | Max drawdown 5-8%
  ⚠️ Key watchpoints: Technical leaning bullish: watch whether price breaks above resistance, whether RSI is overbought
```

> 💡 For the full example, run `python gold_assistant.py --html` locally; the terminal and the HTML report in `reports/` show all analysis details.

### HTML Report

Running `python gold_assistant.py --html` generates a dark-themed visual report in `reports/`, including:

- Real-time price and market snapshot
- **Plotly interactive price chart** (with MA20 / MA50)
- **Plotly interactive RSI chart** (with overbought / oversold lines)
- Three-dimension score cards
- Per-dimension detailed analysis
- Investment advice and risk control
- Key watchpoint list

### Report Screenshot

![HTML Report Example](docs/screenshots/image.png)

> 📸 PRs adding more screenshots to `docs/screenshots/` are welcome.

---

## 🧪 Backtesting Framework

[`backtest.py`](backtest.py) provides historical backtesting:

- Simulate scoring day by day on historical data
- Compute Pearson correlation between composite score and future N-day returns
- Analyze average return and win rate per score bucket
- Evaluate long/short strategies (long ≥65 / short ≤35)

> ⚠️ **Backtesting limitation**: by default `technical_only=True`, i.e. only the **technical** signal participates (based on real K-lines, reliable); fundamental/sentiment use static/neutral values, **for illustration only**. If all historical K-line sources are unavailable, it degrades to **simulated-data** backtesting (demonstration logic only, not real conclusions).

```bash
python gold_assistant.py --backtest
# or
python backtest.py
```

Backtest results are saved as `backtest_result.json` (already ignored by `.gitignore`).

---

## 🧫 Testing

Run unit tests with pytest:

```bash
# Install pytest if not yet installed
pip install pytest

# Run tests
pytest tests/ -v
```

Or run the test file directly:

```bash
python tests/test_core.py
```

Tests cover the following (see [`tests/test_core.py`](tests/test_core.py)):

- **Technical analysis**: SMA, EMA, RSI, MACD, Bollinger Bands
- **Scoring engine**: three-dimensional weighted scoring, extreme scores, weight normalization
- **Config validation**: `TECH_SCORE_WEIGHTS` structure integrity
- **Utilities**: `safe_float`, `safe_int`, `clamp`

---

## ❓ FAQ

<details>
<summary><b>Can I use it without a FRED API Key?</b></summary>

Yes. Real-time gold price and historical K-lines come from Sina / East Money / Tencent and need no FRED Key; macro data (Treasury yields, CPI, DXY history, etc.) is fetched first from East Money, Sina, and Tencent proxies, with the FRED Key as a more precise supplement. Without the Key the program auto-degrades and remains fully usable.

</details>

<details>
<summary><b>Windows terminal emoji / Chinese garbling?</b></summary>

The program already forces stdout to UTF-8. If issues persist, run:

- PowerShell: `chcp 65001`
- CMD: `chcp 65001`
- Or use a modern terminal such as Windows Terminal.

</details>

<details>
<summary><b>Data source request failed / rate-limited?</b></summary>

- The built-in multi-source fallback ensures a single source failure doesn't break the run
- Sina's API may occasionally rate-limit frequent requests; retry after a few minutes
- FRED free tier is limited to 120 requests/minute, which normal usage won't hit

</details>

<details>
<summary><b>What dependencies do I need to install?</b></summary>

**Zero hard dependencies**. The core logic (HTTP requests, technical indicators, report generation) is entirely implemented with the Python standard library. The only optional dependency in `requirements.txt` is `python-dotenv`, used to auto-load `FRED_API_KEY` from `.env`. The Plotly charts in the HTML report load via CDN, so no local install is needed.

</details>

<details>
<summary><b>How do I adjust the scoring weights?</b></summary>

Edit the `SCORING["weights"]` dict in [`config.py`](config.py). The three dimension weights need not sum to 100; the program normalizes automatically.

</details>

<details>
<summary><b>Does it support other instruments (silver/oil)?</b></summary>

The primary analysis target is gold. `hybrid_data_fetcher.py` already implements data fetching for silver, oil, VIX, etc., which can serve as sentiment auxiliary indicators. To analyze other instruments independently, extend the main flow in `gold_assistant.py`.

</details>

---

> Suggestions and priority votes are welcome in [Issues](../../issues).

---

## 🤝 Contributing

Issues and Pull Requests are welcome!

### Contribution Workflow

1. **Fork** this repository
2. Create a feature branch: `git checkout -b feature/AmazingFeature`
3. Commit your changes: `git commit -m 'Add some AmazingFeature'`
4. Push the branch: `git push origin feature/AmazingFeature`
5. Open a **Pull Request**

### Contribution Areas

- 🐛 Report or fix bugs ([open an Issue](../../issues/new?labels=bug))
- 💡 Propose new features ([open an Issue](../../issues/new?labels=enhancement))
- 📝 Improve docs and examples
- 🌍 Translate the README to other languages
- 🧪 Add more test cases
- 🔌 Integrate new data sources

### Code Standards

- Keep Python code style consistent (PEP 8)
- New features need accompanying tests (in `tests/`)
- Changing config items requires syncing the README
- Commit messages may be in Chinese or English, as long as they are clear

---

## ⚠️ Disclaimer

- This tool is for **learning and research purposes only** and **does not constitute investment advice**
- Gold markets are highly volatile; past performance does not guarantee future returns
- Please decide cautiously according to your own risk tolerance
- All data and analysis may have latency or errors
- The author assumes no liability for any direct or indirect loss caused by using this tool

---

## 📄 License

This project is open-sourced under the [MIT License](LICENSE).

You are free to use, modify, and distribute the code, but please retain the original license notice.

---

## 🙏 Acknowledgements

Data sources for this project include:

- [FRED (Federal Reserve Economic Data)](https://fred.stlouisfed.org/) — Fed economic data
- [East Money Data Center](https://data.eastmoney.com/) — macroeconomic data
- [Sina Finance](https://finance.sina.com.cn/) — real-time quotes and news
- [Tencent Finance](https://gu.qq.com/) — US-ETF quote proxy
- [Reuters](https://www.reuters.com/) — international financial news (one of the sentiment sources)

Thanks to the above data sources for their service to the open-source community.

---

## ⭐ Star History

<a href="https://star-history.com/#houguofei/gold_assistant&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=houguofei/gold_assistant&type=Date&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=houguofei/gold_assistant&type=Date" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=houguofei/gold_assistant&type=Date" />
  </picture>
</a>

---

<div align="center">

**If this project helps you, please ⭐ Star to support!**

Made with ❤️ for gold investors

</div>
