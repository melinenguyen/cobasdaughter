# CoBa's Daughter — Broad (Self-Care & Gifting) Static Ad Strategy

**Scope:** The "Broad" wedge of the performance plan — *self care + gifting messaging, ~70% of ad spend* — built as a smart-funnel static-ad system for Meta (Instagram + Facebook).
**Deliverable:** 100 single-minded static ads. **40 MOF / 60 BOF.**
**Formats:** 1:1 (master) + 9:16 (adapt). **Font:** Plus Jakarta Sans.
**Golden rule:** one idea, one job per ad. No promo-stacking. MOF = a *reason to believe*. BOF = *one* offer.

---

## 1. Where this sits in the funnel

The agency plan splits Broad away from the Equestrian persona and from the 10% upper-funnel brand-activation spend. This system deliberately **skips pure TOF awareness** (that's covered by the brand-activation wedge and KOL content) and concentrates on the two stages that turn attention into revenue:

| Stage | Job of the ad | What it leads with | What it never does |
|-------|---------------|--------------------|--------------------|
| **MOF** (consideration) | Build desire + give a reason to believe | Angle + RTB (ingredient, result, ritual, craft) | Quote a price or discount |
| **BOF** (conversion) | Remove the last friction + make the ask | ONE offer / proof / hero SKU | Mix promos or explain the brand |

**40/60 split rationale (your pick):** retargeting and warm Broad pools are where body-care DTC converts cheapest, so the weight sits on BOF. The 40 MOF ads keep the warm pool topped up and give the algorithm fresh creative to find new pockets of the Broad audience without burning straight to discount.

---

## 2. Competitor teardown — what we're adapting

Spied via Meta Ad Library coverage + brand analysis. We borrow the *mechanics*, not the look.

- **Salt & Stone** — Leads every ad with a single emotional hook ("the body mist that makes everyone ask *what are you wearing?*"), shot UGC-style on skin, *result-and-feeling first, product second*. → We adopt: **one-line hooks built on an outcome**, skin-forward visuals, the "compliment glow" angle (`M-RESULT`, `M-SENSE`).
- **Nécessaire** — Clinical-clean minimalism, plain-spoken honesty, "necessity not hype," defines "clean" instead of sloganeering. → We adopt: the **ingredient-honesty angle** (`M-CLEAN`), tons of negative space, no exclamation-mark energy.
- **Flamingo Estate** — Lush, editorial, sensory storytelling; objects as *desirable things*, heritage and craft as the premium signal. → We adopt: the **ritual + heritage angles** (`M-RITUAL`), rattan-as-keepsake gifting (`M-GIFT`, `B-GIFTSET`), elevated still-life direction.
- **OUAI** — Witty, human, turns customer language into copy; playful but never cheap. → We adopt: the occasional **wink** in hooks ("Skip the candle. Again.", "Cruelty-free, because obviously.") to keep a premium brand from sounding stiff.

**Net positioning for CoBa's Daughter:** *Flamingo Estate's sensory craft × Nécessaire's clean honesty*, with Salt & Stone's outcome-led hooks and a light OUAI wit. Heritage (Vietnamese ritual, cold-pressed coffee, hand-woven rattan) is the ownable differentiator no competitor can copy.

---

## 3. Brand voice — distinctive & intentional

**Voice in one line:** *A close friend with exquisite taste — warm, unhurried, quietly confident. Never shouty, never salesy, never generic "treat yourself" filler.*

Do:
- Short, declarative hooks. One thought.
- Sensory and specific ("cold-pressed coffee + raw cane sugar," not "natural ingredients").
- Confidence over hype. State the result; don't oversell it.
- A dry wink occasionally — earned, never cheesy.
- Lowercase-feel calm; let white space carry the premium.

Don't:
- Stack claims or promos.
- Use "amazing / luxurious / pamper / indulge / must-have."
- Exclamation overload.
- Bury the angle under decoration.

---

## 4. The angle architecture

**MOF — 5 angles × 8 ads = 40** (RTB-led, no price):
| Code | Angle | Reason to believe it leans on |
|------|-------|-------------------------------|
| `M-RITUAL` | Make it a ritual / slow living | Emotional payoff + heritage |
| `M-SENSE` | Sensory escape (scent/texture/aromatherapy) | Real coffee scent, melt-in grain, cooling aloe |
| `M-RESULT` | Visible results (smooth / glow) | Exfoliate + nourish; fast, feelable results |
| `M-CLEAN` | Made with intention (clean/craft) | Short ingredient list, food-grade, real aloe %, heritage |
| `M-GIFT` | The considered gift (emotional) | Rattan keepsake, "they'll actually use it" |

**BOF — 8 angles = 60** (ONE promo each):
| Code | Angle | The single offer |
|------|-------|------------------|
| `B-SCRUBDUO` (8) | Scrub Duo | $69 (was $84) · save $15 |
| `B-ALOEDUO` (8) | Aloe Duo | $59 (was $64) · save $5 |
| `B-SOAPTRIO` (8) | 3-in-1 Soap Trio | Buy 3 for 2 · $72 (was $108) |
| `B-SHIP` (8) | Threshold builder | Free US shipping $50+ |
| `B-HERO` (8) | Hero SKU spotlight | Bestseller social proof (no price) |
| `B-GIFTSET` (8) | Gift set / rattan | Gift-ready framing |
| `B-PROOF` (6) | Review-led conversion | ★ social proof |
| `B-ZODIAC` (6) | Birthday horoscope | 15% off, sign-gated ([SIGN]15) |

> **Promo hygiene:** each BOF ad references exactly one promo. The birthday-horoscope ads must only be served to users whose birthday falls in that sign's window (audience-gated at the ad-set level, per the promo rules). The generic `[SIGN]15` rows are templates — duplicate per sign in Bulk Create (see runbook).

---

## 5. How to read each ad (field map)

Every row in `100-ads.md` / the CSVs has the fields that map directly to text layers in the Canva template:

- **headline** → the hook (largest layer, the scroll-stopper)
- **subhead** → the payoff / RTB or offer detail
- **badge** → a pill/chip: an RTB tag (MOF) or the single offer (BOF)
- **cta** → button label (softer for MOF, harder for BOF)
- **product** → product caption
- **visual** → art direction for the image you place (not printed)

---

## 6. Testing logic (how to actually run these)

1. **Launch by angle, not all at once.** Drop 1–2 concepts per angle first; let Meta find the winning angle, then pour the other concepts of that angle in.
2. **MOF feeds BOF.** Anyone who engages with MOF (`M-*`) should be retargeted with the matching BOF angle (e.g., `M-RESULT` → `B-SCRUBDUO`; `M-GIFT` → `B-GIFTSET`).
3. **One variable per test.** Same image, swap the hook → isolates copy. Same hook, swap image → isolates creative.
4. **Refresh cadence.** Static fatigues fast on Broad; this 100-ad library is built so you always have the next concept of a winning angle ready to ship.

See `CANVA-RUNBOOK.md` to turn this into finished 1:1 + 9:16 designs and batch-export.
