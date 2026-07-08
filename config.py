# -*- coding: utf-8 -*-
"""
黄金投资助手 - 配置文件（单一数据源）
Gold Investment Assistant - Configuration (Single Source of Truth)

所有阈值、权重、参数均集中管理，避免硬编码散落在各模块。
"""

# ============================================================
# API 配置
# ============================================================

YAHOO_API_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"

# 可用的数据源（按优先级排列）
DATA_SOURCES = ["yahoo", "fallback"]

# FRED API 配置
# 优先级: .env 文件 > 环境变量 > 空值（自动降级）
# 获取免费 Key: https://fred.stlouisfed.org/docs/api/api_key.html
import os

# 尝试加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv 未安装，跳过

FRED_API_KEY = os.environ.get("FRED_API_KEY", "")

# FRED 系列 ID 配置
# observation_start 参数用于获取历史数据（计算同比/环比）
FRED_SERIES = {
    "us10y_yield":      {"id": "DGS10",    "history_days": 365},  # 10年期美债收益率
    "us2y_yield":       {"id": "DGS2",     "history_days": 365},  # 2年期美债收益率
    "us10y_tips":       {"id": "DFII10",   "history_days": 365},  # 10年期TIPS实际收益率
    "dxy_index":        {"id": "DTWEXBGS", "history_days": 400},  # 美元指数（Broad）
    "cpi_index":        {"id": "CPIAUCSL", "history_days": 400},  # CPI指数（需计算同比）
    "core_cpi_index":   {"id": "CPILFESL", "history_days": 400},  # 核心CPI指数（需计算同比）
    "fed_rate":         {"id": "FEDFUNDS", "history_days": 180},  # 联邦基金利率
    "vix":              {"id": "VIXCLS",   "history_days": 30},   # VIX（备用）
}

# FRED key → MACRO_PARAMS key 的映射
FRED_TO_MACRO_MAP = {
    "us10y_yield":      "us10y_yield",
    "us2y_yield":       "us2y_yield",
    "us10y_tips":       "us10y_real",
    "dxy_index":        "dxy_current",
    "cpi_index":        "cpi_index",       # 先存指数，后续计算同比
    "core_cpi_index":   "core_cpi_index",  # 先存指数，后续计算同比
    "fed_rate":         "fed_rate_upper",
}

# ============================================================
# 交易品种代码
# ============================================================

TICKERS = {
    "gold":     "GC=F",       # COMEX黄金期货
    "silver":   "SI=F",       # COMEX白银期货
    "dxy":      "DX-Y.NYB",   # 美元指数
    "us10y":    "^TNX",       # 10年期美债收益率
    "us2y":     "2YY=F",      # 2年期美债收益率（正确代码）
    "sp500":    "^GSPC",      # S&P 500
    "oil":      "CL=F",       # WTI原油
    "vix":      "^VIX",       # VIX恐慌指数
    "gld":      "GLD",        # SPDR黄金ETF（用于资金流）
}

# 新浪财经期货代码映射（国内可访问）
# 参考: https://finance.sina.com.cn/money/future/hf.html
SINA_SYMBOLS = {
    # 贵金属
    "gold":     "hf_XAU",     # 伦敦金现货（XAU/USD）
    "silver":   "hf_SI",      # COMEX白银
    # 能源
    "oil":      "hf_CL",      # WTI原油
    "brent_oil": "hf_OIL",    # 布伦特原油
    # 指数
    "dxy":      "hf_DX",      # ICE美元指数期货
    "sp500":    "hf_ES",      # S&P 500 E-mini期货
    "vix":      "hf_VX",      # VIX指数期货
    # 国债期货
    "us10y":    "hf_TY",      # 10年期美国国债期货
    "us2y":     "hf_TU",      # 2年期美国国债期货
}

# 黄金期货代码（用于历史K线获取，现货 hf_XAU 无K线时降级使用）
# COMEX 黄金期货 hf_GC 有完整历史K线，与现货 XAU/USD 基差小（通常 <1%）
SINA_GOLD_FUTURES_SYMBOL = "hf_GC"

# ============================================================
# 数据获取配置
# ============================================================

DATA_FETCH = {
    "request_timeout": 15,         # HTTP 请求超时（秒）
    "request_delay": 1.0,          # 请求间隔（秒），防封IP
    "fred_delay": 0.3,             # FRED 请求间隔
    "kitco_url": "https://www.kitco.com/charts/livegold.html",
    "min_gold_price": 1000,        # 黄金最低合理价格（过滤异常值）
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# ============================================================
# 技术分析参数
# ============================================================

TECHNICAL = {
    # 历史数据天数
    "history_days": 120,

    # 移动平均线周期（综合分析用）
    "ma_short": 20,
    "ma_mid": 50,
    "ma_long": 200,

    # 金叉/死叉检测用均线
    "cross_short": 5,
    "cross_long": 20,

    # RSI
    "rsi_period": 14,
    "rsi_overbought": 70,       # RSI 超买线
    "rsi_oversold": 30,         # RSI 超卖线
    "rsi_extreme_overbought": 80,
    "rsi_extreme_oversold": 20,

    # 布林带
    "bollinger_period": 20,
    "bollinger_std": 2.0,

    # MACD
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,

    # ATR
    "atr_period": 14,

    # 支撑/阻力
    "sr_lookback": 60,
    "sr_tolerance": 0.02,
    "sr_max_levels": 5,         # 最多显示几个支撑/阻力位

    # 背离检测
    "divergence_lookback": 20,

    # 成交量
    "volume_ma": 20,
    "volume_high_ratio": 1.3,   # 放量阈值
    "volume_low_ratio": 0.7,    # 缩量阈值

    # 趋势判断用的短期均线天数
    "trend_short_ma": 5,
}

# 技术面评分阈值（score → signal）
TECH_SCORE_THRESHOLDS = {
    "strong_buy": 70,
    "buy": 60,
    "lean_buy": 55,
    "neutral_upper": 45,  # 中性区间上界
    "neutral_lower": 40,  # 中性区间下界
    "lean_sell": 30,
}

# 技术面评分权重 — 各指标对综合得分的贡献
# 每个指标包含 max_bonus（最大加/减分幅度）和 weight（权重说明，仅文档用途）
TECH_SCORE_WEIGHTS = {
    "rsi":        {"max_bonus": 10, "desc": "RSI超买超卖（20%）"},
    "macd":       {"max_bonus": 7.5, "desc": "MACD趋势动量（15%）"},
    "bollinger":  {"max_bonus": 5, "desc": "布林带位置（10%）"},
    "trend":      {"max_bonus": 7, "desc": "均线趋势方向（20%）"},
    "short_trend": {"max_bonus": 3, "desc": "短期趋势（附加）"},
    "crossover":  {"max_bonus": 5, "desc": "金叉/死叉信号（附加）"},
    "momentum":   {"max_bonus": 5, "desc": "5日动量（10%）"},
    "divergence": {"max_bonus": 7.5, "desc": "背离信号（15%）"},
    "obv":        {"max_bonus": 2.5, "desc": "OBV能量潮（5%）"},
    "volume":     {"max_bonus": 2.5, "desc": "成交量分析（5%）"},
}

# ============================================================
# 基本面分析参数
# ============================================================

FUNDAMENTAL = {
    # 内部维度权重（总计 = 1.0）- 提高结构性权重以反映长期重要性
    "dim_weights": {
        "fed_policy": 0.25,       # Fed政策：25%
        "usd_impact": 0.20,       # 美元影响：20%
        "inflation": 0.15,        # 通胀：15%
        "yield_curve": 0.10,      # 收益率曲线：10%
        "structural": 0.30,       # 结构性因素：30%（财政赤字、去美元化、央行购金等长期趋势）
    },
    # 分数映射系数（-50~+50 → 0~100 的缩放因子）
    "score_scale": 0.6,
}

# 基本面评分阈值
FUND_SCORE_THRESHOLDS = {
    "bullish": 65,
    "lean_bullish": 55,
    "neutral_upper": 45,
    "neutral_lower": 35,
}

# ============================================================
# 情绪面分析参数
# ============================================================

SENTIMENT = {
    # RSS 源配置
    "rss_sources": [
        {"url": "https://www.reuters.com/markets/commodities/rss.xml", "name": "Reuters"},
        {"url": "https://feeds.bbci.co.uk/news/business/rss.xml", "name": "BBC Business"},
        {"url": "https://rss.cnn.com/rss/money_markets.rss", "name": "CNN Money"},
    ],
    "rss_timeout": 10,           # RSS 请求超时（秒）
    "rss_max_per_source": 5,     # 每个源最多抓几条

    # 内部维度权重（总计 = 1.0）
    "dim_weights": {
        "vix": 0.25,               # VIX恐慌指数：25%（市场恐慌是黄金主要驱动因素）
        "news": 0.40,              # 新闻情绪：40%（央行购金、地缘政治、避险需求等）
        "oil": 0.20,               # 原油价格：20%（能源通胀与黄金相关性）
        "gold_silver_ratio": 0.15, # 金银比：15%（相对估值指标）
    },
    # 分数映射系数
    "score_scale": 0.83,

    # 默认油价（仅在获取失败时使用）
    "default_oil_price": 75.0,
}

# 情绪面评分阈值
SENT_SCORE_THRESHOLDS = {
    "bullish": 60,
    "neutral": 50,
    "bearish": 40,
}

# 关键词情绪词典（关键词 → 分数）
KEYWORD_SENTIMENT = {
    # 中文关键词 - 货币政策
    "加息": -8, "加息预期": -7, "鹰派": -7, "紧缩": -6,
    "降息": +8, "降息预期": +7, "鸽派": +7, "宽松": +6,
    "通胀上升": +6, "高通胀": +6, "通胀压力": +5,
    "通胀回落": -4, "通缩": -5,
    "美元走强": -6, "美元飙升": -7, "美元上涨": -5,
    "美元走弱": +6, "美元下跌": +5, "美元贬值": +6,
    "避险需求": +5, "地缘政治": +4, "地缘风险": +4, "战争": +5,
    "央行购金": +7, "央行增持": +7, "储备多元化": +5,
    "财政赤字": +4, "债务上限": +4, "去美元化": +6,
    "衰退": +5, "经济放缓": +4, "硬着陆": +5,
    "黄金ETF流入": +5, "ETF增持": +5,
    "黄金ETF流出": -5, "ETF减持": -5,
    "避险情绪": +5, "恐慌": +4, "VIX飙升": +5,
    "油价上涨": +4, "能源通胀": +4,
    "油价暴跌": -4,
    "美伊": +4, "中东": +4, "俄乌": +4,
    "制裁": +3, "关税": +3,
    "牛市": +4, "熊市": -4,
    "逢低买入": +3, "买入机会": +3, "增持": +4,
    "减持": -4, "卖出": -4, "清仓": -5,
    "目标价上调": +3, "目标价下调": -3,
    "突破": +4, "跌破": -4, "支撑位": +2, "阻力位": -2,
    # 黄金特有关键词
    "黄金": +3, "金价": +3, "贵金属": +2, "避险资产": +4,
    "COMEX": +2, "伦敦金": +2, "现货黄金": +2,
    "央行黄金": +5, "黄金储备": +5,
    "黄金期货": +2, "黄金价格": +2,
    "黄金上涨": +4, "黄金下跌": -4,
    "白银": +2, "铂金": +1,
    # 扩展关键词 - 市场相关
    "美联储": +1, "联储": +1, "FOMC": +1, "鲍威尔": +1,
    "非农数据": +2, "就业数据": +1, "失业率": +1,
    "CPI": +2, "PPI": +1, "PCE": +2,
    "国债收益率": +2, "美债": +1, "收益率": +1,
    "美元指数": +2, "DXY": +1,
    "贸易摩擦": +3, "贸易战": +4, "关税战": +3,
    "量化宽松": +6, "QE": +5, "缩表": -5, "QT": -4,
    "滞胀": +7, "经济衰退": +5,
    "银行危机": +6, "金融危机": +6, "系统性风险": +5,
    "股市下跌": +3, "股市崩盘": +5, "暴跌": +3,
    "股市大涨": -3, "创新高": -2,
    "不确定性": +3, "风险": +2, "动荡": +3,
    # 中国相关
    "人民币": +2, "汇率": +1, "外汇储备": +2,
    "中国央行": +3, "人民银行": +3,
}

# 英文关键词词典（适配Reuters/CNBC/BBC等英文RSS源）
KEYWORD_SENTIMENT_EN = {
    # Fed/Monetary policy - bearish for gold
    "rate hike": -8, "hike rates": -8, "hawkish": -7, "tightening": -6,
    "higher for longer": -7, "rate increase": -7,
    # Fed/Monetary policy - bullish for gold
    "rate cut": +8, "cut rates": +8, "dovish": +7, "easing": +6,
    "pause": +4, "pivot": +6, "lower rates": +7,
    # Inflation - mixed, high inflation bullish
    "higher inflation": +6, "inflation rises": +6, "hot inflation": +6,
    "inflation cools": -4, "disinflation": -5, "deflation": -5,
    "stagflation": +7,
    # USD
    "dollar strengthens": -6, "strong dollar": -6, "dollar rises": -5,
    "dollar weakens": +6, "weak dollar": +6, "dollar falls": +5,
    "dollar index": 0,
    # Safe haven / Geopolitics - bullish
    "safe haven": +6, "geopolitical": +4, "tensions": +4, "war": +6,
    "conflict": +5, "crisis": +4, "risk off": +5, "risk aversion": +4,
    "sanctions": +3, "tariffs": +3, "middle east": +4, "ukraine": +4,
    "taiwan": +4,
    # Central bank buying - bullish
    "central bank buy": +7, "central bank gold": +6, "reserve diversification": +5,
    "gold reserves": +5,
    # Recession/Economy - bullish for safe haven
    "recession": +5, "slowdown": +4, "hard landing": +5,
    "soft landing": -4, "growth concerns": +3, "banking crisis": +6,
    # Debt/Deficit - bullish long-term
    "debt ceiling": +4, "fiscal deficit": +4, "debt crisis": +5,
    "dedollarization": +6,
    # ETF flows
    "etf inflow": +5, "gold etf buys": +5,
    "etf outflow": -5, "gold etf sells": -5,
    # Fear/VIX
    "vix spike": +5, "panic": +4, "fear gauge": +4,
    "volatility surges": +4,
    # Oil/Energy
    "oil rises": +3, "oil surges": +4, "energy prices": +3,
    "oil plunges": -4, "oil crashes": -5,
    # Technical/Market action
    "gold hits record": +6, "all-time high": +5, "breakout": +4,
    "gold drops": -4, "sell-off": -5, "plunges": -5,
    "bullish": +4, "bearish": -4,
    "buy the dip": +3, "buying opportunity": +3,
    "outlook raised": +3, "outlook cut": -3,
    "support level": +2, "resistance level": -2,
    # Jobs/Unemployment
    "strong jobs": -5, "payrolls beat": -4, "low unemployment": -3,
    "weak jobs": +5, "jobless claims rise": +4, "layoffs": +4,
}

# ============================================================
# 综合评分配置
# ============================================================

SCORING = {
    # 各维度权重（总计100）- 三维度架构
    # 技术面: 短期择时，权重降低（黄金基本面驱动更强）
    # 基本面: 中期价值驱动，包含结构性因素（财政、去美元化、央行购金）
    # 情绪面: 短期情绪驱动，权重最高（黄金是典型的情绪驱动型避险资产）
    "weights": {
        "technical":   25,   # 25% - 技术面主要用于择时
        "fundamental":  35,   # 35% - 基本面包含Fed政策、美元、通胀、收益率曲线、结构性因素
        "sentiment":   40,   # 40% - 情绪面（VIX恐慌指数、新闻情绪、油价、金银比）对金价影响最大
    },
    # 综合评分信号阈值
    "thresholds": {
        "strong_buy": 75,
        "buy": 65,
        "lean_buy": 55,
        "neutral_upper": 45,  # 中性区间上界
        "lean_sell": 35,
        "sell": 25,
    },
    # 风控建议参数
    "risk_management": {
        "strong_buy": {
            "stop_loss": "建议设置5-8%止损",
            "take_profit": "目标收益15-25%，分批止盈",
            "max_drawdown": "可承受10%回撤",
        },
        "buy": {
            "stop_loss": "建议设置5-8%止损",
            "take_profit": "目标收益15-25%，分批止盈",
            "max_drawdown": "可承受10%回撤",
        },
        "lean_buy": {
            "stop_loss": "建议设置3-5%止损",
            "take_profit": "目标收益10-15%，及时止盈",
            "max_drawdown": "可承受5-8%回撤",
        },
        "neutral": {
            "stop_loss": "建议设置3-5%止损",
            "take_profit": "目标收益10-15%，及时止盈",
            "max_drawdown": "可承受5-8%回撤",
        },
        "lean_sell": {
            "stop_loss": "建议设置2-3%止损或立即止损",
            "take_profit": "若持仓，建议立即止盈",
            "max_drawdown": "建议降低至3%以下",
        },
        "sell": {
            "stop_loss": "建议设置2-3%止损或立即止损",
            "take_profit": "若持仓，建议立即止盈",
            "max_drawdown": "建议降低至3%以下",
        },
        "strong_sell": {
            "stop_loss": "建议设置2-3%止损或立即止损",
            "take_profit": "若持仓，建议立即止盈",
            "max_drawdown": "建议降低至3%以下",
        },
    },
    # 风险等级一致性阈值
    "risk_consistency_high": 75,
    "risk_consistency_mid": 50,
    "extreme_signal_low": 20,
    "extreme_signal_high": 80,
}

# ============================================================
# 宏观参数默认值（可被用户配置覆盖）
# ============================================================
# 以下参数会被 data_fetcher 自动更新，仅在获取失败时作为 fallback
# 更新时间: 2026-06-29

MACRO_PARAMS = {
    # 美联储政策
    "fed_rate_upper": 3.75,
    "fed_rate_lower": 3.75,
    "rate_hike_probability": 0.10,  # 当前市场预期维持利率
    "market_expects_hike": False,
    "fed_hawkish_bias": False,

    # 美元（DTWEXBGS刻度，约120）
    "dxy_current": 120.89,
    "dxy_3m_ago": 120.32,
    "dxy_1y_ago": 119.34,

    # 通胀（CPI年率，%）
    "cpi_index": 4.2,
    "core_cpi_index": 2.8,
    "cpi_yoy": 4.2,
    "core_cpi_yoy": 2.82,
    "pce_yoy": 2.8,
    "inflation_trend": "rising",  # FRED实际数据：CPI趋势上升

    # 债券收益率
    "us2y_yield": 4.10,
    "us10y_yield": 4.38,
    "us10y_real": 0.18,  # 4.38 - 4.2 = 0.18
    "yield_curve_2s10s": 0.28,  # 4.38 - 4.10 = 0.28

    # 财政
    "us_fiscal_deficit_gdp": 6.0,
    "us_debt_gdp": 125.0,

    # 央行购金（来源: 世界黄金协会2024报告）
    "cb_buying_pct_plan_increase": 45,
    "cb_buying_trend": "rising",

    # 地缘政治
    "geopolitical_risk_level": 0.6,
    "geopolitical_trend": "stable",

    # ETF资金流
    "etf_flow_trend": "outflow",
    "etf_holding_change_30d": -2.5,

    # 去美元化
    "dedollarization_momentum": 0.7,
}

# ============================================================
# 新闻因子配置
# ============================================================
# 默认空列表，通过 RSS/API 自动抓取实时新闻

NEWS_FACTORS = []  # 不再使用硬编码新闻，改为实时抓取

# ============================================================
# 新闻 RSS 源配置（供情绪分析模块自动抓取新闻）
# ============================================================

NEWS_SOURCES = [
    # 新浪财经-美股（保留，有部分有用内容如美联储分析）
    {"url": "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2518&k=&num=30&page=1", "name": "新浪财经-美股", "type": "sina_api"},
    # 新浪7x24实时快讯（市场动态）
    {"url": "https://finance.sina.com.cn/7x24/", "name": "新浪7x24快讯", "type": "html_parse", "selector": "a", "min_length": 20, "max_length": 100},
    # 新浪财经-美股（黄金关键词过滤）
    {"url": "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2518&k=%E9%BB%84%E9%87%91&num=20&page=1", "name": "新浪财经-黄金相关", "type": "sina_api"},
    # 新浪财经-美股（美联储/央行关键词过滤）
    {"url": "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2518&k=%E7%BE%8E%E8%81%94%E5%82%A8&num=20&page=1", "name": "新浪财经-美联储", "type": "sina_api"},
    # Reuters（国际备用）
    {"url": "https://www.reuters.com/markets/commodities/rss.xml", "name": "Reuters", "type": "rss"},
]

# ============================================================
# 报告配置
# ============================================================

REPORT = {
    "language": "zh",
    "currency": "USD",
    "show_chart": True,
    "save_html": True,
    "output_dir": "reports",
}

# ============================================================
# 回测配置
# ============================================================

BACKTEST = {
    "lookback": 60,          # 技术分析回看天数
    "horizon": 5,            # 预测未来收益率天数
    "default_days": 200,     # 模拟数据默认天数
}
