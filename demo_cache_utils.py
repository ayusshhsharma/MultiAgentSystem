import json
import re
from datetime import datetime, timezone
from pathlib import Path

CACHE_DIR = Path("demo_cache")


def topic_to_slug(topic: str) -> str:
    """Convert topic string to a lowercase slug with non-alphanumerics replaced by '-', max 60 chars."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", topic.lower()).strip("-")
    return slug[:60]


def save_demo_run(topic: str, state: dict, elapsed_seconds: float) -> Path:
    """Save run payload {topic, saved_at, elapsed_seconds, state} as JSON to demo_cache/<slug>.json."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    slug = topic_to_slug(topic)
    file_path = CACHE_DIR / f"{slug}.json"
    data = {
        "topic": topic,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(float(elapsed_seconds), 1),
        "state": state,
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return file_path


def list_saved_runs() -> list[dict]:
    """Return a list of metadata for valid saved runs in demo_cache/."""
    if not CACHE_DIR.is_dir():
        return []
    runs = []
    for p in sorted(CACHE_DIR.glob("*.json")):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "topic" in data and "state" in data:
                runs.append({
                    "topic": data["topic"],
                    "file_path": str(p),
                    "filename": p.name,
                    "saved_at": data.get("saved_at", ""),
                    "elapsed_seconds": data.get("elapsed_seconds", 0.0),
                })
        except Exception:
            continue
    return runs


def load_demo_run(file_path: str | Path) -> dict:
    """Load a saved run JSON file and return the dict {topic, saved_at, elapsed_seconds, state}."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)
