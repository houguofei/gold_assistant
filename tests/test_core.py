# -*- coding: utf-8 -*-
"""
黄金投资助手 - 核心模块单元测试
Gold Investment Assistant - Core Module Unit Tests

测试技术分析、评分引擎、情绪分析等核心模块的功能正确性。
"""

import sys
import os
import math

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from technical import TechnicalAnalyzer
from scoring import ScoringEngine
from config import TECH_SCORE_WEIGHTS


# ============================================================
# 技术分析模块测试
# ============================================================

def test_sma():
    """测试简单移动平均线"""
    data = [10.0, 20.0, 30.0, 40.0, 50.0]
    result = TechnicalAnalyzer._sma(data, 3)
    # 前2个应该为None
    assert result[0] is None
    assert result[1] is None
    # 从第3个开始计算
    assert abs(result[2] - 20.0) < 0.001  # (10+20+30)/3 = 20
    assert abs(result[3] - 30.0) < 0.001  # (20+30+40)/3 = 30
    assert abs(result[4] - 40.0) < 0.001  # (30+40+50)/3 = 40
    print("[PASS] test_sma")


def test_ema():
    """测试指数移动平均线"""
    data = [10.0, 20.0, 30.0, 40.0, 50.0]
    result = TechnicalAnalyzer._ema(data, 3)
    # 前2个应该为None
    assert result[0] is None
    assert result[1] is None
    # 第3个是SMA初始化
    assert abs(result[2] - 20.0) < 0.001
    # 第4个: EMA = (40 - 20) * (2/4) + 20 = 30
    assert abs(result[3] - 30.0) < 0.001
    print("[PASS] test_ema")


def test_rsi():
    """测试RSI计算"""
    # 创建一个简单的上涨趋势
    closes = [100.0, 102.0, 104.0, 106.0, 108.0, 110.0]
    analyzer = TechnicalAnalyzer(closes, closes, closes)
    rsi_result = analyzer.rsi(period=3)
    rsi = rsi_result.get("value", 50)
    # RSI应该接近100（全涨）
    assert rsi > 90, f"RSI应该>90，实际={rsi}"
    print("[PASS] test_rsi")


def test_bollinger():
    """测试布林带计算"""
    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0]
    analyzer = TechnicalAnalyzer(closes, closes, closes)
    boll = analyzer.bollinger_bands(period=5)
    assert "upper" in boll
    assert "middle" in boll
    assert "lower" in boll
    assert boll["upper"] > boll["middle"] > boll["lower"]
    print("[PASS] test_bollinger")


def test_macd():
    """测试MACD计算"""
    closes = [100.0] * 50  # 常量数据
    analyzer = TechnicalAnalyzer(closes, closes, closes)
    macd = analyzer.macd()
    assert "macd" in macd
    assert "signal" in macd
    assert "histogram" in macd
    # 常量数据下，MACD应该接近0
    assert abs(macd["macd"]) < 1.0
    print("[PASS] test_macd")


# ============================================================
# 评分引擎模块测试
# ============================================================

def test_scoring_engine():
    """测试三维度评分引擎"""
    tech_score = 75.0
    fund_score = 60.0
    sent_score = 55.0

    engine = ScoringEngine()
    result = engine.compute_final_score(tech_score, fund_score, sent_score)

    assert "final_score" in result
    assert "signal" in result
    assert "dimension_scores" in result
    assert result["dimension_scores"]["technical"] == 75.0
    assert result["dimension_scores"]["fundamental"] == 60.0
    assert result["dimension_scores"]["sentiment"] == 55.0
    # 检查分数在合理范围（50-80之间）
    assert 50 <= result["final_score"] <= 80, f"分数应在50-80之间，实际={result['final_score']}"
    # 检查权重已归一化（总和为100%）
    assert "weights_used" in result
    weights_sum = sum(result["weights_used"].values())
    assert abs(weights_sum - 100) < 1.0, f"权重之和应为100，实际={weights_sum}"
    print("[PASS] test_scoring_engine")


def test_scoring_extreme():
    """测试极端分数"""
    engine = ScoringEngine()
    
    # 极端高分
    result = engine.compute_final_score(95.0, 95.0, 95.0)
    assert result["final_score"] > 85
    assert result["signal"] == "强烈看多"

    # 极端低分
    result = engine.compute_final_score(10.0, 10.0, 10.0)
    assert result["final_score"] < 20
    assert result["signal"] == "强烈看空"
    print("[PASS] test_scoring_extreme")


# ============================================================
# 配置模块测试
# ============================================================

def test_config_weights():
    """测试配置权重"""
    # 检查技术面评分权重
    assert "rsi" in TECH_SCORE_WEIGHTS
    assert "macd" in TECH_SCORE_WEIGHTS
    assert "bollinger" in TECH_SCORE_WEIGHTS
    assert "trend" in TECH_SCORE_WEIGHTS
    # 检查每个权重都有max_bonus
    for key, val in TECH_SCORE_WEIGHTS.items():
        assert "max_bonus" in val, f"{key} 缺少 max_bonus"
        assert isinstance(val["max_bonus"], (int, float)), f"{key} max_bonus 应为数值"
    print("[PASS] test_config_weights")


# ============================================================
# 工具函数测试
# ============================================================

def test_utils():
    """测试工具函数"""
    from utils import safe_float, safe_int, clamp

    # safe_float
    assert safe_float("42.5", 0) == 42.5
    assert safe_float("abc", 0) == 0
    assert safe_float(None, -1) == -1

    # safe_int
    assert safe_int("42", 0) == 42
    assert safe_int("abc", 0) == 0

    # clamp
    assert clamp(5, 0, 10) == 5
    assert clamp(-5, 0, 10) == 0
    assert clamp(15, 0, 10) == 10

    print("[PASS] test_utils")


# ============================================================
# 运行所有测试
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("黄金投资助手 - 单元测试")
    print("=" * 50)
    print()

    test_sma()
    test_ema()
    test_rsi()
    test_bollinger()
    test_macd()
    test_scoring_engine()
    test_scoring_extreme()
    test_config_weights()
    test_utils()

    print()
    print("=" * 50)
    print("[ALL PASS] 所有测试通过!")
    print("=" * 50)
