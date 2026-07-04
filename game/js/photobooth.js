// 📸 Sparkle Photobooth — take selfies (camera), pick gallery photos, or snap
// your character; compose a 2/3/4-photo strip in a themed frame sized for
// Instagram stories (1080x1920) and download/share it.

let G = null;

const OUT_W = 1080, OUT_H = 1920;

const FRAME_THEMES = [
  {
    id: 'y2k', label: 'Y2K Chrome', emoji: '💿',
    caption: '#fff',
    draw: drawY2K,
  },
  {
    id: 'doll', label: 'Dollhouse Pink', emoji: '🎀',
    caption: '#8e2b60',
    draw: drawDoll,
  },
  {
    id: 'story', label: 'Storybook Night', emoji: '🏰',
    caption: '#ffe9fa',
    draw: drawStory,
  },
];

const booth = {
  step: 'source',       // source | capture | decorate
  source: null,         // camera | gallery | game
  count: 3,
  photos: [],           // ImageBitmap/HTMLImageElement per slot
  theme: 'doll',
  caption: '',
  stream: null,
  captureBusy: false,
};

export function initPhotobooth(game) {
  G = game;
  document.getElementById('booth-close').addEventListener('click', closeBooth);
}

export function openBooth() {
  G.state.uiOpen = true;
  document.getElementById('booth').classList.remove('hidden');
  booth.step = 'source';
  booth.photos = [];
  booth.source = null;
  booth.caption = '';
  G.sfx.open();
  render();
}

function closeBooth() {
  stopCamera();
  G.setPoseMode(false);
  document.getElementById('booth').classList.add('hidden');
  G.state.uiOpen = false;
  G.clearNear();
}

function stopCamera() {
  if (booth.stream) {
    booth.stream.getTracks().forEach((t) => t.stop());
    booth.stream = null;
  }
}

function el(html) {
  const d = document.createElement('div');
  d.innerHTML = html;
  return d;
}

function render() {
  const root = document.getElementById('booth-steps');
  root.innerHTML = '';
  if (booth.step === 'source') root.appendChild(renderSource());
  else if (booth.step === 'capture') root.appendChild(renderCapture());
  else root.appendChild(renderDecorate());
}

// ---------------------------------------------------------------------------
// Step 1: choose source + photo count
// ---------------------------------------------------------------------------
function renderSource() {
  const d = el(`
    <div class="booth-step active">
      <p style="font-weight:700; margin-top:6px">Who's in the pictures today, ${G.state.name || 'gorgeous'}?</p>
      <div class="booth-choices" id="src-row">
        <button class="booth-choice" data-src="camera"><span class="big">🤳</span>Real you<span class="sub">uses your camera — we'll ask permission</span></button>
        <button class="booth-choice" data-src="gallery"><span class="big">🖼️</span>My gallery<span class="sub">pick photos from your device</span></button>
        <button class="booth-choice" data-src="game"><span class="big">🎀</span>My character<span class="sub">snap her right here in the kingdom</span></button>
      </div>
      <p style="font-weight:700">How many photos on the strip?</p>
      <div class="booth-choices" id="count-row">
        <button class="booth-choice" data-count="2"><span class="big">✌️</span>2 photos</button>
        <button class="booth-choice selected" data-count="3"><span class="big">🎀</span>3 photos</button>
        <button class="booth-choice" data-count="4"><span class="big">🍀</span>4 photos</button>
      </div>
      <button class="big-btn" id="src-go" disabled>Let's shoot ✨</button>
      <div id="booth-note">📷 Camera photos never leave your device — everything is composed right in your browser.</div>
    </div>`);
  d.querySelectorAll('#src-row .booth-choice').forEach((b) => {
    b.addEventListener('click', () => {
      booth.source = b.dataset.src;
      d.querySelectorAll('#src-row .booth-choice').forEach((x) => x.classList.toggle('selected', x === b));
      d.querySelector('#src-go').disabled = false;
      G.sfx.click();
    });
  });
  d.querySelectorAll('#count-row .booth-choice').forEach((b) => {
    b.addEventListener('click', () => {
      booth.count = +b.dataset.count;
      d.querySelectorAll('#count-row .booth-choice').forEach((x) => x.classList.toggle('selected', x === b));
      G.sfx.click();
    });
  });
  d.querySelector('#src-go').addEventListener('click', () => {
    booth.photos = new Array(booth.count).fill(null);
    booth.step = 'capture';
    render();
  });
  return d;
}

// ---------------------------------------------------------------------------
// Step 2: capture / select photos
// ---------------------------------------------------------------------------
function renderCapture() {
  const isCam = booth.source === 'camera';
  const isGallery = booth.source === 'gallery';
  const d = el(`
    <div class="booth-step active">
      ${isCam ? `
        <div id="booth-video-wrap">
          <video id="booth-video" autoplay playsinline muted></video>
          <div id="booth-countdown"></div>
          <div id="booth-flash"></div>
        </div>
        <div id="cam-gate" style="display:none; padding:18px">
          <p style="font-weight:700; line-height:1.5">To take real selfies, your browser will ask for camera access. Nothing is uploaded — pinky promise. 🤙</p>
          <button class="big-btn" id="cam-allow" style="margin-top:12px; padding:12px 28px; font-size:16px">Enable my camera 📷</button>
          <div class="esc-feedback" id="cam-fb"></div>
          <button class="ghost-btn" id="cam-fallback" style="margin-top:10px">Use my gallery instead 🖼️</button>
        </div>` : ''}
      ${booth.source === 'game' ? `
        <p style="font-weight:700; margin-top:8px">She'll pose for you! Use the arrows to circle around her, then snap. 🎀</p>
        <div class="booth-caption-row" style="margin:10px 0">
          <button class="ghost-btn" data-cam="left">⟲ orbit</button>
          <button class="ghost-btn" data-cam="out">− zoom</button>
          <button class="ghost-btn" data-cam="in">+ zoom</button>
          <button class="ghost-btn" data-cam="right">orbit ⟳</button>
        </div>` : ''}
      ${isGallery ? `<p style="font-weight:700; margin-top:8px">Tap each slot to pick a photo from your device 🖼️</p>` : ''}
      <div id="booth-slots"></div>
      <div class="booth-caption-row">
        ${isCam ? '<button class="big-btn" id="cam-snap" style="padding:12px 30px; font-size:16px">Snap 📸</button>' : ''}
        ${booth.source === 'game' ? '<button class="big-btn" id="game-snap" style="padding:12px 30px; font-size:16px">Snap her 📸</button>' : ''}
        <button class="ghost-btn" id="cap-back">← Back</button>
        <button class="big-btn" id="cap-next" style="padding:12px 30px; font-size:16px" disabled>Decorate →</button>
      </div>
      <input type="file" id="booth-file" accept="image/*" style="display:none" />
    </div>`);

  const slotsEl = d.querySelector('#booth-slots');
  let activeSlot = 0;

  function refreshSlots() {
    slotsEl.innerHTML = '';
    booth.photos.forEach((p, i) => {
      const s = document.createElement('div');
      s.className = 'booth-slot' + (p ? ' filled' : '');
      if (i === activeSlot && !p) s.style.outline = '3px solid var(--hotpink)';
      if (p) {
        const img = document.createElement('img');
        img.src = p.previewUrl;
        s.appendChild(img);
        const redo = document.createElement('div');
        redo.className = 'redo';
        redo.textContent = '🔄';
        s.appendChild(redo);
      } else {
        s.textContent = ['💖', '💿', '🦋', '⭐'][i];
        s.style.display = 'grid';
        s.style.placeItems = 'center';
        s.style.fontSize = '22px';
      }
      s.addEventListener('click', () => {
        activeSlot = i;
        if (isGallery || (p && isGallery)) pickFile();
        else if (p) { booth.photos[i] = null; refreshSlots(); } // retake
        refreshSlots();
      });
      slotsEl.appendChild(s);
    });
    d.querySelector('#cap-next').disabled = booth.photos.some((p) => !p);
  }

  function nextEmpty() {
    const i = booth.photos.findIndex((p) => !p);
    activeSlot = i === -1 ? 0 : i;
  }

  function setPhoto(img) {
    booth.photos[activeSlot] = img;
    nextEmpty();
    refreshSlots();
    G.sfx.collect();
  }

  // gallery picking
  const fileInput = d.querySelector('#booth-file');
  function pickFile() { fileInput.click(); }
  fileInput.addEventListener('change', () => {
    const f = fileInput.files && fileInput.files[0];
    fileInput.value = '';
    if (!f) return;
    const url = URL.createObjectURL(f);
    const img = new Image();
    img.onload = () => setPhoto({ img, previewUrl: url });
    img.src = url;
  });
  if (isGallery) {
    slotsEl.addEventListener('click', () => {}); // slots handle their own clicks
  }

  // camera flow
  if (isCam) {
    const video = d.querySelector('#booth-video');
    const gate = d.querySelector('#cam-gate');
    const wrap = d.querySelector('#booth-video-wrap');
    const startCam = async () => {
      try {
        booth.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 1280 } }, audio: false });
        video.srcObject = booth.stream;
        gate.style.display = 'none';
        wrap.style.display = 'block';
        d.querySelector('#cam-snap').style.display = '';
      } catch (err) {
        gate.style.display = 'block';
        wrap.style.display = 'none';
        d.querySelector('#cam-fb').textContent =
          err && (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError')
            ? 'Camera was blocked — you can allow it in your browser settings, or use your gallery. 💗'
            : 'No camera found — gallery works just as well! 💗';
      }
    };
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      // show the explicit consent gate first — the browser prompt appears on click
      gate.style.display = 'block';
      wrap.style.display = 'none';
      d.querySelector('#cam-snap').style.display = 'none';
      d.querySelector('#cam-allow').addEventListener('click', startCam);
    } else {
      gate.style.display = 'block';
      d.querySelector('#cam-allow').style.display = 'none';
      d.querySelector('#cam-fb').textContent = 'This browser has no camera support — use the gallery! 💗';
    }
    d.querySelector('#cam-fallback').addEventListener('click', () => {
      stopCamera();
      booth.source = 'gallery';
      render();
    });
    d.querySelector('#cam-snap').addEventListener('click', async () => {
      if (booth.captureBusy || !booth.stream) return;
      booth.captureBusy = true;
      const cd = d.querySelector('#booth-countdown');
      for (const n of ['3', '2', '1']) {
        cd.textContent = n;
        G.playTone(660, 0.12);
        await new Promise((r) => setTimeout(r, 650));
      }
      cd.textContent = '';
      G.playTone(1046, 0.25);
      const flash = d.querySelector('#booth-flash');
      flash.style.opacity = '0.9';
      setTimeout(() => (flash.style.opacity = '0'), 130);
      const c = document.createElement('canvas');
      c.width = video.videoWidth || 1280;
      c.height = video.videoHeight || 720;
      const ctx = c.getContext('2d');
      ctx.translate(c.width, 0); ctx.scale(-1, 1); // mirror = selfie feel
      ctx.drawImage(video, 0, 0);
      const img = new Image();
      img.onload = () => { setPhoto({ img, previewUrl: c.toDataURL('image/jpeg', 0.9) }); booth.captureBusy = false; };
      img.src = c.toDataURL('image/jpeg', 0.92);
    });
  }

  // in-game snap: she strikes a pose facing the camera
  if (booth.source === 'game') {
    G.setPoseMode(true);
    d.querySelector('#game-snap').addEventListener('click', () => {
      const url = G.snapGameFrame();
      const img = new Image();
      img.onload = () => setPhoto({ img, previewUrl: url });
      img.src = url;
    });
    d.querySelectorAll('[data-cam]').forEach((b) => {
      b.addEventListener('click', () => {
        const k = b.dataset.cam;
        if (k === 'left') G.nudgeCamera(-0.45, 0);
        if (k === 'right') G.nudgeCamera(0.45, 0);
        if (k === 'in') G.nudgeCamera(0, -1);
        if (k === 'out') G.nudgeCamera(0, 1);
        G.sfx.click();
      });
    });
  }

  d.querySelector('#cap-back').addEventListener('click', () => { stopCamera(); G.setPoseMode(false); booth.step = 'source'; render(); });
  d.querySelector('#cap-next').addEventListener('click', () => { stopCamera(); G.setPoseMode(false); booth.step = 'decorate'; render(); });

  nextEmpty();
  refreshSlots();
  return d;
}

// ---------------------------------------------------------------------------
// Step 3: decorate + preview + export
// ---------------------------------------------------------------------------
function renderDecorate() {
  const d = el(`
    <div class="booth-step active">
      <div class="booth-choices" id="theme-row" style="margin:10px 0">
        ${FRAME_THEMES.map((t) => `<button class="booth-choice${t.id === booth.theme ? ' selected' : ''}" data-theme="${t.id}" style="width:120px; padding:12px 8px"><span class="big">${t.emoji}</span>${t.label}</button>`).join('')}
      </div>
      <div class="booth-caption-row">
        <input class="esc-input" id="booth-caption" maxlength="34" placeholder="write a cute caption… (optional)" value="${booth.caption.replace(/"/g, '&quot;')}" style="width:min(340px,100%)" />
      </div>
      <div id="booth-preview-wrap"><canvas id="booth-preview" width="${OUT_W}" height="${OUT_H}"></canvas></div>
      <div class="booth-caption-row">
        <button class="ghost-btn" id="dec-back">← Photos</button>
        <button class="big-btn" id="booth-download" style="padding:12px 26px; font-size:16px">Print it 💾</button>
        <button class="ghost-btn" id="booth-share" style="display:none">Share 📤</button>
      </div>
      <div id="booth-note">1080 × 1920 — exactly Instagram-story sized. Post it &amp; tag your besties! 💕</div>
    </div>`);

  const canvas = d.querySelector('#booth-preview');
  const repaint = () => composeStrip(canvas);
  repaint();

  d.querySelectorAll('#theme-row .booth-choice').forEach((b) => {
    b.addEventListener('click', () => {
      booth.theme = b.dataset.theme;
      d.querySelectorAll('#theme-row .booth-choice').forEach((x) => x.classList.toggle('selected', x === b));
      G.sfx.click();
      repaint();
    });
  });
  let capTimer;
  d.querySelector('#booth-caption').addEventListener('input', (e) => {
    booth.caption = e.target.value;
    clearTimeout(capTimer);
    capTimer = setTimeout(repaint, 250);
  });
  d.querySelector('#dec-back').addEventListener('click', () => { booth.step = 'capture'; render(); });

  d.querySelector('#booth-download').addEventListener('click', () => {
    const a = document.createElement('a');
    a.download = `dreamhouse-photobooth-${Date.now()}.png`;
    a.href = canvas.toDataURL('image/png');
    a.click();
    G.sfx.fanfare();
    G.confetti(50);
    G.toast('Printed! Check your downloads 💖 Story-ready at 1080×1920');
  });

  // native share when supported (mobile)
  const shareBtn = d.querySelector('#booth-share');
  if (navigator.canShare) {
    shareBtn.style.display = '';
    shareBtn.addEventListener('click', async () => {
      try {
        const blob = await new Promise((r) => canvas.toBlob(r, 'image/png'));
        const file = new File([blob], 'dreamhouse-story.png', { type: 'image/png' });
        if (navigator.canShare({ files: [file] })) {
          await navigator.share({ files: [file], title: 'Dreamhouse Kingdom 💖' });
        } else {
          G.toast('Sharing files is not supported here — use Print instead 💾');
        }
      } catch (e) { /* user cancelled — fine */ }
    });
  }
  return d;
}

// ---------------------------------------------------------------------------
// Canvas composition (1080x1920)
// ---------------------------------------------------------------------------
function composeStrip(canvas) {
  const ctx = canvas.getContext('2d');
  const theme = FRAME_THEMES.find((t) => t.id === booth.theme) || FRAME_THEMES[0];
  theme.draw(ctx);

  // photo strip layout
  const n = booth.photos.length;
  const topPad = 250, bottomPad = 300, gap = 44;
  const availH = OUT_H - topPad - bottomPad;
  const slotH = Math.min(560, (availH - gap * (n - 1)) / n);
  const slotW = 780;
  const x = (OUT_W - slotW) / 2;
  const totalH = slotH * n + gap * (n - 1);
  let y = topPad + (availH - totalH) / 2;

  booth.photos.forEach((p, i) => {
    // polaroid card
    ctx.save();
    const tilt = (i % 2 === 0 ? -1 : 1) * 0.012;
    ctx.translate(x + slotW / 2, y + slotH / 2);
    ctx.rotate(tilt);
    ctx.shadowColor = 'rgba(40,10,40,.35)';
    ctx.shadowBlur = 30;
    ctx.shadowOffsetY = 12;
    ctx.fillStyle = '#fff';
    roundRect(ctx, -slotW / 2 - 16, -slotH / 2 - 16, slotW + 32, slotH + 32, 22);
    ctx.fill();
    ctx.shadowColor = 'transparent';
    // cover-cropped photo
    if (p && p.img) {
      ctx.beginPath();
      roundRect(ctx, -slotW / 2, -slotH / 2, slotW, slotH, 12);
      ctx.clip();
      const iw = p.img.naturalWidth || p.img.width, ih = p.img.naturalHeight || p.img.height;
      const scale = Math.max(slotW / iw, slotH / ih);
      const dw = iw * scale, dh = ih * scale;
      ctx.drawImage(p.img, -dw / 2, -dh / 2, dw, dh);
    }
    ctx.restore();
    y += slotH + gap;
  });

  // header + caption + brand
  ctx.textAlign = 'center';
  ctx.fillStyle = theme.caption;
  ctx.font = '800 64px "Trebuchet MS", sans-serif';
  ctx.fillText('✨ dreamhouse kingdom ✨', OUT_W / 2, 150);
  if (booth.caption.trim()) {
    ctx.font = 'italic 700 58px "Brush Script MT", "Trebuchet MS", cursive';
    ctx.fillText(booth.caption.trim(), OUT_W / 2, OUT_H - 170);
  }
  ctx.font = '700 36px "Trebuchet MS", sans-serif';
  ctx.globalAlpha = 0.85;
  const date = new Date();
  ctx.fillText(`${String(date.getDate()).padStart(2, '0')}.${String(date.getMonth() + 1).padStart(2, '0')}.${date.getFullYear()} 💖`, OUT_W / 2, OUT_H - 90);
  ctx.globalAlpha = 1;
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.roundRect(x, y, w, h, r);
}

function sprinkle(ctx, emojis, count, seed) {
  // deterministic sprinkle so the frame doesn't shuffle on each repaint
  let s = seed;
  const rand = () => { s = (s * 16807) % 2147483647; return s / 2147483647; };
  for (let i = 0; i < count; i++) {
    const e = emojis[i % emojis.length];
    const x = 40 + rand() * (OUT_W - 80);
    const yTop = rand() < 0.5;
    const y = yTop ? 60 + rand() * 190 : OUT_H - 60 - rand() * 210;
    const size = 44 + rand() * 60;
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate((rand() - 0.5) * 0.9);
    ctx.font = `${size}px serif`;
    ctx.textAlign = 'center';
    ctx.globalAlpha = 0.9;
    ctx.fillText(e, 0, 0);
    ctx.restore();
  }
  // side sparkles
  for (let i = 0; i < 26; i++) {
    const x = rand() < 0.5 ? 20 + rand() * 90 : OUT_W - 20 - rand() * 90;
    const y = 200 + rand() * (OUT_H - 400);
    ctx.save();
    ctx.font = `${20 + rand() * 30}px serif`;
    ctx.globalAlpha = 0.75;
    ctx.fillText('✦', x, y);
    ctx.restore();
  }
  ctx.globalAlpha = 1;
}

function drawY2K(ctx) {
  const g = ctx.createLinearGradient(0, 0, OUT_W, OUT_H);
  g.addColorStop(0, '#c5c8dd'); g.addColorStop(0.25, '#f4f5ff');
  g.addColorStop(0.5, '#b8bad1'); g.addColorStop(0.75, '#e8e9f3'); g.addColorStop(1, '#a9acd0');
  ctx.fillStyle = g; ctx.fillRect(0, 0, OUT_W, OUT_H);
  // hot pink border frame
  ctx.strokeStyle = '#ff2d95'; ctx.lineWidth = 22;
  roundRect(ctx, 26, 26, OUT_W - 52, OUT_H - 52, 48); ctx.stroke();
  ctx.strokeStyle = 'rgba(255,255,255,.9)'; ctx.lineWidth = 6;
  roundRect(ctx, 48, 48, OUT_W - 96, OUT_H - 96, 36); ctx.stroke();
  ctx.fillStyle = '#ff2d95';
  sprinkle(ctx, ['🦋', '💿', '⭐', '💾', '✨'], 12, 20011231);
}

function drawDoll(ctx) {
  const g = ctx.createLinearGradient(0, 0, 0, OUT_H);
  g.addColorStop(0, '#ff8fc4'); g.addColorStop(0.5, '#ffd9ec'); g.addColorStop(1, '#ff6fb3');
  ctx.fillStyle = g; ctx.fillRect(0, 0, OUT_W, OUT_H);
  // polka dots
  ctx.fillStyle = 'rgba(255,255,255,.5)';
  for (let yy = 60; yy < OUT_H; yy += 120) {
    for (let xx = 60 + ((yy / 120) % 2) * 60; xx < OUT_W; xx += 120) {
      ctx.beginPath(); ctx.arc(xx, yy, 13, 0, Math.PI * 2); ctx.fill();
    }
  }
  ctx.strokeStyle = '#fff'; ctx.lineWidth = 18;
  roundRect(ctx, 24, 24, OUT_W - 48, OUT_H - 48, 52); ctx.stroke();
  ctx.fillStyle = '#8e2b60';
  sprinkle(ctx, ['🎀', '💖', '👛', '💄', '🌸'], 12, 19590309);
}

function drawStory(ctx) {
  const g = ctx.createLinearGradient(0, 0, 0, OUT_H);
  g.addColorStop(0, '#1c1440'); g.addColorStop(0.55, '#41306e'); g.addColorStop(1, '#6b4a8f');
  ctx.fillStyle = g; ctx.fillRect(0, 0, OUT_W, OUT_H);
  // stars
  let s = 19371221;
  const rand = () => { s = (s * 16807) % 2147483647; return s / 2147483647; };
  ctx.fillStyle = '#fff3c9';
  for (let i = 0; i < 90; i++) {
    const x = rand() * OUT_W, y = rand() * OUT_H, r = 1 + rand() * 3;
    ctx.globalAlpha = 0.4 + rand() * 0.6;
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
  }
  ctx.globalAlpha = 1;
  ctx.strokeStyle = '#ffd166'; ctx.lineWidth = 14;
  roundRect(ctx, 26, 26, OUT_W - 52, OUT_H - 52, 48); ctx.stroke();
  ctx.fillStyle = '#ffe9fa';
  sprinkle(ctx, ['🏰', '🌙', '⭐', '🕯️', '🫧'], 10, 17761204);
}
