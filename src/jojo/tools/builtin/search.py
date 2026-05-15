"""
内置工具：web_search — 搜索互联网。
"""

import httpx

from src.jojo.tools.base import tool
from src.jojo.logger import logger


@tool(
    "web_search",
    "搜索互联网获取最新信息。返回相关结果的标题、URL 和摘要",
    risk="read",
)
async def web_search(query: str, num_results: int = 5) -> str:
    """
    使用 DuckDuckGo Instant Answer API 进行搜索。
    无需 API Key，适用于通用搜索场景。
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_html": "1",
                    "skip_disambig": "1",
                },
                headers={"User-Agent": "JoJo-Agent/0.1"},
            )
            response.raise_for_status()
            data = response.json()

            results = []

            # Abstract (摘要)
            if data.get("AbstractText"):
                results.append(f"[摘要] {data['AbstractText']}")
                if data.get("AbstractURL"):
                    results.append(f"  来源: {data['AbstractURL']}")

            # Related Topics
            related = data.get("RelatedTopics", [])
            count = 0
            for topic in related[:num_results]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(f"[结果{count+1}] {topic['Text']}")
                    if topic.get("FirstURL"):
                        results.append(f"  链接: {topic['FirstURL']}")
                    count += 1

            if not results:
                return f"未找到 '{query}' 的搜索结果。"

            return "\n".join(results)

    except Exception as e:
        logger.error(f"web_search failed: {e}")
        return f"搜索失败: {e}"
