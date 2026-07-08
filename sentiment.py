# -*- coding: utf-8 -*-
"""
黄金投资助手 - 情绪与消息面分析模块
Gold Investment Assistant - Sentiment & News Analysis

分析市场情绪、资金流向、新闻因子等
支持 RSS 自动抓取新闻并基于关键词进行情绪打分。
所有阈值和权重从 config.py 读取。
"""

import re
import urllib.request
from typing import Dict, List, Tuple

from config import (
    KEYWORD_SENTIMENT, KEYWORD_SENTIMENT_EN, SENTIMENT, SENT_SCORE_THRESHOLDS,
    NEWS_SOURCES,
)
from utils import log


class SentimentAnalyzer:
    """
    市场情绪分析引擎
    
    通过市场数据（VIX、ETF流向、金银比、持仓变化等）评估市场情绪。
    """

    def __init__(self, market_data: Dict = None, gold_data: Dict = None,
                 news_factors: List[Dict] = None, skip_rss: bool = False):
        """
        Args:
            market_data: 市场数据 (VIX、原油、白银、标普等)
            gold_data: 黄金历史数据
            news_factors: 新闻情绪因子列表
                [{"text": "标题", "impact": -10~+10, "category": "fed/geo/econ/other"}]
            skip_rss: 跳过RSS自动抓取（用于回测等场景）
        """
        self.market_data = market_data or {}
        self.gold_data = gold_data or {}
        self.news_factors = news_factors or []
        self.skip_rss = skip_rss

    def analyze_vix_signal(self) -> Tuple[float, str, Dict]:
        """VIX恐慌指数信号"""
        vix_data = self.market_data.get("vix")
        if not vix_data:
            return 0, "中性", {"detail": "VIX数据不可用"}

        vix = vix_data.get("price", 20)
        vix_change = vix_data.get("change_pct", 0)

        score = 0
        factors = []

        if vix > 40:
            score = 3  # 极端恐慌，流动性危机可能伤害黄金
            factors.append(f"VIX极度恐慌({vix:.1f}) → 避险vs流动性危机")
        elif vix > 30:
            score = 10
            factors.append(f"VIX恐慌({vix:.1f}) → 强烈避险需求")
        elif vix > 25:
            score = 6
            factors.append(f"VIX偏高({vix:.1f}) → 避险情绪升温")
        elif vix < 15:
            score = -4
            factors.append(f"VIX极低({vix:.1f}) → 市场过度乐观")
        elif vix < 18:
            score = -2
            factors.append(f"VIX偏低({vix:.1f}) → 风险偏好较高")
        else:
            factors.append(f"VIX正常({vix:.1f})")

        # VIX剧烈波动
        if vix_change > 20:
            score += 5
            factors.append(f"VIX暴涨{vix_change:.1f}% → 恐慌急剧升温")
        elif vix_change < -15:
            score -= 3
            factors.append(f"VIX暴跌{vix_change:.1f}% → 恐慌缓解")

        score = max(-20, min(20, score))
        signal = "利多" if score >= 5 else "利空" if score <= -5 else "中性"
        return score, signal, {"vix": vix, "vix_change": vix_change, "factors": factors}

    def analyze_oil_signal(self) -> Tuple[float, str, Dict]:
        """原油信号（通胀传导）"""
        oil_data = self.market_data.get("oil")
        if not oil_data:
            return 0, "中性", {"detail": "原油数据不可用"}

        oil_price = oil_data.get("price", 75)
        oil_change = oil_data.get("change_pct", 0)

        score = 0
        factors = []

        if oil_price > 100:
            score = 5
            factors.append(f"油价偏高(${oil_price:.1f}) → 通胀压力推升黄金需求")
        elif oil_price > 85:
            score = 3
            factors.append(f"油价适中(${oil_price:.1f}) → 温和通胀支撑")
        elif oil_price < 60:
            score = -5
            factors.append(f"油价偏低(${oil_price:.1f}) → 通胀预期降温")

        if oil_change < -5:
            score -= 3
            factors.append(f"油价暴跌{oil_change:.1f}% → 通缩担忧")
        elif oil_change > 5:
            score += 3
            factors.append(f"油价暴涨{oil_change:.1f}% → 能源通胀升温")

        score = max(-20, min(20, score))
        signal = "利多" if score >= 5 else "利空" if score <= -5 else "中性"
        return score, signal, {"oil_price": oil_price, "oil_change": oil_change, "factors": factors}

    def analyze_gold_silver_ratio(self) -> Tuple[float, str, Dict]:
        """金银比分析"""
        silver_data = self.market_data.get("silver")
        gold_data = self.gold_data

        if not silver_data or not gold_data:
            return 0, "中性", {"detail": "数据不足"}

        silver_price = silver_data.get("price", 0)
        gold_price = gold_data.get("current", 0)

        if silver_price <= 0 or gold_price <= 0:
            return 0, "中性", {"detail": "价格异常"}

        ratio = gold_price / silver_price
        score = 0
        factors = []

        if ratio > 90:
            score = 8
            factors.append(f"金银比极高({ratio:.1f}) → 贵金属板块可能被低估")
        elif ratio > 80:
            score = 4
            factors.append(f"金银比偏高({ratio:.1f}) → 白银相对被低估")
        elif ratio < 50:
            score = -5
            factors.append(f"金银比极低({ratio:.1f}) → 黄金相对被高估")
        elif ratio < 60:
            score = -2
            factors.append(f"金银比偏低({ratio:.1f}) → 黄金相对偏贵")
        else:
            factors.append(f"金银比正常({ratio:.1f})")

        score = max(-20, min(20, score))
        signal = "利多" if score >= 5 else "利空" if score <= -5 else "中性"
        return score, signal, {"ratio": round(ratio, 1), "factors": factors}

    @staticmethod
    def _fetch_rss(url: str) -> List[str]:
        """抓取 RSS 并提取标题"""
        timeout = SENTIMENT["rss_timeout"]
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content = resp.read().decode("utf-8", errors="replace")
            # 提取 <title> 标签内容
            titles = re.findall(r"<title>(.*?)</title>", content, re.DOTALL)
            # 过滤 RSS 频道标题（通常第一个）
            return [t.strip() for t in titles[1:] if t.strip()]
        except Exception:
            return []

    @classmethod
    def fetch_news_from_rss(cls, max_per_source: int = None) -> List[Dict]:
        """从新闻源自动抓取新闻并基于关键词打分"""
        if max_per_source is None:
            max_per_source = SENTIMENT["rss_max_per_source"]
        news_factors = []
        for source in NEWS_SOURCES:
            try:
                if source.get("type") == "sina_api":
                    titles = cls._fetch_sina_news(source)
                elif source.get("type") == "html_parse":
                    titles = cls._fetch_html_news(source)
                else:
                    titles = cls._fetch_rss(source["url"])
                for title in titles[:max_per_source]:
                    impact, category = cls._score_text(title)
                    # 保留所有与金融/经济相关的新闻，不仅仅是情绪强烈的
                    if impact != 0 or cls._is_financial_news(title):
                        news_factors.append({
                            "text": f"[{source['name']}] {title}",
                            "impact": impact,
                            "category": category,
                        })
            except Exception as e:
                log.debug(f"新闻源 {source['name']} 获取失败: {e}")
        return news_factors

    @classmethod
    def _is_financial_news(cls, text: str) -> bool:
        """判断是否为财经新闻（含经济、金融、市场、政策等关键词）"""
        financial_keywords = [
            "经济", "金融", "市场", "股市", "债市", "汇市", "期货", "原油", "美元",
            "美联储", "央行", "利率", "通胀", "GDP", "CPI", "PPI", "就业", "失业",
            "贸易", "关税", "制裁", "政策", "财政", "货币", "银行", "保险", "基金",
            "投资", "融资", "并购", "上市", "财报", "业绩", "盈利", "亏损",
            "增长", "下降", "上涨", "下跌", "反弹", "回调", "震荡", "盘整",
            "企业", "公司", "集团", "行业", "板块", "龙头", "概念",
            "中国", "美国", "欧洲", "日本", "英国", "德国", "法国",
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in financial_keywords)

    @classmethod
    def _fetch_sina_news(cls, source: Dict) -> List[str]:
        """从新浪API获取新闻标题"""
        import urllib.request
        import json
        try:
            req = urllib.request.Request(
                source["url"],
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=SENTIMENT["rss_timeout"]) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("result", {}).get("data", [])
                return [item.get("title", "") for item in items if item.get("title")]
        except Exception:
            return []

    @classmethod
    def _fetch_html_news(cls, source: Dict) -> List[str]:
        """从HTML页面解析新闻标题"""
        import urllib.request
        import re
        try:
            req = urllib.request.Request(
                source["url"],
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=SENTIMENT["rss_timeout"]) as resp:
                html = resp.read().decode("utf-8", errors="replace")
                # 根据selector提取标题
                selector = source.get("selector", "a")
                # 简单的正则提取
                pattern = r'<a[^>]*href=["\']([^"\']*)["\'][^>]*>([^<]{10,})</a>'
                matches = re.findall(pattern, html)
                titles = []
                domain = source.get("domain", "")
                for href, title in matches:
                    # 过滤掉导航链接等
                    if len(title) > 15 and len(title) < 100:
                        # 去除空白字符
                        title_clean = re.sub(r'\s+', '', title)
                        titles.append(title_clean)
                return titles[:20]
        except Exception:
            return []

    @classmethod
    def _score_text(cls, text: str) -> Tuple[int, str]:
        """基于关键词词典对文本进行情绪打分（支持中英文）"""
        text_lower = text.lower()
        total_score = 0
        matched_count = 0

        # 中文关键词匹配（单字/词）
        for keyword, score in KEYWORD_SENTIMENT.items():
            if keyword in text_lower:
                total_score += score
                matched_count += 1

        # 英文关键词匹配（支持短语）
        for keyword, score in KEYWORD_SENTIMENT_EN.items():
            if keyword in text_lower:
                total_score += score
                matched_count += 1

        # 如果没有匹配到关键词，返回中性
        if matched_count == 0:
            return 0, "other"

        # 根据分数确定类别
        if total_score > 0:
            category = "bullish"
        elif total_score < 0:
            category = "bearish"
        else:
            category = "other"

        # 限制单条新闻影响范围在 -10 ~ +10
        impact = max(-10, min(10, total_score))
        return impact, category

    def analyze_news_sentiment(self) -> Tuple[float, str, Dict]:
        """
        新闻情绪分析
        优先使用传入的 news_factors，若为空则自动从国内/国际新闻源抓取
        """
        factors = self.news_factors or []

        # 如果没有手动提供新闻，尝试自动抓取（除非跳过）
        if not factors and not self.skip_rss:
            log.info("未提供新闻因子，尝试从新闻源自动抓取...")
            factors = self.fetch_news_from_rss()
            if factors:
                log.info(f"从新闻源抓取到 {len(factors)} 条相关新闻")
            else:
                log.warning("所有新闻源获取失败，情绪分析仅基于市场数据")

        if not factors:
            # 没有新闻数据时，返回中性而非假数据
            return 0, "中性", {
                "detail": "未获取到新闻数据，情绪分析仅基于VIX/原油/金银比",
                "total_news": 0,
                "factors": [],
            }

        total_impact = 0
        category_scores = {}
        factor_texts = []

        for nf in factors:
            impact = nf.get("impact", 0)
            category = nf.get("category", "other")
            text = nf.get("text", "")

            total_impact += impact
            if category not in category_scores:
                category_scores[category] = []
            category_scores[category].append(impact)

            direction = "利多" if impact > 0 else "利空" if impact < 0 else "中性"
            factor_texts.append(f"[{direction}] {text[:60]}")

        cat_summary = {}
        for cat, scores in category_scores.items():
            avg = sum(scores) / len(scores) if scores else 0
            cat_summary[cat] = round(avg, 2)

        avg_impact = total_impact / len(factors)
        score = max(-20, min(20, round(avg_impact, 1)))
        signal = "利多" if score >= 5 else "利空" if score <= -5 else "中性"

        return score, signal, {
            "total_news": len(factors),
            "avg_impact": round(avg_impact, 2),
            "category_scores": cat_summary,
            "factors": factor_texts[:10],
        }

    def full_analysis(self) -> Dict:
        """执行完整情绪分析"""
        vix_score, vix_signal, vix_detail = self.analyze_vix_signal()
        oil_score, oil_signal, oil_detail = self.analyze_oil_signal()
        gs_score, gs_signal, gs_detail = self.analyze_gold_silver_ratio()
        news_score, news_signal, news_detail = self.analyze_news_sentiment()

        return {
            "vix": {"score": vix_score, "signal": vix_signal, **vix_detail},
            "oil": {"score": oil_score, "signal": oil_signal, **oil_detail},
            "gold_silver_ratio": {"score": gs_score, "signal": gs_signal, **gs_detail},
            "news": {"score": news_score, "signal": news_signal, **news_detail},
        }

    def compute_score(self) -> Tuple[float, str, Dict]:
        """计算情绪面综合得分 (0-100)"""
        analysis = self.full_analysis()

        # 从配置读取内部维度权重（百分比，总计 = 1.0）
        w = SENTIMENT["dim_weights"]
        scale = SENTIMENT["score_scale"]

        # 使用百分比权重计算加权得分
        total = (
            analysis["vix"]["score"] * w["vix"] +
            analysis["oil"]["score"] * w["oil"] +
            analysis["gold_silver_ratio"]["score"] * w["gold_silver_ratio"] +
            analysis["news"]["score"] * w["news"]
        )

        score = 50 + total * scale
        score = max(0, min(100, score))

        # 从配置读取信号阈值
        t = SENT_SCORE_THRESHOLDS
        if score >= t["bullish"]:
            signal = "🟢 情绪偏多"
        elif score >= t["neutral"]:
            signal = "🟡 情绪中性偏多"
        elif score >= t["bearish"]:
            signal = "🟡 情绪中性偏空"
        else:
            signal = "🔴 情绪偏空"

        return score, signal, analysis
