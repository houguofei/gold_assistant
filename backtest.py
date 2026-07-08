# -*- coding: utf-8 -*-
"""
黄金投资助手 - 回测框架
Gold Investment Assistant - Backtest Framework

在历史数据上验证评分体系的有效性

⚠️  当前限制说明:
    - 技术面回测: 完全有效，使用历史K线计算所有技术指标
    - 基本面回测: 使用默认静态参数（历史宏观数据需FRED付费API或本地数据库）
    - 情绪面回测: 简化处理（历史新闻/VIX数据需额外数据源）
    - 推荐: 先验证技术面信号有效性，再逐步接入历史宏观数据
"""

import json
import random
import math
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta

from hybrid_data_fetcher import HybridDataFetcher as GoldDataFetcher
from technical import TechnicalAnalyzer
from fundamental import FundamentalAnalyzer
from sentiment import SentimentAnalyzer
from scoring import ScoringEngine
from utils import log


class BacktestEngine:
    """
    回测引擎

    使用历史数据模拟每日分析，验证评分体系对后续收益率的预测能力。
    """

    def __init__(self, historical_data: Dict):
        """
        Args:
            historical_data: 包含 dates, opens, highs, lows, closes, volumes 的字典
        """
        self.dates = historical_data.get("dates", [])
        self.opens = historical_data.get("opens", [])
        self.highs = historical_data.get("highs", [])
        self.lows = historical_data.get("lows", [])
        self.closes = historical_data.get("closes", [])
        self.volumes = historical_data.get("volumes", [])
        self.n = len(self.closes)

    def _slice_data(self, end_idx: int, lookback: int = 120) -> Dict:
        """截取历史数据窗口"""
        start = max(0, end_idx - lookback)
        return {
            "dates": self.dates[start:end_idx],
            "opens": self.opens[start:end_idx],
            "highs": self.highs[start:end_idx],
            "lows": self.lows[start:end_idx],
            "closes": self.closes[start:end_idx],
            "volumes": self.volumes[start:end_idx] if self.volumes else [],
        }

    def _compute_future_return(self, idx: int, horizon: int = 5) -> float:
        """计算未来 N 日收益率"""
        if idx + horizon >= self.n:
            return 0.0
        current = self.closes[idx]
        future = self.closes[idx + horizon]
        return (future - current) / current * 100

    def run(self, lookback: int = 120, horizon: int = 5,
            start_idx: int = None, end_idx: int = None,
            technical_only: bool = True) -> List[Dict]:
        """
        执行回测

        Args:
            lookback: 技术分析回看天数
            horizon: 预测未来收益率天数
            start_idx: 回测起始索引（默认 lookback）
            end_idx: 回测结束索引（默认 n - horizon）
            technical_only: 是否仅回测技术面（推荐，结果更可靠）

        Returns:
            每日回测记录列表
        """
        start = start_idx or lookback
        end = end_idx or (self.n - horizon)

        results = []
        mode_str = "技术面-only" if technical_only else "全维度"
        log.info(f"开始回测 ({mode_str}): 共 {end - start} 个交易日")
        log.info(f"回看窗口: {lookback} 天 | 预测 horizon: {horizon} 天")
        if not technical_only:
            log.warning("基本面/情绪面使用静态参数，结果仅供参考")

        for i in range(start, end):
            if (i - start) % 50 == 0:
                log.info(f"  进度: {i - start}/{end - start}")

            window = self._slice_data(i, lookback)
            current_price = self.closes[i - 1]

            # 技术分析（完全基于历史K线，准确可靠）
            tech = TechnicalAnalyzer(
                closes=window["closes"],
                highs=window["highs"],
                lows=window["lows"],
                volumes=window["volumes"],
            )
            tech_score, tech_signal, tech_analysis = tech.compute_score()

            if technical_only:
                final_score = tech_score
                final_signal = tech_signal
                fund_score = 50.0
                sent_score = 50.0
            else:
                fund = FundamentalAnalyzer()
                fund_score, _, fund_analysis = fund.compute_score()

                sent = SentimentAnalyzer(
                    market_data={},
                    gold_data={"current": current_price},
                    news_factors=[],
                    skip_rss=True,
                )
                sent_score, _, sent_analysis = sent.compute_score()

                scorer = ScoringEngine()
                final = scorer.compute_final_score(
                    technical_score=tech_score,
                    fundamental_score=fund_score,
                    sentiment_score=sent_score,
                    fundamental_details=fund_analysis,
                )
                final_score = final["final_score"]
                final_signal = final["signal"]

            future_return = self._compute_future_return(i - 1, horizon)

            results.append({
                "date": str(self.dates[i - 1])[:10] if i > 0 else "",
                "price": current_price,
                "score": final_score,
                "signal": final_signal,
                "tech_score": tech_score,
                "fund_score": fund_score,
                "sent_score": sent_score,
                "future_return": future_return,
            })

        return results

    def analyze_results(self, results: List[Dict]) -> Dict:
        """分析回测结果，评估评分体系有效性"""
        if not results:
            return {}

        # 按评分分组统计
        score_buckets = {
            "strong_buy": [],   # 75-100
            "buy": [],          # 65-75
            "lean_buy": [],     # 55-65
            "neutral": [],      # 45-55
            "lean_sell": [],    # 35-45
            "sell": [],         # 25-35
            "strong_sell": [],  # 0-25
        }

        for r in results:
            score = r["score"]
            if score >= 75:
                score_buckets["strong_buy"].append(r["future_return"])
            elif score >= 65:
                score_buckets["buy"].append(r["future_return"])
            elif score >= 55:
                score_buckets["lean_buy"].append(r["future_return"])
            elif score >= 45:
                score_buckets["neutral"].append(r["future_return"])
            elif score >= 35:
                score_buckets["lean_sell"].append(r["future_return"])
            elif score >= 25:
                score_buckets["sell"].append(r["future_return"])
            else:
                score_buckets["strong_sell"].append(r["future_return"])

        # 计算各分组的平均未来收益率
        bucket_stats = {}
        for bucket, returns in score_buckets.items():
            if returns:
                bucket_stats[bucket] = {
                    "count": len(returns),
                    "avg_return": round(sum(returns) / len(returns), 2),
                    "win_rate": round(sum(1 for r in returns if r > 0) / len(returns) * 100, 1),
                    "max_return": round(max(returns), 2),
                    "min_return": round(min(returns), 2),
                }
            else:
                bucket_stats[bucket] = {"count": 0, "avg_return": 0, "win_rate": 0}

        # Pearson 相关系数
        scores = [r["score"] for r in results]
        returns = [r["future_return"] for r in results]

        def correlation(x, y):
            n = len(x)
            if n < 2:
                return 0
            mean_x = sum(x) / n
            mean_y = sum(y) / n
            num = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
            den_x = sum((xi - mean_x) ** 2 for xi in x) ** 0.5
            den_y = sum((yi - mean_y) ** 2 for yi in y) ** 0.5
            if den_x == 0 or den_y == 0:
                return 0
            return num / (den_x * den_y)

        corr = correlation(scores, returns)

        # 多空策略收益
        long_returns = [r["future_return"] for r in results if r["score"] >= 65]
        short_returns = [-r["future_return"] for r in results if r["score"] <= 35]
        long_short = long_returns + short_returns

        return {
            "total_days": len(results),
            "score_correlation": round(corr, 3),
            "bucket_stats": bucket_stats,
            "long_strategy": {
                "avg_return": round(sum(long_returns) / len(long_returns), 2) if long_returns else 0,
                "win_rate": round(sum(1 for r in long_returns if r > 0) / len(long_returns) * 100, 1) if long_returns else 0,
                "count": len(long_returns),
            },
            "short_strategy": {
                "avg_return": round(sum(short_returns) / len(short_returns), 2) if short_returns else 0,
                "win_rate": round(sum(1 for r in short_returns if r > 0) / len(short_returns) * 100, 1) if short_returns else 0,
                "count": len(short_returns),
            },
            "long_short_strategy": {
                "avg_return": round(sum(long_short) / len(long_short), 2) if long_short else 0,
                "win_rate": round(sum(1 for r in long_short if r > 0) / len(long_short) * 100, 1) if long_short else 0,
                "count": len(long_short),
            },
        }

    def print_report(self, results: List[Dict], stats: Dict):
        """打印回测报告"""
        log.info("=" * 60)
        log.info("回测报告")
        log.info("=" * 60)
        log.info(f"回测天数: {stats['total_days']}")
        log.info(f"评分-收益相关性: {stats['score_correlation']}")

        log.info("各评分区间表现:")
        log.info(f"  {'信号':<14s} {'次数':>6s} {'平均收益':>10s} {'胜率':>8s}")
        log.info("  " + "-" * 42)
        for bucket, s in stats["bucket_stats"].items():
            log.info(f"  {bucket:<14s} {s['count']:>6d} {s.get('avg_return', 0):>10.2f}% {s.get('win_rate', 0):>7.1f}%")

        log.info("策略表现:")
        for name, label in [("long_strategy", "看多策略(>=65)"),
                             ("short_strategy", "看空策略(<=35)"),
                             ("long_short_strategy", "多空策略")]:
            s = stats[name]
            log.info(f"  {label}: 平均收益 {s['avg_return']:+.2f}% | 胜率 {s['win_rate']:.1f}% | 次数 {s['count']}")

        log.info("=" * 60)


def _generate_simulated_history(days: int = 500, start_price: float = 1800) -> Dict:
    """生成模拟历史数据用于回测演示"""
    dates = []
    opens = []
    highs = []
    lows = []
    closes = []
    volumes = []

    price = start_price
    current_date = datetime.now() - timedelta(days=days)

    for i in range(days):
        while current_date.weekday() >= 5:
            current_date += timedelta(days=1)

        dates.append(current_date.strftime("%Y-%m-%d"))

        trend = 0.0002
        volatility = 0.012 * (1 + 0.5 * math.sin(i / 30))
        daily_return = random.gauss(trend, volatility)

        open_p = price
        close_p = price * (1 + daily_return)
        high_p = max(open_p, close_p) * (1 + abs(random.gauss(0, volatility * 0.5)))
        low_p = min(open_p, close_p) * (1 - abs(random.gauss(0, volatility * 0.5)))
        volume = random.randint(100000, 500000)

        opens.append(round(open_p, 2))
        highs.append(round(high_p, 2))
        lows.append(round(low_p, 2))
        closes.append(round(close_p, 2))
        volumes.append(volume)

        price = close_p
        current_date += timedelta(days=1)

    return {
        "dates": dates, "opens": opens, "highs": highs,
        "lows": lows, "closes": closes, "volumes": volumes,
    }


def run_backtest(technical_only: bool = True):
    """运行回测"""
    log.info("正在准备历史数据...")

    fetcher = GoldDataFetcher()
    data = None

    # 尝试获取真实数据
    try:
        data = fetcher.fetch_gold_data()
    except Exception:
        pass

    if not data or len(data.get("closes", [])) < 200:
        log.warning("无法获取足够真实历史数据，使用模拟数据演示回测逻辑")
        log.info("提示: 接入历史K线数据源（如Tushare/通达信）可获得真实回测结果")
        data = _generate_simulated_history(days=500, start_price=1800)

    log.info(f"使用 {len(data['closes'])} 个交易日数据")

    engine = BacktestEngine(data)
    results = engine.run(lookback=120, horizon=5, technical_only=technical_only)
    stats = engine.analyze_results(results)
    engine.print_report(results, stats)

    # 保存详细结果
    output = {
        "backtest_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "technical_only" if technical_only else "full_dimension",
        "data_note": "模拟数据演示" if len(data.get("closes", [])) == 500 else "真实历史数据",
        "summary": stats,
        "daily_results": results,
    }
    with open("backtest_result.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    log.info("详细结果已保存: backtest_result.json")


if __name__ == "__main__":
    run_backtest()
