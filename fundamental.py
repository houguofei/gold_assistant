# -*- coding: utf-8 -*-
"""
黄金投资助手 - 基本面与宏观分析模块
Gold Investment Assistant - Fundamental & Macro Analysis

分析Fed政策、美元、利率、通胀、财政赤字、去美元化等结构性因素
所有阈值和权重从 config.py 读取。
"""

from typing import Dict, Tuple
from config import MACRO_PARAMS, FUNDAMENTAL, FUND_SCORE_THRESHOLDS


class FundamentalAnalyzer:
    """
    基本面分析引擎
    
    基于实时市场数据和可配置参数，量化评估黄金的基本面环境。
    用户可通过修改 config.py 中的参数来反映最新政策变化。
    """

    def __init__(self, params: Dict = None):
        self.params = {**MACRO_PARAMS, **(params or {})}

    def analyze_fed_policy(self) -> Tuple[float, str, Dict]:
        """
        美联储政策分析
        返回: (score, signal, details)
        score: -50 ~ +50 (对黄金的利多/利空程度)
        
        判断依据（按优先级排序）：
        1. FedWatch 利率预期（市场最真实的预期）
        2. 新闻情绪分析（鹰派/鸽派关键词扫描）
        3. 联邦基金利率 + CPI 组合（辅助参考）
        """
        p = self.params
        score = 0
        factors = []

        # ========== 1. FedWatch 利率预期（核心）==========
        fedwatch = p.get("fedwatch_rates")
        if fedwatch and "next_cut_prob" in fedwatch:
            cut_prob = fedwatch["next_cut_prob"]
            hike_prob = fedwatch.get("hike_prob", 0)
            
            if cut_prob > 0.7:
                score += 20
                factors.append(f"FedWatch 降息概率极高({cut_prob:.0%}) → 强烈利多")
            elif cut_prob > 0.5:
                score += 12
                factors.append(f"FedWatch 降息概率偏高({cut_prob:.0%}) → 利多")
            elif hike_prob > 0.5:
                score -= 20
                factors.append(f"FedWatch 加息概率极高({hike_prob:.0%}) → 强烈利空")
            elif hike_prob > 0.3:
                score -= 12
                factors.append(f"FedWatch 加息概率偏高({hike_prob:.0%}) → 利空")
            else:
                factors.append(f"FedWatch 维持利率概率({1-cut_prob-hike_prob:.0%}) → 中性")
        else:
            # FedWatch 不可用，降级到新闻情绪 + 利率绝对值
            self._fed_policy_from_news(p, score, factors)

        # ========== 2. 实际利率趋势（辅助）==========
        real_yield = p.get("us10y_real", 0)
        if real_yield > 2.0:
            score -= 10
            factors.append(f"实际收益率偏高({real_yield:.2f}%) → 持有黄金机会成本高")
        elif real_yield < 1.0:
            score += 10
            factors.append(f"实际收益率偏低({real_yield:.2f}%) → 黄金吸引力强")
        else:
            factors.append(f"实际收益率适中({real_yield:.2f}%)")

        score = max(-50, min(50, score))

        if score >= 15:
            signal = "利多"
        elif score <= -15:
            signal = "利空"
        else:
            signal = "中性"

        return score, signal, {
            "factors": factors,
            "fed_rate": f"{p.get('fed_rate_lower', '?')}-{p.get('fed_rate_upper', '?')}%",
            "policy_tone": p.get("fed_policy_tone", "unknown"),
            "real_yield": f"{real_yield:.2f}%",
        }

    def _fed_policy_from_news(self, p: dict, score: int, factors: list):
        """
        当 FedWatch 不可用时，从新闻情绪推断 Fed 政策倾向
        
        这是降级方案，优先级低于 FedWatch 但高于利率绝对值。
        """
        fed_sentiment = p.get("fed_news_sentiment", 0)
        fed_rate = p.get("fed_rate_upper", 5.0)
        
        # 新闻情绪主导判断
        if fed_sentiment < -5:
            score -= 15
            factors.append(f"新闻强烈鹰派(情绪{fed_sentiment:+.1f}) → 利空")
        elif fed_sentiment < -2:
            score -= 10
            factors.append(f"新闻偏鹰派(情绪{fed_sentiment:+.1f}) → 利空")
        elif fed_sentiment > 5:
            score += 15
            factors.append(f"新闻强烈鸽派(情绪{fed_sentiment:+.1f}) → 利多")
        elif fed_sentiment > 2:
            score += 10
            factors.append(f"新闻偏鸽派(情绪{fed_sentiment:+.1f}) → 利多")
        else:
            factors.append(f"新闻情绪中性(情绪{fed_sentiment:+.1f})")
        
        # 联邦基金利率作为辅助验证
        if fed_rate > 5.0:
            factors.append(f"联邦基金利率{fed_rate:.2f}%处于高位，加息空间有限")
        elif fed_rate < 2.0:
            score -= 5
            factors.append(f"联邦基金利率{fed_rate:.2f}%处于低位，存在加息可能")

    def analyze_usd(self, gold_data: Dict = None) -> Tuple[float, str, Dict]:
        """
        美元分析
        """
        p = self.params
        score = 0
        factors = []

        dxy = p["dxy_current"]
        dxy_3m = p["dxy_3m_ago"]
        dxy_1y = p["dxy_1y_ago"]

        # 美元水平
        if dxy > 125:
            score -= 20
            factors.append(f"美元指数极高({dxy}) → 强烈压制金价")
        elif dxy > 119:
            score -= 10
            factors.append(f"美元指数偏强({dxy}) → 压制金价")
        elif dxy < 113:
            score += 15
            factors.append(f"美元指数偏弱({dxy}) → 利好金价")

        # 美元趋势
        change_3m = (dxy - dxy_3m) / dxy_3m * 100
        if change_3m > 5:
            score -= 15
            factors.append(f"美元3个月暴涨{change_3m:.1f}% → 强烈压制")
        elif change_3m > 2:
            score -= 8
            factors.append(f"美元3个月上涨{change_3m:.1f}% → 压制")
        elif change_3m < -3:
            score += 12
            factors.append(f"美元3个月下跌{abs(change_3m):.1f}% → 利好")

        # 美元vs一年前
        change_1y = (dxy - dxy_1y) / dxy_1y * 100
        if change_1y > 5:
            score -= 8
        elif change_1y < -5:
            score += 8

        score = max(-50, min(50, score))

        if score >= 10:
            signal = "利多"
        elif score <= -10:
            signal = "利空"
        else:
            signal = "中性"

        return score, signal, {
            "factors": factors,
            "dxy": dxy,
            "change_3m": f"{change_3m:+.1f}%",
            "change_1y": f"{change_1y:+.1f}%",
        }

    def analyze_inflation(self) -> Tuple[float, str, Dict]:
        """通胀分析"""
        p = self.params
        score = 0
        factors = []

        cpi = p["cpi_yoy"]
        core = p["core_cpi_yoy"]
        trend = p["inflation_trend"]

        # 通胀水平
        if cpi > 5:
            score += 15
            factors.append(f"CPI同比{cpi}% → 高通胀强利好黄金")
        elif cpi > 3:
            score += 8
            factors.append(f"CPI同比{cpi}% → 温和通胀支撑黄金")
        elif cpi < 2:
            score -= 8
            factors.append(f"CPI同比{cpi}% → 低通胀削弱黄金需求")

        # 通胀趋势
        if trend == "rising":
            score += 10
            factors.append("通胀趋势上升 → 利多")
        elif trend == "cooling":
            score -= 5
            factors.append("通胀趋势回落 → 轻微利空")
        else:
            factors.append("通胀趋势稳定 → 中性")

        # 核心通胀
        if core > 4:
            score += 8
            factors.append(f"核心CPI偏高({core}%) → 支撑通胀溢价")
        elif core < 2:
            score -= 5

        score = max(-50, min(50, score))

        if score >= 10:
            signal = "利多"
        elif score <= -10:
            signal = "利空"
        else:
            signal = "中性"

        return score, signal, {
            "factors": factors,
            "cpi": f"{cpi}%",
            "core_cpi": f"{core}%",
            "trend": trend,
        }

    def analyze_structural(self) -> Tuple[float, str, Dict]:
        """
        长期结构性因素分析
        （财政赤字、去美元化、央行购金）
        """
        p = self.params
        score = 0
        factors = []
        score_details = []

        # 财政赤字
        deficit = p["us_fiscal_deficit_gdp"]
        if deficit > 6:
            score += 18
            factors.append(f"美国赤字/GDP达{deficit}% → 结构性利多")
            score_details.append(("财政赤字", deficit, ">6%", "+18"))
        elif deficit > 4:
            score += 10
            factors.append(f"美国赤字/GDP为{deficit}% → 支撑黄金")
            score_details.append(("财政赤字", deficit, ">4%", "+10"))
        elif deficit < 3:
            score -= 5
            score_details.append(("财政赤字", deficit, "<3%", "-5"))
        else:
            score_details.append(("财政赤字", deficit, "3-4%", "+0"))

        # 债务/GDP
        debt = p["us_debt_gdp"]
        if debt > 130:
            score += 12
            factors.append(f"债务/GDP达{debt}% → 不可持续，利多黄金")
            score_details.append(("债务/GDP", debt, ">130%", "+12"))
        elif debt > 100:
            score += 6
            factors.append(f"债务/GDP为{debt}% → 支撑黄金")
            score_details.append(("债务/GDP", debt, ">100%", "+6"))
        else:
            score_details.append(("债务/GDP", debt, "<=100%", "+0"))

        # 央行购金
        cb_plan = p["cb_buying_pct_plan_increase"]
        cb_trend = p["cb_buying_trend"]
        if cb_plan > 40:
            score += 10
            factors.append(f"{cb_plan}%央行计划增持黄金 → 强劲需求支撑")
            score_details.append(("央行购金计划", cb_plan, ">40%", "+10"))
        elif cb_plan > 25:
            score += 5
            score_details.append(("央行购金计划", cb_plan, ">25%", "+5"))
        else:
            score_details.append(("央行购金计划", cb_plan, "<=25%", "+0"))
        if cb_trend == "rising":
            score += 5
            factors.append("央行购金趋势上升 → 利多")
            score_details.append(("购金趋势", cb_trend, "rising", "+5"))
        else:
            score_details.append(("购金趋势", cb_trend, "not rising", "+0"))

        # 去美元化
        dedol = p["dedollarization_momentum"]
        if dedol > 0.7:
            score += 8
            factors.append(f"去美元化动能强劲({dedol:.0%}) → 利多黄金")
            score_details.append(("去美元化", f"{dedol:.0%}", ">70%", "+8"))
        elif dedol > 0.4:
            score += 3
            score_details.append(("去美元化", f"{dedol:.0%}", ">40%", "+3"))
        else:
            score_details.append(("去美元化", f"{dedol:.0%}", "<=40%", "+0"))

        score = max(-50, min(50, score))

        if score >= 10:
            signal = "利多"
        elif score <= -10:
            signal = "利空"
        else:
            signal = "中性"

        return score, signal, {
            "factors": factors,
            "score_details": score_details,
            "deficit_gdp": f"{deficit}%",
            "debt_gdp": f"{debt}%",
            "cb_buying": f"{cb_plan}%增持",
            "dedollarization": f"{dedol:.0%}",
        }

    def analyze_yield_curve(self) -> Tuple[float, str, Dict]:
        """收益率曲线分析（2s10s利差，重要衰退指标）"""
        p = self.params
        score = 0
        factors = []
        spread = p.get("yield_curve_2s10s", 0)

        if spread < -0.5:
            score += 15
            factors.append(f"2s10s深度倒挂({spread:.2f}%) → 衰退预期强，利多黄金")
        elif spread < -0.1:
            score += 8
            factors.append(f"2s10s倒挂({spread:.2f}%) → 经济隐忧，支撑黄金")
        elif spread < 0.3:
            score += 2
            factors.append(f"2s10s利差平缓({spread:.2f}%) → 中性")
        else:
            score -= 3
            factors.append(f"2s10s利差陡峭({spread:.2f}%) → 经济预期较好，轻微利空")

        score = max(-20, min(20, score))
        signal = "利多" if score >= 5 else "利空" if score <= -5 else "中性"

        return score, signal, {
            "factors": factors,
            "spread_2s10s": f"{spread:+.2f}%",
        }

    def full_analysis(self) -> Dict:
        """执行完整基本面分析"""
        fed_score, fed_signal, fed_details = self.analyze_fed_policy()
        usd_score, usd_signal, usd_details = self.analyze_usd()
        inf_score, inf_signal, inf_details = self.analyze_inflation()
        yc_score, yc_signal, yc_details = self.analyze_yield_curve()
        str_score, str_signal, str_details = self.analyze_structural()

        return {
            "fed": {"score": fed_score, "signal": fed_signal, **fed_details},
            "usd": {"score": usd_score, "signal": usd_signal, **usd_details},
            "inflation": {"score": inf_score, "signal": inf_signal, **inf_details},
            "yield_curve": {"score": yc_score, "signal": yc_signal, **yc_details},
            "structural": {"score": str_score, "signal": str_signal, **str_details},
        }

    def compute_score(self) -> Tuple[float, str, Dict]:
        """
        计算基本面综合得分 (0-100)
        """
        analysis = self.full_analysis()

        # 各维度得分 (-50~+50) → 归一化到 (0~100)
        # key映射：config里的权重key → full_analysis返回的key
        score_key_map = {
            "fed_policy": "fed",
            "usd_impact": "usd",
            "inflation": "inflation",
            "yield_curve": "yield_curve",
            "structural": "structural",
        }

        # 从配置读取内部维度权重
        weights = FUNDAMENTAL["dim_weights"]
        scale = FUNDAMENTAL["score_scale"]

        weighted = sum(
            analysis[score_key_map[weight_key]]["score"] * weight
            for weight_key, weight in weights.items()
        )

        # 映射到 0-100
        final_score = 50 + weighted * scale
        final_score = max(0, min(100, final_score))

        # 从配置读取信号阈值
        t = FUND_SCORE_THRESHOLDS
        if final_score >= t["bullish"]:
            signal = "🟢 基本面利多"
        elif final_score >= t["lean_bullish"]:
            signal = "🟡 基本面偏多"
        elif final_score >= t["neutral_upper"]:
            signal = "⚪ 基本面中性"
        elif final_score >= t["neutral_lower"]:
            signal = "🟡 基本面偏空"
        else:
            signal = "🔴 基本面利空"

        return final_score, signal, analysis
