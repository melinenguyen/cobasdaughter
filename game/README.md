# 💖 Dreamhouse Kingdom

A 3D browser dream world for girlies — **old-doll glam × Y2K pop culture × storybook nostalgia**.
Not just a game: every activity trains **creativity, logic, memory and language** while you play.

No build step, no assets, no dependencies to install — everything (world, character, music,
sounds, textures) is generated procedurally with the vendored copy of three.js in `lib/`.

## ▶️ How to run

Serve the folder over HTTP (modules + camera access require it):

```bash
cd game
python3 -m http.server 8000
# open http://localhost:8000
```

Any static host works too (GitHub Pages, Netlify, Vercel…). The photobooth camera
needs HTTPS (or localhost) because browsers only allow `getUserMedia` in secure contexts.

## 🎀 What's inside

| Activity | Where | Trains |
| --- | --- | --- |
| 💎 **Trivia crystals** | 5 themed zones (café, boutique, glow bar, pop stage, storybook garden) | knowledge, language |
| 🏰 **Escape room** — “The Forgotten Tower” | the castle | logic, memory, riddles, word play |
| 👗 **Style Studio** — dress-up & makeup | boutique wardrobe, vanity mirror, or the 👗 button | creativity, role play |
| 🪄 **Decorate mode** — personal world building | the 🪄 button | creativity (spend ✨ sparkles you collected) |
| 📸 **Sparkle Photobooth** | pink booth by the plaza | creativity + IG-story sharing |
| 🔮 **Whimsy of the Day** | wishing well or the 🔮 button | daily motivation |
| ⭐ **Star collecting** | everywhere | exploration (funds decorating) |

### The photobooth
- Sources: **your camera** (asks permission first — nothing is uploaded, everything is
  composed in your browser), **your gallery** (file picker), or **your character** posing in 3D.
- Pick **2, 3 or 4** photos per strip.
- Three decorated frame themes: *Y2K Chrome* 💿, *Dollhouse Pink* 🎀, *Storybook Night* 🏰,
  plus a custom caption.
- Exports a **1080 × 1920 PNG** — exactly Instagram-story sized — via download or native share.

### The escape room
Four charm puzzles guard the tower door code: a melody to memorize 💿, a riddle to solve 🪞,
a logic deduction 💍 and a word anagram ⭐. Escaping awards **+25 ✨** and unlocks the
exclusive **Midnight Tiara** in the Style Studio.

## 🎮 Controls

- **WASD / arrows** walk · **Shift** run · **drag** look around · **scroll** zoom
- **E** (or Enter) interact with whatever is glowing near you
- **Esc** closes any window
- Phone/tablet: virtual joystick + drag to look + 💬 button to interact

## 💾 Saving

Progress (name, look, trivia, escape progress, decorations, sparkles, crown) autosaves to
`localStorage` on every change. “Continue my story” resumes; “Start a new story” wipes it.

## 🧪 Dev notes

- `?debug` shows an FPS/draw-call meter and pins full quality.
- Adaptive quality: pixel ratio steps down (and shadows off, last resort) if FPS stays low.
- Fixed-timestep simulation (60 Hz) keeps movement identical on any refresh rate.
- `window.__game` exposes hooks used by the Playwright test suite.
