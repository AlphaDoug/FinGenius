#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多引擎网络搜索工具
搜索引擎降级顺序: Google → Baidu → DuckDuckGo → Bing
"""

import argparse
import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup


class WebContentFetcher:
    """网页正文抓取器"""

    @staticmethod
    def fetch_content(url: str, timeout: int = 10) -> Optional[str]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "header", "footer", "nav"]):
                tag.extract()
            text = soup.get_text(separator="\n", strip=True)
            text = " ".join(text.split())
            return text[:10000] if text else None
        except Exception:
            return None


def _search_google(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """Google搜索"""
    try:
        from googlesearch import search as gsearch
        results = []
        for url in gsearch(query, num_results=num_results, lang="zh-CN"):
            results.append({"url": url, "title": "", "description": "", "source": "google"})
        return results
    except Exception:
        return []


def _search_baidu(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """百度搜索"""
    try:
        from baidusearch.baidusearch import search as bsearch
        raw = bsearch(query, num_results=num_results)
        return [{"url": r.get("url", ""), "title": r.get("title", ""), "description": r.get("abstract", ""), "source": "baidu"} for r in raw if r.get("url")]
    except Exception:
        return []


def _search_duckduckgo(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """DuckDuckGo搜索"""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            raw = list(ddgs.text(query, max_results=num_results))
        return [{"url": r.get("href", ""), "title": r.get("title", ""), "description": r.get("body", ""), "source": "duckduckgo"} for r in raw if r.get("href")]
    except Exception:
        return []


def _search_bing(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """Bing搜索（HTML爬取）"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(f"https://www.bing.com/search?q={query}&count={num_results}", headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for item in soup.select("li.b_algo"):
            link = item.select_one("h2 a")
            desc = item.select_one("p")
            if link and link.get("href"):
                results.append({
                    "url": link["href"],
                    "title": link.get_text(strip=True),
                    "description": desc.get_text(strip=True) if desc else "",
                    "source": "bing",
                })
            if len(results) >= num_results:
                break
        return results
    except Exception:
        return []


# 搜索引擎降级顺序
_ENGINES = [
    ("google", _search_google),
    ("baidu", _search_baidu),
    ("duckduckgo", _search_duckduckgo),
    ("bing", _search_bing),
]


def web_search(query: str, num_results: int = 5, fetch_content: bool = False) -> Dict[str, Any]:
    """
    多引擎网络搜索，自动降级

    Args:
        query: 搜索关键词
        num_results: 结果数量
        fetch_content: 是否抓取网页正文

    Returns:
        dict: 搜索结果
    """
    for engine_name, engine_func in _ENGINES:
        try:
            results = engine_func(query, num_results)
            if results:
                if fetch_content:
                    fetcher = WebContentFetcher()
                    for r in results:
                        content = fetcher.fetch_content(r["url"])
                        if content:
                            r["content"] = content
                return {"success": True, "engine": engine_name, "query": query, "results": results}
        except Exception:
            continue

    return {"success": False, "query": query, "error": "所有搜索引擎均失败", "results": []}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="多引擎网络搜索")
    parser.add_argument("query", type=str, help="搜索关键词")
    parser.add_argument("--num_results", type=int, default=5, help="结果数量")
    parser.add_argument("--fetch_content", action="store_true", help="是否抓取正文")
    args = parser.parse_args()

    result = web_search(args.query, args.num_results, args.fetch_content)
    print(json.dumps(result, ensure_ascii=False, indent=2))
