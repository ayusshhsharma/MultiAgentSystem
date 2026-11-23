import csv
import random
import re
import statistics
import time

from langchain.chat_models import init_chat_model

from agents import llm                      # same model the pipeline uses
from pipeline import run_research_pipeline

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
# Judge model: ideally DIFFERENT from the writer so it isn't grading its own work.
# Change this if the model isn't available on your Groq account.
JUDGE_MODEL = "groq:qwen/qwen3.8-27b"
judge_llm = init_chat_model(JUDGE_MODEL, temperature=0)
judge_llm.invoke("Reply with the word YES")    # fail fast if the model is unavailable
print(f"Judge model OK: {JUDGE_MODEL}")

MAX_JUDGED_SENTENCES = 10     # cap judge calls per report (rate limits + cost)
SLEEP_BETWEEN_TOPICS = 5      # seconds, avoids Groq / Tavily rate limits
random.seed(42)               # reproducible sentence sampling

TOPICS = [
    # recent / fast-changing (a no-search baseline should struggle here)
    "Major reasons behind the recent fall in gold and silver prices in India",
    "Latest developments in solid-state batteries for electric vehicles",
    "Recent clinical trial progress in mRNA cancer vaccines",
    "Current state of India's semiconductor manufacturing plans",
    "Recent changes in global AI regulation",
    "Current status of green hydrogen projects worldwide",
    "Recent trends in the Indian startup funding environment",
    # technical / conceptual
    "Mixture of Experts vs dense LLMs: architecture and trade-offs",
    "How retrieval-augmented generation reduces LLM hallucinations",
    "Technical bottlenecks in scaling green hydrogen production",
    "Differences between vector databases and traditional databases",
    "How prompt injection attacks work against LLM agents",
    # general / mixed
    "Impact of remote work on urban real estate markets",
    "Causes and effects of microplastics in drinking water",
    "Advantages and risks of nuclear microreactors",
    "How quantum computing could affect modern cryptography",
    "Impact of UPI on digital payments in India",
    "Effects of climate change on Himalayan glaciers",
]

CITE_RE = re.compile(r"\[(\d+)\]")


# ---------------------------------------------------------------------------
# BASELINE: one prompt, no search, no sources
# ---------------------------------------------------------------------------
def run_baseline(topic: str) -> str:
    prompt = (
        f"Write a detailed research report on the topic below.\n\nTopic: {topic}\n\n"
        "Structure: Introduction, Key Findings (minimum 3 well-explained points), "
        "Conclusion. Be detailed, factual and professional."
    )
    return llm.invoke(prompt).content


# ---------------------------------------------------------------------------
# TEXT HELPERS
# ---------------------------------------------------------------------------
def report_body(report: str) -> str:
    """Report text without the code-generated Sources section."""
    return report.split("## Sources")[0]


def key_findings_section(body: str) -> str:
    """Only the Key Findings part (intro/conclusion naturally cite less). Falls back to whole body."""
    m = re.search(r"key findings(.*?)(?:\n[#*\s]*conclusion|\Z)", body, re.I | re.S)
    return m.group(1) if m else body


def get_sentences(text: str) -> list[str]:
    """Split markdown text into sentences, skipping headings and very short fragments."""
    sentences = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"^(\s*[-*•]\s+|\s*\d+\.\s+)", "", line)   # strip bullet / list markers
        line = line.replace("**", "")
        # split on . ! ? followed by a capital letter (so "[2]" after a period stays attached)
        for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", line):
            if len(s) >= 40:
                sentences.append(s.strip())
    return sentences


# ---------------------------------------------------------------------------
# METRICS
# ---------------------------------------------------------------------------
def citation_coverage(report: str) -> float:
    """Share of Key Findings sentences carrying at least one [n] citation."""
    sentences = get_sentences(key_findings_section(report_body(report)))
    if not sentences:
        return 0.0
    return sum(1 for s in sentences if CITE_RE.search(s)) / len(sentences)


def hallucinated_citation_rate(draft: str, n_sources: int) -> float:
    """Share of [n] citations in the RAW draft that point to a non-existent source."""
    cited = [int(n) for n in CITE_RE.findall(report_body(draft))]
    if not cited:
        return 0.0
    return sum(1 for n in cited if not (1 <= n <= n_sources)) / len(cited)


def judge_supported(sentence: str, source_texts: str):
    """LLM-as-judge: does the cited source text support this sentence? Returns True/False/None."""
    prompt = (
        "You are a strict fact-checker. Decide whether the SOURCE TEXT supports the CLAIM.\n"
        "Answer YES only if the claim is directly supported by the source text. "
        "Answer NO if it is unsupported, contradicted, or goes beyond the source.\n"
        "Reply with a single word: YES or NO.\n\n"
        f"CLAIM: {sentence}\n\nSOURCE TEXT:\n{source_texts}"
    )
    for attempt in range(3):
        try:
            raw = judge_llm.invoke(prompt).content
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.S)   # drop reasoning block
            matches = re.findall(r"\b(YES|NO)\b", raw.upper())
            return (matches[-1] == "YES") if matches else None         # last verdict wins
        except Exception as e:
            print("  judge error:", str(e)[:150])
            time.sleep(5 * (attempt + 1))
    return None


def faithfulness(report: str, sources: list[dict]) -> float | None:
    """Share of sampled cited sentences that the cited sources actually support."""
    by_id = {s["id"]: s["content"] for s in sources}
    cited_sentences = [
        s for s in get_sentences(key_findings_section(report_body(report)))
        if CITE_RE.search(s)
    ]
    if not cited_sentences:
        return None
    sample = random.sample(cited_sentences, min(MAX_JUDGED_SENTENCES, len(cited_sentences)))

    verdicts = []
    for sent in sample:
        ids = [int(n) for n in CITE_RE.findall(sent) if int(n) in by_id]
        if not ids:
            verdicts.append(False)                 # cites a non-existent source = unsupported
            continue
        source_texts = "\n\n".join(by_id[i] for i in ids)
        clean = CITE_RE.sub("", sent).strip()      # judge shouldn't see the [n] markers
        v = judge_supported(clean, source_texts)
        if v is not None:
            verdicts.append(v)
    return sum(verdicts) / len(verdicts) if verdicts else None


def words(text: str) -> int:
    return len(text.split())


# ---------------------------------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------------------------------
FIELDS = [
    "topic", "baseline_latency_s", "pipeline_latency_s", "baseline_words", "pipeline_words",
    "n_sources", "scrape_rate", "citation_coverage", "hallucinated_cite_rate",
    "faithfulness", "error",
]


def evaluate():
    rows = []
    with open("eval_results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()

        for i, topic in enumerate(TOPICS, 1):
            print(f"\n[{i}/{len(TOPICS)}] {topic}")
            row = {k: "" for k in FIELDS}
            row["topic"] = topic
            try:
                # --- baseline ---
                t0 = time.perf_counter()
                base_report = run_baseline(topic)
                row["baseline_latency_s"] = round(time.perf_counter() - t0, 1)
                row["baseline_words"] = words(base_report)

                # --- pipeline ---
                t0 = time.perf_counter()
                state = run_research_pipeline(topic)
                row["pipeline_latency_s"] = round(time.perf_counter() - t0, 1)

                sources = state["sources"]
                row["pipeline_words"] = words(report_body(state["report"]))
                row["n_sources"] = len(sources)
                row["scrape_rate"] = round(sum(1 for s in sources if s["scraped"]) / len(sources), 3)
                row["citation_coverage"] = round(citation_coverage(state["report"]), 3)
                row["hallucinated_cite_rate"] = round(
                    hallucinated_citation_rate(state["draft"], len(sources)), 3
                )
                faith = faithfulness(state["report"], sources)
                row["faithfulness"] = round(faith, 3) if faith is not None else ""
            except Exception as e:
                row["error"] = str(e)[:200]
                print("  FAILED:", row["error"])

            writer.writerow(row)
            f.flush()                              # keep partial results if the run is interrupted
            rows.append(row)
            time.sleep(SLEEP_BETWEEN_TOPICS)

    write_summary(rows)


def mean(rows, key):
    vals = [float(r[key]) for r in rows if r[key] != "" and not r["error"]]
    return statistics.mean(vals) if vals else float("nan")


def write_summary(rows):
    ok = [r for r in rows if not r["error"]]
    summary = f"""## Evaluation Results ({len(ok)}/{len(rows)} topics completed)

| Metric | Baseline (single prompt, no search) | MultiAgentSystem pipeline |
| :--- | :--- | :--- |
| Avg latency (s) | {mean(ok, 'baseline_latency_s'):.1f} | {mean(ok, 'pipeline_latency_s'):.1f} |
| Avg report length (words) | {mean(ok, 'baseline_words'):.0f} | {mean(ok, 'pipeline_words'):.0f} |
| Sources used per report | 0 | {mean(ok, 'n_sources'):.1f} |
| Page scrape success rate | n/a | {mean(ok, 'scrape_rate'):.0%} |
| Citation coverage (Key Findings) | 0% | {mean(ok, 'citation_coverage'):.0%} |
| Hallucinated citation rate (raw draft) | n/a | {mean(ok, 'hallucinated_cite_rate'):.0%} |
| Faithfulness (LLM-judged, sampled) | not verifiable | {mean(ok, 'faithfulness'):.0%} |
"""
    print("\n" + summary)
    with open("eval_summary.md", "w", encoding="utf-8") as f:
        f.write(summary)


if __name__ == "__main__":
    evaluate()