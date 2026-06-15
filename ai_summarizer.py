"""
AI Summarizer — uses Groq (free tier, Llama 3.3 70B) to:
  1. Classify each article into a TCG section
  2. Write a TCG-style 2-4 sentence summary with bolded bottom line
  3. Detect OPINION / ANALYSIS / POLL / TREND special formats

Free Groq API: https://console.groq.com → API Keys
Limits: generous free tier, very fast inference
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

SYSTEM_PROMPT = f"""You are a sharp news editor for The Common Good (TCG), a nonprofit newsletter
with 25,000 subscribers. Your job is to write summaries so compelling that readers
immediately want to click the link and read the full article.

TCG SECTION CODES:
{SECTION_LIST}

TCG SUMMARY STYLE RULES:
1. Write ONE punchy bold sentence that captures the soul of the story.
   Wrap it entirely in **bold**.
   This is the only required sentence. Make it count.

2. Add a second sentence ONLY if it adds genuinely essential context that
   the first sentence cannot carry. If it doesn't add real value, leave it out.
   Never write a third sentence.

3. THE HOOK TEST: Before you write, ask yourself —
   what is the single most surprising, alarming, or fascinating thing about this story?
   Write THAT. Not a summary of the headline. The thing that makes someone stop scrolling.

4. For OPINION pieces:
   - Lead with the author's name and their core argument in one punchy line.
   - Format: **[Author Name]: [punchy version of their argument — not a description of it].**
   - Make the reader feel the argument, not just know what it's about.

5. Bold names of political figures, legislators, business leaders, dignitaries.
6. Every word must earn its place. Cut anything that doesn't add punch or clarity.
7. Write like a great newspaper front page headline — urgent, specific, impossible to ignore.
8. NOTABLE section is for the biggest stories of the day AND compelling human interest stories
   that are emotionally resonant, surprising, or reveal something important about society.
   If a human story is powerful enough to make someone stop and feel something — it's NOTABLE.

GOOD EXAMPLE (NEWS, 1 sentence):
"**The U.S. just quietly handed the AI industry a blank check — and almost no one noticed.**"

GOOD EXAMPLE (NEWS, 2 sentences where second adds real value):
"**Congress is 48 hours away from shutting down the federal government over a single line in a spending bill.** The sticking point: a **$1.5 billion** border wall provision that neither party will blink on first."

GOOD EXAMPLE (OPINION):
"**Robert Kagan: American democracy isn't dying — it's being auctioned off, and we keep watching like it's someone else's problem.**"

BAD EXAMPLE (too flat, do not write like this):
"The Senate passed an immigration bill that would cut legal immigration. Advocates say they are concerned about the impact."

OUTPUT FORMAT — respond with valid JSON only, no markdown fences:
{{
  "section": "<SECTION_CODE>",
  "type": "NEWS" | "OPINION" | "ANALYSIS" | "POLL" | "TREND",
  "author": "<author name if OPINION, else empty string>",
  "summary": "<1 bold punchy sentence, 2nd sentence only if genuinely necessary>"
}}"""

EXPAND_PROMPT = """Your previous summary had fewer than 3 sentences. You MUST write exactly 3 sentences.

Sentence 1 (bold): Bottom line — who did what and why it matters.
Sentence 2: Key context or details.
Sentence 3: Impact or what comes next.

Rewrite the summary now with all 3 sentences. Return the same JSON format."""


def build_user_prompt(article: Article) -> str:
    text = article.best_text()
    if not text:
        text = article.title
    # Keep under 1500 chars to stay within Groq's free token-per-minute limit
    text = text[:1500]
    return f"""SOURCE: {article.source_name}
TITLE: {article.title}
CONTENT:
{text}"""


def count_sentences(text: str) -> int:
    """Rough sentence count — split on . ! ? followed by space or end."""
    import re
    # Strip bold markers for counting
    clean = re.sub(r"\*\*", "", text)
    parts = re.split(r'(?<=[.!?])\s+', clean.strip())
    return len([p for p in parts if p.strip()])


# ─── Core Summarization ───────────────────────────────────────────────────────

# Titles that indicate live blogs — no stable content to summarize
SKIP_TITLE_PREFIXES = (
    "live update", "live blog", "live coverage", "live:",
    "breaking:", "developing:",
)


def _is_skippable(article: Article) -> bool:
    title_lower = article.title.lower()
    return any(title_lower.startswith(p) for p in SKIP_TITLE_PREFIXES)


def _parse_raw(raw: str) -> dict:
    """Strip fences, extract JSON object, and parse. Raises json.JSONDecodeError on failure."""
    raw = re.sub(r"^```(?:json)?\s*\n?", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\n?```\s*$", "", raw, flags=re.MULTILINE)
    raw = raw.strip()
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if json_match:
        raw = json_match.group(0)
    elif raw.startswith("{") and not raw.rstrip().endswith("}"):
        raw = raw.rstrip().rstrip(",") + '"}'
    return json.loads(raw)


def summarize_article(client, article: Article, retries: int = 2) -> Optional[BriefEntry]:
    """Call Groq (Llama) to classify + summarize one article."""
    # Skip live-update articles — they have no stable summary content
    if _is_skippable(article):
        print(f"  ⏭ Skipping live-update article: {article.title[:60]}")
        return None

    user_prompt = build_user_prompt(article)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_prompt},
    ]

    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.3,
                max_tokens=800,
            )
            raw = response.choices[0].message.content.strip()

            try:
                data = _parse_raw(raw)
            except json.JSONDecodeError:
                # Try regex extraction as fallback
                summary_match = re.search(r'"summary"\s*:\s*"(.+?)(?<!\\)"', raw, re.DOTALL)
                section_match = re.search(r'"section"\s*:\s*"(\w+)"', raw)
                if summary_match:
                    data = {
                        "summary": summary_match.group(1).replace('\\"', '"'),
                        "section": section_match.group(1) if section_match else "GOV_POLICY",
                        "type": "NEWS", "author": "",
                    }
                else:
                    # Can't parse at all — skip
                    print(f"  ✗ JSON parse failed for '{article.title[:50]}'")
                    return None

            section    = data.get("section", "GOV_POLICY")
            entry_type = data.get("type", "NEWS")
            author     = data.get("author", "")
            summary    = data.get("summary", "").strip()

            if section not in TCG_SECTIONS:
                section = "GOV_POLICY"

            # Reject if summary is empty or looks like raw JSON
            if not summary or summary.lstrip().startswith("{"):
                return None

            return BriefEntry(
                article=article,
                section=section,
                summary=summary,
                entry_type=entry_type,
                author=author,
            )

        except Exception as e:
            err_str = str(e).lower()
            if "quota" in err_str or "rate" in err_str or "429" in err_str:
                wait = 30 * (attempt + 1)
                print(f"  ⏳ Rate limited. Waiting {wait}s...")
                time.sleep(wait)
            elif "api_key" in err_str or "invalid" in err_str or "401" in err_str or "403" in err_str:
                raise RuntimeError(f"Groq API error: {e}")
            elif attempt < retries:
                time.sleep(3)
            else:
                print(f"  ✗ Groq error for '{article.title[:50]}': {e}")
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

    DELAY_BETWEEN_CALLS = 12  # Free tier: ~6000 tokens/min — one call every 12s is safe

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
