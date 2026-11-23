# ============================================================
# 1. IMPORT REQUIRED LIBRARIES
# ============================================================

import streamlit as st
from pipeline import run_research_pipeline


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
# 3. CUSTOM CSS  (unchanged)
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

    # CHANGED: Reader Agent replaced by parallel scraping, citations mentioned
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
    'web search, parallel webpage scraping and cited report generation.'   # CHANGED
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

        try:

            # Show progress indicator
            with st.spinner(
                "Your AI research team is working... "
                "This may take a few minutes."
            ):

                # Call the existing pipeline
                research_state = run_research_pipeline(topic.strip())

            # Store results in session state
            st.session_state["research_state"] = research_state
            st.session_state["research_topic"] = topic.strip()

            st.success("Research completed successfully!")

        except Exception as e:

            st.error("Something went wrong while running the research pipeline.")

            with st.expander("View error details"):
                st.exception(e)


# ============================================================
# 8. DISPLAY RESEARCH RESULTS
# ============================================================

if "research_state" in st.session_state:

    state = st.session_state["research_state"]

    research_topic = st.session_state["research_topic"]

    # NEW: structured sources from pipeline.py (list of dicts), empty list if missing
    sources = state.get("sources", [])
    scraped_count = sum(1 for s in sources if s.get("scraped"))

    st.divider()

    st.markdown("## 📊 Research Results")

    st.markdown(f"**Research Topic:** {research_topic}")

    # Display workflow status
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # CHANGED: shows how many sources were found
        st.success(f"✓ Search Complete ({len(sources)} sources)")

    with col2:
        # CHANGED: shows scrape success rate, warning if every page failed
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

        # CHANGED: clickable table instead of a raw text blob
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
                    "URL": st.column_config.LinkColumn("URL"),   # makes links clickable
                },
                hide_index=True,
                use_container_width=True,
            )
        else:
            # fallback to the old text output if sources are missing
            st.markdown(state.get("search_results", "") or "No search results available.")

    # --------------------------------------------------------
    # TAB 2: SCRAPED CONTENT
    # --------------------------------------------------------

    with tab2:

        st.subheader("Scraped Content (per source)")   # CHANGED title

        # CHANGED: one expander per source, with a status icon
        if sources:
            for s in sources:
                icon = "✅" if s.get("scraped") else "⚠️"
                with st.expander(f"{icon} [{s['id']}] {s['title']}"):
                    st.markdown(f"**URL:** {s['url']}")
                    if not s.get("scraped"):
                        st.caption("Scraping failed or returned too little text, so the search snippet was used.")
                    st.text(s["content"])
        else:
            # fallback to the old text output
            st.markdown(state.get("scraped_content", "") or "No scraped content available.")

    # --------------------------------------------------------
    # TAB 3: FINAL REPORT
    # --------------------------------------------------------

    with tab3:

        st.subheader("Generated Research Report")

        report = state.get("report", "")

        # unchanged: the report already contains [n] citations and a ## Sources section
        st.markdown(report or "No report generated.")

        if report:

            st.download_button(
                label="⬇️ Download Research Report",
                data=str(report),
                file_name="research_report.md",
                mime="text/markdown"
            )

    # --------------------------------------------------------
    # TAB 4: CRITIC REVIEW  (unchanged)
    # --------------------------------------------------------

    with tab4:

        st.subheader("Critic Agent Feedback")

        feedback = state.get("feedback", "")

        st.markdown(
            feedback or "No critic feedback available."
        )