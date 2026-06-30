"""Sends the CoBa's Daughter trend digest as an HTML email via Gmail SMTP."""

import logging
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger(__name__)

HEAT_EMOJI = {"Peaking Fast": "🔥🔥", "Peaking": "🔥", "Emerging": "🌱", "Mainstream": "📈"}
CAT_COLOR  = {
    "Beauty":             "#c9a84c",
    "Body Care":          "#8aaa7a",
    "Fashion":            "#a0784a",
    "Equestrian":         "#6b8f71",
    "Pop Culture":        "#b07cc6",
    "Hollywood":          "#e07b54",
    "Film & Music":       "#5b8dd9",
    "Cultural Relevancy": "#7cbfb8",
    "Viral Marketing":    "#e05c7a",
}

STYLES = """
<style>
  body { font-family: Georgia, 'Times New Roman', serif; background: #f5f0e8; margin: 0; padding: 0; }
  .wrapper { max-width: 680px; margin: 0 auto; background: #fff; }
  .header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 36px 32px; text-align: center; }
  .header h1 { color: #c9a84c; font-size: 22px; margin: 0 0 6px; letter-spacing: 2px; text-transform: uppercase; }
  .header p { color: #d4c5a0; font-size: 13px; margin: 0; }
  .section { padding: 24px 32px; border-bottom: 1px solid #f0ead8; }
  .section-title { font-size: 14px; font-weight: bold; color: #1a1a2e; text-transform: uppercase;
                   letter-spacing: 1.5px; margin: 0 0 14px; padding-bottom: 8px;
                   border-bottom: 2px solid #c9a84c; }
  .spotlight-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .spotlight-box { background: #f9f5ec; border-left: 3px solid #c9a84c; padding: 12px; border-radius: 4px; }
  .spotlight-box .label { font-size: 10px; color: #8a7a5a; text-transform: uppercase; letter-spacing: 1px; }
  .spotlight-box .value { font-size: 13px; color: #2a2a2a; margin-top: 4px; }
  .trend-card { border: 1px solid #ede8da; border-radius: 8px; margin-bottom: 16px; overflow: hidden; }
  .trend-header { padding: 12px 16px; color: #fff; font-size: 13px; font-weight: bold; }
  .trend-body { padding: 14px 16px; }
  .trend-meta { font-size: 12px; color: #888; margin-bottom: 8px; }
  .score-row { display: flex; gap: 16px; margin-bottom: 10px; }
  .score-item { flex: 1; }
  .score-label { font-size: 10px; color: #888; text-transform: uppercase; letter-spacing: 1px; }
  .score-bar-bg { background: #f0ead8; border-radius: 4px; height: 6px; margin-top: 4px; }
  .score-bar { height: 6px; border-radius: 4px; }
  .what { font-size: 13px; color: #444; font-style: italic; margin-bottom: 10px; }
  .tactics { background: #f9f5ec; padding: 10px 12px; border-radius: 6px; }
  .tactics .t-label { font-size: 10px; color: #8a7a5a; text-transform: uppercase; letter-spacing: 1px; font-weight: bold; }
  .tactics ul { margin: 4px 0 0; padding-left: 16px; }
  .tactics li { font-size: 12px; color: #555; margin-bottom: 3px; }
  .launch-card { background: #fff8ee; border-left: 4px solid #e07b54; padding: 12px 14px;
                 border-radius: 4px; margin-bottom: 10px; }
  .launch-brand { font-size: 13px; font-weight: bold; color: #c05a30; }
  .launch-what { font-size: 13px; color: #444; margin: 4px 0; }
  .launch-resp { font-size: 12px; color: #666; font-style: italic; }
  .hw-item { font-size: 13px; color: #444; padding: 6px 0; border-bottom: 1px solid #f5f0e8; }
  .hw-item:last-child { border-bottom: none; }
  .seed-card { background: #f4faf4; border-left: 3px solid #8aaa7a; padding: 10px 12px;
               border-radius: 4px; margin-bottom: 10px; }
  .seed-sub { font-size: 12px; font-weight: bold; color: #4a7a50; }
  .seed-thread { font-size: 12px; color: #555; margin: 3px 0; }
  .seed-angle { font-size: 12px; color: #666; font-style: italic; }
  .hashtag-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
  .hashtag { background: #f0ead8; color: #6b5a30; font-size: 11px; padding: 3px 8px;
             border-radius: 12px; font-weight: bold; }
  .footer { background: #1a1a2e; padding: 20px 32px; text-align: center; }
  .footer p { color: #8a7a6a; font-size: 11px; margin: 0; }
</style>
"""


def _bar(score: float, color: str) -> str:
    pct = min(100, max(0, score * 10))
    return (
        f'<div class="score-bar-bg">'
        f'<div class="score-bar" style="width:{pct}%;background:{color};"></div>'
        f'</div>'
    )


def _build_html(report: dict[str, Any], dashboard_url: str = "") -> str:
    date        = report.get("report_date", datetime.utcnow().strftime("%Y-%m-%d"))
    gmt7_hour   = (datetime.utcnow().hour + 7) % 24
    slot        = "9AM" if gmt7_hour < 12 else "3PM"
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
        date_label = dt.strftime("%B %-d, %Y")
    except Exception:
        date_label = date

    spotlight      = report.get("cobas_daughter_spotlight", {})
    top_trends     = report.get("top_trends", [])
    brand_launches = report.get("brand_launches_now", [])
    hw             = report.get("hollywood_pulse", {})
    eq             = report.get("equestrian_pulse", {})
    viral          = report.get("viral_pulse", {})
    hashtags       = report.get("hot_hashtags", [])
    seeds          = report.get("reddit_seeding", [])
    tw             = report.get("trend_watch", {})
    summary        = report.get("executive_summary", "")

    parts = [f"<!DOCTYPE html><html><head><meta charset='utf-8'>{STYLES}</head><body>"]
    parts.append('<div class="wrapper">')

    # Header
    parts.append(f"""
    <div class="header">
      <h1>🐴 CoBa's Daughter</h1>
      <p>Trend Intelligence · {slot} · {date_label}</p>
      {f'<p style="margin-top:10px;"><a href="{dashboard_url}" style="color:#c9a84c;">View Full Dashboard →</a></p>' if dashboard_url else ""}
    </div>""")

    # Executive summary
    if summary:
        parts.append(f"""
    <div class="section" style="background:#f9f5ec;">
      <p style="font-size:14px;color:#444;font-style:italic;margin:0;">{summary}</p>
    </div>""")

    # Brand Spotlight
    if spotlight:
        parts.append('<div class="section"><div class="section-title">✦ Your Action Plan Today</div>')
        parts.append('<div class="spotlight-grid">')
        for icon, key, label in [
            ("🎯", "top_opportunity", "Top Opportunity"),
            ("🐎", "equestrian_angle", "Equestrian"),
            ("✨", "beauty_body_care_angle", "Beauty & Body Care"),
            ("🌍", "cultural_moment", "Cultural Moment"),
            ("👀", "brand_to_watch", "Brand to Watch"),
        ]:
            val = spotlight.get(key, "")
            if val:
                parts.append(f"""
          <div class="spotlight-box">
            <div class="label">{icon} {label}</div>
            <div class="value">{val}</div>
          </div>""")
        parts.append('</div></div>')

    # Brand Launches
    if brand_launches:
        parts.append('<div class="section"><div class="section-title">🛍️ Brand Launches & Moves — Right Now</div>')
        for launch in brand_launches[:4]:
            urgency_color = "#e05c30" if launch.get("urgency") == "Now" else "#c9a84c"
            parts.append(f"""
        <div class="launch-card">
          <div class="launch-brand" style="color:{urgency_color};">
            {'🔴' if launch.get('urgency')=='Now' else '🟡'} {launch.get('brand','')}
          </div>
          <div class="launch-what">{launch.get('what','')}</div>
          <div class="launch-resp">↳ Our response: {launch.get('our_response','')}</div>
        </div>""")
        parts.append('</div>')

    # Hollywood Pulse
    if hw:
        parts.append('<div class="section"><div class="section-title">🎬 Hollywood Pulse</div>')
        for m in hw.get("top_celebrity_moments", [])[:3]:
            parts.append(f'<div class="hw-item">• {m}</div>')
        for lk in hw.get("top_celebrity_looks", [])[:2]:
            parts.append(f'<div class="hw-item">👗 {lk}</div>')
        if hw.get("brand_tie_in_opportunity"):
            parts.append(f'<p style="font-size:12px;color:#888;margin:10px 0 0;font-style:italic;">CoBa\'s Tie-In: {hw["brand_tie_in_opportunity"]}</p>')
        parts.append('</div>')

    # Top Trends
    if top_trends:
        parts.append('<div class="section"><div class="section-title">🏆 Top Trends</div>')
        for trend in top_trends[:6]:
            cat    = trend.get("category", "")
            color  = CAT_COLOR.get(cat, "#c9a84c")
            heat   = trend.get("heat_level", "")
            v      = trend.get("virality_score", 0)
            b      = trend.get("brand_relevance_score", 0)
            tactics = trend.get("tactics", {})
            post_now = tactics.get("post_now", [])
            hooks    = tactics.get("caption_hooks", [])
            hashtag_str = "  ".join(trend.get("key_hashtags", [])[:4])
            urgency = trend.get("urgency", "")

            parts.append(f'<div class="trend-card">')
            parts.append(f'<div class="trend-header" style="background:{color};">#{trend.get("rank")} — {trend.get("trend_name","")} &nbsp;·&nbsp; {cat} &nbsp;·&nbsp; {HEAT_EMOJI.get(heat,"")} {heat}</div>')
            parts.append(f'<div class="trend-body">')
            if urgency:
                urgency_color = "#e05c30" if urgency == "Post Today" else "#c9a84c"
                parts.append(f'<div style="font-size:11px;font-weight:bold;color:{urgency_color};margin-bottom:8px;">⚡ {urgency}</div>')
            parts.append(f'<div class="trend-meta">Window: {trend.get("window","")} &nbsp;|&nbsp; Sources: {", ".join(trend.get("signal_sources",[])[:3])}</div>')
            parts.append(f'<div class="score-row"><div class="score-item"><div class="score-label">Virality {v}/10</div>{_bar(v,"#c9a84c")}</div><div class="score-item"><div class="score-label">Brand Fit {b}/10</div>{_bar(b,color)}</div></div>')
            if trend.get("what_is_it"):
                parts.append(f'<div class="what">{trend["what_is_it"]}</div>')
            if trend.get("brand_relevance_reason"):
                parts.append(f'<p style="font-size:12px;color:#666;margin:0 0 10px;">💡 {trend["brand_relevance_reason"]}</p>')
            if post_now or hooks:
                parts.append('<div class="tactics"><div class="t-label">Action Plan</div><ul>')
                for p in post_now[:2]:
                    parts.append(f'<li>📱 {p}</li>')
                if hooks:
                    parts.append(f'<li>✍️ Hook: <em>{hooks[0]}</em></li>')
                parts.append('</ul></div>')
            if hashtag_str:
                parts.append(f'<p style="font-size:12px;color:#8a7a5a;margin:10px 0 0;">{hashtag_str}</p>')
            parts.append('</div></div>')
        parts.append('</div>')

    # Viral Pulse
    if viral:
        parts.append('<div class="section"><div class="section-title">🚀 Viral Pulse</div>')
        for label, key in [("Viral Products", "viral_products"), ("Viral Moments", "viral_moments"),
                            ("Social Trends", "viral_social_trends"), ("Community", "community_conversations")]:
            items = viral.get(key, [])
            if items:
                parts.append(f'<p style="font-size:11px;font-weight:bold;color:#888;text-transform:uppercase;letter-spacing:1px;margin:10px 0 4px;">{label}</p>')
                for item in items[:3]:
                    parts.append(f'<p style="font-size:13px;color:#444;margin:2px 0;">• {item}</p>')
        parts.append('</div>')

    # Hot Hashtags
    if hashtags:
        parts.append('<div class="section"><div class="section-title">#️⃣ Hot Hashtags</div><div class="hashtag-row">')
        for h in hashtags[:15]:
            parts.append(f'<span class="hashtag">{h["hashtag"]}</span>')
        parts.append('</div></div>')

    # Equestrian Pulse
    if eq:
        parts.append('<div class="section"><div class="section-title">🐎 Equestrian Pulse</div>')
        topics = eq.get("trending_topics", [])
        if topics:
            parts.append(f'<p style="font-size:13px;color:#444;">Trending: {" · ".join(topics[:3])}</p>')
        if eq.get("crossover_opportunity"):
            parts.append(f'<p style="font-size:13px;color:#444;">Beauty × Equestrian: {eq["crossover_opportunity"]}</p>')
        parts.append('</div>')

    # Reddit Seeding
    if seeds:
        parts.append('<div class="section"><div class="section-title">🌱 Reddit Seeding Opportunities</div>')
        parts.append('<p style="font-size:12px;color:#888;margin:0 0 12px;font-style:italic;">Participate authentically — never promote directly</p>')
        for seed in seeds[:4]:
            urgency = seed.get("urgency", "")
            badge = "🔴" if urgency == "Post Today" else "🟡"
            parts.append(f"""
        <div class="seed-card">
          <div class="seed-sub">{badge} {seed.get('subreddit','')} · {seed.get('seed_type','')}</div>
          <div class="seed-thread">{seed.get('thread_topic','')}</div>
          <div class="seed-angle">Angle: {seed.get('angle','')}</div>
        </div>""")
        parts.append('</div>')

    # Trend Watch
    if tw:
        parts.append('<div class="section"><div class="section-title">👀 Trend Watch</div>')
        for t in tw.get("emerging_to_watch", [])[:3]:
            parts.append(f'<p style="font-size:13px;color:#444;margin:3px 0;">🌱 {t}</p>')
        for t in tw.get("fading_trends", [])[:2]:
            parts.append(f'<p style="font-size:13px;color:#999;margin:3px 0;">📉 {t}</p>')
        if tw.get("predicted_next_week"):
            parts.append(f'<p style="font-size:13px;color:#c9a84c;margin:10px 0 0;font-weight:bold;">Next Week: {tw["predicted_next_week"]}</p>')
        parts.append('</div>')

    # Footer
    parts.append(f"""
    <div class="footer">
      <p>CoBa's Daughter Trend Intelligence · {date_label} {slot} · Powered by Claude AI</p>
      {f'<p style="margin-top:6px;"><a href="{dashboard_url}" style="color:#c9a84c;">View Full Dashboard</a></p>' if dashboard_url else ""}
    </div>""")

    parts.append('</div></body></html>')
    return "\n".join(parts)


def send(
    report: dict[str, Any],
    sender_email: str,
    sender_password: str,
    to_email: str,
    cc_email: str = "",
    dashboard_url: str = "",
) -> bool:
    """Send the trend digest as an HTML email via Gmail SMTP. Returns True on success."""
    if not sender_email or not sender_password:
        logger.warning("Email credentials not configured — skipping email notification")
        return False

    date = report.get("report_date", datetime.utcnow().strftime("%Y-%m-%d"))
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
        date_label = dt.strftime("%B %-d")
    except Exception:
        date_label = date

    subject = f"US Trend Daily Update - {date_label}"
    html_body = _build_html(report, dashboard_url=dashboard_url)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender_email
    msg["To"]      = to_email
    if cc_email:
        msg["Cc"] = cc_email

    msg.attach(MIMEText(html_body, "html"))

    recipients = [to_email] + ([cc_email] if cc_email else [])

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipients, msg.as_string())
        logger.info(f"Email sent to {to_email}" + (f" (cc: {cc_email})" if cc_email else ""))
        return True
    except Exception as e:
        logger.error(f"Email send error: {e}")
        return False
