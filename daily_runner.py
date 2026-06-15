"""
Daily Runner — command-line script for GitHub Actions scheduled email.
Runs every day at 12pm EST, fetches the last 24h of news, summarizes,
and emails the brief to the team.

Usage:
    python daily_runner.py
    python daily_runner.py --hours 12 --max-articles 50
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="TCG Daily News Brief Runner")
    parser.add_argument("--hours",        type=float, default=24,  help="Look-back window in hours")
    parser.add_argument("--max-articles", type=int,   default=50,  help="Max articles to summarize")
    parser.add_argument("--initials",     type=str,   default="TCG", help="Initials for citations")
    parser.add_argument("--no-email",     action="store_true",     help="Skip email, just print")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"TCG Daily News Brief — {datetime.now().strftime('%A, %B %-d, %Y')}")
    print(f"Window: last {args.hours}h | Max articles: {args.max_articles}")
    print(f"{'='*60}\n")

    # Check required env vars
    if not os.environ.get("GEMINI_API_KEY"):
        print("❌ ERROR: GEMINI_API_KEY is not set. Add it to your .env or GitHub secrets.")
        sys.exit(1)

    # Step 1: Fetch articles
    print("📡 Fetching articles from sources...")
    from news_fetcher import fetch_all_articles
    articles = fetch_all_articles(max_age_hours=args.hours, enrich_text=True)

    if not articles:
        print("⚠ No articles found. Exiting.")
        sys.exit(0)

    print(f"   → Found {len(articles)} unique articles\n")

    # Step 2: Summarize with AI
    print(f"🤖 Summarizing up to {args.max_articles} articles with Gemini AI...")
    print("   (Free tier: ~4 seconds per article)")
    from ai_summarizer import summarize_all, organize_by_section
    entries = summarize_all(articles, max_articles=args.max_articles)

    if not entries:
        print("⚠ No summaries generated. Exiting.")
        sys.exit(0)

    # Step 3: Format
    print(f"\n📝 Formatting brief ({len(entries)} entries)...")
    organized = organize_by_section(entries)

    # Import formatter from app.py
    from app import brief_to_plain_text
    plain_text = brief_to_plain_text(organized, args.initials)

    # Step 4: Print preview
    print("\n" + "─"*60)
    print(plain_text[:2000])
    if len(plain_text) > 2000:
        print(f"\n... [{len(plain_text) - 2000} more characters] ...")
    print("─"*60)

    # Step 5: Email
    if args.no_email:
        print("\n⏭ Skipping email (--no-email flag set).")
        return

    recipients_env = os.environ.get("EMAIL_RECIPIENTS", "")
    recipients = [r.strip() for r in recipients_env.split(",") if r.strip()]

    if not recipients:
        print("\n⚠ No EMAIL_RECIPIENTS set. Brief not emailed.")
        print("  Set EMAIL_RECIPIENTS=email1@example.com,email2@example.com in .env")
        return

    if not os.environ.get("SMTP_PASSWORD"):
        print("\n⚠ SMTP_PASSWORD not set. Brief not emailed.")
        return

    print(f"\n📧 Emailing brief to: {', '.join(recipients)}")
    from emailer import send_brief_email
    send_brief_email(
        recipients=recipients,
        subject=f"TCG Daily Brief — {datetime.now().strftime('%B %-d, %Y')}",
        body_text=plain_text,
    )
    print("✅ Done!\n")


if __name__ == "__main__":
    main()
