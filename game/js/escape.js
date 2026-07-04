// 🏰 The Forgotten Tower — a point-and-click escape room.
// Four charm puzzles (memory · language · logic · word magic) reveal the
// digits of the door code. Escaping unlocks the Midnight Tiara.

let G = null;

const PUZZLES = {
  melody: { icon: '💿', name: 'CD Player', digit: 7, kind: 'memory' },
  mirror: { icon: '🪞', name: 'Magic Mirror', digit: 3, kind: 'language' },
  jewelry: { icon: '💍', name: 'Jewelry Box', digit: 9, kind: 'logic' },
  poster: { icon: '⭐', name: 'Star Poster', digit: 1, kind: 'word' },
};
const CODE_ORDER = ['mirror', 'melody', 'jewelry', 'poster']; // as printed on the door note → 3791

const MELODY_COLORS = [
  { c: '#ff2d95', freq: 523.25, emoji: '💖' },
  { c: '#4fc3f7', freq: 659.25, emoji: '💙' },
  { c: '#a98bf5', freq: 783.99, emoji: '💜' },
  { c: '#ffd166', freq: 1046.5, emoji: '💛' },
];
const MELODY_SEQ = [0, 2, 1, 3, 0, 1];

let melodyInput = [];
let melodyPlaying = false;
let mirrorTries = 0;
let arrangement = []; // jewelry picks

export function initEscape(game) {
  G = game;
  document.getElementById('escape-close').addEventListener('click', () => closeEscape());
}

export function openEscape() {
  G.state.uiOpen = true;
  document.getElementById('escape').classList.remove('hidden');
  G.sfx.open();
  renderScene();
  renderCharms();
  if (G.state.escape.escaped) {
    showPanel(panelIntro(true));
  } else {
    showPanel(panelIntro(false));
  }
}

function closeEscape() {
  document.getElementById('escape').classList.add('hidden');
  G.state.uiOpen = false;
  G.clearNear();
}

function solved(id) { return !!G.state.escape.solved[id]; }
function allSolved() { return Object.keys(PUZZLES).every(solved); }

function renderScene() {
  const scene = document.getElementById('escape-scene');
  scene.innerHTML = `
    <div class="esc-window"><div class="esc-moon"></div></div>
    <div class="esc-floor"></div>
    <div class="esc-rug"></div>
  `;
  const spots = [
    { id: 'melody', style: 'right:6%; top:14%; width:19%; height:30%;' },
    { id: 'mirror', style: 'left:30%; top:6%; width:17%; height:44%;' },
    { id: 'jewelry', style: 'left:53%; top:26%; width:16%; height:24%;' },
    { id: 'poster', style: 'right:28%; top:8%; width:14%; height:26%;' },
    { id: 'door', style: 'left:6%; bottom:8%; width:16%; height:52%;' },
  ];
  spots.forEach((s) => {
    const b = document.createElement('button');
    const p = PUZZLES[s.id];
    b.className = 'esc-hotspot' + (s.id !== 'door' && solved(s.id) ? ' solved' : '');
    b.style.cssText = s.style;
    if (s.id === 'door') {
      b.innerHTML = `<span class="big">${G.state.escape.escaped ? '🚪✨' : '🔐'}</span><span>Tower Door</span>`;
    } else {
      b.innerHTML = `<span class="big">${p.icon}</span><span>${p.name}</span>`;
    }
    b.addEventListener('click', () => { G.sfx.click(); openSpot(s.id); });
    document.getElementById('escape-scene').appendChild(b);
  });
}

function renderCharms() {
  const el = document.getElementById('escape-charms');
  el.innerHTML = '';
  CODE_ORDER.forEach((id) => {
    const p = PUZZLES[id];
    const d = document.createElement('div');
    d.className = 'charm' + (solved(id) ? ' found' : '');
    d.textContent = solved(id) ? `${p.icon} ${p.digit}` : `${p.icon} ?`;
    el.appendChild(d);
  });
}

function showPanel(node) {
  const panel = document.getElementById('escape-panel');
  panel.innerHTML = '';
  panel.appendChild(node);
}

function puzzleCard(title, html) {
  const d = document.createElement('div');
  d.className = 'esc-puzzle';
  d.innerHTML = `<h3>${title}</h3>${html}`;
  return d;
}

function markSolved(id, card) {
  G.state.escape.solved[id] = true;
  G.save();
  G.sfx.correct();
  renderScene();
  renderCharms();
  const p = PUZZLES[id];
  card.querySelector('.esc-feedback').innerHTML = `✨ The charm glows and whispers a number: <b style="font-size:22px">${p.digit}</b>`;
  G.confetti(24);
}

// ---------------------------------------------------------------------------
function panelIntro(escaped) {
  return puzzleCard(
    escaped ? '🌙 The tower remembers you' : '📜 A note on the rug',
    escaped
      ? `<p>The door swings open at your touch now. The Midnight Tiara is yours forever —
         and the tower keeps its softest lamp lit for you. 💜</p>`
      : `<p>“Locked by a sleepy spell at 11:59pm, Dec 31, 1999…<br/>
         Four charms guard four numbers. Read the door in this order:</p>
         <div class="esc-row" style="font-size:24px">🪞 → 💿 → 💍 → ⭐</div>
         <p style="margin-top:10px">Wake every charm, then whisper the code to the door.”</p>`
  );
}

// --- Melody memory puzzle ---------------------------------------------------
function openSpot(id) {
  if (id === 'door') return showPanel(panelDoor());
  if (solved(id)) {
    const p = PUZZLES[id];
    const card = puzzleCard(`${p.icon} ${p.name}`, `<p>The charm hums happily. Its number is <b>${p.digit}</b>.</p>`);
    return showPanel(card);
  }
  if (id === 'melody') return showPanel(panelMelody());
  if (id === 'mirror') return showPanel(panelMirror());
  if (id === 'jewelry') return showPanel(panelJewelry());
  if (id === 'poster') return showPanel(panelPoster());
}

function panelMelody() {
  melodyInput = [];
  const card = puzzleCard('💿 CD Player — Melody of Hearts',
    `<p>A burnt CD labeled “summer mix ’99” 💿. It plays a sparkly melody —
     <b>listen, then play it back</b> by heart.</p>
     <div class="esc-row" id="melody-row"></div>
     <div class="esc-row">
       <button class="ghost-btn" id="melody-play">▶ Play melody</button>
     </div>
     <div class="esc-feedback" id="melody-fb"></div>
     <div class="esc-hint">memory training: hum it in your head as it plays 🎧</div>`);
  const row = card.querySelector('#melody-row');
  MELODY_COLORS.forEach((m, i) => {
    const b = document.createElement('button');
    b.className = 'melody-btn';
    b.style.background = m.c;
    b.textContent = m.emoji;
    b.dataset.idx = i;
    b.addEventListener('click', () => {
      if (melodyPlaying) return;
      flashBtn(b, i);
      melodyInput.push(i);
      const upTo = MELODY_SEQ.slice(0, melodyInput.length);
      if (melodyInput.join() !== upTo.join()) {
        melodyInput = [];
        card.querySelector('#melody-fb').textContent = 'Almost! The melody restarts… 💭';
        G.sfx.wrong();
      } else if (melodyInput.length === MELODY_SEQ.length) {
        markSolved('melody', card);
      } else {
        card.querySelector('#melody-fb').textContent = '♪'.repeat(melodyInput.length);
      }
    });
    row.appendChild(b);
  });
  card.querySelector('#melody-play').addEventListener('click', async () => {
    if (melodyPlaying) return;
    melodyPlaying = true;
    melodyInput = [];
    card.querySelector('#melody-fb').textContent = 'listen… 🎧';
    for (const idx of MELODY_SEQ) {
      const btn = row.children[idx];
      flashBtn(btn, idx);
      await new Promise((r) => setTimeout(r, 520));
    }
    card.querySelector('#melody-fb').textContent = 'your turn! 💫';
    melodyPlaying = false;
  });
  return card;
}

function flashBtn(btn, idx) {
  btn.classList.add('lit');
  G.playTone(MELODY_COLORS[idx].freq, 0.32);
  setTimeout(() => btn.classList.remove('lit'), 330);
}

// --- Mirror riddle (language) ------------------------------------------------
function panelMirror() {
  mirrorTries = 0;
  const card = puzzleCard('🪞 Magic Mirror — a riddle',
    `<p>The mirror fogs over and writes in glitter:</p>
     <p style="font-style:italic; margin-top:8px">“I have no wings, yet I flutter inside you<br/>
     whenever you're excited or in love.<br/>
     In the year 2000 I also lived in your hair.<br/>
     <b>What am I?”</b></p>
     <div class="esc-row">
       <input class="esc-input" id="mirror-input" placeholder="type your answer…" autocomplete="off" />
       <button class="ghost-btn" id="mirror-go">Answer</button>
     </div>
     <div class="esc-feedback" id="mirror-fb"></div>
     <div class="esc-hint" id="mirror-hint"></div>`);
  const check = () => {
    const v = card.querySelector('#mirror-input').value.trim().toLowerCase();
    if (/butterfl/.test(v)) {
      markSolved('mirror', card);
    } else {
      mirrorTries++;
      G.sfx.wrong();
      card.querySelector('#mirror-fb').textContent = 'The mirror giggles. Try again! 💭';
      if (mirrorTries >= 2) card.querySelector('#mirror-hint').textContent = 'hint: it comes in clips, and in tummies 🦋';
    }
  };
  card.querySelector('#mirror-go').addEventListener('click', check);
  card.querySelector('#mirror-input').addEventListener('keydown', (e) => { if (e.key === 'Enter') check(); });
  return card;
}

// --- Jewelry box logic puzzle -------------------------------------------------
function panelJewelry() {
  arrangement = [];
  const card = puzzleCard('💍 Jewelry Box — charm logic',
    `<p>Three charm slots wait in a row (left → right). The lid is engraved:</p>
     <p style="margin-top:6px">1️⃣ The <b>heart</b> refuses to sit beside the <b>moon</b>.<br/>
     2️⃣ The <b>star</b> sits immediately left of the <b>heart</b>.</p>
     <p style="margin-top:6px">Tap the charms in order, left to right:</p>
     <div class="esc-row" id="jewel-row"></div>
     <div class="esc-row" id="jewel-picked" style="min-height:40px; font-size:26px"></div>
     <div class="esc-feedback" id="jewel-fb"></div>
     <div class="esc-hint">logic training: test each rule before you commit 🧠</div>`);
  const CHARMS = ['💗', '⭐', '🌙'];
  const ANSWER = '🌙⭐💗'; // moon, star, heart — heart not beside moon ✓, star immediately left of heart ✓
  const row = card.querySelector('#jewel-row');
  CHARMS.forEach((ch) => {
    const b = document.createElement('button');
    b.className = 'arrange-btn';
    b.textContent = ch;
    b.addEventListener('click', () => {
      if (arrangement.includes(ch)) return;
      arrangement.push(ch);
      b.classList.add('selected');
      card.querySelector('#jewel-picked').textContent = arrangement.join(' → ');
      if (arrangement.length === 3) {
        if (arrangement.join('') === ANSWER) {
          markSolved('jewelry', card);
        } else {
          G.sfx.wrong();
          card.querySelector('#jewel-fb').textContent = 'The lid stays shut… re-read the rules! 💭';
          setTimeout(() => {
            arrangement = [];
            row.querySelectorAll('.arrange-btn').forEach((x) => x.classList.remove('selected'));
            card.querySelector('#jewel-picked').textContent = '';
          }, 900);
        }
      }
    });
    row.appendChild(b);
  });
  return card;
}

// --- Poster word puzzle -------------------------------------------------------
function panelPoster() {
  const card = puzzleCard('⭐ Star Poster — word magic',
    `<p>A faded boy-band poster hides glitter letters scribbled in gel pen:</p>
     <div class="esc-row" style="font-size:28px; letter-spacing:8px"><b>M A E R D</b></div>
     <p>Unscramble the magic word every princess falls asleep holding.</p>
     <div class="esc-row">
       <input class="esc-input" id="poster-input" placeholder="the magic word…" maxlength="12" autocomplete="off" />
       <button class="ghost-btn" id="poster-go">Cast it</button>
     </div>
     <div class="esc-feedback" id="poster-fb"></div>
     <div class="esc-hint">language training: your eyes see letters, your heart sees words 💫</div>`);
  const check = () => {
    const v = card.querySelector('#poster-input').value.trim().toLowerCase();
    if (v === 'dream' || v === 'dreams') {
      markSolved('poster', card);
    } else {
      G.sfx.wrong();
      card.querySelector('#poster-fb').textContent = 'The glitter fizzles… try another word! 💭';
    }
  };
  card.querySelector('#poster-go').addEventListener('click', check);
  card.querySelector('#poster-input').addEventListener('keydown', (e) => { if (e.key === 'Enter') check(); });
  return card;
}

// --- Door ---------------------------------------------------------------------
function panelDoor() {
  if (G.state.escape.escaped) return panelIntro(true);
  const card = puzzleCard('🔐 The Tower Door',
    `<p>Four dials shimmer, one per charm — in the order from the note:</p>
     <div class="esc-row" style="font-size:20px">🪞 💿 💍 ⭐</div>
     <div class="code-slots" id="code-slots"></div>
     <div class="esc-row"><button class="big-btn" id="door-go" style="padding:12px 30px; font-size:16px">Whisper the code 🗝️</button></div>
     <div class="esc-feedback" id="door-fb"></div>`);
  const slots = card.querySelector('#code-slots');
  for (let i = 0; i < 4; i++) {
    const inp = document.createElement('input');
    inp.className = 'code-slot';
    inp.maxLength = 1;
    inp.inputMode = 'numeric';
    inp.addEventListener('input', () => {
      inp.value = inp.value.replace(/\D/g, '');
      if (inp.value && slots.children[i + 1]) slots.children[i + 1].focus();
    });
    slots.appendChild(inp);
  }
  card.querySelector('#door-go').addEventListener('click', () => {
    const code = [...slots.children].map((x) => x.value).join('');
    const target = CODE_ORDER.map((id) => PUZZLES[id].digit).join('');
    if (code === target) {
      G.state.escape.escaped = true;
      G.state.unlocks.midnight = true;
      G.state.stars += 25;
      G.save();
      G.updateHUD();
      G.sfx.fanfare();
      G.confetti(120);
      renderScene();
      showPanel(puzzleCard('🎉 You escaped the Forgotten Tower!',
        `<p>The spell dissolves into fairy dust. On the pillow inside lies the
         <b>🌙 Midnight Tiara</b> — now yours in the Style Studio — plus <b>+25 ✨</b>!</p>
         <p style="margin-top:10px">Logic, memory and word magic: you have them all, ${G.state.name || 'dreamgirl'}. 💜</p>
         <div class="esc-row"><button class="big-btn" id="esc-done" style="padding:12px 30px; font-size:16px">Take a bow 👑</button></div>`));
      document.getElementById('esc-done')?.addEventListener('click', () => closeEscape());
      G.toast('🌙 Midnight Tiara unlocked! Find it in the Style Studio 👗');
    } else {
      G.sfx.wrong();
      card.querySelector('#door-fb').textContent = code.length < 4 ? 'The door waits for all four numbers…' : 'The lock hums a sad note. Wake more charms? 💭';
    }
  });
  return card;
}
