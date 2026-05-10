import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "")

    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "TrendTracker/1.0")

    TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
    DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5050"))

    REPORTS_DIR = os.getenv("REPORTS_DIR", "reports")
    SCHEDULER_TIMEZONE = os.getenv("SCHEDULER_TIMEZONE", "America/New_York")

    # US Pop-culture subreddits to monitor
    REDDIT_SUBREDDITS = [
        "popculture", "entertainment", "beauty", "SkincareAddiction",
        "MakeupAddiction", "femalefashionadvice", "malefashionadvice",
        "streetwear", "Showerthoughts", "TikTokCringe", "TikTok",
        "HollywoodGossip", "Music", "movies", "television",
        "celebrity", "Trending", "viral", "BeautyGuruChatter",
    ]

    # YouTube trending categories (US)
    YOUTUBE_REGION = "US"
    YOUTUBE_CATEGORIES = {
        "0": "All",
        "10": "Music",
        "17": "Sports",
        "23": "Comedy",
        "24": "Entertainment",
        "25": "News & Politics",
    }

    # Google Trends keywords seed list (agent will expand dynamically)
    GTRENDS_SEED_KEYWORDS = [
        "trending now", "viral", "hot right now",
        "beauty trend 2025", "fashion trend 2025",
        "tiktok trend", "instagram trend",
    ]

    # News RSS feeds
    NEWS_FEEDS = {
        "Entertainment Weekly": "https://feeds.feedburner.com/ew/news",
        "People Magazine": "https://people.com/feed/",
        "E! News": "https://www.eonline.com/news/rss",
        "Cosmopolitan": "https://www.cosmopolitan.com/rss/all.xml/",
        "Refinery29": "https://www.refinery29.com/rss.xml",
        "Hypebeast": "https://hypebeast.com/feed",
        "Byrdie Beauty": "https://www.byrdie.com/news-rss",
        "Allure": "https://www.allure.com/feed/rss",
        "WWD Fashion": "https://wwd.com/feed/",
        "The Hollywood Reporter": "https://www.hollywoodreporter.com/feed/",
        "Variety": "https://variety.com/feed/",
        "Billboard": "https://www.billboard.com/feed/",
        "Complex": "https://www.complex.com/rss",
        "Highsnobiety": "https://www.highsnobiety.com/feed/",
    }

    # Twitter/X trending search queries
    TWITTER_QUERIES = [
        "#trending", "#viral", "#beauty", "#fashion",
        "#OOTD", "#hollywoodtrend", "#beautytrend",
        "#tiktoktrend", "#aesthetics",
    ]
