import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")  # fallback if Gemini not set
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "")

    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "TrendTracker/1.0")

    TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN", "")
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

    INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
    INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")

    GMAIL_SENDER = os.getenv("GMAIL_SENDER", "")
    GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
    EMAIL_TO = os.getenv("EMAIL_TO", "meline.nguyen@lixibox.com")
    EMAIL_CC = os.getenv("EMAIL_CC", "phuonglt.job@gmail.com")
    DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5050"))

    REPORTS_DIR = os.getenv("REPORTS_DIR", "reports")
    SCHEDULER_TIMEZONE = os.getenv("SCHEDULER_TIMEZONE", "America/New_York")

    # US Pop-culture + Beauty + Equestrian subreddits
    REDDIT_SUBREDDITS = [
        # Pop Culture & Entertainment
        "popculture", "entertainment", "celebrity", "HollywoodGossip",
        "movies", "television", "Music", "TikTokCringe", "TikTok", "viral",
        # Beauty & Skincare
        "beauty", "SkincareAddiction", "MakeupAddiction", "BeautyGuruChatter",
        "DIYBeauty", "AsianBeauty", "fragrance", "Wetshaving",
        # Fashion & Lifestyle
        "femalefashionadvice", "malefashionadvice", "streetwear",
        "luxuryfashion", "WomensFashion", "Fashionadvice",
        # Body Care & Wellness
        "bodycare", "selfcare", "Wellness", "FeminineHygiene",
        # Equestrian
        "Equestrian", "Horses", "equestrian", "HorseBack", "Dressage",
        # Social/Viral
        "Trending", "InternetIsBeautiful",
    ]

    # YouTube categories (US)
    YOUTUBE_REGION = "US"
    YOUTUBE_CATEGORIES = {
        "0": "All",
        "10": "Music",
        "17": "Sports",
        "23": "Comedy",
        "24": "Entertainment",
        "25": "News & Politics",
        "26": "How-to & Style",
    }

    # YouTube niche search terms (supplement trending chart)
    YOUTUBE_NICHE_SEARCHES = [
        "equestrian lifestyle 2025",
        "horse girl aesthetic",
        "body care routine viral",
        "beauty trend 2025",
        "fashion week 2025",
        "viral skincare hack",
        "equestrian fashion",
    ]

    # Google Trends seed keywords
    GTRENDS_SEED_KEYWORDS = [
        "trending now", "viral", "beauty trend 2025", "fashion trend 2025",
        "tiktok trend", "equestrian style", "body care routine",
        "cultural moment", "viral marketing",
    ]

    # News RSS feeds — beauty, fashion, entertainment, equestrian
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
        "Horse & Hound": "https://www.horseandhound.co.uk/feed",
        "The Chronicle of the Horse": "https://www.chronofhorse.com/feed",
    }

    # Twitter/X queries
    TWITTER_QUERIES = [
        "#trending", "#viral", "#beauty", "#fashion",
        "#OOTD", "#beautytrend", "#tiktoktrend",
        "#equestrian", "#horsegirl", "#equestrianstyle",
        "#bodycare", "#selfcare", "#aesthetics",
    ]
