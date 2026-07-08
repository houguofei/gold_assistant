# -*- coding: utf-8 -*-
"""
黄金投资助手 - 工具模块
Gold Investment Assistant - Utilities

提供日志系统、HTTP重试、通用工具函数等基础能力。
"""

import logging
import sys
import io
import time
import random
import json
import urllib.request
from typing import Optional, Any, Callable


# ============================================================
# 日志系统
# ============================================================

def setup_logger(name: str = "gold_assistant", level: int = logging.INFO) -> logging.Logger:
    """
    配置并返回项目统一 Logger。

    输出格式: [时间] [级别] 消息
    同时输出到 stdout 和文件 gold_assistant.log。
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # 已初始化，避免重复

    logger.setLevel(level)

    # 格式
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # 控制台输出
    console_handler = logging.StreamHandler(
        io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    )
    console_handler.setLevel(level)
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    # 文件输出
    try:
        file_handler = logging.FileHandler("gold_assistant.log", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(funcName)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        logger.addHandler(file_handler)
    except Exception:
        pass  # 文件写入失败不影响主流程

    return logger


# 全局 logger 实例
log = setup_logger()


# ============================================================
# HTTP 请求工具
# ============================================================

def fetch_url(
    url: str,
    headers: dict = None,
    timeout: int = 15,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    as_json: bool = False,
) -> Optional[Any]:
    """
    带重试的 HTTP 请求工具。

    Args:
        url: 请求地址
        headers: 请求头（默认使用标准 UA）
        timeout: 超时秒数
        max_retries: 最大重试次数
        retry_delay: 基础重试间隔（秒），实际会加随机抖动
        as_json: 是否将响应解析为 JSON

    Returns:
        成功返回响应内容（str 或 dict），失败返回 None
    """
    if headers is None:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    last_error = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                if as_json:
                    return json.loads(raw)
                return raw
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = retry_delay * (1.5 ** attempt) + random.uniform(0, 0.5)
                log.debug(f"请求失败 ({attempt+1}/{max_retries}): {url[:60]}... "
                          f"等待 {delay:.1f}s 后重试")
                time.sleep(delay)

    log.debug(f"请求最终失败: {url[:60]}... 错误: {last_error}")
    return None


def fetch_json(
    url: str,
    headers: dict = None,
    timeout: int = 15,
    max_retries: int = 3,
) -> Optional[dict]:
    """便捷方法：获取 JSON 数据"""
    return fetch_url(url, headers, timeout, max_retries, as_json=True)


def fetch_html(
    url: str,
    headers: dict = None,
    timeout: int = 15,
    max_retries: int = 3,
) -> Optional[str]:
    """便捷方法：获取 HTML 文本"""
    return fetch_url(url, headers, timeout, max_retries, as_json=False)


# ============================================================
# 通用工具函数
# ============================================================

def safe_float(value: Any, default: float = 0.0) -> float:
    """安全地将值转换为 float"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """安全地将值转换为 int"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def clamp(value: float, min_val: float, max_val: float) -> float:
    """将值限制在 [min_val, max_val] 范围内"""
    return max(min_val, min(max_val, value))


def retry_on_failure(
    func: Callable,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    description: str = "",
) -> Optional[Any]:
    """
    通用重试装饰器：对任意函数执行重试。

    Args:
        func: 要执行的函数（无参数，用 lambda 包装）
        max_retries: 最大重试次数
        retry_delay: 基础重试间隔
        description: 操作描述（用于日志）

    Returns:
        函数返回值，全部失败返回 None
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            result = func()
            if result is not None:
                return result
        except Exception as e:
            last_error = e

        if attempt < max_retries - 1:
            delay = retry_delay * (1.5 ** attempt) + random.uniform(0, 0.5)
            log.debug(f"{description} 失败 ({attempt+1}/{max_retries})，"
                      f"等待 {delay:.1f}s 后重试")
            time.sleep(delay)

    log.debug(f"{description} 全部 {max_retries} 次尝试均失败")
    return None
