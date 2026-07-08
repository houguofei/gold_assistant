# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║  黄金投资分析助手  |  Gold Investment Assistant              ║
║                                                              ║
║  综合技术面、基本面、情绪面三维度分析                          ║
║  输出评分 + 投资建议 + 风控方案                              ║
╚══════════════════════════════════════════════════════════════╝

使用方法:
    python gold_assistant.py              # 默认运行
    python gold_assistant.py --html       # 生成HTML报告
    python gold_assistant.py --quick      # 快速模式（仅关键指标）
    python gold_assistant.py --backtest   # 运行回测分析
"""

import sys
import os
import io
import json
from datetime import datetime
import traceback

# 设置stdout/stderr为UTF-8编码（解决Windows终端emoji显示问题）
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import log
from hybrid_data_fetcher import HybridDataFetcher as GoldDataFetcher
from technical import TechnicalAnalyzer
from fundamental import FundamentalAnalyzer
from sentiment import SentimentAnalyzer
from scoring import ScoringEngine
from report import ReportGenerator
from backtest import BacktestEngine
from config import BACKTEST

# 从配置文件读取默认参数和新闻因子（单一数据源）
from config import MACRO_PARAMS as DEFAULT_MACRO_PARAMS
from config import NEWS_FACTORS as DEFAULT_NEWS_FACTORS


# ============================================================
# 用户可配置的覆盖参数（可选）
# ============================================================
# 如需覆盖 config.py 中的默认值，取消注释并修改以下字典：

USER_MACRO_OVERRIDES = {
    # "us10y_real": 1.9,       # 10年期实际收益率
    # "rate_hike_probability": 0.90,  # 加息概率
}

USER_NEWS_OVERRIDES = [
    # {"text": "自定义新闻", "impact": +5, "category": "other"},
]


def run_analysis(generate_html: bool = False, quick_mode: bool = False):
    """执行完整分析流程"""

    # ============================================================
    # 第1步：获取市场数据与宏观数据（真实数据源）
    # ============================================================
    fetcher = GoldDataFetcher()
    all_data = fetcher.fetch_all_market_data()

    # 自动获取宏观数据并更新参数
    macro_data = fetcher.fetch_macro_data()

    # 显示宏观数据来源
    data_sources = macro_data.pop("_data_sources", {})
    default_used = [k for k, v in data_sources.items() if "默认" in v]
    if default_used:
        log.warning(f"以下宏观数据使用了默认值: {', '.join(default_used)}")

    gold_data = all_data.get("gold")
    if not gold_data:
        log.error("无法获取黄金数据，分析终止。所有数据源均失败。")
        return

    # 检查数据质量
    data_quality = gold_data.get("data_quality", "unknown")
    data_warning = gold_data.get("data_warning", "")
    if data_quality == "reference":
        log.warning("当前使用参考价格生成数据")
    elif data_quality == "simulated":
        log.warning("历史数据为模拟生成，仅当前价格真实。技术指标仅供参考。")
    elif data_quality == "based_on_real_price":
        log.info("数据基于真实当前价格")
    elif data_quality == "real":
        log.info("纯真实数据")

    if data_warning:
        log.warning(f"数据警告: {data_warning}")

    log.info(f"数据源: {gold_data.get('source', 'unknown')}")
    log.info(f"数据天数: {len(gold_data.get('closes', []))} 天")
    log.info(f"当前价格: ${gold_data['current']:,.2f}")

    # ============================================================
    # 第2步：技术分析
    # ============================================================
    log.info("=" * 60)
    log.info("执行技术分析...")

    tech = TechnicalAnalyzer(
        closes=gold_data["closes"],
        highs=gold_data["highs"],
        lows=gold_data["lows"],
        volumes=gold_data.get("volumes"),
    )
    tech_score, tech_signal, tech_analysis = tech.compute_score()
    log.info(f"技术面得分: {tech_score:.1f}/100 → {tech_signal}")

    if quick_mode:
        log.info(f"  RSI: {tech_analysis['rsi']['value']:.1f} ({tech_analysis['rsi']['detail']})")
        log.info(f"  趋势: {tech_analysis['trend']['overall_desc']}")
        log.info(f"  MACD: {tech_analysis['macd']['detail']}")

    # ============================================================
    # 第3步：基本面分析
    # ============================================================
    log.info("=" * 60)
    log.info("执行基本面分析...")

    # 合并默认参数、自动获取的宏观数据与用户覆盖参数
    macro_params = {**DEFAULT_MACRO_PARAMS, **macro_data, **USER_MACRO_OVERRIDES}
    news_factors = DEFAULT_NEWS_FACTORS + USER_NEWS_OVERRIDES

    fund_analyzer = FundamentalAnalyzer(params=macro_params)
    fund_score, fund_signal, fund_analysis = fund_analyzer.compute_score()
    log.info(f"基本面得分: {fund_score:.1f}/100 → {fund_signal}")

    # ============================================================
    # 第4步：情绪面分析
    # ============================================================
    log.info("=" * 60)
    log.info("执行情绪面分析...")

    # 转换市场数据格式（包含宏观数据）
    market_for_sentiment = {}
    for name, data in all_data.items():
        if data and name != "gold":
            market_for_sentiment[name] = {
                "price": data["current"],
                "change_pct": round(
                    (data["current"] - data["prev_close"]) / data["prev_close"] * 100
                    if data.get("prev_close") else 0, 2
                ),
            }
    
    # 添加宏观数据到市场数据（用于显示）
    if "dxy_index" in macro_data:
        market_for_sentiment["dxy"] = {
            "price": macro_data["dxy_index"],
            "change_pct": 0,
        }
    if "us10y_yield" in macro_data:
        market_for_sentiment["us10y"] = {
            "price": macro_data["us10y_yield"],
            "change_pct": 0,
        }

    sent_analyzer = SentimentAnalyzer(
        market_data=market_for_sentiment,
        gold_data=gold_data,
        news_factors=news_factors,
    )
    sent_score, sent_signal, sent_analysis = sent_analyzer.compute_score()
    log.info(f"情绪面得分: {sent_score:.1f}/100 → {sent_signal}")

    # ============================================================
    # 第5步：综合评分
    # ============================================================
    log.info("=" * 60)
    log.info("计算综合评分...")

    scorer = ScoringEngine()
    final_result = scorer.compute_final_score(
        technical_score=tech_score,
        fundamental_score=fund_score,
        sentiment_score=sent_score,
        fundamental_details=fund_analysis,
        technical_details=tech_analysis,
    )

    # ============================================================
    # 第6步：生成报告
    # ============================================================
    reporter = ReportGenerator()

    # 终端报告
    reporter.generate_full_report(
        gold_data=gold_data,
        market_data=market_for_sentiment,
        tech_analysis=tech_analysis,
        fund_analysis=fund_analysis,
        sent_analysis=sent_analysis,
        final_result=final_result,
    )

    # HTML报告
    if generate_html:
        html_data = {
            "gold_price": gold_data["current"],
            "gold_data": gold_data,
            "final": final_result,
            "technical": tech_analysis,
            "fundamental": fund_analysis,
            "sentiment": sent_analysis,
            "market": market_for_sentiment,
        }
        filepath = reporter.save_html_report(html_data)
        log.info(f"HTML报告已保存: {filepath}")

    return final_result


def run_backtest():
    """运行回测分析"""
    log.info("=" * 60)
    log.info("执行历史回测...")

    fetcher = GoldDataFetcher()

    # 尝试获取真实历史数据
    log.info("正在获取历史数据...")
    data = fetcher.fetch_gold_data()

    if not data or not data.get("closes") or data.get("is_reference", True):
        log.warning("无法获取真实历史数据，回测终止...")
        return

    log.info(f"使用 {len(data['closes'])} 个交易日真实数据")

    engine = BacktestEngine(data)
    results = engine.run(
        lookback=BACKTEST["lookback"],
        horizon=BACKTEST["horizon"],
    )
    stats = engine.analyze_results(results)
    engine.print_report(results, stats)

    # 保存详细结果
    import json
    from datetime import datetime
    output = {
        "backtest_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": stats,
        "daily_results": results[:50],
    }
    with open("backtest_result.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    log.info("详细结果已保存: backtest_result.json")


# ============================================================
# 主入口
# ============================================================
if __name__ == "__main__":
    args = sys.argv[1:]
    generate_html = "--html" in args
    quick_mode = "--quick" in args
    run_backtest_mode = "--backtest" in args

    try:
        if run_backtest_mode:
            run_backtest()
        else:
            result = run_analysis(generate_html=generate_html, quick_mode=quick_mode)
    except KeyboardInterrupt:
        log.info("分析已中断。")
    except Exception as e:
        log.error(f"分析出错: {e}")
        import traceback
        traceback.print_exc()
