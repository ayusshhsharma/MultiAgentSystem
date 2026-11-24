# ============================================================
# 1. IMPORT REQUIRED LIBRARIES
# ============================================================

import time
import streamlit as st
from pipeline import run_research_pipeline
from demo_cache_utils import save_demo_run, list_saved_runs, load_demo_run


# ============================================================
# 2. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Multi-Agent Research System",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# 3. CUSTOM CSS
# ============================================================

st.markdown("""
<style>

    /* Main application background */
    .stApp {
        background-color: #0E1117;
    }

    /* Main title */
    .main-title {
        font-size: 38px;
        font-weight: 750;
        color: #FFFFFF;
        margin-bottom: 5px;
    }

    /* Subtitle */
    .subtitle {
        color: #A0AEC0;
        font-size: 16px;
        margin-bottom: 25px;
    }

    /* Result cards */
    .info-card {
        background-color: #1C2333;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #30394D;
        margin-bottom: 15px;
    }

    /* Agent labels */
    .agent-label {
        color: #60A5FA;
        font-size: 14px;
        font-weight: bold;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #151B27;
    }

    /* Buttons */
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        height: 45px;
        font-weight: 600;
    }

</style>
""", unsafe_allow_html=True)


# ============================================================
# 4. SIDEBAR
# ============================================================

with st.sidebar:

    st.title("🔬 Research AI")

    st.caption("Multi-Agent Research Platform")

    st.divider()

    st.subheader("Research Workflow")

    st.markdown("""
    **01.** 🔎 Search Agent

    Finds up to 5 recent, relevant sources.

    **02.** 📖 Parallel Scraper

    Scrapes all sources at the same time.

    **03.** ✍️ Writer Agent

    Writes the report with inline [1] citations.

    **04.** 🧐 Critic Agent

    Reviews the generated report.
    """)

    st.divider()

    # SECTION: SAVED DEMO RUNS (Replay offline)
    st.subheader("Saved Demo Runs")
    saved_runs = list_saved_runs()
    if saved_runs:
        topic_options = [r["topic"] for r in saved_runs]
        selected_topic = st.selectbox(
            "Select a pre-generated run",
            topic_options,
            key="saved_demo_topic"
        )
        if st.button("📂 Load Saved Run", use_container_width=True):
            chosen = next(r for r in saved_runs if r["topic"] == selected_topic)
            payload = load_demo_run(chosen["file_path"])
            st.session_state["research_state"] = payload["state"]
            st.session_state["research_topic"] = payload["topic"]
            st.session_state["is_saved_run"] = True
            st.session_state["elapsed_seconds"] = payload.get("elapsed_seconds", 0.0)
            st.rerun()
    else:
        st.caption("No saved demo runs yet. Generate runs via make_demo_cache.py or run a topic live.")

    st.divider()

    st.subheader("Technology Stack")

    st.markdown("""
    - Python
    - LangChain
    - LangGraph
    - Groq LLM
    - Tavily Search
    - BeautifulSoup
    - Streamlit
    """)

    st.divider()

    st.caption("Powered by your Multi-Agent Research Pipeline")


# ============================================================
# 5. MAIN HEADER
# ============================================================

st.markdown(
    '<div class="main-title">Multi-Agent Research System</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Research any topic using intelligent AI agents, '
    'web search, parallel webpage scraping and cited report generation.'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# 6. RESEARCH INPUT SECTION
# ============================================================

st.markdown("### Start a New Research")

topic = st.text_area(
    "Enter your research topic",
    placeholder=(
        "Example: What are the major reasons behind "
        "the downfall of gold and silver prices in India?"
    ),
    height=100
)

st.caption(
    "💡 **Example topics:** "
    "`Major reasons behind the recent fall in gold and silver prices in India` • "
    "`Mixture of Experts vs dense LLMs: architecture and trade-offs` • "
    "`Impact of UPI on digital payments in India`"
)

start_research = st.button(
    "🚀 Start Research",
    type="primary",
    use_container_width=True
)


# ============================================================
# 7. EXECUTE RESEARCH PIPELINE
# ============================================================

if start_research:

    if not topic.strip():

        st.warning("Please enter a research topic first.")

    else:

        clean_topic = topic.strip()
        t0 = time.perf_counter()

        try:
            # Wrap pipeline call in live st.status
            with st.status("Your AI research team is working...", expanded=True) as status:

                def progress_callback(step_num: int, message: str):
                    status.update(label=f"Step {step_num}/4: {message}...")
                    st.write(f"✓ **Step {step_num}:** {message}")

                research_state = run_research_pipeline(clean_topic, on_progress=progress_callback)
                elapsed = round(time.perf_counter() - t0, 1)
                status.update(
                    label=f"Research complete in {elapsed}s!",
                    state="complete",
                    expanded=False
                )

            # Auto-save payload for offline replay
            save_demo_run(clean_topic, research_state, elapsed)

            # Store results in session state
            st.session_state["research_state"] = research_state
            st.session_state["research_topic"] = clean_topic
            st.session_state["is_saved_run"] = False
            st.session_state["elapsed_seconds"] = elapsed

            st.success(f"Research completed successfully in {elapsed}s!")

        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "rate limit" in err_msg.lower():
                st.warning("The LLM rate limit was reached. Load a saved run from the sidebar to continue the demo.")
            elif any(term in err_msg for term in ["NameResolutionError", "Max retries exceeded", "Failed to resolve"]):
                st.warning("Network problem reaching the search API. Switch network (phone hotspot) or load a saved run.")
            else:
                st.error("Something went wrong while running the research pipeline.")

            with st.expander("View error details"):
                st.exception(e)


# ============================================================
# 8. DISPLAY RESEARCH RESULTS
# ============================================================

if "research_state" in st.session_state:

    state = st.session_state["research_state"]
    research_topic = st.session_state["research_topic"]
    is_saved = st.session_state.get("is_saved_run", False)
    elapsed = st.session_state.get("elapsed_seconds")

    # Structured sources from pipeline.py (list of dicts)
    sources = state.get("sources", [])
    scraped_count = sum(1 for s in sources if s.get("scraped"))

    st.divider()

    st.markdown("## 📊 Research Results")
    st.markdown(f"**Research Topic:** {research_topic}")

    if is_saved:
        st.caption("ℹ️ *Loaded from saved run (offline)*")
    elif elapsed:
        st.caption(f"⏱️ *Generated live in {elapsed}s*")

    # Display workflow status
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.success(f"✓ Search Complete ({len(sources)} sources)")

    with col2:
        if sources and scraped_count == 0:
            st.warning("⚠ All pages fell back to snippets")
        else:
            st.success(f"✓ Scraped {scraped_count}/{len(sources)} pages")

    with col3:
        st.success("✓ Report Generated")

    with col4:
        st.success("✓ Critic Review Complete")

    st.divider()

    # Create result tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔎 Search Results",
        "📖 Scraped Content",
        "📝 Final Report",
        "🧐 Critic Review"
    ])

    # --------------------------------------------------------
    # TAB 1: SEARCH RESULTS
    # --------------------------------------------------------

    with tab1:
        st.subheader("Search Agent Output")

        if sources:
            st.dataframe(
                [
                    {
                        "#": s["id"],
                        "Title": s["title"],
                        "URL": s["url"],
                        "Scraped": "✅" if s.get("scraped") else "⚠️ snippet",
                        "Chars used": len(s["content"]),
                    }
                    for s in sources
                ],
                column_config={
                    "URL": st.column_config.LinkColumn("URL"),
                },
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.markdown(state.get("search_results", "") or "No search results available.")

    # --------------------------------------------------------
    # TAB 2: SCRAPED CONTENT
    # --------------------------------------------------------

    with tab2:
        st.subheader("Scraped Content (per source)")

        if sources:
            for s in sources:
                icon = "✅" if s.get("scraped") else "⚠️"
                with st.expander(f"{icon} [{s['id']}] {s['title']}"):
                    st.markdown(f"**URL:** {s['url']}")
                    if not s.get("scraped"):
                        st.caption("Scraping failed or returned too little text, so the search snippet was used.")
                    st.text(s["content"])
        else:
            st.markdown(state.get("scraped_content", "") or "No scraped content available.")

    # --------------------------------------------------------
    # TAB 3: FINAL REPORT
    # --------------------------------------------------------

    with tab3:
        st.subheader("Generated Research Report")

        report = state.get("report", "")
        st.markdown(report or "No report generated.")

        if report:
            st.download_button(
                label="⬇️ Download Research Report",
                data=str(report),
                file_name="research_report.md",
                mime="text/markdown"
            )

    # --------------------------------------------------------
    # TAB 4: CRITIC REVIEW
    # --------------------------------------------------------

    with tab4:
        st.subheader("Critic Agent Feedback")

        feedback = state.get("feedback", "")
        st.markdown(feedback or "No critic feedback available.")
