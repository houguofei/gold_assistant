# -*- coding: utf-8 -*-
"""
黄金投资助手 - 技术分析模块
Gold Investment Assistant - Technical Analysis

计算RSI、MACD、布林带、均线、支撑阻力、OBV、金叉死叉、背离检测等技术指标
所有计算使用纯Python实现，无需numpy/pandas
"""

import math
from typing import Dict, List, Optional, Tuple
from config import TECHNICAL, TECH_SCORE_WEIGHTS


class TechnicalAnalyzer:
    """黄金技术分析引擎"""

    def __init__(self, closes: List[float], highs: List[float],
                 lows: List[float], volumes: List[int] = None):
        self.closes = closes
        self.highs = highs
        self.lows = lows
        self.volumes = volumes or [0] * len(closes)
        self.n = len(closes)

    # ================================================================
    # 基础计算
    # ================================================================

    @staticmethod
    def _sma(data: List[float], period: int) -> List[Optional[float]]:
        """简单移动平均线"""
        result = [None] * len(data)
        for i in range(period - 1, len(data)):
            result[i] = sum(data[i - period + 1:i + 1]) / period
        return result

    @staticmethod
    def _ema(data: List[float], period: int) -> List[Optional[float]]:
        """指数移动平均线"""
        result = [None] * len(data)
        if len(data) < period:
            return result

        # 第一个EMA用SMA初始化
        result[period - 1] = sum(data[:period]) / period
        multiplier = 2.0 / (period + 1)

        for i in range(period, len(data)):
            result[i] = (data[i] - result[i - 1]) * multiplier + result[i - 1]
        return result

    # ================================================================
    # 技术指标
    # ================================================================

    def moving_averages(self, short: int = 20, mid: int = 50,
                        long: int = 200) -> Dict:
        """计算移动平均线"""
        ma_short = self._sma(self.closes, short)
        ma_mid = self._sma(self.closes, mid)
        ma_long = self._sma(self.closes, long)

        current = self.closes[-1]

        def _pos(val, label):
            if val is None:
                return None
            return {"value": round(val, 2), "price_above": current > val,
                    "distance_pct": round((current - val) / val * 100, 2)}

        return {
            f"MA{short}": _pos(ma_short[-1], f"MA{short}"),
            f"MA{mid}": _pos(ma_mid[-1], f"MA{mid}"),
            f"MA{long}": _pos(ma_long[-1], f"MA{long}"),
            "ma_short": ma_short,
            "ma_mid": ma_mid,
            "ma_long": ma_long,
        }

    def rsi(self, period: int = 14) -> Dict:
        """相对强弱指标 RSI"""
        if self.n < period + 1:
            return {"value": 50, "signal": "neutral", "detail": "数据不足"}

        # 计算每日涨跌
        changes = [self.closes[i] - self.closes[i - 1]
                   for i in range(1, self.n)]

        gains = [max(c, 0) for c in changes]
        losses = [abs(min(c, 0)) for c in changes]

        # 初始平均
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        # 平滑计算
        for i in range(period, len(changes)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            rsi_val = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi_val = 100.0 - (100.0 / (1.0 + rs))

        # 信号判断
        if rsi_val >= 80:
            signal = "overbought_strong"
            desc = "极度超买 → 强烈卖出信号"
        elif rsi_val >= 70:
            signal = "overbought"
            desc = "超买 → 卖出信号"
        elif rsi_val <= 20:
            signal = "oversold_strong"
            desc = "极度超卖 → 强烈买入信号"
        elif rsi_val <= 30:
            signal = "oversold"
            desc = "超卖 → 买入信号"
        elif rsi_val >= 55:
            signal = "bullish"
            desc = "偏多"
        elif rsi_val <= 45:
            signal = "bearish"
            desc = "偏空"
        else:
            signal = "neutral"
            desc = "中性"

        return {
            "value": round(rsi_val, 2),
            "signal": signal,
            "detail": desc,
        }

    def macd(self, fast: int = 12, slow: int = 26,
             signal_period: int = 9) -> Dict:
        """MACD指标"""
        ema_fast = self._ema(self.closes, fast)
        ema_slow = self._ema(self.closes, slow)

        if ema_fast[-1] is None or ema_slow[-1] is None:
            return {"macd": 0, "signal": 0, "histogram": 0,
                    "trend": "neutral", "detail": "数据不足"}

        # MACD线 = 快EMA - 慢EMA
        macd_line = [None] * self.n
        macd_values = []
        for i in range(self.n):
            if ema_fast[i] is not None and ema_slow[i] is not None:
                macd_line[i] = ema_fast[i] - ema_slow[i]
                macd_values.append(macd_line[i])

        # 信号线 = MACD的EMA
        if len(macd_values) >= signal_period:
            signal_ema = self._ema(macd_values, signal_period)
            signal_val = signal_ema[-1] if signal_ema[-1] else 0
        else:
            signal_val = 0

        macd_val = macd_line[-1] if macd_line[-1] else 0
        histogram = macd_val - signal_val

        # 趋势判断（加入histogram容差，避免线性趋势下histogram≈0时误判为neutral）
        hist_tol = 0.01  # histogram容差
        if macd_val > 0 and histogram >= -hist_tol:
            trend = "bullish"
            desc = "多头排列，动能增强"
        elif macd_val > 0 and histogram < -hist_tol:
            trend = "weakening"
            desc = "多头减弱，警惕回调"
        elif macd_val < 0 and histogram <= hist_tol:
            trend = "bearish"
            desc = "空头排列，动能增强"
        elif macd_val < 0 and histogram > hist_tol:
            trend = "recovering"
            desc = "空头减弱，可能反弹"
        elif macd_val > 0:
            trend = "bullish"
            desc = "多头排列"
        elif macd_val < 0:
            trend = "bearish"
            desc = "空头排列"
        else:
            trend = "neutral"
            desc = "中性"

        return {
            "macd": round(macd_val, 2),
            "signal": round(signal_val, 2),
            "histogram": round(histogram, 2),
            "trend": trend,
            "detail": desc,
        }

    def bollinger_bands(self, period: int = 20, num_std: float = 2.0) -> Dict:
        """布林带"""
        if self.n < period:
            return {"upper": 0, "middle": 0, "lower": 0,
                    "position": "middle", "width": 0}

        recent = self.closes[-period:]
        middle = sum(recent) / period
        variance = sum((x - middle) ** 2 for x in recent) / period
        std = math.sqrt(variance)

        upper = middle + num_std * std
        lower = middle - num_std * std

        current = self.closes[-1]
        width = (upper - lower) / middle * 100

        # 价格在布林带中的位置 (0=下轨, 1=上轨)
        if upper != lower:
            position = (current - lower) / (upper - lower)
        else:
            position = 0.5

        if position >= 0.95:
            pos_desc = "触及上轨 → 超买/可能回落"
        elif position >= 0.8:
            pos_desc = "接近上轨 → 偏高"
        elif position <= 0.05:
            pos_desc = "触及下轨 → 超卖/可能反弹"
        elif position <= 0.2:
            pos_desc = "接近下轨 → 偏低"
        else:
            pos_desc = "中轨附近 → 中性"

        return {
            "upper": round(upper, 2),
            "middle": round(middle, 2),
            "lower": round(lower, 2),
            "position": round(position, 3),
            "position_desc": pos_desc,
            "width": round(width, 2),
        }

    def atr(self, period: int = 14) -> Dict:
        """平均真实波幅 ATR"""
        if self.n < period + 1:
            return {"value": 0, "volatility": "unknown"}

        true_ranges = []
        for i in range(1, self.n):
            tr = max(
                self.highs[i] - self.lows[i],
                abs(self.highs[i] - self.closes[i - 1]),
                abs(self.lows[i] - self.closes[i - 1])
            )
            true_ranges.append(tr)

        # 计算ATR
        atr_val = sum(true_ranges[:period]) / period
        for i in range(period, len(true_ranges)):
            atr_val = (atr_val * (period - 1) + true_ranges[i]) / period

        current = self.closes[-1]
        atr_pct = atr_val / current * 100

        if atr_pct > 3:
            vol_desc = "极高波动"
        elif atr_pct > 2:
            vol_desc = "高波动"
        elif atr_pct > 1:
            vol_desc = "正常波动"
        else:
            vol_desc = "低波动"

        return {
            "value": round(atr_val, 2),
            "percentage": round(atr_pct, 2),
            "volatility": vol_desc,
        }

    def obv(self) -> Dict:
        """OBV能量潮指标 (On-Balance Volume)"""
        if self.n < 2:
            return {"value": 0, "trend": "neutral", "detail": "数据不足"}

        obv = 0
        obv_trend = [0]
        for i in range(1, self.n):
            if self.closes[i] > self.closes[i - 1]:
                obv += self.volumes[i]
            elif self.closes[i] < self.closes[i - 1]:
                obv -= self.volumes[i]
            obv_trend.append(obv)

        # 判断OBV趋势：比较最近5日与20日均值
        recent5 = obv_trend[-5:]
        recent20 = obv_trend[-20:] if self.n >= 20 else obv_trend
        avg5 = sum(recent5) / len(recent5)
        avg20 = sum(recent20) / len(recent20)

        if avg5 > avg20 * 1.01:
            trend = "bullish"
            desc = "OBV上升，量能配合价格上涨"
        elif avg5 < avg20 * 0.99:
            trend = "bearish"
            desc = "OBV下降，量能不支撑价格"
        else:
            trend = "neutral"
            desc = "OBV震荡，量能中性"

        return {
            "value": round(obv, 0),
            "trend": trend,
            "detail": desc,
            "ma5": round(avg5, 0),
            "ma20": round(avg20, 0),
        }

    def ma_crossover(self, short_period: int = 5, long_period: int = 20) -> Dict:
        """均线金叉/死叉检测"""
        ma_short = self._sma(self.closes, short_period)
        ma_long = self._sma(self.closes, long_period)

        if ma_short[-1] is None or ma_long[-1] is None:
            return {"signal": "none", "detail": "数据不足"}

        current_diff = ma_short[-1] - ma_long[-1]

        # 查找最近3天的差值，判断是否刚发生交叉
        cross_signal = "none"
        for i in range(-2, 0):
            if i - 1 >= -len(ma_short) and ma_short[i - 1] is not None:
                prev_diff = ma_short[i - 1] - ma_long[i - 1]
                if prev_diff <= 0 and current_diff > 0:
                    cross_signal = "golden_cross"
                    break
                elif prev_diff >= 0 and current_diff < 0:
                    cross_signal = "death_cross"
                    break

        if cross_signal == "golden_cross":
            desc = f"MA{short_period}上穿MA{long_period}，金叉买入信号"
        elif cross_signal == "death_cross":
            desc = f"MA{short_period}下穿MA{long_period}，死叉卖出信号"
        elif current_diff > 0:
            desc = f"MA{short_period}在MA{long_period}上方，短期偏多"
        else:
            desc = f"MA{short_period}在MA{long_period}下方，短期偏空"

        return {
            "signal": cross_signal,
            "detail": desc,
            "short_above_long": current_diff > 0,
        }

    def detect_divergence(self, lookback: int = 20) -> Dict:
        """RSI/MACD价格背离检测"""
        rsi_period = TECHNICAL.get("rsi_period", 14)
        # 计算完整RSI序列
        rsi_full = []
        changes = [self.closes[i] - self.closes[i - 1] for i in range(1, self.n)]
        gains = [max(c, 0) for c in changes]
        losses = [abs(min(c, 0)) for c in changes]

        if len(gains) < rsi_period + lookback:
            return {"signal": "none", "detail": "数据不足"}

        avg_gain = sum(gains[:rsi_period]) / rsi_period
        avg_loss = sum(losses[:rsi_period]) / rsi_period
        for i in range(rsi_period, len(changes)):
            avg_gain = (avg_gain * (rsi_period - 1) + gains[i]) / rsi_period
            avg_loss = (avg_loss * (rsi_period - 1) + losses[i]) / rsi_period
            if avg_loss == 0:
                rsi_full.append(100.0)
            else:
                rs = avg_gain / avg_loss
                rsi_full.append(100.0 - (100.0 / (1.0 + rs)))

        # 比较近期价格和RSI走势
        if len(rsi_full) < lookback * 2:
            return {"signal": "none", "detail": "数据不足"}

        price_now = self.closes[-1]
        price_then = self.closes[-lookback]
        rsi_now = rsi_full[-1]
        rsi_then = rsi_full[-lookback]

        price_change_pct = (price_now - price_then) / price_then * 100
        rsi_change = rsi_now - rsi_then

        divergence_signal = "none"
        detail = ""

        # 顶背离：价格创新高但RSI没创新高 → 看跌
        if price_change_pct > 2 and rsi_change < -5:
            divergence_signal = "bearish"
            detail = f"顶背离：价格{lookback}日涨{price_change_pct:.1f}%但RSI下降{rsi_change:.1f}，可能见顶回调"
        # 底背离：价格创新低但RSI没创新低 → 看涨
        elif price_change_pct < -2 and rsi_change > 5:
            divergence_signal = "bullish"
            detail = f"底背离：价格{lookback}日跌{abs(price_change_pct):.1f}%但RSI上升{rsi_change:.1f}，可能见底反弹"
        else:
            detail = "无明显背离"

        return {
            "signal": divergence_signal,
            "detail": detail,
            "price_change_pct": round(price_change_pct, 2),
            "rsi_change": round(rsi_change, 2),
        }

    def volume_analysis(self) -> Dict:
        """成交量分析"""
        if self.n < 20 or not any(self.volumes):
            return {"trend": "neutral", "detail": "无成交量数据"}

        vol_now = self.volumes[-1]
        vol_avg5 = sum(self.volumes[-5:]) / 5
        vol_avg20 = sum(self.volumes[-20:]) / 20

        vol_ratio = vol_now / vol_avg20 if vol_avg20 > 0 else 1
        price_change = (self.closes[-1] - self.closes[-2]) / self.closes[-2] * 100

        trend = "neutral"
        detail = ""

        if price_change > 0 and vol_ratio > 1.3:
            trend = "bullish"
            detail = f"放量上涨（量比{vol_ratio:.1f}），买盘强劲"
        elif price_change > 0 and vol_ratio < 0.7:
            trend = "weak_bullish"
            detail = f"缩量上涨（量比{vol_ratio:.1f}），上涨动能不足"
        elif price_change < 0 and vol_ratio > 1.3:
            trend = "bearish"
            detail = f"放量下跌（量比{vol_ratio:.1f}），抛压较大"
        elif price_change < 0 and vol_ratio < 0.7:
            trend = "weak_bearish"
            detail = f"缩量下跌（量比{vol_ratio:.1f}），下跌动能减弱"
        else:
            detail = f"成交量正常（量比{vol_ratio:.1f}）"

        return {
            "trend": trend,
            "detail": detail,
            "vol_ratio": round(vol_ratio, 2),
            "current_vol": vol_now,
            "vol_ma20": round(vol_avg20, 0),
        }

    def support_resistance(self, lookback: int = 60,
                           tolerance: float = 0.02) -> Dict:
        """计算支撑位和阻力位"""
        if self.n < lookback:
            lookback = self.n

        recent_closes = self.closes[-lookback:]
        recent_highs = self.highs[-lookback:]
        recent_lows = self.lows[-lookback:]
        current = self.closes[-1]

        # 找局部极值点
        pivots_high = []
        pivots_low = []

        for i in range(2, len(recent_highs) - 2):
            if (recent_highs[i] > recent_highs[i-1] and
                recent_highs[i] > recent_highs[i-2] and
                recent_highs[i] > recent_highs[i+1] and
                recent_highs[i] > recent_highs[i+2]):
                pivots_high.append(recent_highs[i])

            if (recent_lows[i] < recent_lows[i-1] and
                recent_lows[i] < recent_lows[i-2] and
                recent_lows[i] < recent_lows[i+1] and
                recent_lows[i] < recent_lows[i+2]):
                pivots_low.append(recent_lows[i])

        # 合并相近的水平
        def _cluster_levels(levels, tol):
            if not levels:
                return []
            levels = sorted(levels)
            clusters = [[levels[0]]]
            for lv in levels[1:]:
                if abs(lv - clusters[-1][-1]) / clusters[-1][-1] < tol:
                    clusters[-1].append(lv)
                else:
                    clusters.append([lv])
            return [round(sum(c) / len(c), 2) for c in clusters]

        resistance_raw = [p for p in pivots_high if p > current]
        support_raw = [p for p in pivots_low if p < current]

        resistance = _cluster_levels(resistance_raw, tolerance)
        support = _cluster_levels(support_raw, tolerance)

        # 也加入SMA作为动态支撑阻力
        sma50 = self._sma(self.closes, 50)
        sma200 = self._sma(self.closes, 200)
        if sma50[-1]:
            if sma50[-1] > current:
                resistance.append(round(sma50[-1], 2))
            else:
                support.append(round(sma50[-1], 2))

        resistance = sorted(set(resistance))[:5]
        support = sorted(set(support), reverse=True)[:5]

        return {
            "support": support,
            "resistance": resistance,
            "current_price": current,
        }

    def trend_analysis(self) -> Dict:
        """趋势综合分析"""
        current = self.closes[-1]

        # 短期趋势（5日 vs 20日）
        ma5 = sum(self.closes[-5:]) / 5 if self.n >= 5 else current
        ma20 = self._sma(self.closes, 20)[-1] or current
        ma50 = self._sma(self.closes, 50)[-1] or current
        ma200 = self._sma(self.closes, 200)[-1] or current

        # 趋势方向
        short_trend = "up" if current > ma20 else "down"
        medium_trend = "up" if current > ma50 else "down"
        long_trend = "up" if current > ma200 else "down"

        # 趋势强度（偏离度）
        short_strength = abs(current - ma20) / ma20 * 100 if ma20 else 0
        medium_strength = abs(current - ma50) / ma50 * 100 if ma50 else 0

        # 动量（5日变化率）
        if self.n >= 5:
            momentum_5d = (current - self.closes[-5]) / self.closes[-5] * 100
        else:
            momentum_5d = 0

        if self.n >= 20:
            momentum_20d = (current - self.closes[-20]) / self.closes[-20] * 100
        else:
            momentum_20d = 0

        # 综合趋势判断
        scores = {"up": 0, "down": 0}
        for t in [short_trend, medium_trend, long_trend]:
            scores[t] += 1

        if scores["up"] >= 2:
            overall = "bullish"
            overall_desc = "多头趋势"
        elif scores["down"] >= 2:
            overall = "bearish"
            overall_desc = "空头趋势"
        else:
            overall = "mixed"
            overall_desc = "趋势不明/震荡"

        return {
            "overall": overall,
            "overall_desc": overall_desc,
            "short_trend": short_trend,
            "medium_trend": medium_trend,
            "long_trend": long_trend,
            "momentum_5d": round(momentum_5d, 2),
            "momentum_20d": round(momentum_20d, 2),
            "price_vs_ma20": round((current - ma20) / ma20 * 100, 2) if ma20 else 0,
            "price_vs_ma50": round((current - ma50) / ma50 * 100, 2) if ma50 else 0,
            "price_vs_ma200": round((current - ma200) / ma200 * 100, 2) if ma200 else 0,
        }

    def detect_market_regime(self, lookback: int = 60) -> Dict:
        """
        识别市场状态: 牛市(bull)/熊市(bear)/震荡市(sideways)
        基于均线排列、价格趋势、波动率综合判断
        """
        if self.n < lookback:
            lookback = self.n

        recent_closes = self.closes[-lookback:]
        current = recent_closes[-1]
        start_price = recent_closes[0]
        period_return = (current - start_price) / start_price * 100

        ma5 = self._sma(self.closes, 5)
        ma20 = self._sma(self.closes, 20)
        ma60 = self._sma(self.closes, 60)

        ma5_val = ma5[-1] or current
        ma20_val = ma20[-1] or current
        ma60_val = ma60[-1] if ma60[-1] else current

        # 计算波动率 (ATR/价格)
        atr_val = self.atr(14)
        atr_pct = atr_val.get("value", 0) / current * 100 if current else 0

        # 均线排列得分
        ma_score = 0
        if ma5_val > ma20_val > ma60_val:
            ma_score = 2  # 多头排列
        elif ma5_val < ma20_val < ma60_val:
            ma_score = -2  # 空头排列
        elif current > ma20_val > ma60_val:
            ma_score = 1
        elif current < ma20_val < ma60_val:
            ma_score = -1

        # 趋势得分
        trend_score = 0
        if period_return > 8:
            trend_score = 2
        elif period_return > 3:
            trend_score = 1
        elif period_return < -8:
            trend_score = -2
        elif period_return < -3:
            trend_score = -1

        # 波动率得分（高波动率通常出现在趋势市）
        vol_score = 1 if atr_pct > 1.5 else -1 if atr_pct < 0.8 else 0

        total = ma_score + trend_score + vol_score

        if total >= 2:
            regime = "bull"
            regime_name = "牛市（趋势上涨）"
            description = "均线多头排列，趋势明确向上，顺势做多为主"
        elif total <= -2:
            regime = "bear"
            regime_name = "熊市（趋势下跌）"
            description = "均线空头排列，趋势明确向下，逢高做空或观望"
        else:
            regime = "sideways"
            regime_name = "震荡市"
            description = "均线纠缠，方向不明，区间操作为主或观望等待突破"

        return {
            "regime": regime,
            "name": regime_name,
            "description": description,
            "period_return_pct": round(period_return, 2),
            "atr_pct": round(atr_pct, 2),
            "ma_alignment": "bullish" if ma_score > 0 else "bearish" if ma_score < 0 else "mixed",
            "confidence": min(100, abs(total) * 25 + 50),
        }

    def full_analysis(self) -> Dict:
        """执行完整技术分析"""
        ma = self.moving_averages(
            short=TECHNICAL.get("ma_short", 5),
            mid=TECHNICAL.get("ma_mid", 20),
            long=TECHNICAL.get("ma_long", 60),
        )
        rsi = self.rsi(period=TECHNICAL.get("rsi_period", 14))
        macd = self.macd(
            fast=TECHNICAL.get("macd_fast", 12),
            slow=TECHNICAL.get("macd_slow", 26),
            signal_period=TECHNICAL.get("macd_signal", 9),
        )
        boll = self.bollinger_bands(period=TECHNICAL.get("bollinger_period", 20))
        atr = self.atr(period=TECHNICAL.get("atr_period", 14))
        sr = self.support_resistance()
        trend = self.trend_analysis()
        obv = self.obv()
        crossover = self.ma_crossover(short_period=5, long_period=20)
        divergence = self.detect_divergence()
        volume = self.volume_analysis()
        regime = self.detect_market_regime()

        return {
            "current_price": self.closes[-1],
            "moving_averages": ma,
            "rsi": rsi,
            "macd": macd,
            "bollinger": boll,
            "atr": atr,
            "support_resistance": sr,
            "trend": trend,
            "obv": obv,
            "ma_crossover": crossover,
            "divergence": divergence,
            "volume": volume,
            "market_regime": regime,
        }

    def compute_score(self) -> Tuple[float, str, Dict]:
        """
        计算技术面综合得分 (0-100)
        返回: (score, signal, details)
        """
        analysis = self.full_analysis()
        score = 50  # 基准分
        w = TECH_SCORE_WEIGHTS  # 从配置读取权重

        # 1. RSI — 超买超卖信号
        rsi_val = analysis["rsi"]["value"]
        max_rsi = w["rsi"]["max_bonus"]
        if rsi_val <= 20:
            score += max_rsi            # 极度超卖
        elif rsi_val <= 30:
            score += max_rsi * 0.7
        elif rsi_val <= 40:
            score += max_rsi * 0.3
        elif rsi_val >= 80:
            score -= max_rsi            # 极度超买
        elif rsi_val >= 70:
            score -= max_rsi * 0.7
        elif rsi_val >= 60:
            score -= max_rsi * 0.3

        # 2. MACD — 趋势动量
        macd = analysis["macd"]
        max_macd = w["macd"]["max_bonus"]
        if macd["trend"] == "bullish":
            score += max_macd
        elif macd["trend"] == "recovering":
            score += max_macd * 0.5
        elif macd["trend"] == "bearish":
            score -= max_macd
        elif macd["trend"] == "weakening":
            score -= max_macd * 0.5

        # 3. 布林带位置
        boll_pos = analysis["bollinger"]["position"]
        max_boll = w["bollinger"]["max_bonus"]
        if boll_pos <= 0.05:
            score += max_boll
        elif boll_pos <= 0.2:
            score += max_boll * 0.5
        elif boll_pos >= 0.95:
            score -= max_boll
        elif boll_pos >= 0.8:
            score -= max_boll * 0.5

        # 4. 均线趋势
        trend = analysis["trend"]
        max_trend = w["trend"]["max_bonus"]
        if trend["overall"] == "bullish":
            score += max_trend
        elif trend["overall"] == "bearish":
            score -= max_trend

        # 短期趋势
        max_short = w["short_trend"]["max_bonus"]
        if trend["short_trend"] == "up":
            score += max_short
        else:
            score -= max_short

        # 金叉/死叉信号
        cross = analysis["ma_crossover"]
        max_cross = w["crossover"]["max_bonus"]
        if cross["signal"] == "golden_cross":
            score += max_cross
        elif cross["signal"] == "death_cross":
            score -= max_cross

        # 5. 动量
        mom = trend["momentum_5d"]
        max_mom = w["momentum"]["max_bonus"]
        if mom > 3:
            score += max_mom
        elif mom > 1:
            score += max_mom * 0.4
        elif mom < -3:
            score -= max_mom
        elif mom < -1:
            score -= max_mom * 0.4

        # 6. 背离信号 — 强反转信号
        div = analysis["divergence"]
        max_div = w["divergence"]["max_bonus"]
        if div["signal"] == "bullish":
            score += max_div
        elif div["signal"] == "bearish":
            score -= max_div

        # 7. OBV量能
        obv = analysis["obv"]
        max_obv = w["obv"]["max_bonus"]
        if obv["trend"] == "bullish":
            score += max_obv
        elif obv["trend"] == "bearish":
            score -= max_obv

        # 8. 成交量分析
        vol = analysis["volume"]
        max_vol = w["volume"]["max_bonus"]
        if vol["trend"] == "bullish":
            score += max_vol
        elif vol["trend"] == "weak_bullish":
            score += max_vol * 0.4
        elif vol["trend"] == "bearish":
            score -= max_vol
        elif vol["trend"] == "weak_bearish":
            score -= max_vol * 0.4

        score = max(0, min(100, score))

        if score >= 70:
            signal = "🟢 强烈看多"
        elif score >= 60:
            signal = "🟢 看多"
        elif score >= 55:
            signal = "🟡 偏多"
        elif score >= 45:
            signal = "⚪ 中性"
        elif score >= 40:
            signal = "🟡 偏空"
        elif score >= 30:
            signal = "🔴 看空"
        else:
            signal = "🔴 强烈看空"

        return score, signal, analysis
