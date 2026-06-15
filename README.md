# 📰 TCG Daily News Brief Agent

Automated news brief generator for **The Common Good** newsletter team.
Pulls from 25+ approved sources, summarizes with AI in TCG's house style,
and delivers to the team inbox daily at 12pm EST.

---

## What it does

1. **Fetches** the latest articles from all TCG-approved sources (Reuters, AP, NYT, WSJ, Politico, Axios, Al Jazeera, and more) via RSS feeds
2. **Bypasses paywalls** using archive.is for NYT, WSJ, WaPo, etc.
3. **Summarizes** each article using Google Gemini AI in TCG's exact style — bolded bottom-line first sentence, 2–4 sentences total, names in bold
4. **Classifies** articles into TCG sections: NOTABLE → Domestic (Gov/Policy, Economy, Elections, Courts, Immigration, Health, Environment, Technology) → World (Americas, Ukraine-Russia, Europe, China/Asia, Middle East, Beyond)
5. **Delivers** via a team dashboard (web app) and a daily 12pm email

---

## One-time Setup (do this once, then it's automatic)

### Step 1: Get a free Gemini API key

1. Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with any Google account
3. Click **Create API Key** and copy it
4. Free tier: 15 requests/minute, 1 million tokens/day — plenty for our needs

### Step 2: Set up the email password

1. Log into the TCG Google Workspace account (`tcgnews@thecommongood.net`)
2. Go to **Account Settings → Security → 2-Step Verification** (enable if not already on)
3. Then go to **App Passwords** → select "Mail" → generate
4. Copy the 16-character password (you only see it once)

### Step 3: Create a GitHub repository

1. Go to [github.com](https://github.com) and create a **new private repository** (e.g. `tcg-news-brief`)
2. Upload all these files to it (drag and drop or use GitHub Desktop)
3. Make sure `.env` is NOT uploaded (it's in `.gitignore` for safety)

### Step 4: Add secrets to GitHub

These are like a secure `.env` file that GitHub keeps private:

1. In your GitHub repo, go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret** and add each of these:

| Secret Name | Value |
|-------------|-------|
| `GEMINI_API_KEY` | Your Gemini key from Step 1 |
| `SMTP_USER` | `tcgnews@thecommongood.net` |
| `SMTP_PASSWORD` | The 16-char App Password from Step 2 |
| `EMAIL_RECIPIENTS` | `tcgnews@thecommongood.net` (or comma-separated list) |

### Step 5: Deploy the dashboard (Streamlit Cloud — free)

1. Go to [https://share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click **New app** → select your `tcg-news-brief` repo → set main file to `app.py`
4. Under **Advanced settings → Secrets**, add the same key-value pairs from above
5. Click **Deploy** — you get a shareable URL like `https://your-team.streamlit.app`
6. Share that URL with all 6 team members — no install needed, just open in browser

---

## Daily Use

### Dashboard (recommended)

Open your Streamlit URL in any browser:
- Select time window (6h / 12h / 24h / 48h)
- Enter your initials (used in citations like `(NYTimes) DA 6/14`)
- Click **Generate Brief** and wait ~5 minutes
- Browse by section in the tabs
- Click **Email Brief** to send to the team, or **Download .txt** to save

### Automatic email

Every weekday at 12pm EST, GitHub Actions runs the agent automatically
and emails the brief to your team inbox. No action needed.

### Manual email trigger

Any team member can trigger a fresh brief from GitHub:
1. Go to the repo on GitHub
2. Click the **Actions** tab
3. Click **Daily News Brief** on the left
4. Click **Run workflow** → **Run workflow**

---

## Local Development (optional, for the tech-curious)

```bash
# Clone the repo
git clone https://github.com/your-org/tcg-news-brief.git
cd tcg-news-brief

# Install Python dependencies
pip install -r requirements.txt

# Copy environment template and fill in your keys
cp .env.example .env
# Edit .env with your GEMINI_API_KEY, SMTP credentials, etc.

# Run the dashboard locally
streamlit run app.py

# Or run the email script directly
python daily_runner.py --hours 24 --max-articles 40
```

---

## Limitations & Tips

- **Paywalled content**: The agent tries archive.is for NYT/WSJ/WaPo. If that fails, it uses the RSS snippet (shorter). Your team should still add notable paywalled articles manually.
- **Quality**: AI summaries are a first draft. Team members should review and edit before the newsletter goes out.
- **Rate limits**: Gemini free tier = 15 requests/min. Summarizing 50 articles takes ~5 minutes. This is normal.
- **Sources not in RSS**: A few sources (AILA, Stateside Associates, Chris Riback Newsletter) don't have public RSS feeds — those still need to be added manually.

---

## File Structure

```
tcg-news-brief/
├── app.py              ← Streamlit dashboard (main entry point)
├── daily_runner.py     ← Command-line runner (used by GitHub Actions)
├── news_fetcher.py     ← RSS + web scraping
├── ai_summarizer.py    ← Google Gemini AI summarization
├── emailer.py          ← Email sending
├── sources_config.py   ← All source configs + TCG section structure
├── requirements.txt    ← Python dependencies
├── .env.example        ← Template for environment variables
├── .gitignore          ← Keeps .env out of GitHub
└── .github/
    └── workflows/
        └── daily_brief.yml  ← GitHub Actions schedule (12pm EST weekdays)
```

---

Questions? Reach out to Diksha or open a GitHub Issue.
