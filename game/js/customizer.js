// 👗 Style Studio — dress-up, hair & makeup for the player character.
// Renders swatch UI into #styler and applies changes live via G.applyLook().

export const LOOK_OPTIONS = {
  skinTones: ['#ffe3d0', '#f5c9a5', '#d9995f', '#a96c3f', '#7a4a2b'],
  dressColors: ['#ff2d95', '#ff8fc4', '#a98bf5', '#4fc3f7', '#3ecf8e', '#ffd166', '#ff9f70', '#f4f5ff', '#40284e'],
  dressStyles: [
    { id: 'aline', label: 'A-line dress', emoji: '👗' },
    { id: 'ballgown', label: 'Princess ballgown', emoji: '👑' },
    { id: 'mini', label: 'Y2K mini skirt', emoji: '🦋' },
  ],
  hairStyles: [
    { id: 'buns', label: 'Space buns', emoji: '🐻' },
    { id: 'ponytail', label: 'High ponytail', emoji: '🎀' },
    { id: 'long', label: 'Long waves', emoji: '💃' },
    { id: 'bob', label: 'Sweet bob', emoji: '💇‍♀️' },
  ],
  hairColors: ['#f7cf8e', '#55352b', '#2e2331', '#b03a2e', '#ff8fc4', '#a98bf5', '#e8e9f3'],
  accessories: [
    { id: 'none', label: 'Nothing', emoji: '🚫' },
    { id: 'bow', label: 'Sweet bow', emoji: '🎀' },
    { id: 'tiara', label: 'Gold tiara', emoji: '👸' },
    { id: 'butterfly', label: 'Butterfly clips', emoji: '🦋' },
    { id: 'headband', label: 'Headband', emoji: '🥰' },
    { id: 'midnight', label: 'Midnight Tiara', emoji: '🌙', locked: true },
  ],
  lipsticks: ['none', '#e75480', '#c9184a', '#ff7059', '#8e3b63'],
  eyeshadows: ['none', '#ffb3d0', '#9fd8ff', '#e6c15a', '#c9b3ff'],
  blushLevels: [
    { id: 0, label: 'No blush', emoji: '·' },
    { id: 1, label: 'Soft glow', emoji: '🌸' },
    { id: 2, label: 'Full doll', emoji: '💗' },
  ],
};

export const DEFAULT_LOOK = {
  skin: '#ffe3d0',
  dressStyle: 'aline',
  dressColor: '#ff2d95',
  hairStyle: 'buns',
  hairColor: '#f7cf8e',
  accessory: 'bow',
  lipstick: 'none',
  eyeshadow: 'none',
  blush: 1,
};

// starter vibes on the title screen map to quick looks
export const VIBE_PRESETS = {
  pink:  { dressColor: '#ff2d95', hairColor: '#f7cf8e', accessory: 'bow' },
  lilac: { dressColor: '#a98bf5', hairColor: '#55352b', accessory: 'butterfly' },
  blue:  { dressColor: '#4fc3f7', hairColor: '#2e2331', accessory: 'headband' },
  peach: { dressColor: '#ff9f70', hairColor: '#b03a2e', accessory: 'bow' },
};

const TABS = [
  { id: 'outfit', label: '👗 Outfit' },
  { id: 'hair', label: '💁‍♀️ Hair' },
  { id: 'makeup', label: '💄 Makeup' },
  { id: 'extras', label: '👑 Extras' },
];

let G = null;
let activeTab = 'outfit';

export function initCustomizer(game) {
  G = game;
  const tabsEl = document.getElementById('styler-tabs');
  TABS.forEach((t) => {
    const b = document.createElement('button');
    b.className = 'styler-tab' + (t.id === activeTab ? ' active' : '');
    b.textContent = t.label;
    b.dataset.tab = t.id;
    b.addEventListener('click', () => {
      activeTab = t.id;
      tabsEl.querySelectorAll('.styler-tab').forEach((x) => x.classList.toggle('active', x.dataset.tab === t.id));
      renderBody();
    });
    tabsEl.appendChild(b);
  });

  document.getElementById('btn-styler').addEventListener('click', () => toggleStyler());
  document.getElementById('styler-close').addEventListener('click', () => toggleStyler(false));
  document.getElementById('styler-done').addEventListener('click', () => toggleStyler(false));
}

export function toggleStyler(force) {
  const el = document.getElementById('styler');
  const show = force !== undefined ? force : el.classList.contains('hidden');
  if (show && !G.state.started) return;
  el.classList.toggle('hidden', !show);
  G.state.uiOpen = show;
  G.setPoseMode(show); // camera swings to face the character
  if (show) {
    renderBody();
    G.sfx.open();
  }
}

function section(title) {
  const d = document.createElement('div');
  d.className = 'styler-section';
  const h = document.createElement('h3');
  h.textContent = title;
  d.appendChild(h);
  return d;
}

function swatchRow(colors, current, onPick, { allowNone = false } = {}) {
  const row = document.createElement('div');
  row.className = 'swatches';
  colors.forEach((c) => {
    const s = document.createElement('button');
    s.className = 'swatch' + (c === current ? ' selected' : '') + (c === 'none' ? ' none-swatch' : '');
    if (c !== 'none') s.style.background = c;
    s.title = c === 'none' ? 'None' : c;
    s.addEventListener('click', () => { onPick(c); renderBody(); G.sfx.click(); });
    row.appendChild(s);
  });
  return row;
}

function cardRow(options, currentId, onPick) {
  const row = document.createElement('div');
  row.className = 'option-cards';
  options.forEach((o) => {
    const locked = o.locked && !G.state.unlocks.midnight;
    const b = document.createElement('button');
    b.className = 'option-card' + (o.id === currentId ? ' selected' : '') + (locked ? ' locked' : '');
    b.innerHTML = `<span>${o.emoji}</span><span>${o.label}</span>` + (locked ? '<span class="lock">🔒 escape the tower</span>' : '');
    b.addEventListener('click', () => {
      if (locked) { G.toast('Escape the Forgotten Tower to unlock this! 🏰'); return; }
      onPick(o.id); renderBody(); G.sfx.click();
    });
    row.appendChild(b);
  });
  return row;
}

function renderBody() {
  const body = document.getElementById('styler-body');
  const look = G.state.look;
  body.innerHTML = '';
  const set = (patch) => {
    Object.assign(look, patch);
    G.applyLook();
    G.save();
  };

  if (activeTab === 'outfit') {
    let s = section('Dress style');
    s.appendChild(cardRow(LOOK_OPTIONS.dressStyles, look.dressStyle, (id) => set({ dressStyle: id })));
    body.appendChild(s);
    s = section('Dress color');
    s.appendChild(swatchRow(LOOK_OPTIONS.dressColors, look.dressColor, (c) => set({ dressColor: c })));
    body.appendChild(s);
  } else if (activeTab === 'hair') {
    let s = section('Hair style');
    s.appendChild(cardRow(LOOK_OPTIONS.hairStyles, look.hairStyle, (id) => set({ hairStyle: id })));
    body.appendChild(s);
    s = section('Hair color');
    s.appendChild(swatchRow(LOOK_OPTIONS.hairColors, look.hairColor, (c) => set({ hairColor: c })));
    body.appendChild(s);
  } else if (activeTab === 'makeup') {
    let s = section('Skin tone');
    s.appendChild(swatchRow(LOOK_OPTIONS.skinTones, look.skin, (c) => set({ skin: c })));
    body.appendChild(s);
    s = section('Lipstick');
    s.appendChild(swatchRow(LOOK_OPTIONS.lipsticks, look.lipstick, (c) => set({ lipstick: c })));
    body.appendChild(s);
    s = section('Eyeshadow');
    s.appendChild(swatchRow(LOOK_OPTIONS.eyeshadows, look.eyeshadow, (c) => set({ eyeshadow: c })));
    body.appendChild(s);
    s = section('Blush');
    s.appendChild(cardRow(LOOK_OPTIONS.blushLevels, look.blush, (id) => set({ blush: id })));
    body.appendChild(s);
  } else if (activeTab === 'extras') {
    const s = section('Hair accessory');
    s.appendChild(cardRow(LOOK_OPTIONS.accessories, look.accessory, (id) => set({ accessory: id })));
    body.appendChild(s);
    const note = document.createElement('p');
    note.style.cssText = 'font-size:13px; font-weight:700; opacity:.65; margin-top:14px; line-height:1.5';
    note.textContent = G.state.crowned
      ? 'Your Queen’s crown sits proudly above any accessory. 👑'
      : 'Answer all the kingdom’s trivia to earn the Queen’s crown! 👑';
    body.appendChild(note);
  }
}
