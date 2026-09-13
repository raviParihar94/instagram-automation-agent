"""
Research step of the pipeline: uses the free DuckDuckGo Search API (no key
required) to pull what's currently trending / being talked about for the
configured niche, so the LLM has real signal instead of stale training data.
"""
from duckduckgo_search import DDGS


class ResearchAgent:
    def get_trending_topics(self, keywords: str, max_results: int = 6) -> list:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(keywords, max_results=max_results))
            return [r.get("title", "") for r in results if r.get("title")]
        except Exception as e:
            # Research failing shouldn't crash the whole pipeline — fall back
            # to an empty trend list and let the LLM rely on the niche/prompt.
            print(f"[ResearchAgent] search failed: {e}")
            return []

    def get_trending_hashtags(self, niche: str, max_results: int = 5) -> list:
        query = f"trending instagram hashtags {niche} 2026"
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            return [r.get("title", "") for r in results if r.get("title")]
        except Exception as e:
            print(f"[ResearchAgent] hashtag search failed: {e}")
            return []
