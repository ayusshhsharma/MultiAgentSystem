import os
import socket
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def run_preflight() -> bool:
    print("=" * 60)
    print("MultiAgentSystem - Live Demo Preflight Check")
    print("=" * 60)

    # Check 1: Environment Variables
    tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if tavily_key and groq_key:
        check_1 = True
        print("[PASS] Environment: TAVILY_API_KEY and GROQ_API_KEY are configured.")
    else:
        check_1 = False
        missing = []
        if not tavily_key:
            missing.append("TAVILY_API_KEY")
        if not groq_key:
            missing.append("GROQ_API_KEY")
        print(f"[FAIL] Environment: Missing required key(s) in .env: {', '.join(missing)}")

    # Check 2: DNS Resolution for Tavily
    try:
        ip = socket.gethostbyname("api.tavily.com")
        if ip.startswith("192.0.2."):
            check_2 = False
            print(f"[FAIL] DNS: api.tavily.com resolved to reserved/blocked IP ({ip}).")
            print("       Network is blocking Tavily. Switch to a phone hotspot or use saved demo runs.")
        else:
            check_2 = True
            print(f"[PASS] DNS: api.tavily.com resolved successfully ({ip}).")
    except Exception as e:
        check_2 = False
        print(f"[FAIL] DNS: Could not resolve api.tavily.com: {e}")
        print("       Network is blocking Tavily. Switch to a phone hotspot or use saved demo runs.")

    # Check 3: Groq LLM Connectivity (tiny probe)
    try:
        from agents import llm

        _ = llm.invoke("Hi", max_tokens=5)
        check_3 = True
        print("[PASS] Groq LLM: Model responded successfully.")
    except Exception as e:
        check_3 = False
        err_text = str(e)
        if "429" in err_text or "rate" in err_text.lower() or "quota" in err_text.lower():
            print("[FAIL] Groq LLM: Rate limit or quota reached.")
            print("       Groq quota exhausted. Use saved demo runs.")
        else:
            print(f"[FAIL] Groq LLM check failed: {err_text[:140]}")

    # Check 4: Saved Demo Cache
    cache_dir = Path("demo_cache")
    saved_runs = list(cache_dir.glob("*.json")) if cache_dir.exists() and cache_dir.is_dir() else []
    if saved_runs:
        check_4 = True
        print(f"[PASS] Demo Cache: Found {len(saved_runs)} saved run(s) in demo_cache/.")
    else:
        check_4 = False
        print("[FAIL] Demo Cache: No saved .json runs found in demo_cache/.")

    # Summary Line
    print("-" * 60)
    if check_1 and check_2 and check_3:
        print("READY for live demo")
        return True
    elif check_4:
        print("USE SAVED RUNS (offline mode)")
        return False
    else:
        print("NOT READY")
        return False


if __name__ == "__main__":
    run_preflight()
