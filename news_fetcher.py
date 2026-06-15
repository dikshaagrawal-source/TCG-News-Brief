"""
News Fetcher — pulls articles from RSS feeds and extracts full text.
For paywalled articles, attempts archive.is as a fallback.
"""

import feedparser
import requests
import trafilatura
import time
import hashlib
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, quote
from sources_config import SOURCES


# ─── Config ──────────────────────────────────────────────────────────────────

REQUEST_TIMEOUT = 15  # seconds
REQUEST_DELAY   = 0.5  # seconds between requests (be polite)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ─── Article Data Class ───────────────────────────────────────────────────────

class Article:
    def __init__(self, title, url, source_name, published_dt, summary_snippet="", full_text=""):
        self.title          = title
        self.url            = url
        self.source_name    = source_name
        self.published_dt   = published_dt  # datetime object (UTC)
        self.summary_snippet = summary_snippet  # RSS description
        self.full_text      = full_text         # Full article body (may be empty)
        self.id             = hashlib.md5(url.encode()).hexdigest()[:8]

    def age_hours(self):
        now = datetime.now(timezone.utc)
        if self.published_dt.tzinfo is None:
            self.published_dt = self.published_dt.replace(tzinfo=timezone.utc)
        return (now - self.published_dt).total_seconds() / 3600

    def best_text(self):
        """Return full text if available, else the RSS snippet."""
        return self.full_text if len(self.full_text) > 200 else self.summary_snippet

    def published_str(self):
        """Returns date as M/D string for citations."""
        return self.published_dt.strftime("%-m/%-d")

    def __repr__(self):
        return f"<Article: {self.source_name} | {self.title[:60]}>"


# ─── RSS Fetching ─────────────────────────────────────────────────────────────

def parse_rss_date(entry) -> datetime:
    """Convert feedparser's parsed date tuple to a timezone-aware datetime."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    # Fall back to now minus a few hours (treat as recent)
    return datetime.now(timezone.utc) - timedelta(hours=6)


def fetch_rss_feed(feed_url: str, source_name: str, max_age_hours: float) -> list[Article]:
    """Fetch one RSS feed and return Article objects within the time window."""
    articles = []
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            published = parse_rss_date(entry)
            now = datetime.now(timezone.utc)
            if (now - published).total_seconds() / 3600 > max_age_hours:
                continue

            title   = getattr(entry, "title", "").strip()
            url     = getattr(entry, "link", "").strip()
            snippet = getattr(entry, "summary", "") or getattr(entry, "description", "")
            # Strip HTML from snippet
            import re
            snippet = re.sub(r"<[^>]+>", " ", snippet).strip()
            snippet = re.sub(r"\s+", " ", snippet)

            if title and url:
                articles.append(Article(
                    title=title,
                    url=url,
                    source_name=source_name,
                    published_dt=published,
                    summary_snippet=snippet[:800],
                ))
    except Exception as e:
        print(f"  ⚠ RSS error ({source_name}): {e}")
    return articles


# ─── Full-text Extraction ─────────────────────────────────────────────────────

def extract_full_text(url: str) -> str:
    """Download and extract article body text using trafilatura."""
    try:
        downloaded = trafilatura.fetch_url(url, no_ssl=True)
        if downloaded:
            text = trafilatura.extract(downloaded, include_comments=False,
                                       include_tables=False, no_fallback=False)
            if text and len(text) > 200:
                return text[:4000]  # cap at 4000 chars for AI processing
    except Exception:
        pass
    return ""


def extract_via_archive(url: str) -> str:
    """Try to get full text via archive.is for paywalled articles."""
    try:
        archive_url = f"https://archive.is/newest/{quote(url, safe='')}"
        resp = requests.get(archive_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            text = trafilatura.extract(resp.text, include_comments=False,
                                       include_tables=False)
            if text and len(text) > 200:
                return text[:4000]
    except Exception:
        pass
    return ""


def enrich_article(article: Article, is_paywalled: bool) -> Article:
    """Attempt to fetch full article text."""
    time.sleep(REQUEST_DELAY)

    if not is_paywalled:
        text = extract_full_text(article.url)
        if text:
            article.full_text = text
            return article

    # Paywalled — try archive.is
    text = extract_via_archive(article.url)
    if text:
        article.full_text = text

    return article


# ─── Deduplication ────────────────────────────────────────────────────────────

def deduplicate(articles: list[Article]) -> list[Article]:
    """
    Remove near-duplicate stories by title similarity.
    When duplicates exist, prefer higher-priority source.
    Priority order: Reuters > AP > NYT > WSJ > WashPo > others
    """
    from difflib import SequenceMatcher

    PRIORITY_SOURCES = ["Reuters", "AP", "NYT", "WSJ", "Washington Post",
                        "Politico", "Axios", "NPR", "CNN"]

    def source_priority(art: Article) -> int:
        try:
            return PRIORITY_SOURCES.index(art.source_name)
        except ValueError:
            return len(PRIORITY_SOURCES)

    def similar(a: str, b: str, threshold=0.72) -> bool:
        a_words = set(a.lower().split())
        b_words = set(b.lower().split())
        if not a_words or not b_words:
            return False
        overlap = len(a_words & b_words) / max(len(a_words), len(b_words))
        return overlap > threshold

    seen: list[Article] = []
    for art in sorted(articles, key=source_priority):
        is_dup = False
        for existing in seen:
            if similar(art.title, existing.title):
                is_dup = True
                break
        if not is_dup:
            seen.append(art)

    return seen


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def fetch_all_articles(max_age_hours: float = 24,
                       enrich_text: bool = True,
                       progress_callback=None) -> list[Article]:
    """
    Fetch articles from all configured sources within max_age_hours.
    Returns deduplicated list sorted newest-first.

    progress_callback: optional fn(source_name, current, total) for UI updates.
    """
    all_articles: list[Article] = []
    source_names = list(SOURCES.keys())
    total = len(source_names)

    for i, source_name in enumerate(source_names):
        cfg = SOURCES[source_name]
        if progress_callback:
            progress_callback(source_name, i + 1, total)

        source_articles: list[Article] = []
        for feed_url in cfg["rss_feeds"]:
            fetched = fetch_rss_feed(feed_url, source_name, max_age_hours)
            source_articles.extend(fetched)

        # Deduplicate within this source first
        seen_urls = set()
        unique = []
        for art in source_articles:
            if art.url not in seen_urls:
                seen_urls.add(art.url)
                unique.append(art)

        # Enrich with full text (limit per source to keep it fast)
        if enrich_text:
            is_paywalled = cfg.get("paywall", False)
            # For high-priority sources, enrich more articles
            limit = 8 if cfg.get("priority") == "high" else 5
            for art in unique[:limit]:
                enrich_article(art, is_paywalled=bool(is_paywalled))

        all_articles.extend(unique)

    # Global deduplication
    deduped = deduplicate(all_articles)

    # Sort newest first
    deduped.sort(key=lambda a: a.published_dt, reverse=True)

    print(f"\n✅ Fetched {len(all_articles)} raw → {len(deduped)} unique articles")
    return deduped


# ─── Quick Test ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing news fetcher (last 12 hours, no text enrichment)...")
    articles = fetch_all_articles(max_age_hours=12, enrich_text=False)
    for art in articles[:10]:
        print(f"  [{art.source_name}] {art.title[:80]}  ({art.age_hours():.1f}h ago)")
