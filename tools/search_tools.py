import html
import json
import re
from collections import Counter
from urllib.error import URLError
from urllib.request import Request, urlopen

from crewai_tools import ScrapeWebsiteTool
from duckduckgo_search import DDGS

def get_search_tool():
    """Returns a tool for scraping/crawling websites."""
    return ScrapeWebsiteTool()


def search_duckduckgo(query, max_results=5):
    results = []
    with DDGS() as ddgs:
        for row in ddgs.text(query, max_results=max_results):
            results.append(
                {
                    "title": row.get("title", ""),
                    "url": row.get("href", ""),
                    "snippet": row.get("body", ""),
                }
            )
    return results


def _strip_tags(value):
    return re.sub(r"<[^>]+>", " ", value or "")


def _clean_text(value):
    text = html.unescape(_strip_tags(value))
    return re.sub(r"\s+", " ", text).strip()


def _fetch_html(url, timeout=10):
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                return ""
            return response.read().decode("utf-8", errors="replace")
    except (URLError, ValueError, TimeoutError, OSError):
        return ""


def _extract_headings_from_html(raw_html):
    headings = []
    for match in re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", raw_html or "", flags=re.IGNORECASE | re.DOTALL):
        cleaned = _clean_text(match)
        if cleaned:
            headings.append(cleaned)
    return headings


def _extract_questions(headings, snippet):
    questions = []
    for item in list(headings or []) + [snippet or ""]:
        text = _clean_text(item)
        if not text:
            continue
        if "?" in text:
            for part in re.split(r"(?<=[?])\s+", text):
                part = part.strip()
                if part.endswith("?") and len(part) > 10:
                    questions.append(part)
    return questions


def _estimate_word_count(raw_html, snippet):
    text = _clean_text(raw_html) if raw_html else _clean_text(snippet)
    return len(text.split()) if text else 0


def collect_serp_research(query, max_results=5):
    results = search_duckduckgo(query, max_results=max_results)
    enriched = []
    heading_counter = Counter()
    question_counter = Counter()
    word_counts = []

    for result in results:
        raw_html = _fetch_html(result.get("url", "")) if result.get("url") else ""
        headings = _extract_headings_from_html(raw_html)
        questions = _extract_questions(headings, result.get("snippet", ""))
        word_count = _estimate_word_count(raw_html, result.get("snippet", ""))
        if word_count:
            word_counts.append(word_count)

        for heading in headings[:12]:
            heading_counter[heading] += 1
        for question in questions[:8]:
            question_counter[question] += 1

        enriched.append(
            {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": result.get("snippet", ""),
                "headings": headings[:12],
                "questions": questions[:8],
                "estimated_word_count": word_count,
            }
        )

    return {
        "query": query,
        "results_analyzed": len(enriched),
        "pages": enriched,
        "common_headings": [item for item, _count in heading_counter.most_common(12)],
        "common_questions": [item for item, _count in question_counter.most_common(10)],
        "word_counts": word_counts,
    }


def format_serp_research_for_prompt(payload):
    return json.dumps(payload, indent=2, ensure_ascii=False)
