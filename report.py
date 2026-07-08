# -*- coding: utf-8 -*-
"""
黄金投资助手 - 报告生成器（三维度架构增强版）
Gold Investment Assistant - Report Generator (Enhanced - 3-Dimension Architecture)

生成终端可视化报告和HTML报告，完整展示分析过程数据。
三维度：技术面、基本面、情绪面
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional
from config import SENTIMENT, FUNDAMENTAL, TECHNICAL


def _safe_print(*args, **kwargs):
    """安全打印，自动处理Windows GBK编码问题"""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # 移除emoji等非ASCII字符后重试
        args = tuple(
            a.encode("ascii", "ignore").decode("ascii") if isinstance(a, str) else a
            for a in args
        )
        print(*args, **kwargs)


class ReportGenerator:
    """报告生成引擎"""

    # ANSI颜色代码
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def _safe_print(self, text: str):
        """实例方法兼容，实际调用模块级安全打印"""
        _safe_print(text)

    def _color(self, text: str, color: str) -> str:
        return f"{color}{text}{self.RESET}"

    def _bold(self, text: str) -> str:
        return f"{self.BOLD}{text}{self.RESET}"

    def _dim(self, text: str) -> str:
        return f"{self.DIM}{text}{self.RESET}"

    def _score_color(self, score: float) -> str:
        if score >= 65:
            return self.GREEN
        elif score >= 55:
            return self.CYAN
        elif score >= 45:
            return self.YELLOW
        elif score >= 35:
            return self.YELLOW
        else:
            return self.RED

    def _bar(self, score: float, width: int = 30) -> str:
        """生成进度条"""
        filled = int(score / 100 * width)
        bar = "█" * filled + "░" * (width - filled)
        color = self._score_color(score)
        return f"{color}{bar}{self.RESET}"

    def _sub_score(self, score: float) -> str:
        """子维度得分的颜色标记"""
        color = self._score_color(score)
        return f"{color}{score:+.0f}{self.RESET}"

    # ================================================================
    # 终端报告方法
    # ================================================================

    def print_header(self, gold_price: float, prev_close: float, instrument: str = "unknown"):
        """打印报告头部

        Args:
            instrument: 数据品种标记 — "spot"（现货）、"futures"（期货）、"manual"、"reference" 等
                        标签会据此诚实显示，避免把期货价标成"现货"
        """
        change = gold_price - prev_close
        change_pct = change / prev_close * 100 if prev_close else 0
        chg_color = self.GREEN if change >= 0 else self.RED
        chg_sign = "+" if change >= 0 else ""

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 根据 instrument 选择诚实的标签
        label_map = {
            "spot":      "黄金现货价格 (XAU/USD)",
            "futures":   "黄金期货价格 (COMEX GC)",
            "manual":    "黄金价格 (手动输入)",
            "reference": "黄金参考价格",
        }
        price_label = label_map.get(instrument, "黄金价格")

        self._safe_print("")
        self._safe_print(self._color("=" * 70, self.CYAN))
        self._safe_print(self._color("  ⚜️  黄金投资分析助手  |  Gold Investment Assistant", self.BOLD))
        self._safe_print(self._color(f"  📅 {now}", self.DIM))
        self._safe_print(self._color("=" * 70, self.CYAN))
        self._safe_print("")
        self._safe_print(f"  💰 {price_label}:  {self._bold(f'${gold_price:,.2f}')}/盎司")
        self._safe_print(f"  📊 日内变化:      {chg_color}{chg_sign}{change:.2f} ({chg_sign}{change_pct:.2f}%){self.RESET}")
        self._safe_print("")

    def print_market_snapshot(self, market_data: Dict):
        """打印市场快照"""
        _safe_print(self._color("─" * 70, self.DIM))
        _safe_print(self._bold("  📊 关联市场数据"))
        _safe_print(self._color("─" * 70, self.DIM))

        items = [
            ("美元指数 (DXY)", "dxy", "${price:.2f}"),
            ("10年期美债收益率", "us10y", "{price:.2f}%"),
            ("白银", "silver", "${price:.2f}"),
            ("WTI原油", "oil", "${price:.2f}"),
            ("VIX恐慌指数", "vix", "{price:.1f}"),
            ("S&P 500", "sp500", "${price:,.0f}"),
        ]

        for label, key, fmt in items:
            data = market_data.get(key)
            if data and data.get("price", 0) > 0:
                price = data.get("price", 0)
                chg = data.get("change_pct", 0)
                chg_color = self.GREEN if chg >= 0 else self.RED
                chg_sign = "+" if chg >= 0 else ""
                price_str = fmt.format(price=price)
                _safe_print(f"  {label:24s}  {price_str:>12s}  "
                      f"{chg_color}{chg_sign}{chg:.2f}%{self.RESET}")
            else:
                _safe_print(f"  {label:24s}  {'N/A':>12s}")

        _safe_print("")

    def print_tech_analysis(self, score: float, analysis: Dict):
        """打印技术面分析（含评分公式和计算过程）"""
        print(self._color("─" * 70, self.DIM))
        print(f"  📈 {self._bold('技术面分析')}")

        # 市场状态
        regime = analysis.get("market_regime", None)
        if regime:
            regime_color = self.GREEN if regime["regime"] == "bull" else \
                          self.RED if regime["regime"] == "bear" else self.YELLOW
            print(f"  市场状态: {regime_color}{regime['name']}{self.RESET} (置信度{regime['confidence']}%)")

        print(f"  评分维度: RSI(20%) + MACD(15%) + 布林带(10%) + 均线趋势(20%) + 背离(15%) + 动量(10%) + 量能(10%)")
        print()

        # RSI
        rsi = analysis.get("rsi", {})
        if rsi:
            rsi_val = rsi.get("value", 50)
            rsi_color = self.RED if rsi_val > 70 else self.GREEN if rsi_val < 30 else self.YELLOW
            print(f"    RSI(14): {rsi_color}{rsi_val:.1f}{self.RESET} → {rsi.get('detail', 'N/A')}")

        # MACD
        macd = analysis.get("macd", {})
        if macd:
            print(f"    MACD: {macd.get('macd', 0):.2f} / {macd.get('signal', 0):.2f} → {macd.get('detail', 'N/A')}")

        # 布林带
        boll = analysis.get("bollinger", {})
        if boll:
            pos = boll.get("position", 0.5)
            print(f"    布林带位置: {pos:.1%} → {boll.get('position_desc', 'N/A')}")

        # 均线趋势
        trend = analysis.get("trend", {})
        if trend:
            momentum = trend.get("momentum_5d", 0)
            mom_color = self.GREEN if momentum >= 0 else self.RED
            print(f"    趋势: {trend.get('overall_desc', 'N/A')} (5日动量: {mom_color}{momentum:+.1f}%{self.RESET})")

        # 金叉/死叉信号
        cross = analysis.get("ma_crossover", {})
        if cross and cross.get("signal") != "none":
            cross_color = self.GREEN if cross.get("signal") == "golden_cross" else self.RED
            print(f"    {cross_color}交叉信号: {cross.get('detail', '')}{self.RESET}")

        # 背离信号
        div = analysis.get("divergence", {})
        if div:
            if div.get("signal") == "bullish":
                div_color = self.GREEN
            elif div.get("signal") == "bearish":
                div_color = self.RED
            else:
                div_color = ""
            print(f"    {div_color}背离检测: {div.get('detail', '')}{self.RESET}")

        # 成交量
        vol = analysis.get("volume", {})
        if vol and vol.get("detail") != "无成交量数据":
            vol_color = self.GREEN if "bullish" in vol.get("trend", "") else self.RED if "bearish" in vol.get("trend", "") else ""
            print(f"    {vol_color}成交量: {vol.get('detail', '')}{self.RESET}")

        # OBV
        obv = analysis.get("obv", {})
        if obv:
            obv_color = self.GREEN if obv.get("trend") == "bullish" else self.RED if obv.get("trend") == "bearish" else ""
            print(f"    {obv_color}OBV能量潮: {obv.get('detail', '')}{self.RESET}")

        # 最终得分
        print()
        print(f"    {'─' * 50}")
        print(f"    最终得分: {self._score_color(score)}{self._bold(f'{score:.1f}/100')} "
              f"{self._bar(score)}")

        # 支撑/阻力（附加信息）
        sr = analysis.get("support_resistance", {})
        if sr:
            supports = sr.get("support", [])
            resistances = sr.get("resistance", [])
            if supports or resistances:
                print()
                if supports:
                    print(f"    支撑位: {', '.join(f'${s:,.0f}' for s in supports[:3])}")
                if resistances:
                    print(f"    阻力位: {', '.join(f'${r:,.0f}' for r in resistances[:3])}")

        print()

    def print_fund_analysis(self, score: float, analysis: Dict):
        """打印基本面分析（含评分公式和计算过程）"""
        weights = FUNDAMENTAL["dim_weights"]
        scale = FUNDAMENTAL["score_scale"]

        print(self._color("─" * 70, self.DIM))
        print(f"  🏦 {self._bold('基本面分析')}")
        print(f"  评分维度: Fed政策({weights['fed_policy']:.0%}) + 美元({weights['usd_impact']:.0%}) + "
              f"通胀({weights['inflation']:.0%}) + 收益率曲线({weights['yield_curve']:.0%}) + "
              f"结构性({weights['structural']:.0%})")
        print()

        # 各子维度得分（key对应fundamental.py返回的键名）
        dim_labels = [
            ("fed", "Fed政策", "🏛️", weights["fed_policy"]),
            ("usd", "美元", "💵", weights["usd_impact"]),
            ("inflation", "通胀", "📈", weights["inflation"]),
            ("yield_curve", "收益率曲线", "📊", weights["yield_curve"]),
            ("structural", "结构性", "🏗️", weights["structural"]),
        ]

        weighted_sum = 0
        for key, label, icon, weight in dim_labels:
            section = analysis.get(key, {})
            if not section:
                continue
            sub_score = section.get("score", 0)
            sub_signal = section.get("signal", "N/A")
            factors = section.get("factors", [])
            weighted = sub_score * weight
            weighted_sum += weighted

            print(f"    {icon} {label}: 得分{sub_score:+.0f} × 权重{weight:.0%} = {weighted:+.1f} → {sub_signal}")
            
            # 如果是结构性分析，显示详细计算过程
            if key == "structural":
                score_details = section.get("score_details", [])
                if score_details:
                    print(f"       计算明细:")
                    for factor_name, value, condition, change in score_details:
                        change_color = self.GREEN if change.startswith("+") else self.RED
                        print(f"         • {factor_name}: {value} ({condition}) → {change_color}{change}{self.RESET}")
                    print(f"         ───────────────────")
                    print(f"         小计: {sub_score:+.0f}")
            
            for f in factors:
                print(f"       • {f}")

        # 计算汇总
        final_calc = 50 + weighted_sum * scale
        print()
        print(f"    {'─' * 50}")
        print(f"    加权和: {weighted_sum:+.1f}")
        print(f"    计算: 50 + {weighted_sum:+.1f} × {scale} = 50 + {weighted_sum * scale:+.1f} = {final_calc:.1f}")
        print(f"    最终得分: {self._score_color(score)}{self._bold(f'{score:.1f}/100')} "
              f"{self._bar(score)}")
        print()

    def print_sent_analysis(self, score: float, analysis: Dict):
        """打印情绪面分析（含评分公式和计算过程）"""
        print(self._color("─" * 70, self.DIM))
        print(f"  💭 {self._bold('情绪面分析')}")
        sent_scale = SENTIMENT["score_scale"]
        print(f"  计算公式: score = 50 + (VIX×{SENTIMENT['dim_weights']['vix']:.1f} + Oil×{SENTIMENT['dim_weights']['oil']:.1f} + 金银比×{SENTIMENT['dim_weights']['gold_silver_ratio']:.1f} + 新闻×{SENTIMENT['dim_weights']['news']:.1f}) × {sent_scale}")
        print()

        # 各子维度
        dim_labels = {
            "vix": ("VIX恐慌指数", "😱", 1.5),
            "oil": ("原油价格", "🛢️", 1.0),
            "gold_silver_ratio": ("金银比", "⚖️", 1.0),
            "news": ("新闻情绪", "📰", 1.5),
        }

        weighted_sum = 0
        for key, (label, icon, weight) in dim_labels.items():
            section = analysis.get(key, {})
            if not section:
                continue
            sub_score = section.get("score", 0)
            sub_signal = section.get("signal", "N/A")
            factors = section.get("factors", [])
            if not factors:
                factors = [section.get("detail", "")]
            weighted = sub_score * weight
            weighted_sum += weighted

            print(f"    {icon} {label}: 得分{sub_score:+.0f} × 权重{weight:.1f} = {weighted:+.1f} → {sub_signal}")
            for f in factors:
                if f:
                    print(f"       • {f}")

        # 计算汇总
        scale = SENTIMENT["score_scale"]
        final_calc = 50 + weighted_sum * scale
        print()
        print(f"    {'─' * 50}")
        print(f"    加权和: {weighted_sum:+.1f}")
        print(f"    计算: 50 + {weighted_sum:+.1f} × {scale} = 50 + {weighted_sum * scale:+.1f} = {final_calc:.1f}")
        print(f"    最终得分: {self._score_color(score)}{self._bold(f'{score:.1f}/100')} "
              f"{self._bar(score)}")
        print()

    def print_final_result(self, result: Dict):
        """打印最终结果（含综合评分公式）"""
        score = result["final_score"]
        signal = result["signal"]
        rec = result["recommendation"]
        regime = result.get("market_regime", None)

        print(self._color("=" * 70, self.CYAN))
        print(self._bold("  🎯 综合分析结论"))
        print(self._color("=" * 70, self.CYAN))
        print()

        # 市场状态
        if regime:
            regime_color = self.GREEN if regime["regime"] == "bull" else \
                          self.RED if regime["regime"] == "bear" else self.YELLOW
            print(f"  {self._bold('市场状态:')} {regime_color}{regime['name']}{self.RESET}")
            print(f"    置信度: {regime['confidence']}% | 60日涨跌: {regime['period_return_pct']:+.2f}%")
            print(f"    {regime['description']}")
            print()

        # 综合评分公式（三维度架构）
        weights = result.get("weights_used", result["weights"])
        print(f"  {self._bold('综合评分权重:')}")
        weight_str = " + ".join([f"{k[:4]}×{v}%" for k, v in weights.items()])
        print(f"    final = {weight_str}")
        print()

        # 各维度得分（三维度）
        dims = result["dimension_scores"]

        dim_labels = [
            ("技术面", "technical", "📈"),
            ("基本面", "fundamental", "🏦"),
            ("情绪面", "sentiment", "💭"),
        ]

        contributions = []
        for label, key, icon in dim_labels:
            s = dims.get(key, 50)
            w = weights.get(key, 25)
            weighted = s * w / 100
            contributions.append(weighted)
            sc = self._score_color(s)
            print(f"    {icon} {label:6s}: {sc}{s:.1f}{self.RESET} × {w}% = {weighted:+.1f} "
                  f"{self._bar(s, 20)}")

        total_contrib = sum(contributions)
        print()
        print(f"    {'─' * 50}")
        print(f"    计算: {' + '.join(f'{c:+.1f}' for c in contributions)} = {total_contrib:.1f}")
        print()
        score_color = self._score_color(score)
        print(f"    最终得分: {score_color}{self._bold(f'{score:.1f}/100')} "
              f"{self._bar(score, 40)}")
        print(f"    综合信号: {signal}")
        print()

        # 投资建议
        print(self._color("─" * 70, self.DIM))
        print(self._bold("  💡 投资建议"))
        print(self._color("─" * 70, self.DIM))
        print()
        print(f"  操作建议:  {self._bold(rec['position'])}")
        print(f"  仓位建议:  {rec['allocation']}")
        print(f"  策略描述:  {rec['strategy']}")
        entry_timing = rec.get("entry_timing", "")
        if entry_timing:
            print(f"  入场时机:  {self.CYAN}{entry_timing}{self.RESET}")
        print()

        # 风控
        rm = rec.get("risk_management", {})
        if rm:
            print(f"  {self._bold('风控建议:')}")
            print(f"    止损: {rm.get('stop_loss', 'N/A')}")
            print(f"    止盈: {rm.get('take_profit', 'N/A')}")
            print(f"    回撤容忍: {rm.get('max_drawdown_tolerance', 'N/A')}")
            print()

        # 关注点
        watch = rec.get("watch_list", [])
        if watch:
            print(f"  {self._bold('关键关注点:')}")
            for w in watch:
                print(f"    ⚠️  {w}")
            print()

        # 风险等级
        risk = result.get("risk_level", {})
        if risk:
            risk_color = self.GREEN if risk.get("level") == "低" else \
                         self.YELLOW if risk.get("level") == "中" else self.RED
            print(f"  {self._bold('风险等级:')} {risk_color}{risk.get('level', '中')}{self.RESET}"
                  f" — {risk.get('description', '')}")
            print(f"  {self._bold('一致性:')} {risk.get('consistency', 0):.1f}%")

        print()
        print(self._color("=" * 70, self.CYAN))
        print(self._dim("  ⚠️  以上分析仅供参考，不构成投资建议。"))
        print(self._dim("  ⚠️  黄金市场波动剧烈，请根据自身风险承受能力谨慎决策。"))
        print(self._color("=" * 70, self.CYAN))
        print()

    def generate_full_report(self, gold_data: Dict, market_data: Dict,
                              tech_analysis: Dict, fund_analysis: Dict,
                              sent_analysis: Dict, final_result: Dict):
        """生成完整终端报告"""
        current = gold_data.get("current", 0)
        prev = gold_data.get("prev_close", 0)
        instrument = gold_data.get("instrument", "unknown")

        self.print_header(current, prev, instrument)
        self.print_market_snapshot(market_data)

        # 技术面
        tech_score = final_result["dimension_scores"]["technical"]
        self.print_tech_analysis(tech_score, tech_analysis)

        # 基本面
        fund_score = final_result["dimension_scores"]["fundamental"]
        self.print_fund_analysis(fund_score, fund_analysis)

        # 情绪面
        sent_score = final_result["dimension_scores"]["sentiment"]
        self.print_sent_analysis(sent_score, sent_analysis)

        # 最终结果
        self.print_final_result(final_result)

    # ================================================================
    # HTML 报告方法
    # ================================================================

    def save_html_report(self, report_data: Dict, filename: str = None):
        """保存HTML格式报告"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gold_report_{timestamp}.html"

        filepath = os.path.join(self.output_dir, filename)
        html = self._build_html(report_data)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"  📄 HTML报告已保存: {filepath}")
        return filepath

    def _build_plotly_charts(self, data: Dict) -> str:
        """生成 Plotly 图表 JSON 配置"""
        gold_data = data.get("gold_data", {})
        closes = gold_data.get("closes", [])
        highs = gold_data.get("highs", [])
        lows = gold_data.get("lows", [])
        dates = gold_data.get("dates", [])

        if not closes or len(closes) < 20:
            return ""

        # 生成日期字符串列表
        date_strs = []
        for d in dates:
            if isinstance(d, datetime):
                date_strs.append(d.strftime("%Y-%m-%d"))
            else:
                date_strs.append(str(d)[:10])

        # 计算均线
        def sma(values, period):
            result = [None] * len(values)
            for i in range(period - 1, len(values)):
                result[i] = sum(values[i - period + 1:i + 1]) / period
            return result

        ma20 = sma(closes, 20)
        ma50 = sma(closes, 50)

        # 计算 RSI
        def calc_rsi(values, period=14):
            if len(values) < period + 1:
                return [50] * len(values)
            changes = [values[i] - values[i - 1] for i in range(1, len(values))]
            gains = [max(c, 0) for c in changes]
            losses = [abs(min(c, 0)) for c in changes]
            avg_gain = sum(gains[:period]) / period
            avg_loss = sum(losses[:period]) / period
            rsi = [None] * len(values)
            for i in range(period, len(changes)):
                avg_gain = (avg_gain * (period - 1) + gains[i]) / period
                avg_loss = (avg_loss * (period - 1) + losses[i]) / period
                if avg_loss == 0:
                    rsi[i + 1] = 100
                else:
                    rs = avg_gain / avg_loss
                    rsi[i + 1] = 100 - (100 / (1 + rs))
            return rsi

        rsi = calc_rsi(closes)

        chart_data = {
            "price": {
                "x": date_strs,
                "close": closes,
                "high": highs,
                "low": lows,
                "ma20": ma20,
                "ma50": ma50,
            },
            "rsi": {
                "x": date_strs,
                "value": rsi,
            }
        }
        return json.dumps(chart_data)

    def _build_html(self, data: Dict) -> str:
        """构建HTML报告（含完整分析过程数据）"""
        final = data.get("final", {})
        score = final.get("final_score", 50)
        dims = final.get("dimension_scores", {})
        weights = final.get("weights", {})
        rec = final.get("recommendation", {})
        risk = final.get("risk_level", {})

        gold_data = data.get("gold_data", {})
        instrument = gold_data.get("instrument", "unknown")
        instrument_labels = {
            "spot": "黄金现货 (XAU/USD)",
            "futures": "COMEX 黄金期货 (GC)",
            "manual": "手动输入价格",
            "reference": "参考价格",
        }
        instrument_label = instrument_labels.get(instrument, f"黄金 ({instrument})")

        # 子维度数据
        tech_analysis = data.get("technical", {})
        fund_analysis = data.get("fundamental", {})
        sent_analysis = data.get("sentiment", {})
        market_data = data.get("market", {})
        gold_data = data.get("gold_data", {})

        # 颜色映射
        def score_bg(s):
            if s >= 65: return "#2ecc71"
            elif s >= 55: return "#3498db"
            elif s >= 45: return "#f39c12"
            elif s >= 35: return "#e67e22"
            else: return "#e74c3c"

        def score_text(s):
            if s >= 65: return "利多"
            elif s >= 55: return "偏多"
            elif s >= 45: return "中性"
            elif s >= 35: return "偏空"
            else: return "利空"

        # 生成图表数据
        chart_json = self._build_plotly_charts(data)

        # === 技术面子维度 HTML（展示分析结果）===
        trend = tech_analysis.get("trend", {})
        rsi_data = tech_analysis.get("rsi", {})
        macd_data = tech_analysis.get("macd", {})
        boll_data = tech_analysis.get("bollinger", {})
        cross_data = tech_analysis.get("ma_crossover", {})
        div_data = tech_analysis.get("divergence", {})
        vol_data = tech_analysis.get("volume", {})
        obv_data = tech_analysis.get("obv", {})
        atr_data = tech_analysis.get("atr", {})
        sr_data = tech_analysis.get("support_resistance", {})
        tech_score = dims.get("technical", 50)

        tech_rows = []

        # 市场状态
        regime_data = tech_analysis.get("market_regime", None)
        if regime_data:
            regime_color = "#2ecc71" if regime_data["regime"] == "bull" else "#e74c3c" if regime_data["regime"] == "bear" else "#f39c12"
            tech_rows.append(f"""
            <tr><td><strong>市场状态</strong></td>
            <td style="color:{regime_color};font-weight:bold">{regime_data['name']}</td>
            <td>置信度{regime_data['confidence']}% | 60日{regime_data['period_return_pct']:+.2f}%</td></tr>""")

        if rsi_data:
            tech_rows.append(f"""
            <tr><td>RSI({TECHNICAL['rsi_period']})</td><td>{rsi_data.get('value', 50):.1f}</td>
            <td>{rsi_data.get('detail', 'N/A')}</td></tr>""")
        if macd_data:
            tech_rows.append(f"""
            <tr><td>MACD</td><td>{macd_data.get('macd', 0):.2f}/{macd_data.get('signal', 0):.2f}</td>
            <td>{macd_data.get('detail', 'N/A')}</td></tr>""")
        if boll_data:
            tech_rows.append(f"""
            <tr><td>布林带</td><td>位置 {boll_data.get('position', 0):.1%}</td>
            <td>{boll_data.get('position_desc', 'N/A')}</td></tr>""")
        if trend:
            cross_signal = ""
            if cross_data and cross_data.get("signal") != "none":
                cross_signal = f" | {cross_data.get('detail', '')}"
            tech_rows.append(f"""
            <tr><td>均线趋势</td><td>{trend.get('overall_desc', 'N/A')}</td>
            <td>5日动量 {trend.get('momentum_5d', 0):+.1f}%{cross_signal}</td></tr>""")
        if div_data:
            div_signal = div_data.get("detail", "N/A")
            div_color = "#2ecc71" if div_data.get("signal") == "bullish" else "#e74c3c" if div_data.get("signal") == "bearish" else ""
            tech_rows.append(f"""
            <tr><td>背离检测</td><td style="color:{div_color}">{div_data.get('signal', 'none')}</td>
            <td>{div_signal}</td></tr>""")
        if vol_data and vol_data.get("detail") != "无成交量数据":
            vol_color = "#2ecc71" if "bullish" in vol_data.get("trend", "") else "#e74c3c" if "bearish" in vol_data.get("trend", "") else ""
            tech_rows.append(f"""
            <tr><td>成交量</td><td style="color:{vol_color}">{vol_data.get('trend', '')}</td>
            <td>{vol_data.get('detail', '')}</td></tr>""")
        if obv_data:
            obv_color = "#2ecc71" if obv_data.get("trend") == "bullish" else "#e74c3c" if obv_data.get("trend") == "bearish" else ""
            tech_rows.append(f"""
            <tr><td>OBV能量潮</td><td style="color:{obv_color}">{obv_data.get('trend', '')}</td>
            <td>{obv_data.get('detail', '')}</td></tr>""")
        if atr_data:
            tech_rows.append(f"""
            <tr><td>ATR波动率</td><td>{atr_data.get('percentage', 0):.2%}</td>
            <td>{atr_data.get('volatility', 'N/A')}</td></tr>""")
        if sr_data:
            supports = sr_data.get("support", [])
            resistances = sr_data.get("resistance", [])
            if supports:
                tech_rows.append(f"""
                <tr><td>支撑位</td><td colspan="2">{', '.join(f'${s:,.0f}' for s in supports[:3])}</td></tr>""")
            if resistances:
                tech_rows.append(f"""
                <tr><td>阻力位</td><td colspan="2">{', '.join(f'${r:,.0f}' for r in resistances[:3])}</td></tr>""")

        # 技术面评分维度说明 HTML
        tech_formula_html = f"""
        <div class="formula-box">
          <div class="formula-title">评分维度</div>
          <div class="formula">RSI(20%) + MACD(15%) + 布林带(10%) + 均线趋势(20%) + 背离(15%) + 动量(10%) + 量能(10%)</div>
          <div class="formula-detail">
            技术面综合得分: <strong>{tech_score:.1f}/100</strong>
          </div>
        </div>"""

        # === 基本面子维度 HTML（含计算过程）===
        fund_weights = FUNDAMENTAL["dim_weights"]
        fund_scale = FUNDAMENTAL["score_scale"]
        fund_rows = []
        # key映射：analysis key -> (显示名称, config weight key)
        fund_labels = [
            ("fed", "Fed政策", "fed_policy"),
            ("usd", "美元", "usd_impact"),
            ("inflation", "通胀", "inflation"),
            ("yield_curve", "收益率曲线", "yield_curve"),
            ("structural", "结构性", "structural"),
        ]
        fund_weighted_sum = 0
        fund_score = dims.get("fundamental", 50)
        for key, label, weight_key in fund_labels:
            section = fund_analysis.get(key, {})
            weight = fund_weights[weight_key]
            if section:
                sub_score = section.get("score", 0)
                sub_signal = section.get("signal", "N/A")
                factors = section.get("factors", [])
                weighted = sub_score * weight
                fund_weighted_sum += weighted

                # 结构性分析添加详细计算过程
                detail_html = ""
                if key == "structural":
                    score_details = section.get("score_details", [])
                    if score_details:
                        detail_rows = []
                        for factor_name, value, condition, change in score_details:
                            change_color = "#2ecc71" if change.startswith("+") else "#e74c3c"
                            detail_rows.append(f"""
                                <tr style="font-size:12px;">
                                    <td style="padding-left:20px;">{factor_name}</td>
                                    <td>{value}</td>
                                    <td style="color:#7f8c8d;">{condition}</td>
                                    <td style="color:{change_color};font-weight:bold;">{change}</td>
                                </tr>""")
                        detail_html = f"""
                            <tr>
                                <td colspan="6">
                                    <div style="margin-top:8px;padding:8px;background:#1a1a2e;border-radius:6px;">
                                        <strong style="color:#3498db;">计算明细:</strong>
                                        <table style="width:100%;margin-top:5px;">
                                            <tr style="font-size:12px;font-weight:bold;color:#7f8c8d;">
                                                <td>因素</td><td>数值</td><td>条件</td><td>得分变化</td>
                                            </tr>
                                            {"".join(detail_rows)}
                                            <tr style="font-size:12px;border-top:1px solid #333;font-weight:bold;">
                                                <td colspan="3">小计</td>
                                                <td style="color:#e94560;">{sub_score:+.0f}</td>
                                            </tr>
                                        </table>
                                    </div>
                                </td>
                            </tr>"""

                fund_rows.append(f"""
                <tr>
                    <td>{label}</td>
                    <td style="color:{score_bg(50 + sub_score * 0.6)}">{sub_score:+.0f}</td>
                    <td>{weight:.0%}</td>
                    <td class="sub-score" style="color:{score_bg(50 + weighted * 0.6)}">{weighted:+.1f}</td>
                    <td>{sub_signal}</td>
                    <td class="factor-text">{'; '.join(factors[:2])}</td>
                </tr>""")
                if detail_html:
                    fund_rows.append(detail_html)
        # 添加汇总行
        fund_calc = fund_weighted_sum * fund_scale
        fund_rows.append(f"""
            <tr style="border-top:2px solid #e94560;font-weight:bold;">
                <td colspan="3">汇总</td>
                <td>{fund_weighted_sum:+.1f}</td>
                <td colspan="2">50 + {fund_weighted_sum:+.1f} × {fund_scale} = {fund_score:.1f}</td>
            </tr>""")

        # === 情绪面子维度 HTML（含计算过程）===
        sent_rows = []
        sent_weights = SENTIMENT["dim_weights"]
        sent_weighted_sum = 0
        sent_labels = {
            "vix": ("VIX恐慌", sent_weights["vix"]),
            "oil": ("原油", sent_weights["oil"]),
            "gold_silver_ratio": ("金银比", sent_weights["gold_silver_ratio"]),
            "news": ("新闻", sent_weights["news"])
        }
        for key, (label, weight) in sent_labels.items():
            section = sent_analysis.get(key, {})
            if section:
                sub_score = section.get("score", 0)
                sub_signal = section.get("signal", "N/A")
                factors = section.get("factors", [])
                if not factors:
                    factors = [section.get("detail", "")]
                weighted = sub_score * weight
                sent_weighted_sum += weighted
                sent_rows.append(f"""
                <tr>
                    <td>{label}</td>
                    <td style="color:{score_bg(50 + sub_score)}">{sub_score:+.0f}</td>
                    <td>{weight:.0%}</td>
                    <td class="sub-score" style="color:{score_bg(50 + weighted)}">{weighted:+.1f}</td>
                    <td>{sub_signal}</td>
                    <td class="factor-text">{'; '.join(factors[:2])}</td>
                </tr>""")
        # 添加汇总行
        sent_scale = SENTIMENT["score_scale"]
        sent_final = 50 + sent_weighted_sum * sent_scale
        sent_rows.append(f"""
            <tr style="border-top:2px solid #e94560;font-weight:bold;">
                <td colspan="3">汇总</td>
                <td>{sent_weighted_sum:+.1f}</td>
                <td colspan="2">50 + {sent_weighted_sum:+.1f} × {sent_scale} = {sent_final:.1f}</td>
            </tr>""")

        # === 关联市场 HTML ===
        market_rows = []
        market_items = [
            ("美元指数", "dxy", "${price:.2f}"),
            ("10年期美债", "us10y", "{price:.2f}%"),
            ("白银", "silver", "${price:.2f}"),
            ("WTI原油", "oil", "${price:.2f}"),
            ("VIX恐慌指数", "vix", "{price:.1f}"),
            ("S&P 500", "sp500", "${price:,.0f}"),
        ]
        for label, key, fmt in market_items:
            mdata = market_data.get(key, {})
            if mdata and mdata.get("price", 0) > 0:
                price = mdata["price"]
                chg = mdata.get("change_pct", 0)
                chg_color = "#2ecc71" if chg >= 0 else "#e74c3c"
                market_rows.append(f"""
                <tr>
                    <td>{label}</td>
                    <td>{fmt.format(price=price)}</td>
                    <td style="color:{chg_color}">{chg:+.2f}%</td>
                </tr>""")

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>黄金投资分析报告</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
body {{ font-family: -apple-system, 'Segoe UI', sans-serif; background: #1a1a2e; color: #eee; margin: 0; padding: 20px; }}
.container {{ max-width: 1100px; margin: 0 auto; }}
.header {{ background: linear-gradient(135deg, #16213e, #0f3460); padding: 30px; border-radius: 12px; margin-bottom: 20px; }}
.header h1 {{ margin: 0; color: #e94560; font-size: 28px; }}
.header .subtitle {{ color: #aaa; margin-top: 5px; }}
.price {{ font-size: 48px; font-weight: bold; color: #e94560; margin: 15px 0; }}
.card {{ background: #16213e; border-radius: 10px; padding: 20px; margin-bottom: 15px; }}
.card h2 {{ color: #e94560; margin-top: 0; font-size: 18px; }}
.score-bar {{ height: 30px; background: #333; border-radius: 15px; overflow: hidden; margin: 10px 0; }}
.score-fill {{ height: 100%; border-radius: 15px; display: flex; align-items: center; padding-left: 15px; font-weight: bold; transition: width 0.5s; }}
.dim-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
.dim-item {{ background: #1a1a2e; padding: 15px; border-radius: 8px; text-align: center; }}
.dim-item .label {{ color: #aaa; font-size: 12px; }}
.dim-item .value {{ font-size: 24px; font-weight: bold; margin: 5px 0; }}
.dim-item .weight {{ color: #666; font-size: 11px; }}
.rec-box {{ background: #0f3460; border: 2px solid #e94560; border-radius: 10px; padding: 20px; }}
.rec-title {{ color: #e94560; font-size: 20px; font-weight: bold; margin-bottom: 15px; }}
.factor {{ padding: 5px 0; border-bottom: 1px solid #333; font-size: 14px; }}
.chart-container {{ width: 100%; height: 450px; margin: 15px 0; }}
.disclaimer {{ text-align: center; color: #666; font-size: 12px; margin-top: 30px; padding: 20px; }}

/* 分析过程表格 */
.process-table {{ width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 13px; }}
.process-table th {{ background: #0f3460; color: #e94560; padding: 8px 12px; text-align: left; font-weight: 600; }}
.process-table td {{ padding: 8px 12px; border-bottom: 1px solid #333; }}
.process-table tr:hover {{ background: #1a1a2e; }}
.process-table .sub-score {{ font-weight: bold; font-size: 14px; }}
.factor-text {{ color: #aaa; font-size: 12px; max-width: 300px; }}

/* 公式框 */
.formula-box {{ background: #0f3460; border-left: 4px solid #e94560; padding: 12px 15px; margin: 10px 0; border-radius: 0 8px 8px 0; }}
.formula-title {{ color: #e94560; font-size: 12px; font-weight: bold; margin-bottom: 5px; text-transform: uppercase; }}
.formula {{ color: #eee; font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; margin: 5px 0; }}
.formula-detail {{ color: #aaa; font-size: 12px; margin-top: 5px; }}
.formula-detail strong {{ color: #e94560; font-size: 14px; }}

/* 维度得分条 */
.dim-bar {{ display: flex; align-items: center; margin: 8px 0; }}
.dim-bar-label {{ width: 80px; font-size: 13px; }}
.dim-bar-track {{ flex: 1; height: 20px; background: #333; border-radius: 10px; overflow: hidden; margin: 0 10px; }}
.dim-bar-fill {{ height: 100%; border-radius: 10px; display: flex; align-items: center; padding-left: 8px; font-size: 11px; font-weight: bold; }}
.dim-bar-value {{ width: 50px; text-align: right; font-weight: bold; font-size: 13px; }}
.dim-bar-weight {{ width: 60px; text-align: right; color: #666; font-size: 11px; }}

/* 风险等级 */
.risk-badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-weight: bold; font-size: 14px; }}
.risk-low {{ background: #2ecc71; color: #000; }}
.risk-mid {{ background: #f39c12; color: #000; }}
.risk-high {{ background: #e74c3c; color: #fff; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>⚜️ 黄金投资分析报告</h1>
    <div class="subtitle">Gold Investment Analysis Report | {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
    <div class="price">${data.get('gold_price', 0):,.2f}/oz</div>
    <div style="color:#aaa;font-size:14px;">{instrument_label} | 日内变化: {((data.get('gold_price',0) - gold_data.get('prev_close',0)) / gold_data.get('prev_close',1) * 100):+.2f}%</div>
  </div>

  <!-- 关联市场数据 -->
  <div class="card">
    <h2>📊 关联市场数据</h2>
    <table class="process-table">
      <tr><th>品种</th><th>价格</th><th>涨跌幅</th></tr>
      {"".join(market_rows) if market_rows else '<tr><td colspan="3">暂无数据</td></tr>'}
    </table>
  </div>

  <!-- 综合评分 -->
  <div class="card">
    <h2>🎯 综合评分</h2>
    <div class="score-bar">
      <div class="score-fill" style="width:{score}%; background:{score_bg(score)};">
        {score:.1f}/100 — {score_text(score)}
      </div>
    </div>
    <p style="margin:10px 0 0 0;color:#aaa;">
      <strong>信号:</strong> {final.get('signal', 'N/A')} |
      <strong>建议:</strong> {rec.get('position', 'N/A')} |
      <strong>风险:</strong>
      <span class="risk-badge risk-{'low' if risk.get('level')=='低' else 'mid' if risk.get('level')=='中' else 'high'}">
        {risk.get('level', '中')}
      </span>
      ({risk.get('consistency', 0):.0f}% 一致性)
    </p>
  </div>

  <!-- 维度得分详情 -->
  <div class="card">
    <h2>📊 维度得分详情（三维度架构）</h2>
    {"".join(f'''
    <div class="dim-bar">
      <div class="dim-bar-label">{icon} {label}</div>
      <div class="dim-bar-track">
        <div class="dim-bar-fill" style="width:{s}%; background:{score_bg(s)};">
          {s:.1f}
        </div>
      </div>
      <div class="dim-bar-value" style="color:{score_bg(s)}">{s:.1f}</div>
      <div class="dim-bar-weight">权重{w}%</div>
    </div>'''
    for label, key, icon in [("技术面","technical","📈"),("基本面","fundamental","🏦"),
                              ("情绪面","sentiment","💭")]
    for s in [dims.get(key, 50)] for w in [weights.get(key, 25)])}
  </div>

  <!-- 技术面分析过程 -->
  <div class="card">
    <h2>📈 技术面分析过程</h2>
    {tech_formula_html}
    <table class="process-table">
      <tr><th>指标</th><th>数值</th><th>信号/说明</th></tr>
      {"".join(tech_rows) if tech_rows else '<tr><td colspan="3">暂无数据</td></tr>'}
    </table>
  </div>

  <!-- 基本面分析过程 -->
  <div class="card">
    <h2>🏦 基本面分析过程</h2>
    <div class="formula-box">
      <div class="formula-title">评分维度</div>
      <div class="formula">Fed政策({fund_weights['fed_policy']:.0%}) + 美元({fund_weights['usd_impact']:.0%}) + 通胀({fund_weights['inflation']:.0%}) + 收益率曲线({fund_weights['yield_curve']:.0%}) + 结构性({fund_weights['structural']:.0%})</div>
      <div class="formula-detail">
        基本面综合得分: <strong>{dims.get('fundamental', 50):.1f}/100</strong>
      </div>
    </div>
    <table class="process-table">
      <tr><th>维度</th><th>原始得分</th><th>权重</th><th>加权贡献</th><th>信号</th><th>关键因子</th></tr>
      {"".join(fund_rows) if fund_rows else '<tr><td colspan="6">暂无数据</td></tr>'}
    </table>
  </div>

  <!-- 情绪面分析过程 -->
  <div class="card">
    <h2>💭 情绪面分析过程</h2>
    <div class="formula-box">
      <div class="formula-title">计算公式</div>
      <div class="formula">score = 50 + (VIX×{SENTIMENT['dim_weights']['vix']:.1f} + Oil×{SENTIMENT['dim_weights']['oil']:.1f} + 金银比×{SENTIMENT['dim_weights']['gold_silver_ratio']:.1f} + 新闻×{SENTIMENT['dim_weights']['news']:.1f}) × {SENTIMENT['score_scale']}</div>
    </div>
    <table class="process-table">
      <tr><th>维度</th><th>原始得分</th><th>权重</th><th>加权贡献</th><th>信号</th><th>关键因子</th></tr>
      {"".join(sent_rows) if sent_rows else '<tr><td colspan="6">暂无数据</td></tr>'}
    </table>
  </div>

  <!-- 投资建议 -->
  <div class="card rec-box">
    <div class="rec-title">💡 投资建议</div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;">
      <div>
        <p><strong>操作:</strong> {rec.get('position', 'N/A')}</p>
        <p><strong>仓位:</strong> {rec.get('allocation', 'N/A')}</p>
        <p><strong>策略:</strong> {rec.get('strategy', 'N/A')}</p>
        {f'<p style="color:#3498db;"><strong>入场时机:</strong> {rec.get("entry_timing", "")}</p>' if rec.get('entry_timing') else ''}
      </div>
      <div>
        <p><strong>风控建议:</strong></p>
        <ul style="margin:5px 0;">
          <li>止损: {rec.get('risk_management', {}).get('stop_loss', 'N/A')}</li>
          <li>止盈: {rec.get('risk_management', {}).get('take_profit', 'N/A')}</li>
          <li>回撤容忍: {rec.get('risk_management', {}).get('max_drawdown_tolerance', 'N/A')}</li>
        </ul>
      </div>
    </div>
  </div>

  <!-- 关键关注点 -->
  <div class="card">
    <h2>⚠️ 关键关注点</h2>
    {"".join(f'<div class="factor">• {w}</div>' for w in rec.get('watch_list', []))}
  </div>

  <div class="disclaimer">
    ⚠️ 以上分析仅供参考，不构成投资建议。黄金市场波动剧烈，请根据自身风险承受能力谨慎决策。<br>
    Generated by Gold Investment Assistant | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
  </div>
</div>

<script>
const chartData = {chart_json};

// 价格走势图
if (chartData.price) {{
  const tracePrice = {{
    x: chartData.price.x,
    y: chartData.price.close,
    type: 'scatter',
    mode: 'lines',
    name: '收盘价',
    line: {{ color: '#e94560', width: 2 }}
  }};
  const traceMA20 = {{
    x: chartData.price.x,
    y: chartData.price.ma20,
    type: 'scatter',
    mode: 'lines',
    name: 'MA20',
    line: {{ color: '#3498db', width: 1.5 }}
  }};
  const traceMA50 = {{
    x: chartData.price.x,
    y: chartData.price.ma50,
    type: 'scatter',
    mode: 'lines',
    name: 'MA50',
    line: {{ color: '#f39c12', width: 1.5 }}
  }};
  Plotly.newPlot('priceChart', [tracePrice, traceMA20, traceMA50], {{
    paper_bgcolor: '#16213e',
    plot_bgcolor: '#1a1a2e',
    font: {{ color: '#eee' }},
    xaxis: {{ gridcolor: '#333', title: '' }},
    yaxis: {{ gridcolor: '#333', title: '价格 (USD)' }},
    legend: {{ x: 0, y: 1 }},
    margin: {{ t: 30, b: 40 }}
  }}, {{ responsive: true }});
}}

// RSI 图
if (chartData.rsi) {{
  const traceRSI = {{
    x: chartData.rsi.x,
    y: chartData.rsi.value,
    type: 'scatter',
    mode: 'lines',
    name: 'RSI(14)',
    line: {{ color: '#9b59b6', width: 2 }}
  }};
  const traceOverbought = {{
    x: chartData.rsi.x,
    y: chartData.rsi.value.map(() => 70),
    type: 'scatter',
    mode: 'lines',
    name: '超买线',
    line: {{ color: '#e74c3c', width: 1, dash: 'dash' }}
  }};
  const traceOversold = {{
    x: chartData.rsi.x,
    y: chartData.rsi.value.map(() => 30),
    type: 'scatter',
    mode: 'lines',
    name: '超卖线',
    line: {{ color: '#2ecc71', width: 1, dash: 'dash' }}
  }};
  Plotly.newPlot('rsiChart', [traceRSI, traceOverbought, traceOversold], {{
    paper_bgcolor: '#16213e',
    plot_bgcolor: '#1a1a2e',
    font: {{ color: '#eee' }},
    xaxis: {{ gridcolor: '#333', title: '' }},
    yaxis: {{ gridcolor: '#333', title: 'RSI', range: [0, 100] }},
    legend: {{ x: 0, y: 1 }},
    margin: {{ t: 30, b: 40 }}
  }}, {{ responsive: true }});
}}
</script>
</body>
</html>"""
        return html
