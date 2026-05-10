"""
Cultural calendar collector — no API required.

Provides US cultural events, holidays, awareness months, award shows,
fashion weeks, and major pop-culture moments happening now and soon.
This enriches trend context without needing any external credentials.
"""

import logging
from calendar import month_name
from datetime import date, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# ── Recurring cultural calendar ────────────────────────────────────────────
# Format: (month, day, name, category, tags)
FIXED_EVENTS: list[tuple[int, int, str, str, list[str]]] = [
    # January
    (1, 1,  "New Year's Day", "Holiday", ["newyear", "fresh start", "resolution"]),
    (1, 15, "Martin Luther King Jr. Day (observed)", "Cultural", ["mlk", "community", "equality"]),
    (1, 20, "Inauguration Day (presidential years)", "Cultural", ["politics", "america"]),
    # February
    (2, 1,  "Black History Month begins", "Cultural", ["blackhistorymonth", "community", "representation"]),
    (2, 2,  "Groundhog Day", "Pop Culture", ["groundhogday", "viral"]),
    (2, 9,  "Grammy Awards (approx)", "Entertainment", ["grammys", "music", "redcarpet"]),
    (2, 14, "Valentine's Day", "Holiday", ["valentinesday", "love", "giftguide", "beauty"]),
    (2, 20, "Presidents' Day", "Holiday", ["presidentday", "sale"]),
    # March
    (3, 1,  "Women's History Month begins", "Cultural", ["womenshistorymonth", "womenempowerment"]),
    (3, 2,  "Oscar Awards (approx)", "Entertainment", ["oscars", "hollywood", "redcarpet", "fashion"]),
    (3, 8,  "International Women's Day", "Cultural", ["iwd", "womensday", "girlpower"]),
    (3, 17, "St. Patrick's Day", "Holiday", ["stpatricksday", "greenbeauty"]),
    (3, 20, "First Day of Spring", "Seasonal", ["springbeauty", "springskin", "springfashion"]),
    # April
    (4, 1,  "April Fools' Day", "Pop Culture", ["aprilfools", "viral"]),
    (4, 22, "Earth Day", "Cultural", ["earthday", "sustainable", "cleanbeauty", "greenbeauty"]),
    # May
    (5, 1,  "Asian American & Pacific Islander Month begins", "Cultural", ["aapiheritagemonth"]),
    (5, 4,  "Star Wars Day", "Pop Culture", ["maythefourthbewithyou", "viral"]),
    (5, 5,  "Cinco de Mayo", "Cultural", ["cincodemayo", "latinx"]),
    (5, 8,  "Met Gala (approx first Monday)", "Fashion", ["metgala", "fashion", "redcarpet", "couture"]),
    (5, 11, "Mother's Day (second Sunday)", "Holiday", ["mothersday", "giftsformom", "beauty", "selfcare"]),
    (5, 26, "Memorial Day", "Holiday", ["memorialday", "summer", "sale"]),
    # June
    (6, 1,  "Pride Month begins", "Cultural", ["pride", "pridemonth", "lgbtq", "inclusive"]),
    (6, 15, "Father's Day (third Sunday)", "Holiday", ["fathersday", "giftsfordad"]),
    (6, 19, "Juneteenth", "Cultural", ["juneteenth", "blackowned", "community"]),
    (6, 21, "First Day of Summer", "Seasonal", ["summerbeauty", "summerfashion", "summerskin"]),
    # July
    (7, 4,  "Independence Day", "Holiday", ["4thofjuly", "america", "redwhitebue"]),
    # August
    (8, 12, "International Youth Day", "Cultural", ["youthday", "genz"]),
    (8, 26, "Women's Equality Day", "Cultural", ["womensequality"]),
    # September
    (9, 1,  "New York Fashion Week (approx)", "Fashion", ["nyfw", "fashionweek", "ss2026", "runway"]),
    (9, 5,  "Labor Day", "Holiday", ["laborday", "sale", "endofsummer"]),
    (9, 22, "First Day of Fall", "Seasonal", ["fallbeauty", "autumnfashion", "fallskincare"]),
    # October
    (10, 1, "Breast Cancer Awareness Month begins", "Cultural", ["breastcancerawareness", "pinkribbon"]),
    (10, 31,"Halloween", "Holiday", ["halloween", "halloweenbeauty", "halloweenmakeup", "costume"]),
    # November
    (11, 1, "Dia de los Muertos", "Cultural", ["diadeMuertos", "latinx", "culture"]),
    (11, 11,"Veterans Day", "Holiday", ["veteransday"]),
    (11, 27,"Thanksgiving (fourth Thursday)", "Holiday", ["thanksgiving", "gratitude", "sale"]),
    (11, 28,"Black Friday", "Viral", ["blackfriday", "deals", "giftguide", "viralproducts"]),
    (11, 30,"Cyber Monday (approx)", "Viral", ["cybermonday", "deals", "onlineshopping"]),
    # December
    (12, 1, "World AIDS Day", "Cultural", ["worldaidsday", "health"]),
    (12, 21,"First Day of Winter", "Seasonal", ["winterbeauty", "winterfashion", "holidayskin"]),
    (12, 24,"Christmas Eve", "Holiday", ["christmas", "christmasbeauty", "giftsforher"]),
    (12, 25,"Christmas Day", "Holiday", ["christmas", "christmasday"]),
    (12, 26,"Kwanzaa begins", "Cultural", ["kwanzaa", "blackculture"]),
    (12, 31,"New Year's Eve", "Holiday", ["nye", "nyebeauty", "glam", "partylook"]),
]

# Equestrian calendar
EQUESTRIAN_EVENTS: list[tuple[int, int, str, list[str]]] = [
    (1, 10, "Winter Equestrian Festival begins (Wellington, FL)", ["wef", "equestrian", "horseback"]),
    (3, 15, "Spring horse show season opens", ["horseshow", "equestrian", "dressage"]),
    (4, 20, "Rolex Kentucky Three-Day Event (approx)", ["kentucky3day", "eventing", "equestrian"]),
    (5, 3,  "Kentucky Derby (first Saturday in May)", ["kentuckyderby", "derby", "horseracing", "derbyfashion"]),
    (5, 17, "Preakness Stakes", ["preakness", "horseracing"]),
    (6, 7,  "Belmont Stakes", ["belmontstakes", "horseracing", "tripplecrown"]),
    (6, 15, "US Equestrian Festival", ["usef", "equestrian"]),
    (8, 1,  "Summer Olympic Equestrian Events (Olympic years)", ["olympicequestrian", "equestrian"]),
    (9, 20, "USHJA International Hunter Derby Championship", ["hunterderby", "equestrian"]),
    (10, 1, "Fall horse show season", ["fallequestrinan", "horseshow"]),
    (11, 15,"World Equestrian Games (alternating years)", ["westeqg", "equestrian"]),
    (12, 1, "National Western Stock Show prep", ["stockshow", "western", "equestrian"]),
]

# Awareness months
AWARENESS_MONTHS: dict[int, list[tuple[str, list[str]]]] = {
    1: [("National Mentoring Month", ["mentoring", "community"])],
    2: [("Black History Month", ["blackhistorymonth", "representation"]),
        ("American Heart Month", ["heartmonth", "wellness"])],
    3: [("Women's History Month", ["womenshistorymonth"]),
        ("National Nutrition Month", ["nutrition", "wellness"])],
    4: [("Earth Month", ["earthmonth", "sustainability", "cleanbeauty"]),
        ("Sexual Assault Awareness Month", ["awareness", "community"])],
    5: [("Asian American Heritage Month", ["aapiheritagemonth"]),
        ("Mental Health Awareness Month", ["mentalhealthmonth", "selfcare", "wellness"])],
    6: [("Pride Month", ["pride", "lgbtq", "inclusive"]),
        ("Alzheimer's Awareness Month", ["alzheimers", "awareness"])],
    7: [("Minority Mental Health Month", ["mentalhealth", "community"])],
    8: [("National Wellness Month", ["wellness", "selfcare", "bodycare"])],
    9: [("Hispanic Heritage Month", ["hispanicheritagemonth", "latinx"]),
        ("Suicide Prevention Month", ["awareness", "community"])],
    10: [("Breast Cancer Awareness Month", ["pinkribbon", "breastcancer"]),
         ("LGBTQ+ History Month", ["lgbtq", "pride"]),
         ("National Disability Employment Month", ["inclusion", "community"])],
    11: [("Native American Heritage Month", ["nativeamerican", "indigenous"]),
         ("National Gratitude Month", ["gratitude", "selfcare"])],
    12: [("Universal Human Rights Month", ["humanrights", "community"])],
}


def collect() -> dict[str, Any]:
    """Return cultural events happening now, soon, and this month."""
    today = date.today()
    results: dict[str, Any] = {
        "source": "Cultural Calendar",
        "today": today.strftime("%Y-%m-%d"),
        "happening_now": [],       # within ±3 days
        "coming_this_week": [],    # next 7 days
        "coming_this_month": [],   # rest of the month
        "awareness_month": [],     # awareness month themes
        "equestrian_events": [],   # equestrian calendar
        "errors": [],
    }

    try:
        window_past = today - timedelta(days=2)
        window_near = today + timedelta(days=3)
        window_week = today + timedelta(days=7)

        for month, day, name, category, tags in FIXED_EVENTS:
            try:
                event_date = date(today.year, month, day)
            except ValueError:
                continue

            event = {
                "name": name,
                "date": event_date.strftime("%Y-%m-%d"),
                "category": category,
                "hashtags": [f"#{t}" for t in tags],
                "days_away": (event_date - today).days,
            }

            if window_past <= event_date <= window_near:
                results["happening_now"].append(event)
            elif window_near < event_date <= window_week:
                results["coming_this_week"].append(event)
            elif today < event_date <= date(today.year, today.month + 1 if today.month < 12 else 1, 1):
                results["coming_this_month"].append(event)

        # Equestrian events
        for month, day, name, tags in EQUESTRIAN_EVENTS:
            try:
                event_date = date(today.year, month, day)
            except ValueError:
                continue
            days_away = (event_date - today).days
            if -7 <= days_away <= 30:
                results["equestrian_events"].append({
                    "name": name,
                    "date": event_date.strftime("%Y-%m-%d"),
                    "hashtags": [f"#{t}" for t in tags],
                    "days_away": days_away,
                })

        # Awareness month
        month_events = AWARENESS_MONTHS.get(today.month, [])
        for name, tags in month_events:
            results["awareness_month"].append({
                "name": name,
                "hashtags": [f"#{t}" for t in tags],
            })

    except Exception as e:
        results["errors"].append(str(e))

    logger.info(
        f"Cultural calendar: {len(results['happening_now'])} now, "
        f"{len(results['coming_this_week'])} this week"
    )
    results["collected_at"] = datetime.utcnow().isoformat()
    return results
