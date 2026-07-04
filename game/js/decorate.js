// 🪄 Decorate mode — personal world building. Spend sparkles to place
// treasures anywhere on the island; click placed ones to return them.
// Everything persists in the save.

import * as THREE from '../lib/three.module.min.js';

let G = null;
let active = false;
let selectedType = null;
let ghost = null;
let ghostValid = false;
const placedGroups = []; // parallel to G.state.decorations
const raycaster = new THREE.Raycaster();
const pointerNdc = new THREE.Vector2();

export const DECOR_ITEMS = [
  { id: 'blossom', label: 'Blossom tree', emoji: '🌸', cost: 15, collider: 0.75 },
  { id: 'gumdrop', label: 'Mint tree', emoji: '🌳', cost: 12, collider: 0.75 },
  { id: 'flowers', label: 'Flower patch', emoji: '🌷', cost: 8, collider: 0 },
  { id: 'heart', label: 'Heart statue', emoji: '💗', cost: 25, collider: 0.8 },
  { id: 'disco', label: 'Disco ball', emoji: '🪩', cost: 30, collider: 0.6 },
  { id: 'lamp', label: 'Star lamp', emoji: '⭐', cost: 18, collider: 0.4 },
  { id: 'flamingo', label: 'Flamingo', emoji: '🦩', cost: 20, collider: 0.4 },
  { id: 'picnic', label: 'Picnic rug', emoji: '🧺', cost: 10, collider: 0 },
];

export function initDecorate(game) {
  G = game;
  document.getElementById('btn-decor').addEventListener('click', () => toggleDecorate());
  renderBar();

  // rebuild saved decorations
  G.state.decorations.forEach((dec, i) => addDecorMesh(dec, i));

  const canvas = G.renderer.domElement;
  canvas.addEventListener('pointermove', (e) => {
    if (!active || !selectedType) return;
    moveGhost(e);
  });
  canvas.addEventListener('pointerdown', (e) => {
    if (!active || G.state.uiOpen) return;
    // delete: clicking an existing decoration (when no item selected)
    updatePointer(e);
    raycaster.setFromCamera(pointerNdc, G.camera);
    if (!selectedType) {
      const hits = raycaster.intersectObjects(placedGroups.filter(Boolean), true);
      if (hits.length) {
        let g = hits[0].object;
        while (g.parent && g.userData.decorIdx === undefined) g = g.parent;
        if (g.userData.decorIdx !== undefined) removeDecor(g.userData.decorIdx);
      }
      return;
    }
    moveGhost(e); // make sure the ghost matches this exact click point (touch taps skip pointermove)
    if (ghost && ghostValid) placeAtGhost();
    else if (ghost) G.toast('Can\'t place it there — find an open spot! 💭');
  });
  // debug/testing visibility
  window.__decor = {
    get active() { return active; },
    get selectedType() { return selectedType; },
    get ghostValid() { return ghostValid; },
    get ghostPos() { return ghost ? { x: ghost.position.x, z: ghost.position.z } : null; },
  };
}

function renderBar() {
  const bar = document.getElementById('decor-items');
  bar.innerHTML = '';
  DECOR_ITEMS.forEach((item) => {
    const b = document.createElement('button');
    b.className = 'decor-item' + (selectedType === item.id ? ' selected' : '');
    b.disabled = G.state.stars < item.cost && selectedType !== item.id;
    b.innerHTML = `<span class="big">${item.emoji}</span><span>${item.label}</span><span>✨${item.cost}</span>`;
    b.addEventListener('click', () => {
      selectedType = selectedType === item.id ? null : item.id;
      removeGhost();
      if (selectedType) makeGhost(item.id);
      renderBar();
      G.sfx.click();
    });
    bar.appendChild(b);
  });
  document.getElementById('decor-hint').textContent = selectedType
    ? 'click the ground to place it 🪄 · pick it again to cancel'
    : `you have ✨${G.state.stars} · pick a treasure, or click a placed one to return it (full refund)`;
}

export function toggleDecorate(force) {
  active = force !== undefined ? force : !active;
  if (!G.state.started) active = false;
  document.getElementById('decor-bar').classList.toggle('show', active);
  document.getElementById('btn-decor').classList.toggle('active', active);
  if (!active) {
    selectedType = null;
    removeGhost();
  } else {
    renderBar();
    G.toast('🪄 Decorate mode — build your dream kingdom!');
  }
  return active;
}

export function isDecorating() { return active; }

function updatePointer(e) {
  const r = G.renderer.domElement.getBoundingClientRect();
  pointerNdc.x = ((e.clientX - r.left) / r.width) * 2 - 1;
  pointerNdc.y = -((e.clientY - r.top) / r.height) * 2 + 1;
}

function groundPoint(e) {
  updatePointer(e);
  raycaster.setFromCamera(pointerNdc, G.camera);
  const hit = raycaster.intersectObject(G.ground, false);
  return hit.length ? hit[0].point : null;
}

function makeGhost(type) {
  ghost = buildDecor(type);
  ghost.traverse((o) => {
    if (o.isMesh) {
      o.material = o.material.clone();
      o.material.transparent = true;
      o.material.opacity = 0.55;
      o.castShadow = false;
    }
  });
  ghost.visible = false;
  G.scene.add(ghost);
}

function removeGhost() {
  if (ghost) {
    G.scene.remove(ghost);
    ghost = null;
  }
}

function moveGhost(e) {
  const p = groundPoint(e);
  if (!p) { if (ghost) ghost.visible = false; return; }
  ghost.visible = true;
  ghost.position.set(p.x, 0, p.z);
  const item = DECOR_ITEMS.find((i) => i.id === selectedType);
  const r = Math.hypot(p.x, p.z);
  ghostValid =
    r < 57 &&
    Math.hypot(p.x - G.player.position.x, p.z - G.player.position.z) > 1.2 &&
    !G.colliders.some((c) => Math.hypot(p.x - c.x, p.z - c.z) < c.r + (item.collider || 0.5) + 0.3);
  ghost.traverse((o) => {
    if (o.isMesh) o.material.color && o.material.emissive?.set(ghostValid ? 0x114411 : 0x661122);
  });
}

function placeAtGhost() {
  const item = DECOR_ITEMS.find((i) => i.id === selectedType);
  if (G.state.stars < item.cost) {
    G.toast(`Need ✨${item.cost} — collect more stars!`);
    return;
  }
  G.state.stars -= item.cost;
  const dec = { type: selectedType, x: +ghost.position.x.toFixed(2), z: +ghost.position.z.toFixed(2), ry: +(Math.random() * Math.PI * 2).toFixed(2) };
  G.state.decorations.push(dec);
  addDecorMesh(dec, G.state.decorations.length - 1);
  G.save();
  G.updateHUD();
  G.sfx.collect();
  G.spawnBurst(new THREE.Vector3(dec.x, 1, dec.z), 0xff8fc4, 16);
  renderBar();
  if (G.state.stars < item.cost) { selectedType = null; removeGhost(); renderBar(); }
}

function removeDecor(idx) {
  const dec = G.state.decorations[idx];
  if (!dec) return;
  const item = DECOR_ITEMS.find((i) => i.id === dec.type);
  const g = placedGroups[idx];
  if (g) {
    G.scene.remove(g);
    placedGroups[idx] = null;
  }
  if (dec.colliderIdx !== undefined) {
    // colliders are append-only; just neutralize it
    G.colliders[dec.colliderIdx].r = 0;
  }
  G.state.decorations[idx] = null;
  G.state.stars += item.cost;
  G.save();
  G.updateHUD();
  G.sfx.collect();
  G.toast(`Returned ${item.emoji} — +✨${item.cost} back`);
  renderBar();
}

function addDecorMesh(dec, idx) {
  if (!dec) return;
  const g = buildDecor(dec.type);
  g.position.set(dec.x, 0, dec.z);
  g.rotation.y = dec.ry || 0;
  g.userData.decorIdx = idx;
  G.scene.add(g);
  placedGroups[idx] = g;
  const item = DECOR_ITEMS.find((i) => i.id === dec.type);
  if (item.collider) {
    dec.colliderIdx = G.colliders.length;
    G.colliders.push({ x: dec.x, z: dec.z, r: item.collider });
  }
}

// ---------------------------------------------------------------------------
// Decoration builders (small, cute, cheap)
// ---------------------------------------------------------------------------
function std(color, opts = {}) { return new THREE.MeshStandardMaterial({ color, roughness: 0.9, ...opts }); }

function buildDecor(type) {
  const g = new THREE.Group();
  if (type === 'blossom' || type === 'gumdrop') {
    const h = 2.4;
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.28, h, 7), std(0xb07a5e));
    trunk.position.y = h / 2; trunk.castShadow = true; g.add(trunk);
    if (type === 'blossom') {
      [[0, h + 0.6, 0, 1.2], [0.7, h + 0.25, 0.2, 0.85], [-0.65, h + 0.35, -0.15, 0.8]].forEach(([x, y, z, s], i) => {
        const m = new THREE.Mesh(new THREE.SphereGeometry(1, 10, 8), std(i % 2 ? 0xffcfe6 : 0xffb7d9));
        m.position.set(x, y, z); m.scale.setScalar(s); m.castShadow = i === 0; g.add(m);
      });
    } else {
      const top = new THREE.Mesh(new THREE.SphereGeometry(1.1, 10, 8), std(0xa9e8bb));
      top.position.y = h + 0.7; top.scale.set(1, 1.3, 1); top.castShadow = true; g.add(top);
    }
  } else if (type === 'flowers') {
    for (let i = 0; i < 7; i++) {
      const f = new THREE.Mesh(new THREE.SphereGeometry(0.14, 7, 5), std([0xff8fc4, 0xfff3c9, 0xcbb2ff, 0xffffff][i % 4]));
      const a = (i / 7) * Math.PI * 2;
      f.position.set(Math.cos(a) * (0.3 + (i % 3) * 0.2), 0.12, Math.sin(a) * (0.3 + (i % 3) * 0.2));
      g.add(f);
    }
  } else if (type === 'heart') {
    const base = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.65, 0.7, 12), std(0xffffff));
    base.position.y = 0.35; base.castShadow = true; g.add(base);
    const heart = G.makeHeartMesh(0xff2d95, 0.6);
    heart.position.y = 1.5;
    g.add(heart);
    g.userData.spin = heart;
  } else if (type === 'disco') {
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.09, 2.4, 8), std(0xd0d3e8, { metalness: 0.6, roughness: 0.35 }));
    pole.position.y = 1.2; g.add(pole);
    const ball = new THREE.Mesh(new THREE.SphereGeometry(0.55, 12, 8), std(0xe8e9f3, { metalness: 0.85, roughness: 0.25, flatShading: true }));
    ball.position.y = 2.5; ball.castShadow = true; g.add(ball);
    g.userData.spin = ball;
  } else if (type === 'lamp') {
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.1, 1.9, 8), std(0xfff6ee));
    pole.position.y = 0.95; g.add(pole);
    const star = new THREE.Mesh(G.makeStarGeo(0.34, 0.15), std(0xffd166, { emissive: 0xaa7712, emissiveIntensity: 0.8 }));
    star.position.y = 2.05; g.add(star);
    g.userData.spin = star;
  } else if (type === 'flamingo') {
    const body = new THREE.Mesh(new THREE.SphereGeometry(0.34, 10, 8), std(0xff8fa8));
    body.position.y = 0.85; body.scale.set(1, 0.85, 1.25); body.castShadow = true; g.add(body);
    [[-0.1], [0.12]].forEach(([x]) => {
      const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.028, 0.028, 0.85, 6), std(0xe66a86));
      leg.position.set(x, 0.42, 0); g.add(leg);
    });
    const neck = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.07, 0.75, 6), std(0xff8fa8));
    neck.position.set(0, 1.35, 0.32); neck.rotation.x = 0.35; g.add(neck);
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.13, 8, 6), std(0xff8fa8));
    head.position.set(0, 1.68, 0.48); g.add(head);
    const beak = new THREE.Mesh(new THREE.ConeGeometry(0.05, 0.18, 6), std(0x40282e));
    beak.position.set(0, 1.64, 0.62); beak.rotation.x = Math.PI / 2.3; g.add(beak);
  } else if (type === 'picnic') {
    const rug = new THREE.Mesh(new THREE.CylinderGeometry(1.1, 1.1, 0.04, 18), std(0xffd9ec));
    rug.position.y = 0.02; rug.receiveShadow = true; g.add(rug);
    const basket = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.18, 0.26, 10), std(0xc98d5f));
    basket.position.set(0.4, 0.15, 0.2); basket.castShadow = true; g.add(basket);
    const cake = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 0.14, 10), std(0xfff6ee));
    cake.position.set(-0.3, 0.09, -0.2); g.add(cake);
    const cherry = new THREE.Mesh(new THREE.SphereGeometry(0.05, 6, 5), std(0xff2d95));
    cherry.position.set(-0.3, 0.2, -0.2); g.add(cherry);
  }
  return g;
}

// gentle spin for placed items that want it
export function updateDecorations(t) {
  for (const g of placedGroups) {
    if (g && g.userData.spin) g.userData.spin.rotation.y = t * 0.8;
  }
}
