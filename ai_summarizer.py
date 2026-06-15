"""
AI Summarizer — uses Google Gemini (free tier) to:
  1. Classify each article into a TCG section
  2. Write a TCG-style 2-4 sentence summary with bolded bottom line
  3. Detect OPINION / ANALYSIS / POLL / TREND special formats

Free Gemini API: https://aistudio.google.com/app/apikey
Limits: 15 requests/minute, 1 million tokens/day (more than enough)
"""

import os
import time
import json
import re
from typing import Optional
from groq import Groq

from news_fetcher import Article
from sources_config import TCG_SECTIONS, SOURCE_ABBREVIATIONS


# ─── Setup ───────────────────────────────────────────────────────────────────

def init_groq():
    """Initialize Groq client with API key from environment."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY not set.\n"
            "Get a free key in 2 minutes at https://console.groq.com\n"
            "Then add GROQ_API_KEY=gsk_... to your .env file."
        )
    return Groq(api_key=api_key)


# ─── Summarized Article ───────────────────────────────────────────────────────

class BriefEntry:
    """One formatted entry ready for the TCG newsletter."""
    def __init__(self, article: Article, section: str, summary: str,
                 entry_type: str = "NEWS", author: str = ""):
        self.article    = article
        self.section    = section    # one of TCG_SECTIONS keys
        self.summary    = summary    # formatted summary text
        self.entry_type = entry_type # NEWS, OPINION, ANALYSIS, POLL, TREND
        self.author     = author     # for OPINION entries

    @property
    def source_abbrev(self) -> str:
        return SOURCE_ABBREVIATIONS.get(self.article.source_name, self.article.source_name)

    def citation(self, initials: str = "TCG") -> str:
        """Returns citation like (NYTimes) TCG 6/14"""
        return f"({self.source_abbrev}) {initials} {self.article.published_str()}"

    def format_for_display(self, initials: str = "TCG") -> str:
        """Full formatted string for the newsletter."""
        prefix = ""
        if self.entry_type == "OPINION":
            prefix = f"OPINION | {self.author} — " if self.author else "OPINION — "
        elif self.entry_type == "ANALYSIS":
            prefix = f"ANALYSIS | {self.source_abbrev} — "
        elif self.entry_type == "POLL":
            prefix = "POLL | "
        elif self.entry_type == "TREND":
            prefix = "TREND — "

        return f"{prefix}{self.summary}\n{self.article.url}\n{self.citation(initials)}"


# ─── Prompt Templates ─────────────────────────────────────────────────────────

SECTION_LIST = "\n".join(
    f'  - "{k}": {v}' for k, v in TCG_SECTIONS.items()
)

SYSTEM_PROMPT = f"""You are a news editor for The Common Good (TCG), a nonprofit newsletter
with 25,000 subscribers. Your job is to classify articles into sections and write
tight, impactful summaries in TCG's house style.

TCG SECTION CODES:
{SECTION_LIST}

TCG SUMMARY STYLE RULES:
1. FIRST SENTENCE must "bottom line" the story — state WHO did WHAT and WHY it matters.
   It should be bold in the output (wrap in **bold**).
2. 1-3 more sentences max for context/impact. Keep total under 4 sentences.
3. Bold names of U.S. legislators, prominent political figures, business leaders,
   and foreign dignitaries (e.g., **President Biden**, **Speaker Johnson**).
4. Think WHO / WHAT / WHERE / WHEN / WHY / IMPACT.
5. Be direct. No fluff. Write for an informed general audience.
6. If the article is an OPINION piece, set type to "OPINION".
7. If the article is an analysis/explainer, set type to "ANALYSIS".
8. If the article reports a poll/survey result, set type to "POLL".
9. If the article describes an emerging trend, set type to "TREND".
10. Otherwise set type to "NEWS".

OUTPUT FORMAT — respond with valid JSON only, no markdown fences:
{{
  "section": "<SECTION_CODE>",
  "type": "NEWS" | "OPINION" | "ANALYSIS" | "POLL" | "TREND",
  "author": "<author name if OPINION, else empty string>",
  "summary": "<formatted summary with **bold** for first sentence and key names>"
}}"""


def build_user_prompt(article: Article) -> str:
    text = article.best_text()
    if not text:
        text = article.title
    # Truncate to keep within token limits
    text = text[:3000]
    return f"""SOURCE: {article.source_name}
TITLE: {article.title}
CONTENT:
{text}"""


# ─── Core Summarization ───────────────────────────────────────────────────────

def summarize_article(client, article: Article, retries: int = 2) -> Optional[BriefEntry]:
    """Call Groq (Llama) to classify + summarize one article."""
    prompt = build_user_prompt(article)

    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.3,
                max_tokens=400,
            )
            raw = response.choices[0].message.content.strip()

            # Strip markdown fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            data = json.loads(raw)
            section   = data.get("section", "GOV_POLICY")
            entry_type = data.get("type", "NEWS")
            author    = data.get("author", "")
            summary   = data.get("summary", "").strip()

            # Validate section code
            if section not in TCG_SECTIONS:
                section = "GOV_POLICY"

            return BriefEntry(
                article=article,
                section=section,
                summary=summary,
                entry_type=entry_type,
                author=author,
            )

        except json.JSONDecodeError:
            # Try to extract summary as plain text fallback
            summary = raw[:400] if raw else article.title
            return BriefEntry(article=article, section="GOV_POLICY", summary=summary)

        except Exception as e:
            err_str = str(e).lower()
            if "quota" in err_str or "rate" in err_str or "429" in err_str:
                wait = 30 * (attempt + 1)
                print(f"  ⏳ Rate limited. Waiting {wait}s...")
                time.sleep(wait)
            elif "api_key" in err_str or "invalid" in err_str or "401" in err_str or "403" in err_str:
                # Bad key — don't keep retrying, raise immediately so Streamlit shows the error
                raise RuntimeError(f"Groq API error: {e}")
            elif attempt < retries:
                time.sleep(3)
            else:
                print(f"  ✗ Gemini error for '{article.title[:50]}': {e}")
                return None

    return None


# ─── Batch Processing ─────────────────────────────────────────────────────────

def summarize_all(articles: list[Article],
                  progress_callback=None,
                  max_articles: int = 60) -> list[BriefEntry]:
    """
    Summarize a list of articles.
    Respects Gemini free tier: 15 RPM → ~4 second delay between calls.
    max_articles: cap to avoid burning through too many tokens in one run.
    """
    model = init_groq()
    entries: list[BriefEntry] = []

    # Prioritize articles: newest first, limit to max_articles
    to_process = articles[:max_articles]
    total = len(to_process)

    DELAY_BETWEEN_CALLS = 0.5  # Groq is very fast, generous free tier

    for i, article in enumerate(to_process):
        if progress_callback:
            progress_callback(article.source_name, i + 1, total)

        entry = summarize_article(model, article)
        if entry:
            entries.append(entry)

        # Respect rate limit
        if i < total - 1:
            time.sleep(DELAY_BETWEEN_CALLS)

    print(f"\n✅ Summarized {len(entries)}/{total} articles")
    return entries


# ─── Organize by Section ──────────────────────────────────────────────────────

def organize_by_section(entries: list[BriefEntry]) -> dict[str, list[BriefEntry]]:
    """Group BriefEntries by their TCG section code."""
    from sources_config import SECTION_ORDER
    organized = {section: [] for section in SECTION_ORDER}
    for entry in entries:
        sec = entry.section if entry.section in organized else "GOV_POLICY"
        organized[sec].append(entry)
    # Remove empty sections
    return {k: v for k, v in organized.items() if v}


# ─── Quick Test ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    # Test with a mock article
    test = Article(
        title="Congress passes bipartisan spending bill to avert shutdown",
        url="https://example.com/test",
        source_name="Reuters",
        published_dt=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        summary_snippet=(
            "The House and Senate passed a continuing resolution to fund the "
            "government through March, with President Biden expected to sign it. "
            "The bill narrowly avoided a government shutdown set to begin at midnight."
        )
    )

    client = init_groq()
    entry = summarize_article(client, test)
    if entry:
        print(f"Section: {entry.section}")
        print(f"Type:    {entry.entry_type}")
        print(f"Summary:\n{entry.summary}")
        print(f"\nFormatted:\n{entry.format_for_display('DA')}")
