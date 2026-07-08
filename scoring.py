# -*- coding: utf-8 -*-
"""
黄金投资助手 - 综合评分与建议引擎
Gold Investment Assistant - Scoring & Recommendation Engine

将技术面、基本面、情绪面的分析结果综合为一个评分和投资建议。
所有阈值和风控参数从 config.py 读取。
"""

from typing import Dict, Tuple, List
from config import SCORING


class ScoringEngine:
    """
    综合评分引擎

    将各维度分析结果加权合并，输出最终评分和投资建议。
    权重默认从 config.py 读取，也可通过参数覆盖。
    """

    def __init__(self, weights: Dict = None):
        self.weights = weights or SCORING["weights"]

    def compute_final_score(self, technical_score: float,
                            fundamental_score: float,
                            sentiment_score: float,
                            fundamental_details: Dict = None,
                            technical_details: Dict = None) -> Dict:
        """
        计算最终综合评分（三维度架构）

        Args:
            technical_score: 技术面得分 (0-100)
            fundamental_score: 基本面得分 (0-100)（包含结构性因素）
            sentiment_score: 情绪面得分 (0-100)
            fundamental_details: 基本面分析详细结果
            technical_details: 技术面分析详细结果（用于提供支撑阻力位建议）
        """
        # 根据市场状态动态调整权重（三维度：技术、基本面、情绪）
        w = self._adjust_weights_by_regime(technical_details)

        # 提取市场状态信息用于报告
        regime_info = None
        if technical_details:
            regime_info = technical_details.get("market_regime", None)

        total_weight = sum(w.values())

        # 三维度加权综合评分
        raw_score = (
            technical_score * w["technical"] +
            fundamental_score * w["fundamental"] +
            sentiment_score * w["sentiment"]
        ) / total_weight

        # 确保在0-100范围
        final_score = max(0, min(100, raw_score))

        # 生成信号
        signal, signal_strength = self._score_to_signal(final_score)

        # 先评估风险等级（用于一致性调整仓位）
        risk_level = self._assess_risk_level(
            technical_score, fundamental_score, sentiment_score
        )

        # 生成建议
        recommendation = self._generate_recommendation(
            final_score, signal, signal_strength,
            technical_score, fundamental_score, sentiment_score,
            risk_level, technical_details
        )

        return {
            "final_score": round(final_score, 1),
            "signal": signal,
            "signal_strength": signal_strength,
            "recommendation": recommendation,
            "risk_level": risk_level,
            "market_regime": regime_info,
            "dimension_scores": {
                "technical": round(technical_score, 1),
                "fundamental": round(fundamental_score, 1),
                "sentiment": round(sentiment_score, 1),
            },
            "weights": self.weights,
            "weights_used": w,
        }

    def _adjust_weights_by_regime(self, technical_details: Dict = None) -> Dict:
        """
        根据市场状态（牛市/熊市/震荡市）动态调整各维度权重（三维度架构）
        
        调整策略：
        - 趋势市（牛市/熊市）：提高技术面权重，降低基本面权重
        - 震荡市：提高基本面和情绪面权重，技术面权重降低
        """
        base_weights = self.weights.copy()

        regime_info = None
        if technical_details:
            regime_info = technical_details.get("market_regime", None)

        if not regime_info:
            return base_weights

        regime = regime_info.get("regime", "sideways")

        adjusted = base_weights.copy()
        if regime == "bull":
            # 牛市：技术面更重要（顺势而为），基本面权重降低
            adjusted["technical"] = base_weights["technical"] + 5
            adjusted["fundamental"] = base_weights["fundamental"] - 5
        elif regime == "bear":
            # 熊市：情绪面/风控更重要，技术面也重要
            adjusted["technical"] = base_weights["technical"] + 5
            adjusted["sentiment"] = base_weights["sentiment"] + 5
            adjusted["fundamental"] = base_weights["fundamental"] - 10
        else:  # sideways
            # 震荡市：基本面和情绪面更重要，高抛低吸
            adjusted["technical"] = base_weights["technical"] - 5
            adjusted["fundamental"] = base_weights["fundamental"] + 3
            adjusted["sentiment"] = base_weights["sentiment"] + 2

        # 确保权重非负
        for k in adjusted:
            adjusted[k] = max(5, adjusted[k])

        # 归一化到总和100
        total = sum(adjusted.values())
        for k in adjusted:
            adjusted[k] = round(adjusted[k] / total * 100)

        return adjusted

    def _score_to_signal(self, score: float) -> Tuple[str, str]:
        """评分转换为交易信号（从配置读取阈值）"""
        t = SCORING["thresholds"]
        if score >= t["strong_buy"]:
            return "强烈看多", "strong_buy"
        elif score >= t["buy"]:
            return "看多", "buy"
        elif score >= t["lean_buy"]:
            return "偏多", "lean_buy"
        elif score >= t["neutral_upper"]:
            return "中性", "neutral"
        elif score >= t["lean_sell"]:
            return "偏空", "lean_sell"
        elif score >= t["sell"]:
            return "看空", "sell"
        else:
            return "强烈看空", "strong_sell"

    def _generate_recommendation(self, score: float, signal: str,
                                  strength: str,
                                  tech: float, fund: float,
                                  sent: float,
                                  risk_level: Dict = None,
                                  tech_details: Dict = None) -> Dict:
        """生成具体投资建议（三维度架构）"""

        # 基础持仓建议
        base_allocations = {
            "strong_buy": ("积极建仓/加仓", "30-40%仓位", "可以积极分批建仓，每次回调都是加仓机会"),
            "buy": ("分批建仓", "20-30%仓位", "建议分3-4批入场，利用回调逐步建仓"),
            "lean_buy": ("小仓位试探", "10-15%仓位", "可以小仓位试探性买入，等待更明确信号再加仓"),
            "neutral": ("观望/维持现有仓位", "现有仓位不变", "暂不加减仓，等待方向明确"),
            "lean_sell": ("减仓/止盈", "减仓至10%以下", "建议部分止盈，降低风险敞口"),
            "sell": ("大幅减仓", "减仓至5%以下", "建议大幅减仓，保留极小仓位观望"),
            "strong_sell": ("清仓离场", "清仓或仅保留极小对冲仓位", "建议清仓离场，等待底部信号再入场"),
        }
        position, allocation, strategy = base_allocations[strength]

        # 根据信号一致性动态调整仓位建议
        entry_timing = ""
        if risk_level:
            consistency = risk_level.get("consistency", 80)
            if consistency < 70:
                # 信号分歧大，建议更保守
                if "buy" in strength:
                    strategy += "（注意：各维度信号分歧较大，建议更轻仓）"
                    if allocation == "30-40%仓位":
                        allocation = "20-25%仓位"
                    elif allocation == "20-30%仓位":
                        allocation = "10-15%仓位"
                elif "sell" in strength:
                    strategy += "（注意：各维度信号分歧较大，减仓可更谨慎）"
            entry_timing = self._generate_entry_timing(strength, tech_details)

        # 关键关注点
        watch_list = self._generate_watch_list(tech, fund, sent)

        # 止损/止盈建议（从配置读取）
        risk_management = self._generate_risk_management(strength)

        result = {
            "position": position,
            "allocation": allocation,
            "strategy": strategy,
            "watch_list": watch_list,
            "risk_management": risk_management,
        }
        if entry_timing:
            result["entry_timing"] = entry_timing

        return result

    def _generate_entry_timing(self, strength: str, tech_details: Dict = None) -> str:
        """根据技术分析提供具体入场时机建议"""
        if not tech_details:
            return ""

        timing = ""
        sr = tech_details.get("support_resistance", {})
        supports = sr.get("support", [])
        resistances = sr.get("resistance", [])

        if "buy" in strength:
            if supports:
                nearest_support = supports[0]
                timing = f"理想入场点: 回踩至支撑位 ${nearest_support:,.0f} 附近可考虑加仓"
            rsi = tech_details.get("rsi", {})
            rsi_val = rsi.get("value", 50)
            if rsi_val < 35:
                timing += " | RSI接近超卖区，短线反弹概率较高"
        elif "sell" in strength:
            if resistances:
                nearest_resistance = resistances[0]
                timing = f"理想减仓点: 反弹至阻力位 ${nearest_resistance:,.0f} 附近可考虑减仓"
        else:
            if supports and resistances:
                timing = f"观望区间: 支撑 ${supports[0]:,.0f} - 阻力 ${resistances[0]:,.0f}，突破方向明确后再操作"

        return timing

    def _generate_watch_list(self, tech, fund, sent) -> List[str]:
        """
        生成关键关注点（三维度架构）
        
        结构性因素已作为基本面内部维度，其关注点将通过基本面维度反映
        """
        watch = []

        if tech < 40:
            watch.append("技术面偏空：关注RSI是否超卖、关键支撑位能否守住")
        elif tech > 60:
            watch.append("技术面偏多：关注能否突破上方阻力、RSI是否超买")

        if fund < 40:
            watch.append("基本面偏空：关注Fed政策动向、美元走势、央行购金")
        elif fund > 60:
            watch.append("基本面偏多：关注通胀数据、财政赤字进展、去美元化趋势")

        if sent < 40:
            watch.append("情绪偏空：关注VIX走势、ETF资金流向、地缘政治")
        elif sent > 60:
            watch.append("情绪偏多：关注是否过度乐观、获利了结压力")

        if not watch:
            watch.append("各维度信号不一致，建议观望等待方向明确")

        return watch

    def _generate_risk_management(self, strength) -> Dict:
        """生成风控建议（从配置读取）"""
        rm = SCORING["risk_management"]
        params = rm.get(strength, rm["neutral"])
        return {
            "stop_loss": params["stop_loss"],
            "take_profit": params["take_profit"],
            "max_drawdown_tolerance": params["max_drawdown"],
        }

    def _assess_risk_level(self, tech, fund, sent) -> Dict:
        """评估综合风险等级（三维度架构，从配置读取阈值）"""
        scores = [tech, fund, sent]
        avg = sum(scores) / len(scores)
        variance = sum((s - avg) ** 2 for s in scores) / len(scores)
        consistency = 100 - min(100, variance ** 0.5)

        high_thresh = SCORING["risk_consistency_high"]
        mid_thresh = SCORING["risk_consistency_mid"]
        extreme_low = SCORING["extreme_signal_low"]
        extreme_high = SCORING["extreme_signal_high"]

        if consistency > high_thresh:
            level = "低"
            desc = "各维度信号一致，方向较为明确"
        elif consistency > mid_thresh:
            level = "中"
            desc = "各维度信号部分分歧，建议谨慎操作"
        else:
            level = "高"
            desc = "各维度信号严重分歧，建议观望"

        if any(s < extreme_low or s > extreme_high for s in scores):
            if level == "低":
                level = "中"
            desc += "（存在极端信号，注意反转风险）"

        return {"level": level, "description": desc,
                "consistency": round(consistency, 1)}
