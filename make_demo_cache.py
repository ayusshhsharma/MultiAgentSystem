import time
from pathlib import Path
from pipeline import run_research_pipeline
from demo_cache_utils import save_demo_run, topic_to_slug, CACHE_DIR

DEMO_TOPICS = [
    "Major reasons behind the recent fall in gold and silver prices in India",
    "Mixture of Experts vs dense LLMs: architecture and trade-offs",
    "Impact of UPI on digital payments in India",
]

SLEEP_BETWEEN_TOPICS = 10  # seconds, helps avoid Groq / Tavily rate limits


def generate_demo_cache():
    print("=" * 60)
    print("MultiAgentSystem - Pre-generating Demo Cache")
    print(f"Target directory: {CACHE_DIR.resolve()}")
    print("=" * 60)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    for i, topic in enumerate(DEMO_TOPICS, 1):
        slug = topic_to_slug(topic)
        target_file = CACHE_DIR / f"{slug}.json"

        print(f"\n[{i}/{len(DEMO_TOPICS)}] Topic: {topic}")

        if target_file.exists():
            print(f"  -> Skipping: already cached at {target_file.name}")
            continue

        print("  -> Running research pipeline...")
        t0 = time.perf_counter()
        try:
            state = run_research_pipeline(topic)
            elapsed = round(time.perf_counter() - t0, 1)
            saved_path = save_demo_run(topic, state, elapsed)
            print(f"  -> Success! Saved to {saved_path.name} in {elapsed}s")
        except Exception as e:
            print(f"  -> FAILED: {e}")

        if i < len(DEMO_TOPICS):
            print(f"  -> Sleeping {SLEEP_BETWEEN_TOPICS}s before next topic...")
            time.sleep(SLEEP_BETWEEN_TOPICS)

    print("\n" + "=" * 60)
    print("Demo cache generation process finished.")
    print("=" * 60)


if __name__ == "__main__":
    generate_demo_cache()
