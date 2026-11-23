from langchain.tools import tool
import requests
from rich import print
from bs4 import BeautifulSoup
from tavily import TavilyClient
import os
from concurrent.futures import ThreadPoolExecutor   # NEW: runs scraping in parallel threads
from dotenv import load_dotenv
load_dotenv()

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


# ---------------------------------------------------------------------------
# EXISTING agent tools (unchanged, still usable by Search/Reader agents)
# ---------------------------------------------------------------------------

@tool
def get_web_content(query: str) -> str:
    """
    Searches the web for recent and reliable information related to the query.
    Returns Titles,Links, and Snippets.
    """
    search_results = tavily.search(query, max_results=5)
    results = []
    for result in search_results['results']:
        results.append(f"Title: {result['title']}\nLink: {result['url']}\nSnippet: {result['content'][:300]}\n")
    return "\n------------------\n".join(results)


@tool
def scrape_url(url: str) -> str:
    """Scrape and return clean text content from a given URL for deeper reading."""
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:3000]
    except Exception as e:
        return f"Could not scrape URL: {str(e)}"


# ---------------------------------------------------------------------------
# NEW: structured search + parallel scraping (used by the pipeline, not agents)
# ---------------------------------------------------------------------------

def search_sources(query: str, max_results: int = 5) -> list[dict]:
    """
    Like get_web_content, but returns structured data instead of a text blob.
    Each source gets a numeric id (starting at 1) which becomes the [1], [2]
    citation number used by the Writer and in the final Sources section.
    """
    res = tavily.search(query, max_results=max_results)
    return [
        {
            "id": i + 1,                  # citation number
            "title": r["title"],
            "url": r["url"],
            "snippet": r["content"],      # full Tavily snippet, kept as a fallback
        }
        for i, r in enumerate(res["results"])
    ]


def scrape_one(url: str, limit: int = 3000) -> str:
    """
    Scrape a single page and return clean text.
    Returns "" on any failure (instead of an error string) so the caller
    can detect the failure and fall back to the search snippet.
    """
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()           # treat 403/404/500 as failures, not as content
        soup = BeautifulSoup(resp.text, "html.parser")
        # also drop header/aside: they are mostly menus and sidebars, not article text
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:limit]
    except Exception:
        return ""                         # one bad page must not crash the whole pipeline


def scrape_many(sources: list[dict], max_workers: int = 5) -> list[dict]:
    """
    Scrape all source URLs concurrently with threads.
    (requests is blocking, so threads give a near-linear speedup for I/O waits.)
    Adds a "content" key to every source dict.
    """
    urls = [s["url"] for s in sources]

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        # ex.map keeps the input order, so source [1] always stays source [1]
        texts = list(ex.map(scrape_one, urls))

    for s, text in zip(sources, texts):
        if len(text) > 200:
            # keep Tavily's query-relevant snippet AND the start of the page text
            s["content"] = f"Search snippet: {s['snippet'][:800]}\n\nPage text: {text[:2000]}"
            s["scraped"] = True
        else:
            s["content"] = s["snippet"][:1500]   # scrape failed or too short: snippet only
            s["scraped"] = False
    return sources