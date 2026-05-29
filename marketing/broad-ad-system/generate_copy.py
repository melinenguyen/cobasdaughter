#!/usr/bin/env python3
"""
CoBa's Daughter - Broad campaign: full Meta ad copy for all 100 ads.

Pulls angle / concept / product / hook from generate_ads.py (source of truth)
and adds, per ad:
  - headline_cta    : Meta "Headline" field — a short CTA sentence
  - caption         : Meta "Primary text" — the post caption
  - ad_description  : Meta "Description" field — one supporting line

Run:  python3 generate_copy.py
Outputs:
  - 100-ad-copy.csv   (ad_id, funnel, angle, concept, product, hook, headline_cta, caption, ad_description)
  - 100-ad-copy.md    (human-readable, grouped by angle)

Rules kept: one offer per BOF ad, no price on MOF ads, single-minded per ad.
"""

import csv
import os
from generate_ads import rows

HERE = os.path.dirname(os.path.abspath(__file__))

# (headline_cta, caption, ad_description) — index-aligned to generate_ads.ADS order
COPY = [
    # ---- MOF: Ritual ----
    ("Make your shower a ritual.",
     "Ten quiet minutes. Cold-pressed coffee, raw cane sugar, steam. The smallest ritual that makes the whole day feel handled. Meet the Coffee Scrub.",
     "The body ritual worth slowing down for."),
    ("Start your daily ritual.",
     "Self-care isn't selfish — it's maintenance. Bookend your day with something that's only for you. Body care, made to be felt.",
     "Body care that earns its place in your routine."),
    ("Take the five minutes.",
     "Scrub, soak, breathe. Five minutes that quietly change the other twenty-three hours. Your reset starts in the shower.",
     "A five-minute reset for body and mind."),
    ("Romanticize your routine.",
     "Texture, warmth, scent — the small luxuries that add up. Romanticize the mundane, starting with your shower. The Coffee Scrub.",
     "The everyday ritual that feels like a treat."),
    ("Keep the ritual.",
     "Some rituals are inherited — and some are worth keeping. Body care made the slow way, the way it was always meant to be. Meet CoBa's Daughter.",
     "Heritage body care, made the slow way."),
    ("Wash the day off.",
     "An end-of-day ritual for skin that's had enough. Lather, scrub, reset — and actually feel the day leave. Your PM wind-down, sorted.",
     "The grounding ritual your evenings were missing."),
    ("Build the glow habit.",
     "Glow isn't an accident — it's a habit. Two minutes of scrub, three times a week. That's the whole secret. The Coffee Scrub.",
     "Two minutes, three times a week. That's it."),
    ("Upgrade your bathroom.",
     "Make the smallest room the nicest one. Objects and rituals worth slowing down for — body care that looks as good as it feels.",
     "Body care beautiful enough to leave on display."),
    # ---- MOF: Sensory ----
    ("Find your new favourite scent.",
     "It smells like a slow morning in a warm kitchen. Real coffee, raw sugar — nothing synthetic pretending to be. The Coffee Scrub.",
     "Real coffee. Real scent. Nothing fake."),
    ("Feel the texture.",
     "Grains that melt as they buff — never sandpaper, never slip. The kind of texture you can feel working. Meet the Coffee Scrub.",
     "Exfoliation you can actually feel working."),
    ("Find your calm.",
     "Aromatherapy, minus the woo. Scents that actually slow your breathing down. The 3-in-1 Soap Trio.",
     "Scents that quietly change your mood."),
    ("Cool down.",
     "The first cold gel of summer on warm skin. Instant relief that sinks in — never sticky, never greasy. Pure Aloe Gel.",
     "Cooling relief that disappears into skin."),
    ("Escape your Tuesday.",
     "Close your eyes — you're not in the shower anymore. Scent that takes you somewhere, even on a Tuesday. Body care as a small escape.",
     "A sensory escape, built into your shower."),
    ("Smell expensive.",
     "Skin that smells expensive — quietly. The kind of scent people lean in to ask about. Find your signature.",
     "The 'what are you wearing?' kind of scent."),
    ("Try the aloe.",
     "Cool, clean, and a little addictive. Aloe gel that disappears into skin and takes the heat with it. You'll reach for it daily.",
     "Lightweight aloe you'll reach for daily."),
    ("Wake up your skin.",
     "Coffee for your skin, not your nerves. All the ritual of your morning cup — none of the jitters. The Coffee Scrub.",
     "Your morning coffee, reimagined for skin."),
    # ---- MOF: Results ----
    ("See it in one shower.",
     "Smoother in one shower — we timed it. Buff away the dull and reveal the skin that was always there. Exfoliate + nourish.",
     "Visibly smoother skin after one wash."),
    ("Smooth the rough spots.",
     "Goodbye, bumpy arms. Gentle exfoliation for the rough patches nobody talks about. The Coffee Scrub does the quiet work.",
     "Gentle exfoliation for rough, bumpy skin."),
    ("Shave smarter.",
     "Razor bumps didn't stand a chance. Exfoliate before, soothe after — smooth, settled skin every time. Scrub + Aloe.",
     "Exfoliate before, soothe after. Smooth skin."),
    ("Get the glow.",
     "The 'what are you using?' kind of glow. Soft, lit-from-within skin from the neck down. The Coffee Scrub.",
     "Lit-from-within glow, head to toe."),
    ("Prep your glow.",
     "Self-tan, but make it even. Exfoliate first and watch your glow go on flawless — no patches, no streaks. The Coffee Scrub.",
     "The exfoliating prep step for a flawless tan."),
    ("Soothe the burn.",
     "Sunburn's worst enemy. Pure aloe that calms the heat and saves the weekend. Keep the Aloe Gel close.",
     "Pure aloe that calms heat on contact."),
    ("Feel the difference.",
     "Soft enough to notice — every time you sit down. Body skin that finally feels as cared-for as your face. The Exfoliate & Nourish Set.",
     "Body skin as cared-for as your face."),
    ("Build your routine.",
     "Your body skincare routine has been waiting. Exfoliate, nourish, repeat — results you can actually feel. The Exfoliate & Nourish Set.",
     "Exfoliate, nourish, repeat — feelable results."),
    # ---- MOF: Clean ----
    ("Read the label.",
     "Ingredients you can pronounce — that's the point. Coffee, sugar, oil. That's the whole list. The Coffee Scrub.",
     "Coffee, sugar, oil. Nothing to hide."),
    ("Meet the maker.",
     "Made the slow way, on purpose. Small batches, real ingredients, no shortcuts. This is body care with intention.",
     "Small-batch body care, made with intention."),
    ("See what's inside.",
     "If it's not good enough to eat, it's not going on your skin. Food-grade ingredients, head to toe. The Coffee Scrub.",
     "Food-grade ingredients, head to toe."),
    ("Shop clean.",
     "No synthetic fragrance. No fake glow. No filler. Just what your skin actually wants — and nothing it doesn't.",
     "Clean formulas. Nothing your skin doesn't need."),
    ("Check the gel.",
     "The aloe inside is actually aloe — not water with a green tint and a promise. Real, high-percentage Aloe Gel.",
     "Real aloe, not water with a green tint."),
    ("Feel good about it.",
     "Cruelty-free, because obviously. Kind to your skin, kinder to everything else. Body care you can feel good about.",
     "Cruelty-free body care, always."),
    ("Discover why.",
     "We left out everything your skin doesn't need — and kept the ingredients that earn their place. Intentional by design.",
     "Only the ingredients that earn their place."),
    ("Discover the story.",
     "Heritage in a jar. Rooted in Vietnamese ritual, made for everyday skin. Meet CoBa's Daughter.",
     "Body care rooted in Vietnamese ritual."),
    # ---- MOF: Gift ----
    ("Find the gift.",
     "The gift that says 'I actually thought about this.' Beautiful enough to give, good enough they'll rebuy. The Rattan Valise.",
     "A gift beautiful enough to give twice."),
    ("Skip the candle.",
     "Skip the candle — again. Give a gift she'll use every single day, not shelve. The Exfoliate & Nourish Set.",
     "The gift she'll actually use every day."),
    ("See the gift sets.",
     "Hand-woven rattan, filled with the good stuff. A keepsake basket she'll keep long after the last scrub. The Rattan Basket.",
     "A rattan keepsake, filled with bestsellers."),
    ("Shop their gift.",
     "For the person who buys everyone else's gifts — it's their turn. Make it easy, make it beautiful. The Rattan Valise.",
     "A considered gift for the gift-giver."),
    ("Discover the valise.",
     "A gift that travels well. The Rattan Valise looks as good on a shelf as it does in a suitcase. Beautifully practical.",
     "The rattan valise that goes everywhere."),
    ("Find the anniversary gift.",
     "Anniversaries deserve more than flowers that die. Give a ritual that lasts longer than a bouquet. Body care, beautifully gifted.",
     "A gift that outlasts the bouquet."),
    ("Explore gift sets.",
     "Wrapped, ribboned, and ready to impress. Gifting handled — you just sign the card. The gift sets are here.",
     "Gift-ready sets. You just sign the card."),
    ("Shop the gift set.",
     "Give the glow, not the guesswork. A body care set anyone will be happy to unwrap. The Exfoliate & Nourish Set.",
     "The foolproof gift for anyone."),
    # ---- BOF: Scrub Duo ($69, save $15) ----
    ("Shop the Scrub Duo.",
     "Two scrubs, one smoother you. The Scrub Duo is $69 (was $84) — that's $15 back in your pocket. Stock up on the bestseller.",
     "Scrub Duo — $69, save $15."),
    ("Get the duo.",
     "Double the glow for $15 less. Our bestselling Coffee Scrub, now in a duo for $69. Smooth skin, sorted.",
     "Two coffee scrubs, $69. Save $15."),
    ("Shop the duo.",
     "One for the shower, one for the gift bag. The Scrub Duo is $69 — keep one, give one, save $15.",
     "Scrub Duo, $69 — keep one, gift one."),
    ("Stock up now.",
     "Never run out of your favourite scrub again. Grab the Scrub Duo for $69 and save $15. Future-you says thanks.",
     "Scrub Duo — $69, save $15."),
    ("Buy the duo.",
     "Smooth skin, twice over. The Scrub Duo is $69 instead of $84 — the easiest $15 you'll save all week.",
     "Two coffee scrubs for $69."),
    ("Shop the bestseller duo.",
     "Your bestseller, now buy-in-twos. Two Coffee Scrubs for $69 — save $15 on the one everyone repurchases.",
     "Bestselling scrub, now a $69 duo."),
    ("Grab the duo.",
     "The duo that disappears fastest. Scrub Duo, $69 (was $84) — while it lasts. Save $15 before it's gone.",
     "Scrub Duo, $69 — while it lasts."),
    ("Shop the Scrub Duo.",
     "$15 off your smoothest skin yet. Two coffee scrubs, one easy decision — the Scrub Duo is $69.",
     "Scrub Duo — $69, save $15."),
    # ---- BOF: Aloe Duo ($59, save $5) ----
    ("Shop the Aloe Duo.",
     "Cool skin, doubled. The Aloe Duo is $59 (was $64) — cooling relief for home and away. Save $5.",
     "Aloe Duo — $59, save $5."),
    ("Get the duo.",
     "One by the bed, one in the bag. The Aloe Duo is $59 — cooling relief, everywhere you need it. Save $5.",
     "Two aloe gels, $59. Save $5."),
    ("Stock up now.",
     "Sunburn season, sorted. Two pure aloe gels for $59 — be ready before the first burn. The Aloe Duo.",
     "Aloe Duo — $59, be ready."),
    ("Buy the duo.",
     "Twice the cool-down for $5 less. The Aloe Duo is $59 instead of $64. Keep calm and reapply.",
     "Two aloe gels for $59."),
    ("Shop the duo.",
     "Never search for your aloe again. The Aloe Duo is $59 — one for home, one for away. Save $5.",
     "Aloe Duo — $59, save $5."),
    ("Grab the duo.",
     "Cooling relief, buy-in-twos. Two pure aloe gels for $59 — because one is never quite enough.",
     "Two aloe gels for $59."),
    ("Soothe and save.",
     "The after-sun your skin will thank you for. The Aloe Duo is $59 (was $64) — cool, calm, save $5.",
     "Aloe Duo — $59, save $5."),
    ("Shop the Aloe Duo.",
     "Hydration that travels in pairs. Two aloe gels for $59 — save $5 and never go without.",
     "Aloe Duo — $59, save $5."),
    # ---- BOF: Soap Trio (buy 3 for 2, $72) ----
    ("Shop the trio.",
     "Buy 3, pay for 2. The 3-in-1 Soap Trio is $72 instead of $108 — three bars, the price of two.",
     "Soap Trio — buy 3 for 2, $72."),
    ("Get the trio.",
     "Three soaps, the price of two. The Soap Trio is $72 — that's $36 saved. Stock the soap dish.",
     "Soap Trio — $72, save $36."),
    ("Shop now.",
     "One bar's never enough — good thing there's three. Buy 3 for 2 with the Soap Trio, just $72.",
     "Soap Trio — buy 3 for 2, $72."),
    ("Buy the trio.",
     "Cleanse, lather, repeat — three times over. The 3-in-1 Soap Trio is $72 (was $108). Buy 3 for 2.",
     "Soap Trio — $72, save $36."),
    ("Shop the trio.",
     "Keep one, gift two — or keep all three. Buy 3 for 2 with the Soap Trio, just $72.",
     "Soap Trio — buy 3 for 2, $72."),
    ("Claim your free bar.",
     "Your free third bar is waiting. Buy 3 for 2 with the 3-in-1 Soap Trio — three bars for $72.",
     "Buy 2 soaps, get the 3rd free — $72."),
    ("Get the trio.",
     "The soap that turns showers into spa time — times three. $72 for the Soap Trio, save $36. Buy 3 for 2.",
     "Soap Trio — buy 3 for 2, $72."),
    ("Shop the Soap Trio.",
     "Stock the soap dish for a season. Buy 3 for 2 — the Soap Trio is $72 (was $108). Save $36.",
     "Soap Trio — $72, save $36."),
    # ---- BOF: Free shipping ($50+) ----
    ("Shop now.",
     "Your glow ships free. Orders over $50 get free US shipping — fill your cart and let it land at your door.",
     "Free US shipping on orders $50+."),
    ("Reach free shipping.",
     "Add one more — shipping's on us at $50. Free US shipping when you cross the line. Your skin says go for it.",
     "Free US shipping over $50."),
    ("Build your order.",
     "Treat yourself plus free shipping — easy math. Spend $50, ship free across the US. Stock up on the good stuff.",
     "Spend $50, ship free."),
    ("Top up and ship free.",
     "Almost at $50? Your skin says go for it. Free US shipping kicks in the moment you cross $50.",
     "Free US shipping at $50+."),
    ("Shop bestsellers.",
     "Bestsellers in, shipping out — free. Orders over $50 ship free across the US. Start with the Coffee Scrub.",
     "Free US shipping on orders $50+."),
    ("Shop the edit.",
     "The glow's worth it — the shipping's free. Free US delivery on every order over $50. Treat your skin.",
     "Free US shipping over $50."),
    ("Fill your cart.",
     "Everything you've been eyeing, one order, free shipping. Orders $50+ ship free across the US.",
     "Free US shipping on $50+."),
    ("Shop now.",
     "Skip the shipping fee, not the self-care. Free US shipping on every order over $50. The good stuff, delivered.",
     "Free US shipping over $50."),
    # ---- BOF: Hero SKU ----
    ("Shop the Coffee Scrub.",
     "Meet the scrub 10,000 showers swear by. Cold-pressed coffee, raw sugar, smoother skin in one wash. Our #1 bestseller.",
     "Our #1 bestselling Coffee Scrub."),
    ("Shop the hero.",
     "The Coffee Scrub — the one everyone means. Cold-pressed coffee + raw sugar, visibly smoother skin in one wash.",
     "The bestselling Coffee Scrub."),
    ("Shop the Aloe Gel.",
     "The aloe gel that earns its spot by your bed. Cooling, fast-absorbing, endlessly reached-for. Our bestselling Aloe Gel.",
     "Our bestselling, fast-absorbing Aloe Gel."),
    ("Get it now.",
     "Sold out twice. Back for good. The Coffee Scrub everyone waited for is back in stock — don't miss it again.",
     "Back in stock: the Coffee Scrub."),
    ("Shop the Coffee Scrub.",
     "If you buy one thing, make it this. The Coffee Scrub is where everyone starts — and where most people stay.",
     "Start here: the bestselling Coffee Scrub."),
    ("See the reviews.",
     "5 stars, 2,000+ times over. The Coffee Scrub our reviewers can't stop talking about. See what the fuss is about.",
     "5 stars, 2,000+ reviews."),
    ("Shop the Aloe Gel.",
     "The aloe gel that does the most by doing the least. One hero ingredient, endless uses. Our bestselling Aloe Gel.",
     "One-ingredient hero. Endless uses."),
    ("Shop now.",
     "Your shelf called — it wants the bestseller. The Coffee Scrub is the one worth the hype. See for yourself.",
     "The #1 bestseller, worth the hype."),
    # ---- BOF: Gift set / rattan ----
    ("Shop the gift set.",
     "Gifting, beautifully handled. The Rattan Valise arrives wrapped and ready — bestsellers inside, keepsake outside.",
     "The Rattan Valise — wrapped and ready."),
    ("Shop gift sets.",
     "The gift that arrives looking expensive. Hand-woven rattan, filled with bestsellers. Gifting, sorted.",
     "A rattan gift set that looks luxe."),
    ("Shop the set.",
     "One set, every base covered. The Exfoliate & Nourish Set is the gift that does it all — and gets used.",
     "The set that does it all."),
    ("Shop the basket.",
     "She'll keep the basket forever. A rattan keepsake plus body care she'll actually use. The Rattan Basket.",
     "Rattan keepsake + bestsellers inside."),
    ("Shop the valise.",
     "Anniversary, sorted in one click. The Rattan Valise is a gift that lasts long past the date. Wrapped and ready.",
     "The Rattan Valise — anniversary-ready."),
    ("Shop the set.",
     "Give the whole ritual, not just a piece. The Exfoliate & Nourish Set is ready to gift — glow included.",
     "The complete ritual, ready to gift."),
    ("Shop gift sets.",
     "The 'where did you get that?' gift. Rattan, ribbon, and bestsellers inside. Give something they'll ask about.",
     "The gift they'll ask about."),
    ("Shop the set.",
     "Birthdays, handled beautifully. A body care set worth unwrapping — and worth keeping. The Exfoliate & Nourish Set.",
     "The birthday gift worth unwrapping."),
    # ---- BOF: Social proof ----
    ("Shop bestsellers.",
     "\"I've repurchased four times\" — and she's not alone. Find out what the fuss is about. The Coffee Scrub.",
     "5 stars: 'I've repurchased four times.'"),
    ("Shop the scrub.",
     "\"My legs have never been this smooth.\" Real words, real skin. Join the thousands who made the switch. The Coffee Scrub.",
     "5 stars: 'Never been this smooth.'"),
    ("Join them.",
     "10,000+ smoother showers and counting. See why the Coffee Scrub keeps selling out — then never run low again.",
     "Loved by 10,000+ and counting."),
    ("Shop now.",
     "\"The only body product I actually finish.\" Real words from real skin. Meet the body care you'll use to the last drop.",
     "5 stars: 'The only one I finish.'"),
    ("See the reviews.",
     "Rated 4.9 — earned, not bought. Thousands of reviews can't all be wrong. Meet the Coffee Scrub.",
     "Rated 4.9 from thousands of reviews."),
    ("Shop gifts.",
     "\"Gifted it. Now they're obsessed too.\" The body care that converts everyone. Find their next favourite.",
     "5 stars: 'Gifted it, now they're obsessed.'"),
    # ---- BOF: Birthday horoscope (15% off) ----
    ("Treat yourself, Gemini.",
     "Happy birthday, Gemini. Your glow deserves a gift too — take 15% off with code GEMINI15. It's written in the stars.",
     "15% off for Gemini — code GEMINI15."),
    ("Shop your birthday.",
     "It's your season, Cancer — glow accordingly. Take 15% off your birthday edit with code CANCER15.",
     "15% off for Cancer — code CANCER15."),
    ("Treat yourself, Leo.",
     "Leo season is your season. Self-gifting is written in the stars — take 15% off with code LEO15.",
     "15% off for Leo — code LEO15."),
    ("Shop your birthday.",
     "Virgo, you've earned a little softness. Take 15% off your birthday glow with code VIRGO15.",
     "15% off for Virgo — code VIRGO15."),
    ("Claim your code.",
     "The stars say: treat yourself. It's your birthday month — take 15% off with your sign's code, [SIGN]15.",
     "15% off in your birthday month."),
    ("Shop your birthday edit.",
     "A birthday glow, written in the stars. Take 15% off your sign's season with code [SIGN]15.",
     "15% off your birthday edit — [SIGN]15."),
]

HEADERS = ["ad_id", "funnel", "angle", "concept", "product", "hook",
           "headline_cta", "caption", "ad_description"]


def merged():
    base = rows()
    assert len(base) == len(COPY) == 100, f"len mismatch: {len(base)} vs {len(COPY)}"
    out = []
    for r, (cta, caption, desc) in zip(base, COPY):
        out.append({
            "ad_id": r["ad_id"],
            "funnel": r["funnel"],
            "angle": r["angle"],
            "concept": r["concept"],
            "product": r["product"],
            "hook": r["headline"],          # on-image hook from the design system
            "headline_cta": cta,
            "caption": caption,
            "ad_description": desc,
        })
    return out


def write_csv(path, data):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS)
        w.writeheader()
        w.writerows(data)


def write_md(path, data):
    lines = ["# CoBa's Daughter — Broad: 100 Ads, Full Copy\n",
             "Per ad: **Hook** (on-image) · **Headline (CTA sentence)** · "
             "**Caption** (primary text) · **Ad Description**. "
             "One offer per BOF ad; no price on MOF.\n"]
    current = None
    for r in data:
        if r["angle"] != current:
            current = r["angle"]
            lines.append(f"\n## {r['funnel']} · {r['angle']}\n")
        lines.append(f"**{r['ad_id']}** · _{r['concept']}_ · {r['product']}")
        lines.append(f"- **Hook:** {r['hook']}")
        lines.append(f"- **Headline (CTA):** {r['headline_cta']}")
        lines.append(f"- **Caption:** {r['caption']}")
        lines.append(f"- **Ad description:** {r['ad_description']}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    data = merged()
    write_csv(os.path.join(HERE, "100-ad-copy.csv"), data)
    write_md(os.path.join(HERE, "100-ad-copy.md"), data)
    mof = sum(1 for r in data if r["funnel"] == "MOF")
    print(f"OK: {len(data)} ads ({mof} MOF / {len(data)-mof} BOF)")
    print("Wrote: 100-ad-copy.csv, 100-ad-copy.md")


if __name__ == "__main__":
    main()
