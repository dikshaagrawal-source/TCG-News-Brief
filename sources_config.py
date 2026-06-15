"""
TCG Approved News Sources Configuration
All sources from The Common Good's approved list, with RSS feeds,
paywall status, abbreviations, and TCG section assignments.
"""

# ─── TCG Section Structure ───────────────────────────────────────────────────

TCG_SECTIONS = {
    "NOTABLE":     "NOTABLE",
    "GOV_POLICY":  "Government & Policy",
    "ECONOMY":     "Economy & Business",
    "ELECTIONS":   "Elections",
    "COURTS":      "Courts, Justice & Corruption",
    "IMMIGRATION": "Immigration",
    "HEALTH":      "Health",
    "ENVIRONMENT": "Environment & Climate",
    "TECHNOLOGY":  "Technology",
    "AMERICAS":    "Americas",
    "UKRAINE_RUSSIA": "Ukraine-Russia",
    "EUROPE":      "Europe",
    "CHINA_ASIA":  "China & Asia",
    "MIDDLE_EAST": "Middle East",
    "BEYOND":      "Beyond",
}

SECTION_ORDER = [
    "NOTABLE",
    "GOV_POLICY", "ECONOMY", "ELECTIONS", "COURTS",
    "IMMIGRATION", "HEALTH", "ENVIRONMENT", "TECHNOLOGY",
    "AMERICAS", "UKRAINE_RUSSIA", "EUROPE", "CHINA_ASIA",
    "MIDDLE_EAST", "BEYOND",
]

DOMESTIC_SECTIONS = {
    "GOV_POLICY", "ECONOMY", "ELECTIONS", "COURTS",
    "IMMIGRATION", "HEALTH", "ENVIRONMENT", "TECHNOLOGY",
}

WORLD_SECTIONS = {
    "AMERICAS", "UKRAINE_RUSSIA", "EUROPE",
    "CHINA_ASIA", "MIDDLE_EAST", "BEYOND",
}

# ─── Source Abbreviations (per TCG style guide) ──────────────────────────────

SOURCE_ABBREVIATIONS = {
    "AP":               "AP",
    "Bloomberg":        "Bloomberg",
    "NYT":              "NYTimes",
    "NYTimes":          "NYTimes",
    "Los Angeles Times": "LATimes",
    "Financial Times":  "FT",
    "WSJ":              "WSJ",
    "Washington Post":  "WashPo",
    "HuffPost":         "HuffPo",
    "Foreign Policy":   "ForeignPolicy",
    "TIME":             "TIME",
    "New Republic":     "NewRepublic",
    "USA Today":        "USAToday",
    "US News":          "USNews",
    "Al Jazeera":       "AlJazeera",
    "CNN":              "CNN",
    "NPR":              "NPR",
    "Reuters":          "Reuters",
    "Politico":         "Politico",
    "Axios":            "Axios",
    "The Hill":         "Hill",
    "The Atlantic":     "Atlantic",
    "The Economist":    "Economist",
    "New Yorker":       "NewYorker",
    "ProPublica":       "ProPublica",
    "The Bulwark":      "Bulwark",
    "GZERO Media":      "GZERO",
    "Council on Foreign Relations": "CFR",
    "KFF":              "KFF",
    "AILA":             "AILA",
    "Semafor":          "Semafor",
}

# ─── Sources Configuration ────────────────────────────────────────────────────
# paywall: False = free, True = hard paywall, "partial" = some free articles

SOURCES = {
    # ── Wire Services ──────────────────────────────────────────────────────
    "Reuters": {
        "rss_feeds": [
            "https://feeds.reuters.com/reuters/topNews",
            "https://feeds.reuters.com/Reuters/worldNews",
            "https://feeds.reuters.com/reuters/politicsNews",
            "https://feeds.reuters.com/reuters/businessNews",
        ],
        "paywall": False,
        "abbreviation": "Reuters",
        "priority": "high",
    },
    "AP": {
        "rss_feeds": [
            "https://rsshub.app/apnews/topics/apf-topnews",
            "https://rsshub.app/apnews/topics/apf-politics",
            "https://rsshub.app/apnews/topics/apf-intlnews",
        ],
        "paywall": False,
        "abbreviation": "AP",
        "priority": "high",
    },

    # ── Broadcast / General ────────────────────────────────────────────────
    "NPR": {
        "rss_feeds": [
            "https://feeds.npr.org/1001/rss.xml",   # News
            "https://feeds.npr.org/1014/rss.xml",   # Politics
            "https://feeds.npr.org/1006/rss.xml",   # World
        ],
        "paywall": False,
        "abbreviation": "NPR",
        "priority": "medium",
    },
    "CNN": {
        "rss_feeds": [
            "http://rss.cnn.com/rss/edition.rss",
            "http://rss.cnn.com/rss/edition_us.rss",
            "http://rss.cnn.com/rss/edition_world.rss",
        ],
        "paywall": False,
        "abbreviation": "CNN",
        "priority": "medium",
    },

    # ── Political / Beltway ────────────────────────────────────────────────
    "Politico": {
        "rss_feeds": [
            "https://rss.politico.com/politics-news.xml",
            "https://rss.politico.com/congress.xml",
        ],
        "paywall": False,
        "abbreviation": "Politico",
        "priority": "high",
    },
    "Axios": {
        "rss_feeds": [
            "https://api.axios.com/feed/",
        ],
        "paywall": False,
        "abbreviation": "Axios",
        "priority": "high",
    },
    "The Hill": {
        "rss_feeds": [
            "https://thehill.com/rss/syndicator/19110",
            "https://thehill.com/homenews/senate/feed/",
            "https://thehill.com/homenews/house/feed/",
        ],
        "paywall": False,
        "abbreviation": "Hill",
        "priority": "medium",
    },
    "The Bulwark": {
        "rss_feeds": [
            "https://thebulwark.com/feed/",
        ],
        "paywall": "partial",
        "abbreviation": "Bulwark",
        "priority": "medium",
    },
    "New Republic": {
        "rss_feeds": [
            "https://newrepublic.com/feed.rss",
        ],
        "paywall": "partial",
        "abbreviation": "NewRepublic",
        "priority": "medium",
    },
    "RealClearPolitics": {
        "rss_feeds": [
            "https://www.realclearpolitics.com/index.xml",
        ],
        "paywall": False,
        "abbreviation": "RCP",
        "priority": "low",
    },

    # ── Major Newspapers ───────────────────────────────────────────────────
    "NYT": {
        "rss_feeds": [
            "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
            "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
            "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
            "https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml",
        ],
        "paywall": True,
        "abbreviation": "NYTimes",
        "priority": "high",
    },
    "WSJ": {
        "rss_feeds": [
            "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
            "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
            "https://feeds.a.dj.com/rss/RSSWSJD.xml",
        ],
        "paywall": True,
        "abbreviation": "WSJ",
        "priority": "high",
    },
    "Washington Post": {
        "rss_feeds": [
            "https://feeds.washingtonpost.com/rss/national",
            "https://feeds.washingtonpost.com/rss/world",
            "https://feeds.washingtonpost.com/rss/politics",
        ],
        "paywall": True,
        "abbreviation": "WashPo",
        "priority": "high",
    },
    "Financial Times": {
        "rss_feeds": [
            "https://www.ft.com/rss/home",
        ],
        "paywall": True,
        "abbreviation": "FT",
        "priority": "medium",
    },
    "Los Angeles Times": {
        "rss_feeds": [
            "https://www.latimes.com/rss2.0.xml",
        ],
        "paywall": "partial",
        "abbreviation": "LATimes",
        "priority": "medium",
    },

    # ── Magazines ─────────────────────────────────────────────────────────
    "TIME": {
        "rss_feeds": [
            "https://time.com/feed/",
        ],
        "paywall": False,
        "abbreviation": "TIME",
        "priority": "medium",
    },
    "The Atlantic": {
        "rss_feeds": [
            "https://feeds.theatlantic.com/TheAtlantic/all",
        ],
        "paywall": "partial",
        "abbreviation": "Atlantic",
        "priority": "medium",
    },
    "The Economist": {
        "rss_feeds": [
            "https://www.economist.com/the-world-this-week/rss.xml",
            "https://www.economist.com/united-states/rss.xml",
        ],
        "paywall": True,
        "abbreviation": "Economist",
        "priority": "medium",
    },
    "New Yorker": {
        "rss_feeds": [
            "https://www.newyorker.com/feed/news",
        ],
        "paywall": "partial",
        "abbreviation": "NewYorker",
        "priority": "medium",
    },

    # ── International ──────────────────────────────────────────────────────
    "Al Jazeera": {
        "rss_feeds": [
            "https://www.aljazeera.com/xml/rss/all.xml",
        ],
        "paywall": False,
        "abbreviation": "AlJazeera",
        "priority": "high",
    },
    "Foreign Policy": {
        "rss_feeds": [
            "https://foreignpolicy.com/feed/",
        ],
        "paywall": "partial",
        "abbreviation": "ForeignPolicy",
        "priority": "medium",
    },
    "GZERO Media": {
        "rss_feeds": [
            "https://www.gzeromedia.com/feeds/gzero-media-rss.xml",
        ],
        "paywall": False,
        "abbreviation": "GZERO",
        "priority": "medium",
    },
    "Council on Foreign Relations": {
        "rss_feeds": [
            "https://www.cfr.org/rss/",
        ],
        "paywall": False,
        "abbreviation": "CFR",
        "priority": "low",
    },

    # ── Investigative / Specialty ──────────────────────────────────────────
    "ProPublica": {
        "rss_feeds": [
            "https://feeds.propublica.org/propublica/main",
        ],
        "paywall": False,
        "abbreviation": "ProPublica",
        "priority": "medium",
    },
    "KFF": {
        "rss_feeds": [
            "https://kffhealthnews.org/feed/",
        ],
        "paywall": False,
        "abbreviation": "KFF",
        "priority": "medium",
    },
    "Semafor": {
        "rss_feeds": [
            "https://www.semafor.com/feed",
        ],
        "paywall": False,
        "abbreviation": "Semafor",
        "priority": "medium",
    },
}
