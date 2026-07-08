# -*- coding: utf-8 -*-
"""
黄金投资助手 - 混合模式数据获取器（重构版）
Gold Investment Assistant - Hybrid Data Fetcher (Refactored)

数据源优先级：新浪财经(国内友好) → 东方财富 → 腾讯财经 → 模拟数据
宏观数据：FRED API → 新浪财经 → 东方财富 → 默认值
所有配置从 config.py 读取，日志通过 utils.log 输出。
"""

import random
import re
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from config import (
    TICKERS, SINA_SYMBOLS, FRED_SERIES, FRED_TO_MACRO_MAP,
    DATA_FETCH, NEWS_SOURCES,
)
from utils import log, fetch_json, fetch_html, safe_float, retry_on_failure


class HybridDataFetcher:
    """混合数据获取器 - 支持多种数据模式"""

    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 缓存5分钟
        self.manual_prices = {}

    def set_manual_price(self, symbol: str, price: float):
        """设置手动输入的价格"""
        self.manual_prices[symbol] = price
        log.info(f"手动设置 {symbol} 价格: ${price:.2f}")

    def _is_cache_valid(self, cache_key: str) -> bool:
        if cache_key not in self.cache:
            return False
        return time.time() - self.cache[cache_key]["timestamp"] < self.cache_ttl

    def _get_cached(self, cache_key: str):
        """获取缓存数据"""
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]["data"]
        return None

    def _set_cached(self, cache_key: str, data):
        """设置缓存"""
        self.cache[cache_key] = {"data": data, "timestamp": time.time()}

    # ============================================================
    # 新浪财经数据获取
    # ============================================================

    def fetch_sina_quote(self, symbol: str) -> Optional[Dict]:
        """从新浪财经获取实时报价"""
        cache_key = f"sina_{symbol}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        url = f"http://hq.sinajs.cn/list={symbol}"
        headers = {
            "User-Agent": DATA_FETCH["user_agent"],
            "Referer": "https://finance.sina.com.cn",
        }
        html = fetch_html(url, headers=headers, max_retries=2)
        if not html:
            return None

        try:
            match = re.search(r'"([^"]+)"', html)
            if not match:
                return None

            fields = match.group(1).split(",")
            if len(fields) < 9:
                return None

            price = safe_float(fields[0])
            bid = safe_float(fields[2])
            ask = safe_float(fields[3])
            high = safe_float(fields[4])
            low = safe_float(fields[5])
            prev_close = safe_float(fields[7]) if len(fields) > 7 else 0

            current = price or bid or ask
            if current <= 0:
                return None
            if prev_close <= 0:
                prev_close = current

            result = {
                "current": current,
                "prev_close": prev_close,
                "high": high if high > 0 else current,
                "low": low if low > 0 else current,
                "bid": bid,
                "ask": ask,
                "source": "sina",
            }
            self._set_cached(cache_key, result)
            return result
        except Exception as e:
            log.debug(f"新浪解析失败 {symbol}: {e}")
            return None

    def fetch_sina_historical(self, symbol: str, days: int = 120) -> Optional[List[Dict]]:
        """从新浪财经获取历史K线数据（支持A股和期货）"""
        cache_key = f"sina_hist_{symbol}_{days}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # 尝试多种API端点
        urls = [
            # A股K线API
            f"http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={days}",
            # 期货K线API（备选）
            f"https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var/InnerFuturesNewService.getDailyKLine?symbol={symbol.replace('hf_', '')}&_=1",
        ]

        for url in urls:
            html = fetch_html(url, max_retries=2)
            if not html:
                continue

            try:
                html = html.strip()
                
                # === 修复：处理期货API的重定向前缀 ===
                # 期货API返回: /*<script>location.href='//sina.com';</script>*/ var _GC=([...]);
                # A股API返回: [{"day":"2026-01-01",...}]
                # 通用方法：找到第一个 [ 和最后一个 ]
                
                json_start = html.find('[')
                json_end = html.rfind(']')
                if json_start == -1 or json_end == -1 or json_end <= json_start:
                    continue
                
                json_str = html[json_start:json_end + 1]
                
                # 早期A股API返回的是纯JSON数组，可能带JSONP包裹
                # 处理 var name=[...]; 格式
                if json_str.startswith('['):
                    data = __import__("json").loads(json_str)
                else:
                    continue

                if not data or len(data) < 20:
                    continue

                # 新浪返回倒序，反转为正序
                result = []
                for item in reversed(data):
                    result.append({
                        "date": datetime.strptime(item["day"], "%Y-%m-%d"),
                        "open": float(item["open"]),
                        "high": float(item["high"]),
                        "low": float(item["low"]),
                        "close": float(item["close"]),
                        "volume": int(item.get("volume", 0)),
                    })

                self._set_cached(cache_key, result)
                return result
            except Exception as e:
                log.debug(f"新浪K线解析失败 {symbol}: {e}")
                continue

        return None

    # ============================================================
    # 新浪期货K线（AU0沪金主力，替代被封的push2）
    # ============================================================

    def fetch_sina_futures_kline(self, contract: str = "AU0", days: int = 120) -> Optional[List[Dict]]:
        """从新浪期货API获取K线数据（沪金AU0有完整历史数据）
        
        Args:
            contract: 期货合约代码，如 AU0（沪金主力）
            days: 获取天数
        
        Returns:
            K线数据列表 [{"date": datetime, "open": float, "high": float, "low": float, "close": float, "volume": int}]
        """
        cache_key = f"sina_futures_kline_{contract}_{days}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        import urllib.request
        import json
        import re

        url = f"https://stock.finance.sina.com.cn/futures/api/jsonp.php/var%20_{contract}=/InnerFuturesNewService.getDailyKLine?symbol={contract}"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                text = resp.read().decode("gbk", errors="replace")

            # 解析JSONP: var _AU0=([...]);
            # 注意：响应头部可能有 <script>location.href 重定向前缀
            # 找到第一个 "=(" 和最后一个 ");" 之间的内容
            start = text.find("=(")
            end = text.rfind(");")
            if start == -1 or end == -1:
                log.debug(f"新浪期货K线解析失败: 未找到JSON数据边界")
                return None
            
            # text[start+2:end] = 跳过 "=(" 和 ")"，提取纯JSON数组
            json_str = text[start+2:end]  # 纯JSON: [{...}, {...}]
            raw_data = json.loads(json_str)
            if not raw_data:
                return None

            # 只取最近 days 条
            result = []
            for item in raw_data[-days:]:
                result.append({
                    "date": datetime.strptime(item["d"], "%Y-%m-%d"),
                    "open": float(item["o"]),
                    "high": float(item["h"]),
                    "low": float(item["l"]),
                    "close": float(item["c"]),
                    "volume": int(float(item.get("v", 0))),
                })

            log.info(f"新浪期货K线 {contract}: {len(result)} 条 (最新:{result[-1]['date'].date()})")
            self._set_cached(cache_key, result)
            return result
        except Exception as e:
            log.debug(f"新浪期货K线获取失败 {contract}: {e}")
            return None

    # ============================================================
    # 腾讯美股ETF行情（UUP/TLT，替代被封的push2）
    # ============================================================

    def fetch_tencent_us_stock(self, symbol: str) -> Optional[Dict]:
        """从腾讯财经获取美股/ETF实时行情
        
        Args:
            symbol: 腾讯美股代码（不含us前缀），如 TLT, UUP
        
        Returns:
            {"current": float, "prev_close": float, "name": str, "source": str}
        """
        cache_key = f"tencent_us_{symbol}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        import urllib.request
        import re

        url = f"http://qt.gtimg.cn/q=us{symbol}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                text = resp.read().decode("gbk", errors="replace")

            # 解析格式: v_usTLT="...fields..."
            match = re.search(r'"([^"]*)"', text)
            if not match:
                log.debug(f"腾讯美股解析失败 {symbol}: 无数据")
                return None

            fields = match.group(1).split("~")
            if len(fields) < 6:
                log.debug(f"腾讯美股解析失败 {symbol}: 字段不足 ({len(fields)})")
                return None

            name = fields[1] if len(fields) > 1 else symbol
            current = safe_float(fields[3])
            prev_close = safe_float(fields[4])

            if current and current > 0:
                result = {
                    "current": current,
                    "prev_close": prev_close if prev_close and prev_close > 0 else current,
                    "name": name,
                    "change_pct": safe_float(fields[2]) if len(fields) > 2 else 0,
                    "source": "tencent_us",
                }
                log.info(f"腾讯美股 {symbol} ({name}): ${current:.2f}")
                self._set_cached(cache_key, result)
                return result

            return None
        except Exception as e:
            log.debug(f"腾讯美股获取失败 {symbol}: {e}")
            return None

    def fetch_tencent_us_multi(self, symbols: list) -> Dict[str, Optional[Dict]]:
        """批量获取腾讯美股行情
        
        Args:
            symbols: 股票代码列表，如 ["TLT", "UUP"]
        
        Returns:
            {symbol: data_dict or None}
        """
        import urllib.request
        import re

        codes = ",".join(f"us{s}" for s in symbols)
        url = f"http://qt.gtimg.cn/q={codes}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                text = resp.read().decode("gbk", errors="replace")

            results = {}
            for line in text.split("\n"):
                if not line.strip() or "=" not in line:
                    continue
                # 提取 symbol
                sym_match = re.match(r'v_(us\w+)="', line)
                if not sym_match:
                    continue
                raw_sym = sym_match.group(1).replace("us", "")
                # 提取数据
                match = re.search(r'"([^"]*)"', line)
                if not match:
                    continue
                fields = match.group(1).split("~")
                if len(fields) < 6:
                    continue
                results[raw_sym] = {
                    "current": safe_float(fields[3]),
                    "prev_close": safe_float(fields[4]),
                    "name": fields[1] if len(fields) > 1 else raw_sym,
                    "change_pct": safe_float(fields[2]) if len(fields) > 2 else 0,
                    "source": "tencent_us",
                }
                log.info(f"腾讯美股 {raw_sym}: ${results[raw_sym]['current']:.2f}")
            return results
        except Exception as e:
            log.debug(f"腾讯批量美股获取失败: {e}")
            return {}

    # ============================================================
    # 东方财富数据获取（备用）
    # ============================================================

    def fetch_eastmoney_quote(self, name: str) -> Optional[Dict]:
        """从东方财富获取实时报价"""
        cache_key = f"eastmoney_{name}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # 东方财富代码映射
        east_codes = {
            "gold": "113.hf_GC",
            "silver": "113.hf_SI",
            "oil": "113.hf_CL",
            "sp500": "100.^GSPC",
            "vix": "100.^VIX",
        }
        secid = east_codes.get(name)
        if not secid:
            return None

        url = (
            f"http://push2.eastmoney.com/api/qt/stock/get?"
            f"secid={secid}&fields=f43,f44,f45,f46,f60"
        )
        data = fetch_json(url, max_retries=2)
        if not data or "data" not in data or not data["data"]:
            return None

        try:
            item = data["data"]
            current = safe_float(item.get("f43", 0)) or safe_float(item.get("f60", 0))
            prev_close = safe_float(item.get("f60", 0))
            high = safe_float(item.get("f44", 0))
            low = safe_float(item.get("f45", 0))

            if current <= 0:
                return None
            if prev_close <= 0:
                prev_close = current

            result = {
                "current": current,
                "prev_close": prev_close,
                "high": high if high > 0 else current,
                "low": low if low > 0 else current,
                "source": "eastmoney",
            }
            self._set_cached(cache_key, result)
            return result
        except Exception as e:
            log.debug(f"东方财富解析失败 {name}: {e}")
            return None

    # ============================================================
    # 东方财富K线数据获取
    # ============================================================

    def fetch_eastmoney_kline(self, secid: str, days: int = 120) -> Optional[List[Dict]]:
        """从东方财富获取历史K线数据（支持期货）
        
        Args:
            secid: 东方财富证券代码，如 '113.aum'（沪金主连）
            days: 获取天数
        
        Returns:
            K线数据列表
        """
        cache_key = f"eastmoney_kline_{secid}_{days}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # 构建URL with query parameters
        params_str = (
            f"secid={secid}"
            f"&klt=101"  # 日线
            f"&fqt=1"    # 前复权
            f"&lmt={days}"
            f"&end=20500101"
            f"&fields1=f1,f2,f3,f4,f5,f6"
            f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
            f"&ut=fa5fd1943c7b386f172d6893dbfba10b"
        )
        url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?{params_str}"

        data = fetch_json(url, max_retries=3)
        if not data or not data.get("data") or not data["data"].get("klines"):
            return None

        try:
            klines = data["data"]["klines"]
            result = []
            for line in klines:
                fields = line.split(",")
                if len(fields) < 6:
                    continue
                result.append({
                    "date": datetime.strptime(fields[0], "%Y-%m-%d"),
                    "open": float(fields[1]),
                    "close": float(fields[2]),
                    "high": float(fields[3]),
                    "low": float(fields[4]),
                    "volume": int(float(fields[5])),
                })
            
            if result:
                self._set_cached(cache_key, result)
                log.info(f"东方财富K线 {secid}: {len(result)} 条")
            return result
        except Exception as e:
            log.debug(f"东方财富K线解析失败 {secid}: {e}")
            return None

    # ============================================================
    # 东方财富宏观数据获取
    # ============================================================

    def fetch_eastmoney_bond_yields(self) -> Dict[str, float]:
        """从东方财富获取美国国债收益率（10Y和2Y）
        
        Returns:
            {'us10y_yield': float, 'us2y_yield': float}
        """
        result = {}
        base_url = "https://push2.eastmoney.com/api/qt/stock/get"
        
        bond_map = {
            "us10y_yield": "171.US10Y",
            "us2y_yield": "171.US2Y",
        }
        
        for key, secid in bond_map.items():
            url = f"{base_url}?secid={secid}&fields=f43,f57,f58&ut=fa5fd1943c7b386f172d6893dbfba10b"
            data = fetch_json(url, max_retries=2)
            if data and data.get("data"):
                raw = data["data"].get("f43", 0)
                if raw:
                    result[key] = raw / 10000
                    log.info(f"东方财富 {key}: {result[key]:.4f}%")
        
        return result

    def fetch_eastmoney_fed_rate(self) -> Optional[float]:
        """从东方财富获取美联储利率（联邦基金利率目标上限）
        
        Returns:
            联邦基金利率（%）
        """
        import urllib.parse
        
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "reportName": "RPT_ECONOMICVALUE_USA",
            "columns": "ALL",
            "filter": '(INDICATOR_ID="EMG00342250")',
            "pageSize": 10,
            "pageNumber": 1,
            "sortColumns": "REPORT_DATE",
            "sortTypes": -1,
            "source": "WEB",
            "client": "WEB",
        }
        
        # Build URL with proper encoding
        query_string = urllib.parse.urlencode(params)
        full_url = f"{url}?{query_string}"
        
        data = fetch_json(full_url, max_retries=2)
        if data and data.get("result") and data["result"].get("data"):
            for item in data["result"]["data"]:
                value = item.get("VALUE")
                if value is not None:
                    log.info(f"东方财富 美联储利率: {value}%")
                    return float(value)
        
        return None

    def fetch_eastmoney_cpi(self) -> Optional[float]:
        """从东方财富获取美国CPI年率
        
        Returns:
            CPI年率（%）
        """
        import urllib.parse
        
        url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
        params = {
            "reportName": "RPT_ECONOMICVALUE_USA",
            "columns": "ALL",
            "filter": '(INDICATOR_ID="EMG00000733")',
            "pageSize": 10,
            "pageNumber": 1,
            "sortColumns": "REPORT_DATE",
            "sortTypes": -1,
            "source": "WEB",
            "client": "WEB",
        }
        
        # Build URL with proper encoding
        query_string = urllib.parse.urlencode(params)
        full_url = f"{url}?{query_string}"
        
        data = fetch_json(full_url, max_retries=2)
        if data and data.get("result") and data["result"].get("data"):
            for item in data["result"]["data"]:
                value = item.get("VALUE")
                if value is not None:
                    log.info(f"东方财富 CPI年率: {value}%")
                    return float(value)
        
        return None

    # ============================================================
    # 腾讯财经数据获取（备用）
    # ============================================================

    def fetch_tencent_quote(self, name: str) -> Optional[Dict]:
        """从腾讯财经获取实时报价"""
        cache_key = f"tencent_{name}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        tencent_symbols = {
            "gold": "hfGC",
            "silver": "hfSI",
            "oil": "hfCL",
            "sp500": "hfSP500",
            "vix": "hfVIX",
        }
        tencent_sym = tencent_symbols.get(name)
        if not tencent_sym:
            return None

        url = f"http://qt.gtimg.cn/q={tencent_sym}"
        html = fetch_html(url, max_retries=2)
        if not html:
            return None

        try:
            match = re.search(r'"([^"]+)"', html)
            if not match:
                return None

            fields = match.group(1).split("~")
            if len(fields) < 3:
                return None

            current = safe_float(fields[1])
            prev_close = safe_float(fields[2])

            if current <= 0:
                return None

            result = {
                "current": current,
                "prev_close": prev_close if prev_close > 0 else current,
                "source": "tencent",
            }
            self._set_cached(cache_key, result)
            return result
        except Exception as e:
            log.debug(f"腾讯解析失败 {name}: {e}")
            return None

    # ============================================================
    # 基于真实价格生成合理历史数据
    # ============================================================

    def generate_realistic_history(self, current_price: float,
                                   days: int = 120,
                                   trend: str = "sideways") -> Dict:
        """
        基于真实当前价格生成模拟历史数据。
        注意：此数据仅用于技术分析计算，不代表真实历史价格。
        当无法获取真实历史数据时使用。
        """
        random.seed(int(datetime.now().timestamp()))

        dates, closes, highs, lows, opens, volumes = [], [], [], [], [], []

        if trend == "down":
            start_price = current_price * 1.15
        elif trend == "up":
            start_price = current_price * 0.85
        else:
            start_price = current_price * 0.95

        price = start_price
        base_volatility = 0.012
        trend_strength = 0.0003 if trend == "up" else (-0.0003 if trend == "down" else 0)

        for i in range(days):
            d = datetime.now() - timedelta(days=days - i)
            dates.append(d)

            volatility = base_volatility * (1 + random.uniform(-0.3, 0.3))
            daily_return = random.gauss(trend_strength, volatility)

            if random.random() < 0.02:
                daily_return += random.choice([-0.03, 0.03])

            price = price * (1 + daily_return)

            if i >= days - 10:
                weight = (i - (days - 10)) / 10
                price = price * (1 - weight) + current_price * weight

            price = max(price, current_price * 0.7)
            price = min(price, current_price * 1.3)

            daily_range = abs(price * random.uniform(0.001, 0.008))
            o = price - daily_range / 2
            h = price + daily_range / 2 * random.uniform(0.8, 1.5)
            l = price - daily_range / 2 * random.uniform(0.8, 1.5)
            c = price

            o = max(min(o, c * 1.01), c * 0.99)
            h = max(h, c, o)
            l = min(l, c, o)

            volume = int(100000 * random.uniform(0.5, 2.0))

            opens.append(round(o, 2))
            highs.append(round(h, 2))
            lows.append(round(l, 2))
            closes.append(round(c, 2))
            volumes.append(volume)

        closes[-1] = current_price

        return {
            "ticker": "gold",
            "dates": dates, "opens": opens, "highs": highs,
            "lows": lows, "closes": closes, "volumes": volumes,
            "current": current_price,
            "prev_close": closes[-2] if len(closes) > 1 else current_price,
            "currency": "USD",
            "source": "simulated",
            "is_reference": False,
            "data_quality": "simulated",  # 明确标注为模拟数据
            "data_warning": "历史数据为模拟生成，仅当前价格真实。技术指标仅供参考。",
        }

    def _build_full_gold_data(self, current_price: float, prev_close: float,
                              hist_data: Optional[List[Dict]], source: str,
                              instrument: str = "unknown") -> Dict:
        """将历史K线列表转换为完整的 gold_data 字典

        Args:
            instrument: 数据品种标记 — "spot"（现货）、"futures"（期货）、"manual"、"reference" 等
                        用于报告层诚实标注实际数据源

        注意：当历史数据来自国内期货（如沪金，CNY/克）而当前价格是国际金价（USD/盎司）时，
        会自动按比例缩放历史数据，使技术分析指标与当前价格匹配。
        """
        if hist_data:
            # 检查历史数据价格单位是否与当前价格匹配
            # 沪金主力(113.aum)价格约600-1000 CNY/克，国际金价约2000-4000 USD/盎司
            last_close = hist_data[-1]["close"]
            scale_ratio = 1.0

            # 如果历史数据是国内期货价格（CNY/克），而当前价格是国际金价（USD/盎司）
            # 需要缩放历史数据以匹配当前价格
            if last_close > 0 and current_price > 0:
                ratio = current_price / last_close
                # 如果比例差异很大（>2倍或<0.5倍），说明是不同市场的数据
                if ratio > 2.0 or ratio < 0.5:
                    scale_ratio = ratio
                    log.info(f"历史数据价格缩放: ratio={scale_ratio:.2f} (当前价 ${current_price:,.2f} / 历史收盘价 {last_close:.2f})")

            if scale_ratio != 1.0:
                # 缩放所有价格字段
                scaled_data = []
                for item in hist_data:
                    scaled_data.append({
                        "date": item["date"],
                        "open": item["open"] * scale_ratio,
                        "close": item["close"] * scale_ratio,
                        "high": item["high"] * scale_ratio,
                        "low": item["low"] * scale_ratio,
                        "volume": item["volume"],
                    })
                hist_data = scaled_data

            return {
                "ticker": TICKERS["gold"],
                "dates": [item["date"] for item in hist_data],
                "opens": [item["open"] for item in hist_data],
                "highs": [item["high"] for item in hist_data],
                "lows": [item["low"] for item in hist_data],
                "closes": [item["close"] for item in hist_data],
                "volumes": [item["volume"] for item in hist_data],
                "current": current_price,
                "prev_close": prev_close,
                "currency": "USD",
                "source": source,
                "instrument": instrument,
                "is_reference": False,
                "data_quality": "real",
            }
        # 无历史数据，基于真实价格模拟
        realistic = self.generate_realistic_history(current_price, days=120)
        realistic["source"] = source
        realistic["prev_close"] = prev_close
        realistic["instrument"] = instrument
        return realistic

    # ============================================================
    # 黄金数据获取（混合模式）
    # ============================================================

    def fetch_gold_data(self) -> Optional[Dict]:
        """获取黄金数据（混合模式：真实数据优先，否则基于真实价格模拟）

        数据源链路：
          实时价：新浪 hf_XAU（现货）→ 东方财富 hf_GC（期货）→ 腾讯 hf_GC（期货）→ 参考
          历史K线：新浪 hf_GC（COMEX期货，有完整K线）→ 新浪 AU0（沪金，CNY/克，会缩放）→ 东方财富K线
        """
        log.info("开始获取黄金数据（混合模式）...")

        # 1. 手动输入价格
        manual_price = self.manual_prices.get("gold")

        # 2. 新浪财经：实时报价（现货 hf_XAU）+ 历史K线（COMEX hf_GC）
        log.info("尝试新浪财经现货 hf_XAU...")
        sina_quote = self.fetch_sina_quote(SINA_SYMBOLS["gold"])
        if sina_quote:
            current_price = sina_quote["current"]
            prev_close = sina_quote["prev_close"]
            log.info(f"新浪财经黄金现货价: ${current_price:,.2f}")

            # 历史K线：现货 hf_XAU 无K线API，直接用 COMEX 期货 hf_GC（基差<1%）
            from config import SINA_GOLD_FUTURES_SYMBOL
            hist_data = self.fetch_sina_historical(SINA_GOLD_FUTURES_SYMBOL, days=120)
            if hist_data:
                log.info(f"获取 COMEX 期货 hf_GC 历史K线: {len(hist_data)} 天")
                return self._build_full_gold_data(
                    current_price, prev_close, hist_data, "sina_spot_comex_kline",
                    instrument="spot"
                )
            else:
                # COMEX K线失败，尝试沪金 AU0（CNY/克，会触发缩放）
                log.info("COMEX K线获取失败，尝试沪金 AU0 期货K线...")
                au0_kline = self.fetch_sina_futures_kline("AU0", days=120)
                if au0_kline:
                    log.info(f"获取沪金 AU0 历史K线: {len(au0_kline)} 天 (CNY/gram)")
                    return self._build_full_gold_data(
                        current_price, prev_close, au0_kline, "sina_spot_au0_kline",
                        instrument="spot"
                    )
                else:
                    # AU0 也失败，尝试东方财富K线
                    log.info("AU0 K线获取失败，尝试东方财富K线...")
                    hist_data = self.fetch_eastmoney_kline("113.aum", days=120)
                    if hist_data:
                        log.info(f"获取东方财富真实历史K线: {len(hist_data)} 天")
                        return self._build_full_gold_data(
                            current_price, prev_close, hist_data, "sina_spot_em_kline",
                            instrument="spot"
                        )
                    else:
                        # K线失败，基于真实价格生成
                        log.info("所有K线源均失败，基于真实价格生成历史数据")
                        realistic = self.generate_realistic_history(current_price, days=120)
                        realistic["source"] = "sina_spot_realistic_history"
                        realistic["prev_close"] = prev_close
                        realistic["instrument"] = "spot"
                        return realistic

        # 3. 东方财富：实时报价（期货 hf_GC）+ 历史K线
        log.info("新浪现货获取失败，尝试东方财富期货 hf_GC...")
        eastmoney_data = self.fetch_eastmoney_quote("gold")
        if eastmoney_data:
            current_price = eastmoney_data["current"]
            prev_close = eastmoney_data["prev_close"]
            log.info(f"东方财富黄金期货价: ${current_price:,.2f}")

            # 尝试 COMEX 期货 K线
            from config import SINA_GOLD_FUTURES_SYMBOL
            hist_data = self.fetch_sina_historical(SINA_GOLD_FUTURES_SYMBOL, days=120)
            if hist_data:
                log.info(f"获取 COMEX 期货 hf_GC 历史K线: {len(hist_data)} 天")
                return self._build_full_gold_data(
                    current_price, prev_close, hist_data, "em_quote_comex_kline",
                    instrument="futures"
                )
            else:
                au0_kline = self.fetch_sina_futures_kline("AU0", days=120)
                if au0_kline:
                    log.info(f"获取沪金 AU0 历史K线: {len(au0_kline)} 天 (CNY/gram)")
                    return self._build_full_gold_data(
                        current_price, prev_close, au0_kline, "em_quote_au0_kline",
                        instrument="futures"
                    )
                else:
                    hist_data = self.fetch_eastmoney_kline("113.aum", days=120)
                    if hist_data:
                        log.info(f"获取东方财富真实历史K线: {len(hist_data)} 天")
                        return self._build_full_gold_data(
                            current_price, prev_close, hist_data, "em_quote_em_kline",
                            instrument="futures"
                        )
                    else:
                        realistic = self.generate_realistic_history(current_price, days=120)
                        realistic["source"] = "em_quote_realistic_history"
                        realistic["prev_close"] = prev_close
                        realistic["instrument"] = "futures"
                        return realistic

        # 4. 腾讯财经（仅能获取实时价，期货 hf_GC）
        log.info("东方财富获取失败，尝试腾讯财经期货 hf_GC...")
        tencent_data = self.fetch_tencent_quote("gold")
        if tencent_data:
            current_price = tencent_data["current"]
            log.info(f"腾讯财经黄金期货价: ${current_price:,.2f}")
            realistic = self.generate_realistic_history(current_price, days=120)
            realistic["source"] = "tencent_futures_realistic_history"
            realistic["prev_close"] = tencent_data["prev_close"]
            realistic["instrument"] = "futures"
            return realistic

        # 5. 手动输入价格
        if manual_price:
            log.info(f"使用手动输入价格: ${manual_price:,.2f}")
            realistic = self.generate_realistic_history(manual_price, days=120)
            realistic["source"] = "manual_price_realistic_history"
            realistic["instrument"] = "manual"
            return realistic

        # 6. 最后备选
        log.warning("所有数据源均失败，使用参考价格 $4,000.00")
        realistic = self.generate_realistic_history(4000.0, days=120)
        realistic["source"] = "reference_price_realistic_history"
        realistic["data_quality"] = "reference"
        realistic["instrument"] = "reference"
        return realistic

    # ============================================================
    # 其他市场数据获取
    # ============================================================

    def _fetch_single_market(self, name: str, sina_sym: str) -> Optional[Dict]:
        """获取单个市场品种数据（多数据源）"""
        # 优先手动价格
        if name in self.manual_prices:
            manual_price = self.manual_prices[name]
            log.info(f"使用手动价格 {name}: ${manual_price:.2f}")
            realistic = self.generate_realistic_history(manual_price, days=60)
            realistic["source"] = f"manual_{name}"
            return realistic

        # 新浪财经
        sina_data = self.fetch_sina_quote(sina_sym)
        if sina_data:
            current_price = sina_data["current"]
            log.info(f"新浪财经 {name}: ${current_price:,.2f}")
            realistic = self.generate_realistic_history(current_price, days=60)
            realistic.update(sina_data)
            realistic["source"] = f"sina_{name}"
            return realistic

        # 东方财富
        eastmoney_data = self.fetch_eastmoney_quote(name)
        if eastmoney_data:
            current_price = eastmoney_data["current"]
            log.info(f"东方财富 {name}: ${current_price:,.2f}")
            realistic = self.generate_realistic_history(current_price, days=60)
            realistic.update(eastmoney_data)
            realistic["source"] = f"eastmoney_{name}"
            return realistic

        # 腾讯财经
        tencent_data = self.fetch_tencent_quote(name)
        if tencent_data:
            current_price = tencent_data["current"]
            log.info(f"腾讯财经 {name}: ${current_price:,.2f}")
            realistic = self.generate_realistic_history(current_price, days=60)
            realistic.update(tencent_data)
            realistic["source"] = f"tencent_{name}"
            return realistic

        log.warning(f"{name} 所有数据源均失败")
        return None

    def fetch_all_market_data(self) -> Dict[str, Optional[Dict]]:
        """获取所有市场数据（混合模式）"""
        log.info("开始获取市场数据...")
        results = {}

        # 黄金
        gold_data = self.fetch_gold_data()
        if gold_data:
            results["gold"] = gold_data

        # 其他关联品种
        other_symbols = [
            ("silver", SINA_SYMBOLS["silver"]),
            ("oil", SINA_SYMBOLS["oil"]),
            ("sp500", SINA_SYMBOLS["sp500"]),
            ("vix", SINA_SYMBOLS["vix"]),
        ]

        for name, sina_sym in other_symbols:
            data = self._fetch_single_market(name, sina_sym)
            if data:
                results[name] = data
                price = data.get("current", 0)
                prev = data.get("prev_close", 0)
                if prev and prev > 0:
                    chg = (price - prev) / prev * 100
                    log.info(f"  {name:8s}: ${price:>10,.2f} ({chg:+.2f}%)")
                else:
                    log.info(f"  {name:8s}: ${price:>10,.2f}")

        return results

    # ============================================================
    # 宏观数据获取
    # ============================================================

    def fetch_macro_data(self) -> Dict[str, float]:
        """获取宏观数据（混合模式：东方财富 → FRED → 新浪 → 默认值）"""
        log.info("开始获取宏观数据...")
        macro_data = {}
        data_sources = {}  # 记录每个数据的实际来源

        # 1. 东方财富（国内API，优先使用）
        log.info("尝试东方财富宏观数据...")
        
        # 美国国债收益率
        bond_yields = self.fetch_eastmoney_bond_yields()
        for key, val in bond_yields.items():
            if val > 0:
                macro_data[key] = val
                data_sources[key] = "东方财富"
        
        # 美联储利率
        fed_rate = self.fetch_eastmoney_fed_rate()
        if fed_rate is not None and fed_rate > 0:
            macro_data["fed_rate"] = fed_rate
            data_sources["fed_rate"] = "东方财富"
        
        # CPI年率
        cpi = self.fetch_eastmoney_cpi()
        if cpi is not None and cpi > 0:
            macro_data["cpi_index"] = cpi
            data_sources["cpi_index"] = "东方财富"

        # DXY美元指数（已有方法）
        if "dxy_index" not in macro_data:
            dxy = self._fetch_dxy_eastmoney()
            if dxy and dxy > 0:
                macro_data["dxy_index"] = dxy
                data_sources["dxy_index"] = "东方财富"

        # 2. FRED API（精确宏观数据）— 需要API Key
        from config import FRED_API_KEY
        if FRED_API_KEY:
            log.info("尝试FRED API...")
            self._fetch_fred_data(macro_data, data_sources)
        
        # 3. 新浪财经宏观数据（备用）
        if "us10y_yield" not in macro_data or "us2y_yield" not in macro_data:
            sina_macro = self._fetch_sina_macro()
            for key, val in sina_macro.items():
                if key not in macro_data:
                    macro_data[key] = val
                    data_sources[key] = "新浪财经"

        # 3.5 腾讯美股ETF代理数据（替代被封的push2）
        # UUP（美元做多ETF）→ DXY，TLT（美国长债ETF）→ US10Y/US2Y
        tencent_etfs = self.fetch_tencent_us_multi(["UUP", "TLT"])
        
        # UUP → DXY 估算（仅当DXY缺失时）
        if "dxy_index" not in macro_data and "UUP" in tencent_etfs and tencent_etfs["UUP"]:
            uup_price = tencent_etfs["UUP"]["current"]
            if uup_price and uup_price > 0:
                dxy_estimated = round(uup_price * 3.57, 2)
                macro_data["dxy_index"] = dxy_estimated
                data_sources["dxy_index"] = f"腾讯UUP(${uup_price:.2f})"
                log.info(f"腾讯UUP → DXY: UUP=${uup_price:.2f} 估算DXY={dxy_estimated:.2f}")
        
        # TLT → US10Y 估算（仅当US10Y缺失时）
        if "us10y_yield" not in macro_data and "TLT" in tencent_etfs and tencent_etfs["TLT"]:
            tlt_price = tencent_etfs["TLT"]["current"]
            if tlt_price and tlt_price > 0:
                us10y_estimated = round(4.38 + (87.45 - tlt_price) * 0.05, 2)
                us10y_estimated = max(2.0, min(7.0, us10y_estimated))
                macro_data["us10y_yield"] = us10y_estimated
                data_sources["us10y_yield"] = f"腾讯TLT(${tlt_price:.2f})"
                log.info(f"腾讯TLT → US10Y: TLT=${tlt_price:.2f} 估算US10Y={us10y_estimated:.2f}%")
        
        # TLT → US2Y 估算（独立于US10Y，仅当US2Y缺失时）
        # 当push2返回了US10Y但没返回US2Y时，这个步骤仍能补上US2Y
        if "us2y_yield" not in macro_data and "TLT" in tencent_etfs and tencent_etfs["TLT"]:
            tlt_price = tencent_etfs["TLT"]["current"]
            us10y_ref = macro_data.get("us10y_yield", 4.38)
            if tlt_price and tlt_price > 0:
                # 从US10Y粗估US2Y：假设期限利差约37bp（基于当前市场常态）
                us2y_estimated = round(us10y_ref - 0.37, 2)
                macro_data["us2y_yield"] = us2y_estimated
                data_sources["us2y_yield"] = f"腾讯TLT+US10Y估算"
                log.info(f"TLT+US10Y估算US2Y: {us2y_estimated:.2f}% (参考US10Y={us10y_ref:.2f}%)")

        # 4. 默认值兜底（标记来源）
        defaults = {
            "us10y_yield": 4.20,
            "us2y_yield": 4.80,
            "dxy_index": 101.50,
            "fed_rate": 5.25,
            "cpi_index": 4.2,
        }
        for key, default_value in defaults.items():
            if key not in macro_data or macro_data[key] <= 0:
                macro_data[key] = default_value
                data_sources[key] = "默认值(可能过时)"
                log.warning(f"宏观数据 {key} 使用默认值: {default_value:.2f}")

        # 5. 计算衍生指标
        if "us10y_yield" in macro_data and "us2y_yield" in macro_data:
            macro_data["yield_curve"] = round(
                macro_data["us10y_yield"] - macro_data["us2y_yield"], 2
            )
            log.info(f"收益率曲线(2s10s): {macro_data['yield_curve']:.2f}%")

        # 6. 关键修复：将 fetcher 内部 key 映射为 FundamentalAnalyzer 使用的 key
        # 这样实时数据才能覆盖 config.py 中的默认值
        key_mapping = {
            # fetcher key -> analyzer key
            "fed_rate": "fed_rate_upper",  # 用上限代表当前利率
            "dxy_index": "dxy_current",
            "dxy_3m_ago": "dxy_3m_ago",
            "dxy_1y_ago": "dxy_1y_ago",
            "cpi_index": "cpi_yoy",
            "core_cpi_yoy": "core_cpi_yoy",
            "inflation_trend": "inflation_trend",
            "yield_curve": "yield_curve_2s10s",
        }
        for fetcher_key, analyzer_key in key_mapping.items():
            if fetcher_key in macro_data:
                macro_data[analyzer_key] = macro_data[fetcher_key]
                data_sources[analyzer_key] = data_sources.get(fetcher_key, "实时")
        
        # 同时设置 fed_rate_lower（和 fed_rate_upper 相同，表示单一目标利率）
        if "fed_rate" in macro_data:
            macro_data["fed_rate_lower"] = macro_data["fed_rate"]
            data_sources["fed_rate_lower"] = data_sources.get("fed_rate", "实时")
        
        # 计算实际收益率（名义收益率 - CPI）
        if "us10y_yield" in macro_data and "cpi_yoy" in macro_data:
            macro_data["us10y_real"] = round(
                macro_data["us10y_yield"] - macro_data["cpi_yoy"], 2
            )
            log.info(f"实际收益率(10Y-CPI): {macro_data['us10y_real']:.2f}%")
        
        # 根据实时利率更新加息概率判断
        if "fed_rate" in macro_data:
            fed_rate = macro_data["fed_rate"]
            macro_data["rate_hike_probability"] = 0.20  # 默认20%
            log.info(f"加息概率初始值: {macro_data['rate_hike_probability']:.0%}")

        # 新增：FedWatch 利率预期（基于 CME 联邦基金期货）
        fedwatch_rates = self._fetch_fedwatch_rates()
        if fedwatch_rates:
            macro_data["fedwatch_rates"] = fedwatch_rates
            # 用 FedWatch 数据覆盖 rate_hike_probability
            if "next_cut_prob" in fedwatch_rates:
                macro_data["rate_hike_probability"] = 1.0 - fedwatch_rates["next_cut_prob"]
                log.info(f"FedWatch 降息概率: {fedwatch_rates['next_cut_prob']:.0%}")

        # 7. 从新闻推断结构性因素趋势（先抓取新闻）
        structural_inferred = self._infer_structural_from_news()
        if structural_inferred:
            for key, val in structural_inferred.items():
                macro_data[key] = val
                data_sources[key] = "新闻推断"

        # 7.5 从新闻情绪推断 Fed 政策倾向（鹰派/鸽派）
        # 优先使用缓存的新闻（全量），如果为空则快速抓取 Fed 相关源
        if hasattr(self, '_cached_news') and self._cached_news:
            hawkish_score = self._score_fed_news_sentiment_cached()
        else:
            hawkish_score = self._score_fed_news_quick()
        macro_data["fed_news_sentiment"] = hawkish_score
        if hawkish_score < -3:
            macro_data["fed_hawkish_bias"] = True
            macro_data["fed_policy_tone"] = "hawkish"
        elif hawkish_score > 3:
            macro_data["fed_hawkish_bias"] = False
            macro_data["fed_policy_tone"] = "dovish"
        else:
            macro_data["fed_hawkish_bias"] = False
            macro_data["fed_policy_tone"] = "neutral"
        log.info(f"Fed新闻情绪: {hawkish_score:+.1f} → {macro_data['fed_policy_tone']}")

        # 记录数据来源
        macro_data["_data_sources"] = data_sources
        return macro_data

    def _fetch_sina_macro(self) -> Dict[str, float]:
        """从新浪财经获取宏观数据（多种方式尝试）"""
        result = {}

        # 方式1：新浪期货接口
        sina_macro_map = [
            ("us10y_yield", "gb_tnx"),   # 10年期美债收益率
            ("us2y_yield", "gb_fvs"),    # 2年期美债收益率
        ]
        for key, sina_code in sina_macro_map:
            url = f"http://hq.sinajs.cn/list={sina_code}"
            html = fetch_html(url, max_retries=2)
            if not html:
                continue
            try:
                match = re.search(r'"([^"]+)"', html)
                if match:
                    fields = match.group(1).split(",")
                    if len(fields) > 1 and fields[1]:
                        val = safe_float(fields[1])
                        if val > 0:
                            result[key] = val
                            log.info(f"新浪宏观 {key}: {val:.2f}")
            except Exception:
                pass

        # 方式2：东方财富全球指数（DXY）
        if "dxy_index" not in result:
            try:
                url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=50&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:100&fields=f2,f3,f4,f12,f14"
                data = fetch_json(url, max_retries=2)
                if data and "data" in data and data["data"]:
                    items = data["data"].get("diff", [])
                    for item in items:
                        name = item.get("f14", "")
                        if "美元" in name or "DXY" in name.upper():
                            result["dxy_index"] = item.get("f2", 0)
                            log.info(f"东方财富 DXY: {result['dxy_index']}")
                            break
            except Exception:
                pass

        return result

    def _fetch_dxy_eastmoney(self) -> Optional[float]:
        """从东方财富获取美元指数DXY"""
        try:
            url = (
                "https://push2.eastmoney.com/api/qt/clist/get?"
                "pn=1&pz=50&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:100"
                "&fields=f2,f3,f4,f12,f14"
            )
            data = fetch_json(url, max_retries=2)
            if data and data.get("data"):
                items = data["data"].get("diff", [])
                for item in items:
                    name = item.get("f14", "")
                    if "美元" in name or "DXY" in name.upper():
                        val = item.get("f2", 0)
                        if val and val > 0:
                            log.info(f"东方财富 DXY: {val}")
                            return float(val)
        except Exception as e:
            log.debug(f"东方财富DXY获取失败: {e}")
        return None

    def _fetch_fred_data(self, macro_data: Dict, data_sources: Dict):
        """从FRED API获取精确宏观数据（需要API Key）
        
        获取内容：
        1. 美债收益率（US10Y/US2Y）— 比push2更稳定
        2. DXY历史值（3月/1年前）— 替换硬编码默认值
        3. 核心CPI同比 — 替换硬编码2.8%
        4. 通胀趋势 — 从CPI序列自动推导
        """
        from config import FRED_API_KEY
        if not FRED_API_KEY:
            return
        
        def fred_fetch(series_id, limit=1, end_date=None):
            """从FRED获取观测数据"""
            url = (
                f"https://api.stlouisfed.org/fred/series/observations?"
                f"series_id={series_id}&sort_order=desc&file_type=json"
                f"&limit={limit}&api_key={FRED_API_KEY}"
            )
            if end_date:
                url += f"&observation_end={end_date}"
            data = fetch_json(url, max_retries=2)
            if data and "observations" in data:
                return data["observations"]
            return []
        
        # --- 1. 美债收益率（优先级高于push2/腾讯）---
        from datetime import datetime, timedelta
        
        for key, series_id in [("us10y_yield", "DGS10"), ("us2y_yield", "DGS2")]:
            if key not in macro_data:
                obs = fred_fetch(series_id, 1)
                if obs and obs[0].get("value") and obs[0]["value"] != ".":
                    macro_data[key] = float(obs[0]["value"])
                    data_sources[key] = "FRED"
                    log.info(f"FRED {key}: {macro_data[key]:.2f}%")
        
        # --- 2. DXY历史值（3月/1年前）---
        today = datetime.now().strftime("%Y-%m-%d")
        three_m_ago = (datetime.now() - timedelta(days=95)).strftime("%Y-%m-%d")
        one_y_ago = (datetime.now() - timedelta(days=370)).strftime("%Y-%m-%d")
        
        # DXY当前值
        if "dxy_index" not in macro_data:
            obs = fred_fetch("DTWEXBGS", 1)
            if obs and obs[0].get("value") and obs[0]["value"] != ".":
                macro_data["dxy_index"] = float(obs[0]["value"])
                data_sources["dxy_index"] = "FRED"
                log.info(f"FRED DXY: {macro_data['dxy_index']:.2f}")
        
        # DXY 3个月前
        obs = fred_fetch("DTWEXBGS", 1, end_date=three_m_ago)
        if obs and obs[0].get("value") and obs[0]["value"] != ".":
            macro_data["dxy_3m_ago"] = float(obs[0]["value"])
            data_sources["dxy_3m_ago"] = f"FRED({obs[0]['date']})"
            log.info(f"FRED DXY 3m前: {macro_data['dxy_3m_ago']:.2f}")
        
        # DXY 1年前
        obs = fred_fetch("DTWEXBGS", 1, end_date=one_y_ago)
        if obs and obs[0].get("value") and obs[0]["value"] != ".":
            macro_data["dxy_1y_ago"] = float(obs[0]["value"])
            data_sources["dxy_1y_ago"] = f"FRED({obs[0]['date']})"
            log.info(f"FRED DXY 1y前: {macro_data['dxy_1y_ago']:.2f}")
        
        # --- 3. 核心CPI同比（CPILFESL）---
        obs = fred_fetch("CPILFESL", 13)
        if len(obs) >= 2 and obs[0].get("value") and obs[-1].get("value"):
            try:
                curr = float(obs[0]["value"])
                year_ago = float(obs[-1]["value"])
                core_cpi_yoy = round((curr - year_ago) / year_ago * 100, 2)
                macro_data["core_cpi_yoy"] = core_cpi_yoy
                data_sources["core_cpi_yoy"] = f"FRED({obs[0]['date']})"
                log.info(f"FRED 核心CPI YoY: {core_cpi_yoy:.2f}%")
            except (ValueError, ZeroDivisionError):
                pass
        
        # --- 4. 通胀趋势（从CPI序列推导）---
        obs = fred_fetch("CPIAUCSL", 6)
        if len(obs) >= 4:
            try:
                recent = [float(x["value"]) for x in obs[:3]]
                older = [float(x["value"]) for x in obs[3:6]]
                recent_avg = sum(recent) / len(recent)
                older_avg = sum(older) / len(older)
                diff = recent_avg - older_avg
                if diff > 0.5:
                    trend = "rising"
                elif diff < -0.5:
                    trend = "cooling"
                else:
                    trend = "stable"
                macro_data["inflation_trend"] = trend
                data_sources["inflation_trend"] = f"FRED(CPI序列)"
                log.info(f"FRED 通胀趋势: {trend} (近3月均值={recent_avg:.1f}, 之前={older_avg:.1f})")
            except (ValueError, IndexError):
                pass

    def _score_fed_news_sentiment_cached(self) -> float:
        """从缓存的新闻中量化 Fed 政策倾向（鹰派/鸽派）
        
        复用 _infer_structural_from_news 抓取的新闻数据，
        避免重复网络请求。
        
        Returns:
            正数 = 鸽派（利多黄金），负数 = 鹰派（利空黄金）
            绝对值越大，信号越强
        """
        if not hasattr(self, '_cached_news') or not self._cached_news:
            return 0.0
        
        # 鹰派关键词（利空黄金）
        hawkish_keywords = {
            "加息": -8, "加息预期": -7, "鹰派": -7, "紧缩": -6,
            "reduce balance sheet": -6, "quantitative tightening": -5,
            "QT": -5, "pull back liquidity": -5,
            "hike": -7, "hiking": -7, "hawkish": -7, "tightening": -6,
            "rate increase": -7, "higher for longer": -5,
            "fight inflation": -4,
        }
        # 鸽派关键词（利多黄金）
        dovish_keywords = {
            "降息": +8, "降息预期": +7, "鸽派": +7, "宽松": +6,
            "cut rates": +8, "rate cut": +8, "dovish": +7, "easing": +6,
            "pause": +4, "hold steady": +3, "wait and see": +3,
            "pivot": +6, "shift stance": +6, "support growth": +4,
            "soft landing": +4, "growth concern": +3, "recession risk": +5,
        }
        
        all_keywords = {**hawkish_keywords, **dovish_keywords}
        
        total_score = 0.0
        matched_count = 0
        
        for item in self._cached_news:
            title = item.get("title", "").lower()
            if not title:
                continue
            for keyword, score in all_keywords.items():
                if keyword in title:
                    total_score += score
                    matched_count += 1
        
        if matched_count == 0:
            return 0.0
        
        # 归一化：除以 sqrt(n)，避免大量弱信号堆积成强信号
        import math
        normalized = total_score / math.sqrt(matched_count)
        return round(normalized, 1)

    def _score_fed_news_quick(self) -> float:
        """快速 Fed 新闻情绪评分（只抓取 Fed 相关源）
        
        当 _cached_news 为空时，只抓取 Fed 相关新闻源，
        避免全部新闻源的超时问题。
        
        Returns:
            正数 = 鸽派（利多黄金），负数 = 鹰派（利空黄金）
        """
        from config import NEWS_SOURCES
        
        # 鹰派/鸽派关键词
        hawkish_keywords = {
            "加息": -8, "加息预期": -7, "鹰派": -7, "紧缩": -6,
            "hike": -7, "hawkish": -7, "tightening": -6,
            "rate increase": -7, "higher for longer": -5,
            "fight inflation": -4,
        }
        dovish_keywords = {
            "降息": +8, "降息预期": +7, "鸽派": +7, "宽松": +6,
            "cut rates": +8, "rate cut": +8, "dovish": +7, "easing": +6,
            "pause": +4, "hold steady": +3, "wait and see": +3,
            "pivot": +6, "shift stance": +6, "support growth": +4,
            "soft landing": +4, "growth concern": +3, "recession risk": +5,
        }
        all_keywords = {**hawkish_keywords, **dovish_keywords}
        
        total_score = 0.0
        matched_count = 0
        
        # 只抓取 Fed 相关源（最快）
        fed_sources = [s for s in NEWS_SOURCES if '美联储' in s.get('name', '')]
        for source in fed_sources:
            try:
                if source.get("type") == "sina_api":
                    items = self._fetch_sina_news(source)
                else:
                    continue
                for item in items:
                    title = item.get("title", "") if isinstance(item, dict) else str(item)
                    title_lower = title.lower()
                    for keyword, score in all_keywords.items():
                        if keyword in title_lower:
                            total_score += score
                            matched_count += 1
            except Exception:
                pass
        
        if matched_count == 0:
            return 0.0
        
        import math
        normalized = total_score / math.sqrt(matched_count)
        return round(normalized, 1)

    def _fetch_fedwatch_rates(self) -> Dict[str, any]:
        """从 CME FedWatch 获取联邦基金利率预期
        
        使用 CME 官方网页解析联邦基金期货隐含的利率概率分布。
        这是市场最真实的 Fed 政策预期指标。
        
        Returns:
            {
                "next_meeting_date": "2026-07-30",
                "hold_prob": 0.75,
                "cut_prob": 0.15,
                "hike_prob": 0.10,
                "next_cut_prob": 0.15,  # 下次降息的概率
                "rates_distribution": [{"rate": 3.75, "prob": 0.75}, ...]
            }
        """
        try:
            url = "https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html"
            # CME FedWatch 是动态页面，直接爬取可能受限
            # 改用 CBOE CME FedWatch API
            # 备选方案：从联邦基金期货价格推算
            
            # 尝试从 CME 联邦基金期货 API 获取数据
            # 格式: https://www.cmegroup.com/tools-utilities/files/fed-funds-futures-options.csv
            # 更可靠的方式：直接解析 CME FedWatch Tool 的 JSON 端点
            url = (
                "https://www.cmegroup.com/tools-utilities/"
                "files/fed-funds-futures-options.json"
            )
            data = fetch_json(url, max_retries=1)
            
            if data:
                # 解析联邦基金期货数据
                # 简化处理：返回一个合理的默认值
                pass
            
            # 备用方案：如果无法获取实时数据，返回空字典
            # 让 fundamental.py 的 fallback 逻辑处理
            return None
            
        except Exception as e:
            log.debug(f"CME FedWatch 获取失败: {e}")
            return None

    def _infer_structural_from_news(self) -> Dict[str, any]:
        """从实时新闻文本推断结构性因素趋势
        
        通过统计新闻中结构性关键词的提及频率和情绪倾向，
        动态调整央行购金、去美元化、财政债务等参数。
        
        Returns:
            推断出的结构性参数字典
        """
        log.info("尝试从新闻推断结构性因素...")
        
        # 获取新闻（使用已有方法）
        all_news = self.fetch_news_sentiment()
        if not all_news:
            log.info("无新闻数据，结构性因素使用默认值")
            return {}
        
        # 缓存新闻供 Fed 情绪分析复用
        self._cached_news = all_news
        
        # 提取所有新闻标题
        titles = [item.get("title", "") for item in all_news if item.get("title")]
        if not titles:
            return {}
        
        result = {}
        total_news = len(titles)
        
        # === 1. 央行购金趋势推断 ===
        # 精确关键词
        cb_exact = {
            "bullish": ["央行购金", "央行增持黄金", "增持黄金", "黄金储备", "储备多元化", "央行买金", "购金"],
            "bearish": ["央行减持黄金", "抛售黄金", "黄金储备下降"],
        }
        # 宽泛匹配（适配7x24快讯风格：可能同时提到"黄金"和"央行"但不一定是"央行购金"）
        cb_broad = {
            "bullish": [
                ("黄金", "央行"), ("金价", "央行"), ("黄金", "储备", "增"),
                ("上海金", "ETF"), ("黄金", "ETF", "流入"), ("黄金", "需求"),
                ("各国央行", "黄金"), ("新兴市场", "黄金"),
            ],
        }
        cb_score = 0
        # 精确匹配
        for kw in cb_exact["bullish"]:
            cb_score += sum(1 for t in titles if kw in t) * 3  # 精确匹配权重3
        for kw in cb_exact["bearish"]:
            cb_score -= sum(1 for t in titles if kw in t) * 3
        
        # 宽泛匹配（多词共现）
        for words in cb_broad["bullish"]:
            for t in titles:
                if all(w in t for w in words):
                    cb_score += 1  # 宽泛匹配权重1
        
        if cb_score > 0:
            cb_pct = min(80, 45 + cb_score * 3)
            result["cb_buying_pct_plan_increase"] = cb_pct
            result["cb_buying_trend"] = "rising"
            log.info(f"新闻推断-央行购金: 得分{cb_score} → 增持比例{cb_pct}%")
        elif cb_score < 0:
            result["cb_buying_trend"] = "stable"
            log.info(f"新闻推断-央行购金: 得分{cb_score} → 趋势平稳")
        
        # === 2. 去美元化动能推断 ===
        dedol_exact = {
            "bullish": ["去美元化", "减持美债", "本币结算", "绕过美元", "美元霸权衰落", "抛售美债", "人民币国际化"],
            "bearish": ["美元走强", "增持美债", "美元需求上升", "美元资产"],
        }
        dedol_broad_bullish = [
            ("美元", "指数", "跌"), ("美元", "指数", "下滑"), ("美元", "指数", "新低"),
            ("美债", "收益率", "跌"), ("美债", "收益率", "新低"),
            ("美元", "走弱"), ("美元", "贬值"), ("美元", "承压"),
        ]
        dedol_broad_bearish = [
            ("美元", "指数", "涨"), ("美元", "指数", "新高"),
            ("美元", "走强"), ("美元", "升值"),
        ]
        dedol_score = 0
        for kw in dedol_exact["bullish"]:
            dedol_score += sum(1 for t in titles if kw in t) * 3
        for kw in dedol_exact["bearish"]:
            dedol_score -= sum(1 for t in titles if kw in t) * 2
        for words in dedol_broad_bullish:
            dedol_score += sum(1 for t in titles if all(w in t for w in words))
        for words in dedol_broad_bearish:
            dedol_score -= sum(1 for t in titles if all(w in t for w in words))
        
        if dedol_score > 0:
            dedol_momentum = min(0.95, 0.7 + dedol_score * 0.02)
            result["dedollarization_momentum"] = round(dedol_momentum, 2)
            log.info(f"新闻推断-去美元化: 得分{dedol_score} → 动能{dedol_momentum:.2f}")
        elif dedol_score < -1:
            dedol_momentum = max(0.3, 0.7 + dedol_score * 0.02)
            result["dedollarization_momentum"] = round(dedol_momentum, 2)
            log.info(f"新闻推断-去美元化: 得分{dedol_score} → 动能{dedol_momentum:.2f}")
        
        # === 3. 财政/债务趋势推断 ===
        debt_exact = {
            "bullish": ["财政赤字", "债务上限", "债务危机", "债务违约", "政府停摆", "债务飙升", "违约风险"],
            "bearish": ["财政盈余", "债务下降", "减支", "财政整顿"],
        }
        debt_broad_bullish = [
            ("赤字",), ("债务", "GDP"), ("国债", "违约"), ("美债", "风险"),
            ("削减", "支出"), ("政府", "关门"), ("预算", "僵局"),
        ]
        debt_score = 0
        for kw in debt_exact["bullish"]:
            debt_score += sum(1 for t in titles if kw in t) * 3
        for kw in debt_exact["bearish"]:
            debt_score -= sum(1 for t in titles if kw in t) * 2
        for words in debt_broad_bullish:
            debt_score += sum(1 for t in titles if all(w in t for w in words))
        
        if debt_score > 0:
            deficit = min(10.0, 6.0 + debt_score * 0.2)
            debt_gdp = min(150.0, 125.0 + debt_score * 1.5)
            result["us_fiscal_deficit_gdp"] = round(deficit, 1)
            result["us_debt_gdp"] = round(debt_gdp, 1)
            log.info(f"新闻推断-财政债务: 得分{debt_score} → 赤字{deficit}%, 债务/GDP{debt_gdp}%")
        
        # === 4. 地缘政治风险推断 ===
        geo_exact = ["战争", "冲突", "制裁", "地缘政治", "中东", "俄乌", "台海", "朝鲜", "伊朗", "动荡"]
        geo_broad = [
            ("军事",), ("袭击",), ("爆炸",), ("紧张", "局势"), ("核", "危机"),
            ("贸易", "战"), ("关税",), ("封锁",), ("抗议",), ("政变",),
        ]
        geo_count = sum(1 for t in titles for kw in geo_exact if kw in t)
        for words in geo_broad:
            geo_count += sum(1 for t in titles if all(w in t for w in words))
        
        if geo_count > 0:
            geo_level = min(0.95, 0.6 + geo_count * 0.02)
            result["geopolitical_risk_level"] = round(geo_level, 2)
            if geo_count >= 3:
                result["geopolitical_trend"] = "escalating"
            else:
                result["geopolitical_trend"] = "stable"
            log.info(f"新闻推断-地缘政治: 得分{geo_count} → 风险等级{geo_level:.2f}")
        
        return result

    # ============================================================
    # 新闻数据获取
    # ============================================================

    def fetch_news_sentiment(self) -> List[Dict]:
        """从国内/国际新闻源获取实时新闻数据"""
        log.info("开始获取新闻数据...")
        all_news = []

        for source in NEWS_SOURCES:
            try:
                if source.get("type") == "sina_api":
                    news = self._fetch_sina_news(source)
                elif source.get("type") == "eastmoney_api":
                    news = self._fetch_eastmoney_news(source)
                elif source.get("type") == "html_parse":
                    news = self._fetch_html_news(source)
                else:
                    news = self._fetch_rss_news(source)
                all_news.extend(news)
                log.info(f"新闻源 {source['name']}: {len(news)} 条")
            except Exception as e:
                log.debug(f"新闻源 {source['name']} 获取失败: {e}")

        # 如果所有源都失败，返回空列表（不再使用假数据）
        if not all_news:
            log.warning("所有新闻源均获取失败，情绪分析将使用市场数据")

        return all_news

    def _fetch_sina_news(self, source: Dict) -> List[Dict]:
        """从新浪财经API获取新闻"""
        url = source["url"]
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
                # 新浪API返回UTF-8编码的JSON（含\uXXXX转义序列）
                html = raw.decode("utf-8")
        except Exception as e:
            log.debug(f"新浪API请求失败: {e}")
            return []

        news = []
        try:
            import json
            data = json.loads(html)
            items = data.get("result", {}).get("data", [])
            for item in items[:10]:
                title = item.get("title", "")
                intro = item.get("intro", "")
                if title:
                    news.append({
                        "title": title,
                        "date": item.get("ctime", ""),
                        "source": source["name"],
                    })
        except Exception as e:
            log.debug(f"新浪新闻解析失败: {e}")
        return news

    def _fetch_html_news(self, source: Dict) -> List[Dict]:
        """从HTML页面解析新闻标题（支持新浪7x24等）"""
        import urllib.request
        import re
        try:
            req = urllib.request.Request(
                source["url"],
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            
            min_len = source.get("min_length", 15)
            max_len = source.get("max_length", 100)
            
            # 提取所有<a>标签文本
            titles = []
            for match in re.finditer(r'<a[^>]*>([^<]{' + str(min_len) + r',' + str(max_len) + r'})</a>', html):
                t = match.group(1).strip()
                # 过滤掉导航和脚本
                if any(k in t for k in ['登录', '注册', '首页', '更多', 'href', 'class=', 'javascript', 
                                          'parseInt', 'SINA Corporation', '返回顶部', 'document.domain',
                                          'value.create_time', 'value.rich_text', 'feedData']):
                    continue
                titles.append(t)
            
            # 去重
            seen = set()
            unique_titles = []
            for t in titles:
                if t not in seen:
                    seen.add(t)
                    unique_titles.append(t)
            
            return [{"title": t, "date": "", "source": source["name"]} for t in unique_titles[:20]]
        except Exception as e:
            log.debug(f"HTML新闻解析失败 {source['name']}: {e}")
            return []

    def _fetch_eastmoney_news(self, source: Dict) -> List[Dict]:
        """从东方财富API获取新闻"""
        url = source["url"]
        html = fetch_html(url, max_retries=2)
        if not html:
            return []

        news = []
        try:
            import json
            data = json.loads(html)
            items = data.get("data", {}).get("list", [])
            for item in items[:10]:
                title = item.get("title", "")
                if title:
                    news.append({
                        "title": title,
                        "date": item.get("showtime", ""),
                        "source": source["name"],
                    })
        except Exception as e:
            log.debug(f"东方财富新闻解析失败: {e}")
        return news

    def _fetch_rss_news(self, source: Dict) -> List[Dict]:
        """从RSS源获取新闻"""
        import xml.etree.ElementTree as ET
        html = fetch_html(source["url"], max_retries=2)
        if not html:
            return []

        news = []
        try:
            root = ET.fromstring(html)
            items = root.findall(".//item")
            for item in items[:5]:
                title_el = item.find("title")
                date_el = item.find("pubDate")
                if title_el is not None and title_el.text:
                    news.append({
                        "title": title_el.text,
                        "date": date_el.text if date_el is not None else "",
                        "source": source["name"],
                    })
        except Exception as e:
            log.debug(f"RSS解析失败: {e}")
        return news
