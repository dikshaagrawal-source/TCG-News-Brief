"""
TCG Daily News Brief — Streamlit Dashboard
Team dashboard for generating, viewing, and emailing the daily news brief.

To run locally:  streamlit run app.py
To deploy free:  https://share.streamlit.io → connect your GitHub repo
"""

import streamlit as st
import os
import subprocess
from datetime import datetime, timezone
from collections import defaultdict
from dotenv import load_dotenv

# Load .env for local development
load_dotenv()

from news_fetcher import fetch_all_articles, Article
from ai_summarizer import summarize_all, organize_by_section, BriefEntry
from sources_config import TCG_SECTIONS, SECTION_ORDER, DOMESTIC_SECTIONS, WORLD_SECTIONS, SOURCES
from emailer import send_brief_email

# ─── Page Config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="TCG News Brief Generator",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ──────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* TCG brand feel */
    .main-title {
        font-size: 2rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0;
    }
    .subtitle {
        color: #6c757d;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    .section-header {
        background: #1a1a2e;
        color: white;
        padding: 6px 14px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 1.5px;
        margin: 1.2rem 0 0.5rem 0;
        display: inline-block;
    }
    .subsection-header {
        color: #1a1a2e;
        font-weight: 700;
        font-size: 0.8rem;
        letter-spacing: 1px;
        border-bottom: 2px solid #1a1a2e;
        padding-bottom: 3px;
        margin: 1rem 0 0.4rem 0;
    }
    .brief-entry {
        background: #f8f9fa;
        border-left: 3px solid #1a1a2e;
        padding: 10px 14px;
        margin: 8px 0;
        border-radius: 0 4px 4px 0;
        font-size: 0.88rem;
        line-height: 1.6;
    }
    .citation {
        color: #6c757d;
        font-size: 0.78rem;
        margin-top: 4px;
    }
    .entry-type-badge {
        background: #e9ecef;
        color: #495057;
        padding: 1px 6px;
        border-radius: 3px;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        margin-right: 4px;
    }
    .stButton > button {
        background-color: #1a1a2e;
        color: white;
        border: none;
        padding: 0.5rem 1.5rem;
        border-radius: 4px;
        font-weight: 600;
    }
    .stButton > button:hover {
        background-color: #2d2d5e;
    }
    .metric-card {
        background: white;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 12px 16px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def render_markdown_bold(text: str) -> str:
    """Convert **bold** markers to HTML <strong> for display."""
    import re
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def entry_to_html(entry: BriefEntry, initials: str) -> str:
    """Render a single brief entry as HTML."""
    prefix_html = ""
    if entry.entry_type == "OPINION":
        author_str = entry.author if entry.author else ""
        badge = f'<span class="entry-type-badge">OPINION</span>{author_str} — ' if author_str else '<span class="entry-type-badge">OPINION</span> '
        prefix_html = badge
    elif entry.entry_type == "ANALYSIS":
        prefix_html = f'<span class="entry-type-badge">ANALYSIS</span> {entry.source_abbrev} — '
    elif entry.entry_type == "POLL":
        prefix_html = '<span class="entry-type-badge">POLL</span> '
    elif entry.entry_type == "TREND":
        prefix_html = '<span class="entry-type-badge">TREND</span> '

    summary_html = render_markdown_bold(entry.summary)
    link = entry.article.url
    citation = entry.citation(initials)

    return f"""
    <div class="brief-entry">
        {prefix_html}{summary_html}
        <div class="citation">
            <a href="{link}" target="_blank">🔗 Read article</a> &nbsp;|&nbsp; {citation}
        </div>
    </div>"""


def balance_article_selection(articles: list, max_articles: int) -> list:
    """
    When summarizing ≥20 articles, round-robin across sources so no single
    source dominates and the brief covers more sections.
    """
    by_source = defaultdict(list)
    for art in articles:
        by_source[art.source_name].append(art)

    result = []
    source_lists = list(by_source.values())
    idx = 0
    while len(result) < max_articles and any(source_lists):
        lst = source_lists[idx % len(source_lists)]
        if lst:
            result.append(lst.pop(0))
        idx += 1
    return result


def get_git_version() -> str:
    """Return short git commit hash, or empty string if unavailable."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=3,
            cwd=os.path.dirname(__file__) or ".",
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return ""


def brief_to_plain_text(organized: dict, initials: str) -> str:
    """Convert organized brief to plain text for copying/emailing."""
    lines = []
    lines.append("THE COMMON GOOD — DAILY NEWS BRIEF")
    lines.append(f"Generated {datetime.now().strftime('%A, %B %-d, %Y')}")
    lines.append("=" * 60)
    lines.append("")

    prev_group = None
    for section_key in SECTION_ORDER:
        if section_key not in organized:
            continue
        entries = organized[section_key]
        if not entries:
            continue

        # Group headers
        if section_key == "NOTABLE":
            lines.append("━━━ NOTABLE ━━━")
            lines.append("")
        elif section_key in DOMESTIC_SECTIONS and prev_group != "DOMESTIC":
            lines.append("━━━ DOMESTIC ━━━")
            lines.append("")
            prev_group = "DOMESTIC"
        elif section_key in WORLD_SECTIONS and prev_group != "WORLD":
            lines.append("")
            lines.append("━━━ WORLD ━━━")
            lines.append("")
            prev_group = "WORLD"

        if section_key != "NOTABLE":
            lines.append(f"[ {TCG_SECTIONS[section_key].upper()} ]")

        for entry in entries:
            import re
            summary_plain = re.sub(r"\*\*(.+?)\*\*", r"\1", entry.summary)
            prefix = ""
            if entry.entry_type == "OPINION":
                prefix = f"OPINION | {entry.author} — " if entry.author else "OPINION — "
            elif entry.entry_type == "ANALYSIS":
                prefix = f"ANALYSIS | {entry.source_abbrev} — "
            elif entry.entry_type == "POLL":
                prefix = "POLL | "
            elif entry.entry_type == "TREND":
                prefix = "TREND — "
            lines.append(f"• {prefix}{summary_plain}")
            lines.append(f"  {entry.article.url}")
            lines.append(f"  {entry.citation(initials)}")
            lines.append("")

    return "\n".join(lines)


# ─── Session State ────────────────────────────────────────────────────────────

if "brief_data" not in st.session_state:
    st.session_state.brief_data = None  # dict with organized entries + metadata
if "is_generating" not in st.session_state:
    st.session_state.is_generating = False


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Placeholder_image.svg/200px-Placeholder_image.svg.png",
             width=60)  # Replace with TCG logo if available
    st.markdown("### ⚙️ Settings")
    st.divider()

    time_interval = st.selectbox(
        "📅 Time interval",
        options=[6, 12, 24, 48],
        index=2,  # default: 24h
        format_func=lambda h: f"Last {h} hours",
        help="How far back to pull articles"
    )

    initials = st.text_input(
        "👤 Your initials",
        value="TCG",
        max_chars=4,
        help="Used in citations, e.g. (NYTimes) DA 6/14"
    ).upper()

    max_articles = st.slider(
        "📄 Max articles to summarize",
        min_value=5,
        max_value=100,
        value=40,
        step=5,
        help="More articles = more holistic coverage across all sections. 40 recommended for a full brief."
    )

    st.divider()
    st.markdown("### 📰 Sources")
    all_source_names = sorted(SOURCES.keys())
    source_mode = st.radio(
        "Which sources?",
        options=["All sources", "Select sources"],
        horizontal=True,
    )
    if source_mode == "Select sources":
        selected_sources = st.multiselect(
            "Choose sources",
            options=all_source_names,
            default=all_source_names,
            help="Uncheck sources you want to skip for this run.",
        )
        if not selected_sources:
            st.warning("Pick at least one source.")
            selected_sources = all_source_names
    else:
        selected_sources = None  # None = all sources

    st.divider()
    st.markdown("### 📧 Email Settings")
    email_recipients = st.text_area(
        "Recipients (one per line)",
        value=os.environ.get("EMAIL_RECIPIENTS", "tcgnews@thecommongood.net"),
        height=80,
    )

    st.divider()
    st.markdown("### 🔑 API Status")
    groq_ok   = bool(os.environ.get("GROQ_API_KEY"))
    email_ok  = bool(os.environ.get("RESEND_API_KEY") or os.environ.get("SMTP_PASSWORD"))
    st.markdown(f"{'✅' if groq_ok  else '❌'} Groq API key (AI)")
    st.markdown(f"{'✅' if email_ok else '⚠️'} Email ({'Resend' if os.environ.get('RESEND_API_KEY') else 'not configured'})")

    if not groq_ok:
        st.error("Add GROQ_API_KEY to your .env file.\nGet a free key at https://console.groq.com")
    if not email_ok:
        st.info("No email set up yet — you can still generate and download briefs.\nAdd RESEND_API_KEY to .env to enable email.")


# ─── Main Content ─────────────────────────────────────────────────────────────

st.markdown('<p class="main-title">📰 TCG Daily News Brief</p>', unsafe_allow_html=True)
st.markdown(
    f'<p class="subtitle">The Common Good — Automated news aggregator | '
    f'{datetime.now().strftime("%A, %B %-d, %Y")}</p>',
    unsafe_allow_html=True
)

col_gen, col_email, col_copy = st.columns([2, 1.5, 1.5])

with col_gen:
    generate_btn = st.button(
        f"▶ Generate Brief (last {time_interval}h)",
        disabled=st.session_state.is_generating or not groq_ok,
        use_container_width=True,
    )

with col_email:
    email_btn = st.button(
        "📧 Email Brief",
        disabled=st.session_state.brief_data is None,
        use_container_width=True,
    )

with col_copy:
    if st.session_state.brief_data:
        plain = brief_to_plain_text(st.session_state.brief_data["organized"], initials)
        st.download_button(
            "⬇ Download .txt",
            data=plain,
            file_name=f"tcg_brief_{datetime.now().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    else:
        st.button("⬇ Download .txt", disabled=True, use_container_width=True)

st.divider()

# ─── Generation ───────────────────────────────────────────────────────────────

if generate_btn:
    st.session_state.is_generating = True
    st.session_state.brief_data = None

    progress_bar  = st.progress(0, text="Starting...")
    status_text   = st.empty()

    # Step 1: Fetch RSS
    status_text.markdown("**Step 1/2 — Fetching articles from sources...**")
    fetch_progress = st.empty()

    articles_list = []
    source_counts = {}

    def fetch_progress_cb(source_name, current, total):
        pct = int((current / total) * 50)  # first half of progress bar
        progress_bar.progress(pct, text=f"Fetching: {source_name}...")
        fetch_progress.caption(f"Checked {current}/{total} sources")

    articles_list = fetch_all_articles(
        max_age_hours=time_interval,
        enrich_text=True,
        progress_callback=fetch_progress_cb,
        selected_sources=selected_sources,
    )

    for art in articles_list:
        source_counts[art.source_name] = source_counts.get(art.source_name, 0) + 1

    fetch_progress.empty()

    if not articles_list:
        st.warning("No articles found in the selected time window. Try a longer interval.")
        st.session_state.is_generating = False
        st.stop()

    # Balance article selection for diversity when running ≥20
    if max_articles >= 20:
        articles_list = balance_article_selection(articles_list, max_articles)
    else:
        articles_list = articles_list[:max_articles]

    # Step 2: AI Summarization
    eta_mins = round((len(articles_list) * 20) / 60, 1)
    status_text.markdown(f"**Step 2/2 — Summarizing {len(articles_list)} articles with AI...**  \n_This will take ~{eta_mins} minutes on the free plan. Please keep this tab open._")
    summ_progress = st.empty()

    entries: list[BriefEntry] = []

    def summ_progress_cb(source_name, current, total):
        pct = 50 + int((current / total) * 50)
        eta_min = round(((total - current) * 4.5) / 60, 1)
        progress_bar.progress(pct, text=f"AI summarizing {current}/{total} ({source_name})...")
        summ_progress.caption(f"~{eta_min} min remaining")

    try:
        entries = summarize_all(
            articles_list,
            progress_callback=summ_progress_cb,
            max_articles=max_articles,
        )
    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        summ_progress.empty()
        st.session_state.is_generating = False
        err = str(e)
        if "api_key" in err.lower() or "invalid" in err.lower() or "401" in err or "403" in err:
            st.error(
                "❌ **Groq API key is invalid.**\n\n"
                "Get a valid free key at https://console.groq.com → API Keys, "
                "then update your `.env` file with `GROQ_API_KEY=gsk_...`"
            )
        elif "quota" in err.lower() or "429" in err:
            st.error("❌ **Groq rate limit hit.** Wait a minute and try again, or reduce Max articles in the sidebar.")
        else:
            st.error(f"❌ **AI summarization failed:** {e}")
        st.stop()

    organized = organize_by_section(entries)

    # Save results
    st.session_state.brief_data = {
        "organized": organized,
        "total_articles": len(articles_list),
        "total_entries": len(entries),
        "source_counts": source_counts,
        "generated_at": datetime.now(timezone.utc),
        "interval_hours": time_interval,
    }

    progress_bar.empty()
    status_text.empty()
    summ_progress.empty()
    st.session_state.is_generating = False
    st.rerun()


# ─── Email ────────────────────────────────────────────────────────────────────

if email_btn and st.session_state.brief_data:
    recipients = [r.strip() for r in email_recipients.splitlines() if r.strip()]
    if not recipients:
        st.error("No email recipients specified.")
    elif not email_ok:
        st.error("No email credentials configured.\nAdd RESEND_API_KEY to your .env file (free at resend.com).")
    else:
        with st.spinner("Sending email..."):
            plain = brief_to_plain_text(st.session_state.brief_data["organized"], initials)
            try:
                send_brief_email(
                    recipients=recipients,
                    subject=f"TCG Daily Brief — {datetime.now().strftime('%B %-d, %Y')}",
                    body_text=plain,
                )
                st.success(f"✅ Brief emailed to {', '.join(recipients)}")
            except Exception as e:
                st.error(f"Email failed: {e}")


# ─── Display Brief ────────────────────────────────────────────────────────────

if st.session_state.brief_data:
    data = st.session_state.brief_data
    organized = data["organized"]

    # Stats row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Articles scanned", data["total_articles"])
    m2.metric("Summaries created", data["total_entries"])
    m3.metric("Sources covered",   len(data["source_counts"]))
    m4.metric("Time window",       f"{data['interval_hours']}h")

    st.caption(f"Generated at {data['generated_at'].strftime('%H:%M UTC')}")
    st.divider()

    # Section tabs
    tab_all, tab_notable, tab_domestic, tab_world = st.tabs(
        ["📋 All Sections", "⭐ Notable", "🇺🇸 Domestic", "🌍 World"]
    )

    def render_sections(tab, section_filter=None):
        with tab:
            prev_group = None
            for section_key in SECTION_ORDER:
                if section_key not in organized:
                    continue
                if section_filter and section_key not in section_filter:
                    continue
                entries = organized[section_key]
                if not entries:
                    continue

                # Group labels
                if section_key == "NOTABLE" and section_filter is None:
                    st.markdown('<div class="section-header">NOTABLE</div>', unsafe_allow_html=True)
                elif section_key in DOMESTIC_SECTIONS and prev_group != "DOMESTIC" and section_filter is None:
                    st.markdown('<div class="section-header">DOMESTIC</div>', unsafe_allow_html=True)
                    prev_group = "DOMESTIC"
                elif section_key in WORLD_SECTIONS and prev_group != "WORLD" and section_filter is None:
                    st.markdown('<div class="section-header">WORLD</div>', unsafe_allow_html=True)
                    prev_group = "WORLD"

                if section_key != "NOTABLE":
                    st.markdown(f'<div class="subsection-header">{TCG_SECTIONS[section_key].upper()}</div>',
                                unsafe_allow_html=True)

                for entry in entries:
                    st.markdown(entry_to_html(entry, initials), unsafe_allow_html=True)

    render_sections(tab_all)
    render_sections(tab_notable,  section_filter={"NOTABLE"})
    render_sections(tab_domestic, section_filter=DOMESTIC_SECTIONS)
    render_sections(tab_world,    section_filter=WORLD_SECTIONS)

else:
    # Empty state
    st.markdown("""
    <div style="text-align:center; padding: 60px 20px; color: #6c757d;">
        <div style="font-size: 3rem;">📰</div>
        <h3 style="color: #1a1a2e;">No brief generated yet</h3>
        <p>Select a time interval in the sidebar and click <strong>Generate Brief</strong> to get started.</p>
        <p style="font-size:0.85rem;">First run takes a few minutes (one API call per article).</p>
    </div>
    """, unsafe_allow_html=True)

    # API setup help if needed
    if not groq_ok:
        with st.expander("🔑 How to get your free Groq API key", expanded=True):
            st.markdown("""
1. Go to **[https://console.groq.com](https://console.groq.com)**
2. Sign up with any email (free)
3. Go to **API Keys → Create API Key** → copy it
4. Add it to your `.env` file:
   ```
   GROQ_API_KEY=gsk_your_key_here
   ```
5. Restart the app — that's it! Groq is free with no daily limits.
            """)

# ─── Git Version Footer ───────────────────────────────────────────────────────

_git_ver = get_git_version()
if _git_ver:
    st.markdown(
        f'<div style="position:fixed;bottom:10px;right:14px;'
        f'font-size:10px;color:#bbb;font-family:monospace;'
        f'background:rgba(255,255,255,0.8);padding:2px 6px;border-radius:3px;">'
        f'git {_git_ver}</div>',
        unsafe_allow_html=True,
    )
