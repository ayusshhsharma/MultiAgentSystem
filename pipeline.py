import re
from agents import writer_chain, critic_chain      # CHANGED: search/reader agents are no longer needed
from tools import search_sources, scrape_many      # NEW: structured search + parallel scraping


# ---------------------------------------------------------------------------
# NEW helper: build the numbered context the Writer will cite from
# ---------------------------------------------------------------------------
def build_context(sources: list[dict]) -> str:
    blocks = []
    for s in sources:
        blocks.append(
            f"[{s['id']}] {s['title']}\n"
            f"URL: {s['url']}\n"
            f"<content>\n{s['content']}\n</content>"   # tags mark scraped text as untrusted data
        )
    return "\n\n".join(blocks)


# ---------------------------------------------------------------------------
# NEW helper: validate citations and build the Sources section in code
# ---------------------------------------------------------------------------
def finalize_citations(report: str, sources: list[dict]) -> str:
    valid_ids = {s["id"] for s in sources}
    by_id = {s["id"]: s for s in sources}

    # 1. remove citations that point to source numbers that don't exist (hallucinated)
    def drop_invalid(match):
        return match.group(0) if int(match.group(1)) in valid_ids else ""
    report = re.sub(r"\[(\d+)\]", drop_invalid, report)

    # 2. collect the citation numbers that are actually used in the text
    cited = sorted({int(n) for n in re.findall(r"\[(\d+)\]", report)})

    # 3. build the Sources section ourselves so URLs can never be hallucinated or reordered
    lines = ["\n\n## Sources"]
    for n in cited:
        lines.append(f"{n}. [{by_id[n]['title']}]({by_id[n]['url']})")
    return report + "\n".join(lines)


def run_research_pipeline(topic : str)->dict:

    state ={}
    # step 1 - search (now a direct Tavily call, returns structured sources)
    print("\n "+ "="*50)
    print("step 1 - searching the web ...")
    print("="*50)

    sources = search_sources(topic, max_results=5)

    # keep the old text format in state so app.py's "Search Results" tab still works
    state["search_results"] = "\n------------------\n".join(
        f"[{s['id']}] Title: {s['title']}\nLink: {s['url']}\nSnippet: {s['snippet'][:300]}\n"
        for s in sources
    )

    print("\n search result ",state['search_results'])

    # step 2 - scrape ALL sources in parallel (replaces the Reader agent)
    print("\n"+" ="*50)
    print("step 2 - scraping all sources in parallel ...")
    print("="*50)

    sources = scrape_many(sources, max_workers=5)

    # old-style text version for the "Scraped Content" tab
    state['scraped_content'] = "\n\n".join(
        f"[{s['id']}] {s['url']} ({'scraped' if s['scraped'] else 'snippet fallback'})\n{s['content']}"
        for s in sources
    )
    state["sources"] = sources        # NEW: structured data for tables / ✅⚠️ status in the UI

    print("\nscraped content: \n", state['scraped_content'])

    #step 3 - writer chain

    print("\n"+" ="*50)
    print("step 3 - Writer is drafting the report ...")
    print("="*50)

    research_combined = build_context(sources)   # CHANGED: numbered sources instead of raw text

    draft = writer_chain.invoke({
        "topic" : topic,
        "research" : research_combined
    })

    state["draft"] = draft
    # NEW: strip invalid [n] citations and append a code-generated Sources section
    state["report"] = finalize_citations(draft, sources)

    print("\n Final Report\n",state['report'])

    #critic report

    print("\n"+" ="*50)
    print("step 4 - critic is reviewing the report ")
    print("="*50)

    state["feedback"] = critic_chain.invoke({
        "report":state['report']
    })

    print("\n critic report \n", state['feedback'])

    return state



if __name__ == "__main__":
    topic = input("\n Enter a research topic : ")
    run_research_pipeline(topic)