// 💖 Dreamhouse Kingdom — a Y2K dream world for girlies 💖
// old-doll glam x Y2K pop culture x storybook nostalgia
// Everything is procedural: three.js primitives, canvas textures, WebAudio.

import * as THREE from '../lib/three.module.min.js';
import { ZONES, TOTAL_QUESTIONS } from './trivia.js';
import { quoteOfTheDay, todayKey } from './quotes.js';
import { initCustomizer, toggleStyler, DEFAULT_LOOK, VIBE_PRESETS } from './customizer.js';
import { initEscape, openEscape } from './escape.js';
import { initPhotobooth, openBooth } from './photobooth.js';
import { initDecorate, toggleDecorate, isDecorating, updateDecorations } from './decorate.js';

// ---------------------------------------------------------------------------
// Constants & state
// ---------------------------------------------------------------------------
const ISLAND_R = 64;
const WALK_R = 59;
const RING_R = 34;
const STAR_COUNT = 44;
const SAVE_KEY = 'dreamhouse-kingdom-v1';

const state = {
  started: false,
  uiOpen: false,
  name: '',
  look: { ...DEFAULT_LOOK },
  answered: {},
  collectedStars: [],
  stars: 0,
  crowned: false,
  musicOn: true,
  escape: { solved: {}, escaped: false },
  unlocks: { midnight: false },
  decorations: [],
  lastQuoteDate: '',
};
ZONES.forEach((z) => (state.answered[z.id] = []));

function heartsCount() {
  return ZONES.reduce((n, z) => n + state.answered[z.id].length, 0);
}

function saveGame() {
  try {
    localStorage.setItem(SAVE_KEY, JSON.stringify({
      name: state.name,
      look: state.look,
      answered: state.answered,
      collectedStars: state.collectedStars,
      stars: state.stars,
      crowned: state.crowned,
      musicOn: state.musicOn,
      escape: state.escape,
      unlocks: state.unlocks,
      decorations: state.decorations.filter(Boolean).map(({ type, x, z, ry }) => ({ type, x, z, ry })),
      lastQuoteDate: state.lastQuoteDate,
    }));
  } catch (e) { /* private mode — play on without saving */ }
}

function loadGame() {
  try {
    const raw = localStorage.getItem(SAVE_KEY);
    if (!raw) return false;
    const d = JSON.parse(raw);
    state.name = typeof d.name === 'string' ? d.name : '';
    state.look = { ...DEFAULT_LOOK, ...(d.look || {}) };
    ZONES.forEach((z) => {
      state.answered[z.id] = Array.isArray(d.answered?.[z.id]) ? d.answered[z.id] : [];
    });
    state.collectedStars = Array.isArray(d.collectedStars) ? d.collectedStars : [];
    state.stars = Number.isFinite(d.stars) ? d.stars : 0;
    state.crowned = !!d.crowned;
    state.musicOn = d.musicOn !== false;
    state.escape = { solved: {}, escaped: false, ...(d.escape || {}) };
    state.unlocks = { midnight: false, ...(d.unlocks || {}) };
    state.decorations = Array.isArray(d.decorations) ? d.decorations : [];
    state.lastQuoteDate = d.lastQuoteDate || '';
    return true;
  } catch (e) { return false; }
}

function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rng = mulberry32(20260704);

// ---------------------------------------------------------------------------
// Renderer / scene / camera
// ---------------------------------------------------------------------------
const canvas = document.getElementById('c');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
let pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
renderer.setPixelRatio(pixelRatio);
renderer.setSize(window.innerWidth, window.innerHeight);

const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0xffe3f0, 70, 190);

const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 600);

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

// ---------------------------------------------------------------------------
// Sky, sun, lights
// ---------------------------------------------------------------------------
{
  const skyGeo = new THREE.SphereGeometry(420, 24, 16);
  const skyMat = new THREE.ShaderMaterial({
    side: THREE.BackSide,
    fog: false,
    depthWrite: false,
    uniforms: {
      top: { value: new THREE.Color(0xffb8dd) },
      mid: { value: new THREE.Color(0xe9dfff) },
      bottom: { value: new THREE.Color(0xfff0da) },
    },
    vertexShader: `
      varying float vH;
      void main() {
        vH = normalize(position).y;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }`,
    fragmentShader: `
      varying float vH;
      uniform vec3 top; uniform vec3 mid; uniform vec3 bottom;
      void main() {
        float h = clamp(vH, -0.1, 1.0);
        vec3 col = h < 0.25 ? mix(bottom, mid, smoothstep(-0.1, 0.25, h))
                            : mix(mid, top, smoothstep(0.25, 0.9, h));
        gl_FragColor = vec4(col, 1.0);
      }`,
  });
  scene.add(new THREE.Mesh(skyGeo, skyMat));
}

const hemi = new THREE.HemisphereLight(0xfff1f7, 0xd9f5dc, 0.9);
scene.add(hemi);

const sun = new THREE.DirectionalLight(0xfff2df, 1.6);
sun.position.set(45, 65, 30);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.left = -75; sun.shadow.camera.right = 75;
sun.shadow.camera.top = 75; sun.shadow.camera.bottom = -75;
sun.shadow.camera.near = 10; sun.shadow.camera.far = 180;
sun.shadow.bias = -0.0004;
scene.add(sun);
scene.add(new THREE.AmbientLight(0xffffff, 0.25));

{
  const spr = new THREE.Sprite(new THREE.SpriteMaterial({ map: makeGlowTexture('#fff7e0'), transparent: true, opacity: 0.95, fog: false, depthWrite: false }));
  spr.scale.set(90, 90, 1);
  spr.position.set(180, 230, 120);
  scene.add(spr);
}

// ---------------------------------------------------------------------------
// Texture helpers
// ---------------------------------------------------------------------------
function makeGlowTexture(color) {
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g = c.getContext('2d');
  const grad = g.createRadialGradient(64, 64, 4, 64, 64, 62);
  grad.addColorStop(0, color);
  grad.addColorStop(0.4, color + 'cc');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grad; g.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function makeSparkleTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const g = c.getContext('2d');
  g.translate(32, 32);
  const grad = g.createRadialGradient(0, 0, 1, 0, 0, 30);
  grad.addColorStop(0, 'rgba(255,255,255,1)');
  grad.addColorStop(0.35, 'rgba(255,240,250,0.7)');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grad;
  g.beginPath();
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * Math.PI * 2;
    const r = i % 2 === 0 ? 30 : 7;
    g.lineTo(Math.cos(a) * r, Math.sin(a) * r);
  }
  g.closePath(); g.fill();
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
const sparkleTex = makeSparkleTexture();

function makeStripesTexture(colorA, colorB) {
  const c = document.createElement('canvas'); c.width = 256; c.height = 64;
  const g = c.getContext('2d');
  for (let i = 0; i < 8; i++) {
    g.fillStyle = i % 2 ? colorA : colorB;
    g.fillRect(i * 32, 0, 32, 64);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = THREE.RepeatWrapping;
  return t;
}

function makeLabelSprite(text, accent) {
  const c = document.createElement('canvas'); c.width = 512; c.height = 144;
  const g = c.getContext('2d');
  g.beginPath();
  g.roundRect(10, 14, 492, 116, 56);
  g.fillStyle = 'rgba(255,255,255,0.94)';
  g.fill();
  g.lineWidth = 8; g.strokeStyle = accent; g.stroke();
  g.fillStyle = '#6b4a63';
  g.font = '800 50px "Trebuchet MS", "Segoe UI", sans-serif';
  g.textAlign = 'center'; g.textBaseline = 'middle';
  g.fillText(text, 256, 76);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  const spr = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, transparent: true, depthWrite: false }));
  spr.scale.set(4.6, 1.3, 1);
  return spr;
}

// ---------------------------------------------------------------------------
// Ground, water, island
// ---------------------------------------------------------------------------
const zoneAngles = ZONES.map((_, i) => -Math.PI / 2 + (i * Math.PI * 2) / ZONES.length);
const zonePos = zoneAngles.map((a) => new THREE.Vector3(Math.cos(a) * RING_R, 0, Math.sin(a) * RING_R));
const midAngle = (i) => -Math.PI / 2 + ((i + 0.5) * Math.PI * 2) / ZONES.length;

function paintGround() {
  const S = 2048;
  const c = document.createElement('canvas'); c.width = c.height = S;
  const g = c.getContext('2d');
  const w2c = (wx, wz) => [((wx / ISLAND_R) + 1) * S / 2, ((wz / ISLAND_R) + 1) * S / 2];
  const scale = S / 2 / ISLAND_R;

  const grad = g.createRadialGradient(S / 2, S / 2, S * 0.05, S / 2, S / 2, S * 0.52);
  grad.addColorStop(0, '#d8f3cf');
  grad.addColorStop(0.55, '#cdeec6');
  grad.addColorStop(0.85, '#ffdff0');
  grad.addColorStop(1, '#ffd2e8');
  g.fillStyle = grad; g.fillRect(0, 0, S, S);

  for (let i = 0; i < 260; i++) {
    const a = rng() * Math.PI * 2, r = Math.sqrt(rng()) * ISLAND_R * 0.98;
    const [x, y] = w2c(Math.cos(a) * r, Math.sin(a) * r);
    g.fillStyle = rng() > 0.5 ? 'rgba(255,255,255,0.10)' : 'rgba(160,220,160,0.10)';
    g.beginPath(); g.arc(x, y, (4 + rng() * 14) * (S / 1024), 0, Math.PI * 2); g.fill();
  }

  g.strokeStyle = '#fdeed7';
  g.lineWidth = 5.5 * scale;
  g.beginPath(); g.arc(S / 2, S / 2, RING_R * scale, 0, Math.PI * 2); g.stroke();

  g.lineCap = 'round';
  zonePos.forEach((p) => {
    const [x, y] = w2c(p.x, p.z);
    g.beginPath(); g.moveTo(S / 2, S / 2); g.lineTo(x, y); g.stroke();
  });
  // path to the castle
  {
    const a = midAngle(4); // between the garden and the café
    const [x, y] = w2c(Math.cos(a) * 46, Math.sin(a) * 46);
    g.beginPath(); g.moveTo(S / 2, S / 2); g.lineTo(x, y); g.stroke();
  }

  g.fillStyle = '#fdeed7';
  g.beginPath(); g.arc(S / 2, S / 2, 9 * scale, 0, Math.PI * 2); g.fill();
  g.strokeStyle = '#f7cfe2'; g.lineWidth = 0.8 * scale;
  g.beginPath(); g.arc(S / 2, S / 2, 9 * scale, 0, Math.PI * 2); g.stroke();

  ZONES.forEach((z, i) => {
    const [x, y] = w2c(zonePos[i].x, zonePos[i].z);
    g.fillStyle = '#ffffff';
    g.globalAlpha = 0.3;
    g.beginPath(); g.arc(x, y, 5 * scale, 0, Math.PI * 2); g.fill();
    g.globalAlpha = 1;
  });

  for (let i = 0; i < 420; i++) {
    const a = rng() * Math.PI * 2, r = 11 + Math.sqrt(rng()) * (ISLAND_R - 13);
    const [x, y] = w2c(Math.cos(a) * r, Math.sin(a) * r);
    const size = (1.6 + rng() * 2.4) * (S / 1024);
    g.fillStyle = ['#ffffff', '#ffd9ec', '#fff3c9', '#e2d7ff'][Math.floor(rng() * 4)];
    g.beginPath(); g.arc(x, y, size, 0, Math.PI * 2); g.fill();
  }

  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  return t;
}

let ground;
{
  ground = new THREE.Mesh(
    new THREE.CircleGeometry(ISLAND_R, 96),
    new THREE.MeshStandardMaterial({ map: paintGround(), roughness: 1 })
  );
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);

  const side = new THREE.Mesh(
    new THREE.CylinderGeometry(ISLAND_R, ISLAND_R * 0.96, 4, 96, 1, true),
    new THREE.MeshStandardMaterial({ color: 0xf3cfd8, roughness: 1 })
  );
  side.position.y = -2;
  scene.add(side);

  const sea = new THREE.Mesh(
    new THREE.CircleGeometry(420, 64),
    new THREE.MeshStandardMaterial({ color: 0x9fdcf2, roughness: 0.65, metalness: 0.05 })
  );
  sea.rotation.x = -Math.PI / 2;
  sea.position.y = -3.2;
  scene.add(sea);

  const foam = new THREE.Mesh(
    new THREE.RingGeometry(ISLAND_R * 0.985, ISLAND_R + 4.5, 96),
    new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.55, depthWrite: false })
  );
  foam.rotation.x = -Math.PI / 2;
  foam.position.y = -3.1;
  scene.add(foam);
}

// ---------------------------------------------------------------------------
// Shared materials, colliders, animation registry
// ---------------------------------------------------------------------------
const MAT = {
  cream: new THREE.MeshStandardMaterial({ color: 0xfff6ee, roughness: 0.9 }),
  white: new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.85 }),
  trunk: new THREE.MeshStandardMaterial({ color: 0xb07a5e, roughness: 1 }),
  blossom: new THREE.MeshStandardMaterial({ color: 0xffb7d9, roughness: 0.95 }),
  blossom2: new THREE.MeshStandardMaterial({ color: 0xffcfe6, roughness: 0.95 }),
  leaf: new THREE.MeshStandardMaterial({ color: 0xa9e8bb, roughness: 0.95 }),
  gold: new THREE.MeshStandardMaterial({ color: 0xffd166, roughness: 0.4, metalness: 0.3, emissive: 0x332200 }),
  hotpink: new THREE.MeshStandardMaterial({ color: 0xff2d95, roughness: 0.75 }),
  chrome: new THREE.MeshStandardMaterial({ color: 0xdfe1f0, roughness: 0.25, metalness: 0.8, flatShading: true }),
};

const colliders = [];      // { x, z, r }
const animatedBits = [];   // per-frame callbacks(t)
const interactables = [];  // { id, pos, radius, prompt, promptTouch, available(), action() }

// ---------------------------------------------------------------------------
// Trees & flowers
// ---------------------------------------------------------------------------
function addTree(x, z, kind) {
  const tree = new THREE.Group();
  const h = 2.2 + rng() * 1.4;
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.3, h, 7), MAT.trunk);
  trunk.position.y = h / 2;
  trunk.castShadow = true;
  tree.add(trunk);

  if (kind === 'blossom') {
    const puffGeo = new THREE.SphereGeometry(1, 10, 8);
    [[0, h + 0.7, 0, 1.35], [0.85, h + 0.3, 0.25, 0.95], [-0.8, h + 0.45, -0.2, 0.9], [0.1, h + 0.2, -0.8, 0.8]]
      .forEach(([px, py, pz, s], i) => {
        const m = new THREE.Mesh(puffGeo, i % 2 ? MAT.blossom2 : MAT.blossom);
        m.position.set(px, py, pz);
        m.scale.setScalar(s);
        m.castShadow = i === 0;
        tree.add(m);
      });
  } else {
    const cone = new THREE.Mesh(new THREE.SphereGeometry(1.15, 10, 8), MAT.leaf);
    cone.position.y = h + 0.75;
    cone.scale.set(1, 1.35, 1);
    cone.castShadow = true;
    tree.add(cone);
  }
  tree.position.set(x, 0, z);
  tree.rotation.y = rng() * Math.PI * 2;
  scene.add(tree);
  colliders.push({ x, z, r: 0.75 });
}

const castleAngle = midAngle(4); // between the garden and the café
const castlePos = new THREE.Vector3(Math.cos(castleAngle) * 47, 0, Math.sin(castleAngle) * 47);

function scatterTrees() {
  let placed = 0, guard = 0;
  while (placed < 26 && guard++ < 500) {
    const a = rng() * Math.PI * 2;
    const r = 13 + Math.sqrt(rng()) * (WALK_R - 14);
    const x = Math.cos(a) * r, z = Math.sin(a) * r;
    if (Math.abs(r - RING_R) < 4.5) continue;
    if (zonePos.some((p) => p.distanceTo(new THREE.Vector3(x, 0, z)) < 10)) continue;
    if (castlePos.distanceTo(new THREE.Vector3(x, 0, z)) < 14) continue;
    if (Math.hypot(x, z) < 11) continue;
    addTree(x, z, rng() > 0.45 ? 'blossom' : 'gumdrop');
    placed++;
  }
}
scatterTrees();

{
  const geo = new THREE.SphereGeometry(0.13, 6, 5);
  const mat = new THREE.MeshStandardMaterial({ roughness: 0.95 });
  const count = 240;
  const inst = new THREE.InstancedMesh(geo, mat, count);
  const dummy = new THREE.Object3D();
  const palette = [new THREE.Color(0xff8fc4), new THREE.Color(0xfff3c9), new THREE.Color(0xcbb2ff), new THREE.Color(0xffffff), new THREE.Color(0xffc9a8)];
  for (let i = 0; i < count; i++) {
    const a = rng() * Math.PI * 2, r = 6 + Math.sqrt(rng()) * (WALK_R - 6);
    dummy.position.set(Math.cos(a) * r, 0.1, Math.sin(a) * r);
    dummy.scale.setScalar(0.7 + rng() * 0.9);
    dummy.updateMatrix();
    inst.setMatrixAt(i, dummy.matrix);
    inst.setColorAt(i, palette[Math.floor(rng() * palette.length)]);
  }
  inst.instanceMatrix.needsUpdate = true;
  scene.add(inst);
}

// ---------------------------------------------------------------------------
// Heart & star shape helpers
// ---------------------------------------------------------------------------
function makeHeartMesh(color, scale) {
  const s = new THREE.Shape();
  s.moveTo(0, 0.5);
  s.bezierCurveTo(0, 0.8, -0.5, 1.0, -0.75, 0.7);
  s.bezierCurveTo(-1.05, 0.35, -0.7, -0.1, 0, -0.7);
  s.bezierCurveTo(0.7, -0.1, 1.05, 0.35, 0.75, 0.7);
  s.bezierCurveTo(0.5, 1.0, 0, 0.8, 0, 0.5);
  const geo = new THREE.ExtrudeGeometry(s, { depth: 0.3, bevelEnabled: true, bevelSize: 0.06, bevelThickness: 0.06, bevelSegments: 2 });
  geo.center();
  const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color, roughness: 0.5, emissive: color, emissiveIntensity: 0.25 }));
  m.scale.setScalar(scale);
  m.castShadow = true;
  return m;
}

function makeStarGeo(outer = 0.38, inner = 0.16) {
  const s = new THREE.Shape();
  for (let i = 0; i < 10; i++) {
    const a = (i / 10) * Math.PI * 2 - Math.PI / 2;
    const r = i % 2 === 0 ? outer : inner;
    if (i === 0) s.moveTo(Math.cos(a) * r, Math.sin(a) * r);
    else s.lineTo(Math.cos(a) * r, Math.sin(a) * r);
  }
  s.closePath();
  const geo = new THREE.ExtrudeGeometry(s, { depth: 0.12, bevelEnabled: true, bevelSize: 0.04, bevelThickness: 0.04, bevelSegments: 1 });
  geo.center();
  return geo;
}

// ---------------------------------------------------------------------------
// Center plaza fountain
// ---------------------------------------------------------------------------
{
  const fountain = new THREE.Group();
  [[2.4, 2.6, 0.7, 0.35], [1.5, 1.7, 0.6, 1.0], [0.7, 0.9, 0.55, 1.6]].forEach(([rt, rb, h, y]) => {
    const m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, 20), MAT.white);
    m.position.y = y; m.castShadow = true; m.receiveShadow = true;
    fountain.add(m);
  });
  const water = new THREE.Mesh(
    new THREE.CylinderGeometry(2.2, 2.2, 0.1, 20),
    new THREE.MeshStandardMaterial({ color: 0xaee4f7, roughness: 0.3, emissive: 0x1b5f75, emissiveIntensity: 0.15 })
  );
  water.position.y = 0.62;
  fountain.add(water);
  const heart = makeHeartMesh(0xff2d95, 0.55);
  heart.position.y = 2.6;
  fountain.add(heart);
  scene.add(fountain);
  colliders.push({ x: 0, z: 0, r: 3.0 });
  animatedBits.push((t) => {
    heart.rotation.y = t * 0.8;
    heart.position.y = 2.6 + Math.sin(t * 1.6) * 0.15;
  });
}

// ---------------------------------------------------------------------------
// Building helpers
// ---------------------------------------------------------------------------
function box(w, h, d, color, opts = {}) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), color.isMaterial ? color : new THREE.MeshStandardMaterial({ color, roughness: 0.9, ...opts }));
  m.castShadow = true; m.receiveShadow = true;
  return m;
}
function cyl(rt, rb, h, color, seg = 16) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), color.isMaterial ? color : new THREE.MeshStandardMaterial({ color, roughness: 0.9 }));
  m.castShadow = true; m.receiveShadow = true;
  return m;
}
function cone(r, h, color, seg = 12) {
  const m = new THREE.Mesh(new THREE.ConeGeometry(r, h, seg), color.isMaterial ? color : new THREE.MeshStandardMaterial({ color, roughness: 0.85 }));
  m.castShadow = true;
  return m;
}

function buildCafe() {
  const g = new THREE.Group();
  const body = box(5, 3.2, 4, 0xfff6ee); body.position.y = 1.6; g.add(body);
  const roof = box(5.6, 0.5, 4.6, 0xff9ec7); roof.position.y = 3.45; g.add(roof);
  const awn = new THREE.Mesh(
    new THREE.CylinderGeometry(1.5, 1.5, 4.6, 14, 1, false, 0, Math.PI),
    new THREE.MeshStandardMaterial({ map: makeStripesTexture('#ff9ec7', '#fff6ee'), roughness: 0.9 })
  );
  awn.rotation.z = Math.PI / 2;
  awn.scale.set(0.55, 1, 1);
  awn.position.set(0, 2.5, 2.05);
  awn.castShadow = true;
  g.add(awn);
  const door = box(1.1, 1.9, 0.15, 0xd97ba6); door.position.set(0, 0.95, 2.02); g.add(door);
  [-1.7, 1.7].forEach((x) => {
    const win = box(1.1, 1.1, 0.12, 0xbfe9ff, { roughness: 0.3 }); win.position.set(x, 1.8, 2.02); g.add(win);
  });
  const macTop = cyl(0.9, 1.0, 0.42, 0xffb7d9, 20); macTop.position.y = 4.15;
  const macFill = cyl(0.95, 0.95, 0.18, 0xfff6ee, 20); macFill.position.y = 3.92;
  const macBot = cyl(1.0, 0.9, 0.42, 0xffb7d9, 20); macBot.position.y = 3.7;
  g.add(macTop, macFill, macBot);
  return { group: g, collider: 3.4 };
}

function buildBoutique() {
  const g = new THREE.Group();
  const body = box(4.6, 3.6, 3.6, 0xf3ecff); body.position.y = 1.8; g.add(body);
  const roof = box(5.2, 0.5, 4.2, 0xcbb2ff); roof.position.y = 3.85; g.add(roof);
  const win = box(2.6, 1.7, 0.14, 0xd8f0ff, { roughness: 0.25 }); win.position.set(-0.6, 1.4, 1.82); g.add(win);
  const door = box(1.0, 2.0, 0.15, 0xa98bf5); door.position.set(1.5, 1.0, 1.82); g.add(door);
  const bow = new THREE.Group();
  const knot = new THREE.Mesh(new THREE.SphereGeometry(0.4, 10, 8), MAT.hotpink);
  const loopL = new THREE.Mesh(new THREE.ConeGeometry(0.55, 1.3, 10), MAT.hotpink);
  const loopR = loopL.clone();
  loopL.rotation.z = Math.PI / 2 - 0.35; loopL.position.x = -0.75;
  loopR.rotation.z = -Math.PI / 2 + 0.35; loopR.position.x = 0.75;
  bow.add(knot, loopL, loopR);
  bow.position.y = 4.6;
  bow.children.forEach((m) => (m.castShadow = true));
  g.add(bow);
  // wardrobe out front (opens the Style Studio)
  const ward = new THREE.Group();
  const wbody = box(1.3, 2.1, 0.7, 0xffffff); wbody.position.y = 1.05; ward.add(wbody);
  const wtop = box(1.45, 0.18, 0.85, 0xff8fc4); wtop.position.y = 2.2; ward.add(wtop);
  const knobL = new THREE.Mesh(new THREE.SphereGeometry(0.06, 6, 5), MAT.gold); knobL.position.set(-0.18, 1.1, 0.38); ward.add(knobL);
  const knobR = knobL.clone(); knobR.position.x = 0.18; ward.add(knobR);
  const seam = box(0.04, 1.9, 0.04, 0xcbb2ff); seam.position.set(0, 1.05, 0.36); ward.add(seam);
  ward.position.set(-2.9, 0, 1.6);
  g.add(ward);
  return { group: g, collider: 3.3, extraColliders: [{ dx: -2.9, dz: 1.6, r: 0.9 }], wardOffset: { dx: -2.9, dz: 1.6 } };
}

function buildGlowBar() {
  const g = new THREE.Group();
  const body = cyl(2.3, 2.5, 3.2, 0xffe4d1, 22); body.position.y = 1.6; g.add(body);
  const dome = new THREE.Mesh(new THREE.SphereGeometry(2.35, 22, 12, 0, Math.PI * 2, 0, Math.PI / 2),
    new THREE.MeshStandardMaterial({ color: 0xffc9a8, roughness: 0.9 }));
  dome.position.y = 3.2; dome.castShadow = true; g.add(dome);
  const door = box(1.0, 1.9, 0.15, 0xff9f70); door.position.set(0, 0.95, 2.42); g.add(door);
  const lip = new THREE.Group();
  const base = cyl(0.45, 0.45, 1.1, MAT.gold, 14); base.position.y = 0.55; lip.add(base);
  const stick = cyl(0.34, 0.34, 1.0, 0xff5f9e, 14); stick.position.y = 1.55; lip.add(stick);
  const tip = new THREE.Mesh(new THREE.SphereGeometry(0.34, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2),
    new THREE.MeshStandardMaterial({ color: 0xff5f9e, roughness: 0.6 }));
  tip.position.y = 2.05; tip.castShadow = true; lip.add(tip);
  lip.position.set(3.2, 0, 0.6);
  lip.rotation.z = -0.12;
  g.add(lip);
  // vanity mirror out front (opens the Style Studio)
  const van = new THREE.Group();
  const table = box(1.4, 0.12, 0.6, 0xffffff); table.position.y = 0.8; van.add(table);
  [[-0.55], [0.55]].forEach(([x]) => {
    const leg = cyl(0.05, 0.05, 0.8, 0xffd9ec, 8); leg.position.set(x, 0.4, 0); van.add(leg);
  });
  const mirror = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.55, 0.06, 18),
    new THREE.MeshStandardMaterial({ color: 0xd8f0ff, roughness: 0.15, metalness: 0.4 }));
  mirror.rotation.x = Math.PI / 2;
  mirror.position.set(0, 1.6, -0.1);
  van.add(mirror);
  const rim = new THREE.Mesh(new THREE.TorusGeometry(0.58, 0.06, 8, 20), MAT.gold);
  rim.position.set(0, 1.6, -0.1);
  van.add(rim);
  van.position.set(-3.1, 0, 1.4);
  g.add(van);
  return {
    group: g, collider: 3.2,
    extraColliders: [{ dx: 3.2, dz: 0.6, r: 0.8 }, { dx: -3.1, dz: 1.4, r: 0.9 }],
    vanOffset: { dx: -3.1, dz: 1.4 },
  };
}

function buildStage() {
  const g = new THREE.Group();
  const deck = cyl(4.2, 4.5, 0.6, 0xffd9ec, 24); deck.position.y = 0.3; g.add(deck);
  const arch = new THREE.Mesh(
    new THREE.TorusGeometry(3.2, 0.28, 10, 24, Math.PI),
    MAT.hotpink
  );
  arch.position.y = 0.6; arch.castShadow = true;
  g.add(arch);
  [-3.4, 3.4].forEach((x) => {
    const sp = box(1.1, 1.6, 1.1, 0x8b6fc9); sp.position.set(x, 1.4, 0.4); g.add(sp);
    const c = cyl(0.32, 0.42, 0.12, 0x2e2331, 12);
    c.rotation.x = Math.PI / 2; c.position.set(x, 1.7, 0.97); g.add(c);
  });
  // Y2K disco ball hanging from the arch
  const chain = cyl(0.03, 0.03, 0.7, 0xd0d3e8, 6); chain.position.y = 3.4; g.add(chain);
  const ball = new THREE.Mesh(new THREE.SphereGeometry(0.7, 14, 10), MAT.chrome);
  ball.position.y = 2.7; ball.castShadow = true; g.add(ball);
  animatedBits.push((t) => { ball.rotation.y = t * 1.2; });
  const star = new THREE.Mesh(makeStarGeo(0.7, 0.3), MAT.gold);
  star.position.y = 4.15; star.castShadow = true;
  g.add(star);
  animatedBits.push((t) => { star.rotation.y = t * 0.7; });
  return { group: g, collider: 4.6 };
}

function buildGarden() {
  const g = new THREE.Group();
  const arch = new THREE.Mesh(new THREE.TorusGeometry(2.2, 0.18, 8, 22, Math.PI), MAT.white);
  arch.position.y = 0.4; arch.castShadow = true; g.add(arch);
  const roseGeo = new THREE.SphereGeometry(0.28, 8, 6);
  for (let i = 0; i <= 8; i++) {
    const a = (i / 8) * Math.PI;
    const rose = new THREE.Mesh(roseGeo, i % 2 ? MAT.blossom : MAT.blossom2);
    rose.position.set(Math.cos(a) * 2.2, 0.4 + Math.sin(a) * 2.2, 0);
    g.add(rose);
  }
  [[-2.6, 1.8], [2.6, 1.8]].forEach(([x, z]) => {
    const bed = new THREE.Mesh(new THREE.TorusGeometry(0.9, 0.22, 8, 16), MAT.white);
    bed.rotation.x = Math.PI / 2; bed.position.set(x, 0.18, z); bed.castShadow = true;
    g.add(bed);
    for (let i = 0; i < 5; i++) {
      const f = new THREE.Mesh(roseGeo, [MAT.blossom, MAT.leaf, MAT.blossom2][i % 3]);
      f.scale.setScalar(0.7);
      f.position.set(x + (rng() - 0.5) * 1.1, 0.3, z + (rng() - 0.5) * 1.1);
      g.add(f);
    }
  });
  const seat = box(1.9, 0.14, 0.6, 0xfff6ee); seat.position.set(0, 0.55, 2.6);
  const legL = box(0.14, 0.55, 0.55, 0xd9b8a4); legL.position.set(-0.8, 0.27, 2.6);
  const legR = legL.clone(); legR.position.x = 0.8;
  g.add(seat, legL, legR);
  return { group: g, collider: 2.6, extraColliders: [{ dx: 0, dz: 2.6, r: 1.0 }, { dx: -2.6, dz: 1.8, r: 1.0 }, { dx: 2.6, dz: 1.8, r: 1.0 }] };
}

const BUILDERS = { cafe: buildCafe, boutique: buildBoutique, glow: buildGlowBar, stage: buildStage, garden: buildGarden };

// ---------------------------------------------------------------------------
// The castle — home of the Forgotten Tower escape room
// ---------------------------------------------------------------------------
{
  const g = new THREE.Group();
  const keep = box(9, 5.5, 7, 0xfff2f8); keep.position.y = 2.75; g.add(keep);
  // corner towers
  [[-4.5, -3.2], [4.5, -3.2], [-4.5, 3.2], [4.5, 3.2]].forEach(([x, z], i) => {
    const tw = cyl(1.5, 1.6, 8, 0xfff6ee, 12); tw.position.set(x, 4, z); g.add(tw);
    const roof = cone(1.85, 2.6, i % 2 ? 0xff5fa8 : 0xa98bf5, 12); roof.position.set(x, 9.3, z); g.add(roof);
  });
  // central tower
  const main = cyl(2.0, 2.1, 11, 0xfff2f8, 14); main.position.set(0, 5.5, 0); g.add(main);
  const mainRoof = cone(2.5, 3.2, 0xff2d95, 14); mainRoof.position.y = 12.6; g.add(mainRoof);
  const flagPole = cyl(0.05, 0.05, 1.6, 0xd0d3e8, 6); flagPole.position.y = 14.7; g.add(flagPole);
  const flag = new THREE.Mesh(new THREE.PlaneGeometry(1.0, 0.6), new THREE.MeshBasicMaterial({ color: 0xff2d95, side: THREE.DoubleSide }));
  flag.position.set(0.5, 15.1, 0); g.add(flag);
  animatedBits.push((t) => { flag.scale.y = 1 + Math.sin(t * 3) * 0.08; flag.rotation.y = Math.sin(t * 2.2) * 0.3; });
  // gate
  const gate = box(2.6, 3.4, 0.4, 0xe8d5f5); gate.position.set(0, 1.7, 3.65); g.add(gate);
  const doorArch = new THREE.Mesh(
    new THREE.CylinderGeometry(1.0, 1.0, 0.42, 14, 1, false, -Math.PI / 2, Math.PI),
    new THREE.MeshStandardMaterial({ color: 0x6b4a8f, roughness: 0.9 })
  );
  doorArch.rotation.x = Math.PI / 2;
  doorArch.position.set(0, 2.2, 3.66);
  g.add(doorArch);
  const doorBody = box(2.0, 2.2, 0.42, 0x6b4a8f); doorBody.position.set(0, 1.1, 3.66); g.add(doorBody);
  // tiny windows
  [[-2.5, 3.4], [2.5, 3.4], [0, 8.6]].forEach(([x, y]) => {
    const w = box(0.55, 0.9, 0.2, 0xbfe9ff, { roughness: 0.3 });
    w.position.set(x, y, x === 0 ? 2.05 : 3.55);
    g.add(w);
  });
  g.position.copy(castlePos);
  g.rotation.y = Math.atan2(-castlePos.x, -castlePos.z);
  scene.add(g);
  colliders.push({ x: castlePos.x, z: castlePos.z, r: 7.2 });

  // sparkles floating around the main spire
  const ringSpark = new THREE.Sprite(new THREE.SpriteMaterial({ map: sparkleTex, color: 0xffd9f2, transparent: true, opacity: 0.9, depthWrite: false }));
  ringSpark.scale.set(2.4, 2.4, 1);
  ringSpark.position.set(castlePos.x, 13, castlePos.z);
  scene.add(ringSpark);
  animatedBits.push((t) => {
    ringSpark.position.x = castlePos.x + Math.cos(t * 0.9) * 3;
    ringSpark.position.z = castlePos.z + Math.sin(t * 0.9) * 3;
    ringSpark.material.opacity = 0.5 + Math.sin(t * 3) * 0.35;
  });

  // door interaction point (just outside the gate)
  const doorDir = new THREE.Vector3(-castlePos.x, 0, -castlePos.z).normalize();
  const doorPos = castlePos.clone().add(doorDir.multiplyScalar(8.6));
  const label = makeLabelSprite('🏰 The Forgotten Tower', '#a98bf5');
  label.position.set(doorPos.x, 4.6, doorPos.z);
  scene.add(label);
  interactables.push({
    id: 'castle',
    pos: doorPos,
    radius: 3.6,
    label,
    prompt: () => (state.escape.escaped ? '🏰 Revisit the Forgotten Tower' : '🏰 <b>The Forgotten Tower</b> — dare to enter?'),
    available: () => true,
    action: () => openEscape(),
  });
}

// ---------------------------------------------------------------------------
// Photobooth + giant flip phone photo-op
// ---------------------------------------------------------------------------
{
  const a = midAngle(0); // between café and boutique
  const pos = new THREE.Vector3(Math.cos(a) * 14, 0, Math.sin(a) * 14);
  const g = new THREE.Group();
  const body = box(2.4, 3.1, 2.2, 0xff5fa8); body.position.y = 1.55; g.add(body);
  const roofLip = box(2.7, 0.3, 2.5, 0xfff6ee); roofLip.position.y = 3.2; g.add(roofLip);
  // opening with curtain
  const opening = box(1.5, 2.3, 0.1, 0x40284e); opening.position.set(0, 1.3, 1.12); g.add(opening);
  const curtain = new THREE.Mesh(
    new THREE.PlaneGeometry(1.5, 2.0, 8, 1),
    new THREE.MeshStandardMaterial({ map: makeStripesTexture('#ff2d95', '#ffd9ec'), roughness: 0.9, side: THREE.DoubleSide })
  );
  curtain.position.set(-0.35, 1.35, 1.18);
  curtain.rotation.y = 0.15;
  g.add(curtain);
  animatedBits.push((t) => { curtain.rotation.y = 0.15 + Math.sin(t * 1.3) * 0.06; });
  const camIcon = new THREE.Mesh(new THREE.SphereGeometry(0.22, 10, 8), new THREE.MeshStandardMaterial({ color: 0x40284e, roughness: 0.4 }));
  camIcon.position.set(0, 2.75, 1.15); g.add(camIcon);
  const lens = new THREE.Mesh(new THREE.SphereGeometry(0.1, 8, 6), new THREE.MeshStandardMaterial({ color: 0x9fd8ff, roughness: 0.15 }));
  lens.position.set(0, 2.75, 1.34); g.add(lens);
  g.position.copy(pos);
  g.rotation.y = Math.atan2(-pos.x, -pos.z) + Math.PI; // opening faces the plaza
  scene.add(g);
  colliders.push({ x: pos.x, z: pos.z, r: 1.9 });

  const label = makeLabelSprite('📸 Photobooth', '#ff2d95');
  label.position.set(pos.x, 4.1, pos.z);
  scene.add(label);
  interactables.push({
    id: 'booth',
    pos: pos.clone(),
    radius: 3.4,
    label,
    prompt: () => '📸 <b>Sparkle Photobooth</b> — strike a pose!',
    available: () => true,
    action: () => openBooth(),
  });

  // giant Y2K flip phone photo-op next to the booth
  const phone = new THREE.Group();
  const bottomHalf = box(1.5, 0.3, 2.3, 0xff8fc4); bottomHalf.position.set(0, 0.15, 0); phone.add(bottomHalf);
  const keys = box(1.2, 0.08, 1.7, 0xffd9ec); keys.position.set(0, 0.33, 0.1); phone.add(keys);
  for (let r = 0; r < 3; r++) for (let cx = 0; cx < 3; cx++) {
    const k = box(0.24, 0.06, 0.3, 0xff5fa8);
    k.position.set(-0.4 + cx * 0.4, 0.39, -0.4 + r * 0.5);
    phone.add(k);
  }
  const topHalf = box(1.5, 2.3, 0.3, 0xff8fc4); topHalf.position.set(0, 1.3, -1.25); topHalf.rotation.x = -0.15; phone.add(topHalf);
  const screen = box(1.15, 1.7, 0.1, 0x9fd8ff, { roughness: 0.2 }); screen.position.set(0, 1.32, -1.06); screen.rotation.x = -0.15; phone.add(screen);
  const antenna = cyl(0.05, 0.05, 0.8, 0xd0d3e8, 6); antenna.position.set(0.6, 2.5, -1.42); phone.add(antenna);
  phone.position.set(pos.x + 3.4, 0, pos.z + 0.8);
  phone.rotation.y = rng() * 0.8;
  scene.add(phone);
  colliders.push({ x: pos.x + 3.4, z: pos.z + 0.8, r: 1.6 });
}

// ---------------------------------------------------------------------------
// Wishing well — quote of the day
// ---------------------------------------------------------------------------
{
  const a = midAngle(2); // between glow bar and stage
  const pos = new THREE.Vector3(Math.cos(a) * 14, 0, Math.sin(a) * 14);
  const g = new THREE.Group();
  const wall = cyl(1.1, 1.2, 1.0, 0xf3ecff, 14); wall.position.y = 0.5; g.add(wall);
  const waterW = new THREE.Mesh(new THREE.CylinderGeometry(0.95, 0.95, 0.1, 14),
    new THREE.MeshStandardMaterial({ color: 0x8fd4f5, roughness: 0.25, emissive: 0x1b5f75, emissiveIntensity: 0.3 }));
  waterW.position.y = 0.85; g.add(waterW);
  [[-1, 0], [1, 0]].forEach(([x]) => {
    const post = box(0.16, 1.8, 0.16, 0xd9b8a4); post.position.set(x * 1.0, 1.6, 0); g.add(post);
  });
  const roof = cone(1.6, 1.0, 0xff8fc4, 4); roof.position.y = 2.9; roof.rotation.y = Math.PI / 4; g.add(roof);
  const moon = new THREE.Mesh(new THREE.SphereGeometry(0.2, 10, 8), new THREE.MeshStandardMaterial({ color: 0xfff3c9, emissive: 0xfff3c9, emissiveIntensity: 0.6 }));
  moon.position.y = 3.6; g.add(moon);
  animatedBits.push((t) => { moon.position.y = 3.6 + Math.sin(t * 1.4) * 0.12; });
  g.position.copy(pos);
  scene.add(g);
  colliders.push({ x: pos.x, z: pos.z, r: 1.5 });

  const label = makeLabelSprite('🔮 Wishing Well', '#a98bf5');
  label.position.set(pos.x, 4.4, pos.z);
  scene.add(label);
  interactables.push({
    id: 'well',
    pos: pos.clone(),
    radius: 3.2,
    label,
    prompt: () => '🔮 <b>Wishing Well</b> — today\'s whimsy',
    available: () => true,
    action: () => showQuote(),
  });
}

// ---------------------------------------------------------------------------
// Zones: landmarks + trivia kiosks
// ---------------------------------------------------------------------------
const kiosks = [];

ZONES.forEach((zone, i) => {
  const pos = zonePos[i];
  const angleToCenter = Math.atan2(-pos.x, -pos.z);

  const outward = pos.clone().normalize();
  const landmarkPos = outward.clone().multiplyScalar(RING_R + 9);
  const built = BUILDERS[zone.id]();
  built.group.position.set(landmarkPos.x, 0, landmarkPos.z);
  built.group.rotation.y = angleToCenter;
  scene.add(built.group);
  colliders.push({ x: landmarkPos.x, z: landmarkPos.z, r: built.collider });
  const rotOff = (dx, dz) => {
    const ca = Math.cos(angleToCenter), sa = Math.sin(angleToCenter);
    return { x: landmarkPos.x + dx * ca + dz * sa, z: landmarkPos.z - dx * sa + dz * ca };
  };
  (built.extraColliders || []).forEach((ec) => {
    const p = rotOff(ec.dx, ec.dz);
    colliders.push({ x: p.x, z: p.z, r: ec.r });
  });

  // style-studio interactables at the boutique wardrobe & glow bar vanity
  if (built.wardOffset) {
    const p = rotOff(built.wardOffset.dx, built.wardOffset.dz);
    interactables.push({
      id: 'wardrobe', pos: new THREE.Vector3(p.x, 0, p.z), radius: 3.0,
      prompt: () => '👗 <b>Wardrobe</b> — open the Style Studio',
      available: () => true,
      action: () => toggleStyler(true),
    });
  }
  if (built.vanOffset) {
    const p = rotOff(built.vanOffset.dx, built.vanOffset.dz);
    interactables.push({
      id: 'vanity', pos: new THREE.Vector3(p.x, 0, p.z), radius: 3.0,
      prompt: () => '💄 <b>Vanity Mirror</b> — glam time',
      available: () => true,
      action: () => toggleStyler(true),
    });
  }

  // trivia kiosk on the ring
  const kg = new THREE.Group();
  const pedestal = cyl(0.55, 0.7, 0.9, 0xffffff, 14);
  pedestal.position.y = 0.45;
  kg.add(pedestal);

  const crystalMat = new THREE.MeshStandardMaterial({
    color: zone.color, roughness: 0.25,
    emissive: zone.color, emissiveIntensity: 0.55,
    transparent: true, opacity: 0.95,
  });
  const crystal = new THREE.Mesh(new THREE.OctahedronGeometry(0.55), crystalMat);
  crystal.scale.y = 1.5;
  crystal.position.y = 1.9;
  crystal.castShadow = true;
  kg.add(crystal);

  const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: makeGlowTexture('#ffffff'), color: zone.color, transparent: true, opacity: 0.6, depthWrite: false }));
  glow.scale.set(2.6, 2.6, 1);
  glow.position.y = 1.9;
  kg.add(glow);

  const ring = new THREE.Mesh(
    new THREE.RingGeometry(1.15, 1.5, 32),
    new THREE.MeshBasicMaterial({ color: zone.color, transparent: true, opacity: 0.5, depthWrite: false, side: THREE.DoubleSide })
  );
  ring.rotation.x = -Math.PI / 2;
  ring.position.y = 0.03;
  kg.add(ring);

  const label = makeLabelSprite(`${zone.emoji} ${zone.name}`, zone.accent);
  label.position.y = 3.3;
  kg.add(label);

  kg.position.set(pos.x, 0, pos.z);
  scene.add(kg);
  colliders.push({ x: pos.x, z: pos.z, r: 0.95 });

  const kiosk = { zone, group: kg, crystal, crystalMat, ring, glow, label, pos: new THREE.Vector3(pos.x, 0, pos.z), phase: rng() * 10 };
  kiosks.push(kiosk);

  interactables.push({
    id: `kiosk-${zone.id}`,
    pos: kiosk.pos,
    radius: 3.4,
    prompt: () => (kioskIsDone(kiosk)
      ? `${zone.emoji} <b>${zone.name}</b> — all done! 💛`
      : `${zone.emoji} <b>${zone.topic}</b> trivia`),
    available: () => !kioskIsDone(kiosk),
    action: () => openQuiz(kiosk),
  });
});

function kioskIsDone(k) {
  return state.answered[k.zone.id].length >= k.zone.questions.length;
}

function refreshKioskLook(k) {
  if (kioskIsDone(k)) {
    k.crystalMat.color.set(0xffd166);
    k.crystalMat.emissive.set(0xffd166);
    k.glow.material.color.set(0xffd166);
    if (!k.doneLabelSwapped) {
      k.doneLabelSwapped = true;
      const nl = makeLabelSprite(`✓ ${k.zone.name} 💛`, '#f5b93e');
      nl.position.copy(k.label.position);
      k.group.remove(k.label);
      k.group.add(nl);
      k.label = nl;
    }
  }
}

// ---------------------------------------------------------------------------
// Collectible stars
// ---------------------------------------------------------------------------
const stars = [];
{
  const starGeo = makeStarGeo();
  const starMat = new THREE.MeshStandardMaterial({ color: 0xffd166, roughness: 0.35, emissive: 0xaa7712, emissiveIntensity: 0.5 });
  let placed = 0, guard = 0;
  while (placed < STAR_COUNT && guard++ < 1200) {
    const a = rng() * Math.PI * 2;
    const r = 5 + Math.sqrt(rng()) * (WALK_R - 6);
    const x = Math.cos(a) * r, z = Math.sin(a) * r;
    if (colliders.some((c) => Math.hypot(x - c.x, z - c.z) < c.r + 0.8)) continue;
    if (stars.some((s) => Math.hypot(x - s.position.x, z - s.position.z) < 4)) continue;
    const m = new THREE.Mesh(starGeo, starMat);
    m.position.set(x, 1.1, z);
    m.userData.baseY = 1.1;
    m.userData.phase = rng() * 10;
    m.userData.idx = placed;
    stars.push(m);
    scene.add(m);
    placed++;
  }
}

// ---------------------------------------------------------------------------
// Character — fully customizable doll
// ---------------------------------------------------------------------------
const player = new THREE.Group();
scene.add(player);
let charParts = null;

function buildCharacter(look) {
  while (player.children.length) player.remove(player.children[0]);

  const g = new THREE.Group();
  const skin = new THREE.MeshStandardMaterial({ color: look.skin, roughness: 0.9 });
  const dress = new THREE.MeshStandardMaterial({ color: look.dressColor, roughness: 0.85 });
  const hair = new THREE.MeshStandardMaterial({ color: look.hairColor, roughness: 0.95 });

  // feet / shoes
  const feet = [];
  [-0.13, 0.13].forEach((x) => {
    const f = new THREE.Mesh(new THREE.SphereGeometry(0.14, 8, 6), new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.8 }));
    f.position.set(x, 0.13, 0);
    g.add(f); feet.push(f);
  });

  // dress styles
  let skirt;
  if (look.dressStyle === 'ballgown') {
    skirt = new THREE.Group();
    const gown = new THREE.Mesh(new THREE.ConeGeometry(0.62, 0.95, 18), dress);
    gown.position.y = 0;
    skirt.add(gown);
    const puff = new THREE.Mesh(new THREE.SphereGeometry(0.5, 14, 10), dress);
    puff.scale.set(1, 0.45, 1);
    puff.position.y = 0.42;
    skirt.add(puff);
    skirt.position.y = 0.55;
    skirt.children.forEach((m) => (m.castShadow = true));
  } else if (look.dressStyle === 'mini') {
    // Y2K mini: visible legs + short flared skirt
    [-0.12, 0.12].forEach((x) => {
      const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.065, 0.06, 0.42, 8), skin);
      leg.position.set(x, 0.42, 0);
      g.add(leg);
    });
    skirt = new THREE.Mesh(new THREE.ConeGeometry(0.4, 0.38, 14), dress);
    skirt.position.y = 0.76;
    skirt.castShadow = true;
  } else {
    skirt = new THREE.Mesh(new THREE.ConeGeometry(0.46, 0.62, 14), dress);
    skirt.position.y = 0.56;
    skirt.castShadow = true;
  }
  g.add(skirt);

  const torso = new THREE.Mesh(new THREE.SphereGeometry(0.26, 12, 10), dress);
  torso.scale.set(1, 1.15, 0.85);
  torso.position.y = 0.98;
  torso.castShadow = true;
  g.add(torso);

  const arms = [];
  [-1, 1].forEach((side) => {
    const pivot = new THREE.Group();
    pivot.position.set(side * 0.3, 1.14, 0);
    const sleeve = new THREE.Mesh(new THREE.SphereGeometry(0.11, 8, 6), dress);
    pivot.add(sleeve);
    const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.05, 0.42, 8), skin);
    arm.position.y = -0.24;
    pivot.add(arm);
    const hand = new THREE.Mesh(new THREE.SphereGeometry(0.07, 8, 6), skin);
    hand.position.y = -0.46;
    pivot.add(hand);
    g.add(pivot);
    arms.push(pivot);
  });

  // head
  const head = new THREE.Group();
  head.position.y = 1.62;
  const face = new THREE.Mesh(new THREE.SphereGeometry(0.31, 16, 12), skin);
  face.castShadow = true;
  head.add(face);

  // hair styles
  const hairBack = new THREE.Mesh(new THREE.SphereGeometry(0.335, 14, 10), hair);
  hairBack.position.set(0, 0.045, -0.055);
  hairBack.scale.set(1.02, 1.0, 0.98);
  head.add(hairBack);
  if (look.hairStyle === 'buns') {
    [-1, 1].forEach((side) => {
      const bun = new THREE.Mesh(new THREE.SphereGeometry(0.145, 10, 8), hair);
      bun.position.set(side * 0.27, 0.24, -0.05);
      head.add(bun);
    });
  } else if (look.hairStyle === 'ponytail') {
    const scrunchie = new THREE.Mesh(new THREE.TorusGeometry(0.075, 0.035, 8, 12), MAT.hotpink);
    scrunchie.position.set(0, 0.3, -0.18);
    scrunchie.rotation.x = 1.1;
    head.add(scrunchie);
    [[0, 0.22, -0.3, 0.13], [0, 0.05, -0.4, 0.11], [0, -0.14, -0.44, 0.095]].forEach(([x, y, z, r]) => {
      const seg = new THREE.Mesh(new THREE.SphereGeometry(r, 8, 6), hair);
      seg.position.set(x, y, z);
      head.add(seg);
    });
  } else if (look.hairStyle === 'long') {
    [-1, 1].forEach((side) => {
      const curtain = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.11, 0.62, 8), hair);
      curtain.position.set(side * 0.24, -0.22, -0.02);
      head.add(curtain);
    });
    const back = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.26, 0.6, 10), hair);
    back.position.set(0, -0.25, -0.16);
    head.add(back);
  } else if (look.hairStyle === 'bob') {
    const bob = new THREE.Mesh(new THREE.SphereGeometry(0.36, 14, 10), hair);
    bob.position.set(0, -0.02, -0.06);
    bob.scale.set(1.05, 1.1, 1.0);
    head.add(bob);
    // face window: re-add the face slightly forward
    face.position.z = 0.045;
  }

  // accessories
  if (look.accessory === 'bow') {
    const bow = new THREE.Group();
    const bowMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.85 });
    const knot = new THREE.Mesh(new THREE.SphereGeometry(0.05, 6, 5), bowMat);
    const bl = new THREE.Mesh(new THREE.ConeGeometry(0.075, 0.17, 6), bowMat);
    const br = bl.clone();
    bl.rotation.z = Math.PI / 2; bl.position.x = -0.1;
    br.rotation.z = -Math.PI / 2; br.position.x = 0.1;
    bow.add(knot, bl, br);
    bow.position.set(0.13, 0.31, 0.1);
    bow.rotation.y = 0.4;
    head.add(bow);
  } else if (look.accessory === 'tiara' || look.accessory === 'midnight') {
    const midnight = look.accessory === 'midnight';
    const bandMat = midnight
      ? new THREE.MeshStandardMaterial({ color: 0x3b3e8f, roughness: 0.3, metalness: 0.5, emissive: 0x1a1c50, emissiveIntensity: 0.6 })
      : MAT.gold;
    const band = new THREE.Mesh(new THREE.TorusGeometry(0.2, 0.03, 8, 16, Math.PI), bandMat);
    band.position.set(0, 0.22, 0.02);
    band.rotation.x = -1.25;
    head.add(band);
    [[-0.1, 0.08], [0, 0.14], [0.1, 0.08]].forEach(([x, h]) => {
      const spike = new THREE.Mesh(new THREE.ConeGeometry(0.028, h, 6), bandMat);
      spike.position.set(x, 0.32 + h / 2 - 0.05, 0.13);
      head.add(spike);
    });
    const gem = new THREE.Mesh(new THREE.OctahedronGeometry(0.045), new THREE.MeshStandardMaterial({
      color: midnight ? 0xff8fc4 : 0x9fd8ff, roughness: 0.2,
      emissive: midnight ? 0xff8fc4 : 0x9fd8ff, emissiveIntensity: 0.7,
    }));
    gem.position.set(0, 0.42, 0.14);
    head.add(gem);
  } else if (look.accessory === 'butterfly') {
    [-1, 1].forEach((side) => {
      const clip = new THREE.Group();
      const wingMat = new THREE.MeshBasicMaterial({ color: side < 0 ? 0x9fd8ff : 0xff8fc4, side: THREE.DoubleSide });
      const wg = new THREE.PlaneGeometry(0.09, 0.07);
      const wl = new THREE.Mesh(wg, wingMat); wl.position.x = -0.045; wl.rotation.y = 0.7;
      const wr = new THREE.Mesh(wg, wingMat); wr.position.x = 0.045; wr.rotation.y = -0.7;
      clip.add(wl, wr);
      clip.position.set(side * 0.22, 0.22, 0.16);
      head.add(clip);
    });
  } else if (look.accessory === 'headband') {
    const band = new THREE.Mesh(new THREE.TorusGeometry(0.31, 0.035, 8, 18, Math.PI), MAT.hotpink);
    band.position.set(0, 0.1, 0);
    band.rotation.x = -1.35;
    head.add(band);
  }

  // face: eyes, eyeshadow, blush, lips
  [-1, 1].forEach((side) => {
    const eye = new THREE.Mesh(new THREE.SphereGeometry(0.038, 8, 6), new THREE.MeshBasicMaterial({ color: 0x40282e }));
    eye.position.set(side * 0.115, 0.03, 0.275);
    head.add(eye);
    if (look.eyeshadow && look.eyeshadow !== 'none') {
      const shadow = new THREE.Mesh(new THREE.SphereGeometry(0.055, 8, 6), new THREE.MeshBasicMaterial({ color: look.eyeshadow }));
      shadow.position.set(side * 0.115, 0.065, 0.262);
      shadow.scale.set(1.15, 0.7, 0.4);
      head.add(shadow);
    }
    if (look.blush > 0) {
      const blush = new THREE.Mesh(new THREE.SphereGeometry(0.05, 8, 6), new THREE.MeshBasicMaterial({ color: 0xffa8bf, transparent: true, opacity: look.blush === 2 ? 0.95 : 0.55 }));
      blush.position.set(side * 0.2, -0.06, 0.22);
      blush.scale.set(look.blush === 2 ? 1.25 : 1, 0.6, 0.35);
      head.add(blush);
    }
  });
  const lipColor = look.lipstick && look.lipstick !== 'none' ? look.lipstick : 0xc9576b;
  const lipSize = look.lipstick && look.lipstick !== 'none' ? 0.02 : 0.014;
  const smile = new THREE.Mesh(
    new THREE.TorusGeometry(0.055, lipSize, 6, 10, Math.PI),
    new THREE.MeshBasicMaterial({ color: lipColor })
  );
  smile.position.set(0, -0.075, 0.285);
  smile.rotation.z = Math.PI;
  head.add(smile);
  g.add(head);

  // queen's crown (revealed when crowned) — above everything
  const crown = new THREE.Group();
  const band = new THREE.Mesh(new THREE.CylinderGeometry(0.19, 0.21, 0.1, 10), MAT.gold);
  crown.add(band);
  for (let i = 0; i < 5; i++) {
    const spike = new THREE.Mesh(new THREE.ConeGeometry(0.045, 0.14, 6), MAT.gold);
    const a = (i / 5) * Math.PI * 2;
    spike.position.set(Math.cos(a) * 0.17, 0.11, Math.sin(a) * 0.17);
    crown.add(spike);
  }
  crown.position.set(0, look.hairStyle === 'buns' || look.hairStyle === 'ponytail' ? 0.48 : 0.44, -0.02);
  crown.visible = state.crowned;
  head.add(crown);

  player.add(g);
  charParts = { g, head, arms, feet, skirt, crown };
}

buildCharacter(state.look);
player.position.set(0, 0, 6);

// ---------------------------------------------------------------------------
// Butterflies, clouds, sparkle field, café cat
// ---------------------------------------------------------------------------
const butterflies = [];
{
  const wingGeo = new THREE.PlaneGeometry(0.26, 0.2);
  const colors = [0xff8fc4, 0xcbb2ff, 0xfff3c9, 0xa8ecff];
  for (let i = 0; i < 9; i++) {
    const b = new THREE.Group();
    const mat = new THREE.MeshBasicMaterial({ color: colors[i % colors.length], side: THREE.DoubleSide, transparent: true, opacity: 0.92 });
    const wl = new THREE.Mesh(wingGeo, mat); wl.position.x = -0.12;
    const wr = new THREE.Mesh(wingGeo, mat); wr.position.x = 0.12;
    b.add(wl, wr);
    const ca = rng() * Math.PI * 2, cr = Math.sqrt(rng()) * 38;
    b.userData = {
      wl, wr,
      cx: Math.cos(ca) * cr, cz: Math.sin(ca) * cr,
      r: 4 + rng() * 9, speed: 0.25 + rng() * 0.3,
      phase: rng() * 20, h: 1.6 + rng() * 2.4,
    };
    scene.add(b);
    butterflies.push(b);
  }
}

const clouds = [];
{
  const cloudMat = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 1, transparent: true, opacity: 0.92 });
  const puffGeo = new THREE.SphereGeometry(1, 8, 6);
  for (let i = 0; i < 7; i++) {
    const c = new THREE.Group();
    const n = 3 + Math.floor(rng() * 3);
    for (let j = 0; j < n; j++) {
      const p = new THREE.Mesh(puffGeo, cloudMat);
      p.position.set((j - n / 2) * 2.2 + rng(), rng() * 0.8, (rng() - 0.5) * 2);
      p.scale.set(1.6 + rng() * 1.6, 1 + rng() * 0.5, 1.2 + rng());
      c.add(p);
    }
    c.userData = { r: 55 + rng() * 80, a: rng() * Math.PI * 2, speed: 0.008 + rng() * 0.012, h: 26 + rng() * 14 };
    scene.add(c);
    clouds.push(c);
  }
}

let sparkleField;
{
  const n = 130;
  const positions = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    const a = rng() * Math.PI * 2, r = Math.sqrt(rng()) * (ISLAND_R - 4);
    positions[i * 3] = Math.cos(a) * r;
    positions[i * 3 + 1] = 0.6 + rng() * 7;
    positions[i * 3 + 2] = Math.sin(a) * r;
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  const mat = new THREE.PointsMaterial({
    size: 0.5, map: sparkleTex, transparent: true, opacity: 0.85,
    depthWrite: false, blending: THREE.AdditiveBlending, color: 0xfff0f8, sizeAttenuation: true,
  });
  sparkleField = new THREE.Points(geo, mat);
  scene.add(sparkleField);
}

// Coco the cat — role-play guide by the café
const CAT_LINES = [
  () => `Meow~ Welcome home, ${state.name || 'dreamgirl'}! The kingdom missed you. 💖`,
  () => 'The castle tower has been locked since New Year\'s Eve 1999… spooky, right? 🏰',
  () => 'Psst — the magic mirror in the tower loves things with wings. Just saying. 🦋',
  () => 'Collect ✨ stars and you can redecorate the WHOLE island. I\'d love a flamingo friend. 🦩',
  () => 'You look STUNNING today. The photobooth agrees. 📸',
  () => 'A little bird said answering trivia first-try earns bonus sparkles. ✨',
];
let catLineIdx = 0;
{
  const cafePos = zonePos[0].clone().normalize().multiplyScalar(RING_R + 5.5);
  const cat = new THREE.Group();
  const white = new THREE.MeshStandardMaterial({ color: 0xfffdf8, roughness: 0.95 });
  const body = new THREE.Mesh(new THREE.SphereGeometry(0.34, 12, 10), white);
  body.scale.set(1, 0.9, 1.2); body.position.y = 0.32; body.castShadow = true;
  const headM = new THREE.Mesh(new THREE.SphereGeometry(0.24, 12, 10), white);
  headM.position.set(0, 0.62, 0.3);
  const earGeo = new THREE.ConeGeometry(0.08, 0.14, 6);
  const earMat = new THREE.MeshStandardMaterial({ color: 0xffb7d9, roughness: 0.9 });
  [-1, 1].forEach((s) => {
    const ear = new THREE.Mesh(earGeo, earMat);
    ear.position.set(s * 0.13, 0.83, 0.28);
    cat.add(ear);
  });
  [-1, 1].forEach((s) => {
    const eye = new THREE.Mesh(new THREE.SphereGeometry(0.03, 6, 5), new THREE.MeshBasicMaterial({ color: 0x40282e }));
    eye.position.set(s * 0.09, 0.66, 0.51);
    cat.add(eye);
  });
  const tail = new THREE.Mesh(new THREE.ConeGeometry(0.07, 0.55, 6), white);
  tail.position.set(0, 0.5, -0.42);
  tail.rotation.x = -0.8;
  cat.add(body, headM, tail);
  cat.position.set(cafePos.x + 1.8, 0, cafePos.z + 1.2);
  cat.lookAt(0, 0, 0);
  scene.add(cat);
  colliders.push({ x: cat.position.x, z: cat.position.z, r: 0.5 });
  animatedBits.push((t) => { tail.rotation.z = Math.sin(t * 2.2) * 0.45; });

  interactables.push({
    id: 'cat',
    pos: cat.position.clone(),
    radius: 2.4,
    prompt: () => '🐈 Say hi to <b>Coco</b>',
    available: () => true,
    action: () => {
      toast(CAT_LINES[catLineIdx % CAT_LINES.length]());
      catLineIdx++;
      sfxClick();
    },
  });
}

// ---------------------------------------------------------------------------
// Particle bursts
// ---------------------------------------------------------------------------
const bursts = [];
function spawnBurst(pos, color = 0xffd166, count = 22) {
  const positions = new Float32Array(count * 3);
  const velocities = [];
  for (let i = 0; i < count; i++) {
    positions[i * 3] = pos.x; positions[i * 3 + 1] = pos.y; positions[i * 3 + 2] = pos.z;
    const a = Math.random() * Math.PI * 2, b = Math.random() * Math.PI - Math.PI / 2;
    const sp = 2 + Math.random() * 3;
    velocities.push(new THREE.Vector3(Math.cos(a) * Math.cos(b) * sp, Math.sin(b) * sp + 2.2, Math.sin(a) * Math.cos(b) * sp));
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  const mat = new THREE.PointsMaterial({
    size: 0.42, map: sparkleTex, transparent: true, opacity: 1,
    depthWrite: false, blending: THREE.AdditiveBlending, color,
  });
  const pts = new THREE.Points(geo, mat);
  scene.add(pts);
  bursts.push({ pts, velocities, life: 1 });
}

function updateBursts(dt) {
  for (let i = bursts.length - 1; i >= 0; i--) {
    const b = bursts[i];
    b.life -= dt * 1.4;
    if (b.life <= 0) {
      scene.remove(b.pts);
      b.pts.geometry.dispose();
      b.pts.material.dispose();
      bursts.splice(i, 1);
      continue;
    }
    const arr = b.pts.geometry.attributes.position.array;
    for (let j = 0; j < b.velocities.length; j++) {
      const v = b.velocities[j];
      v.y -= 6 * dt;
      arr[j * 3] += v.x * dt;
      arr[j * 3 + 1] += v.y * dt;
      arr[j * 3 + 2] += v.z * dt;
    }
    b.pts.geometry.attributes.position.needsUpdate = true;
    b.pts.material.opacity = Math.min(1, b.life * 1.6);
  }
}

// ---------------------------------------------------------------------------
// Audio (all synthesized)
// ---------------------------------------------------------------------------
const audio = { ctx: null, master: null, musicGain: null, delay: null };

function initAudio() {
  if (audio.ctx) return;
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    audio.ctx = new Ctx();
    audio.master = audio.ctx.createGain();
    audio.master.gain.value = 0.9;
    audio.master.connect(audio.ctx.destination);
    audio.musicGain = audio.ctx.createGain();
    audio.musicGain.gain.value = state.musicOn ? 0.5 : 0;
    audio.musicGain.connect(audio.master);
    audio.delay = audio.ctx.createDelay(1);
    audio.delay.delayTime.value = 0.33;
    const fb = audio.ctx.createGain(); fb.gain.value = 0.3;
    audio.delay.connect(fb); fb.connect(audio.delay);
    audio.delay.connect(audio.musicGain);
    startMusic();
  } catch (e) { /* no audio — fine */ }
}

function note(freq, time, dur, { type = 'sine', gain = 0.12, dest = null, glideTo = null } = {}) {
  if (!audio.ctx) return;
  const o = audio.ctx.createOscillator();
  const g = audio.ctx.createGain();
  o.type = type;
  o.frequency.setValueAtTime(freq, time);
  if (glideTo) o.frequency.exponentialRampToValueAtTime(glideTo, time + dur);
  g.gain.setValueAtTime(0, time);
  g.gain.linearRampToValueAtTime(gain, time + 0.015);
  g.gain.exponentialRampToValueAtTime(0.0001, time + dur);
  o.connect(g);
  g.connect(dest || audio.master);
  o.start(time);
  o.stop(time + dur + 0.05);
}

function playTone(freq, dur = 0.2) {
  if (!audio.ctx) return;
  note(freq, audio.ctx.currentTime, dur, { gain: 0.1 });
}

const NOTES = { C4: 261.63, D4: 293.66, E4: 329.63, F4: 349.23, G4: 392, A4: 440, B4: 493.88, C5: 523.25, D5: 587.33, E5: 659.25, G5: 783.99, A5: 880, C6: 1046.5, E6: 1318.5, G6: 1568 };

function sfxCollect() {
  if (!audio.ctx) return;
  const t = audio.ctx.currentTime;
  note(NOTES.E6, t, 0.18, { gain: 0.1 });
  note(NOTES.G6, t + 0.07, 0.26, { gain: 0.09 });
}
function sfxCorrect() {
  if (!audio.ctx) return;
  const t = audio.ctx.currentTime;
  [NOTES.C5, NOTES.E5, NOTES.G5, NOTES.C6].forEach((f, i) => note(f, t + i * 0.09, 0.3, { gain: 0.11 }));
}
function sfxWrong() {
  if (!audio.ctx) return;
  const t = audio.ctx.currentTime;
  note(311.13, t, 0.3, { gain: 0.08, glideTo: 261.63, type: 'triangle' });
}
function sfxOpen() {
  if (!audio.ctx) return;
  const t = audio.ctx.currentTime;
  note(NOTES.A4, t, 0.12, { gain: 0.06 });
  note(NOTES.D5, t + 0.06, 0.16, { gain: 0.06 });
}
function sfxClick() {
  if (!audio.ctx) return;
  note(NOTES.C6, audio.ctx.currentTime, 0.06, { gain: 0.04 });
}
function sfxFanfare() {
  if (!audio.ctx) return;
  const t = audio.ctx.currentTime;
  [NOTES.C5, NOTES.E5, NOTES.G5, NOTES.C6, NOTES.E6, NOTES.G6].forEach((f, i) => note(f, t + i * 0.11, 0.5, { gain: 0.1 }));
}

let musicTimer = null;
function startMusic() {
  if (!audio.ctx || musicTimer) return;
  const beat = 60 / 92;
  const chords = [
    [NOTES.C4, NOTES.E4, NOTES.G4],
    [NOTES.G4, NOTES.B4, NOTES.D4 * 2],
    [NOTES.A4, NOTES.C5, NOTES.E5],
    [NOTES.F4, NOTES.A4, NOTES.C5],
  ];
  const penta = [NOTES.C5, NOTES.D5, NOTES.E5, NOTES.G5, NOTES.A5, NOTES.C6];
  let nextBar = audio.ctx.currentTime + 0.1;
  let bar = 0;
  const schedule = () => {
    if (!audio.ctx) return;
    while (nextBar < audio.ctx.currentTime + 1.2) {
      const chord = chords[bar % 4];
      chord.forEach((f) => {
        note(f / 2, nextBar, beat * 4.2, { type: 'triangle', gain: 0.045, dest: audio.musicGain });
      });
      for (let s = 0; s < 8; s++) {
        if (Math.random() < 0.4) {
          const f = penta[Math.floor(Math.random() * penta.length)];
          note(f, nextBar + s * beat * 0.5, 0.32, { gain: 0.05, dest: audio.delay });
        }
      }
      nextBar += beat * 4;
      bar++;
    }
  };
  schedule();
  musicTimer = setInterval(schedule, 500);
}

function setMusic(on) {
  state.musicOn = on;
  document.getElementById('btn-music').textContent = on ? '🎵' : '🔇';
  if (audio.musicGain) {
    audio.musicGain.gain.linearRampToValueAtTime(on ? 0.5 : 0, audio.ctx.currentTime + 0.4);
  }
  saveGame();
}

// ---------------------------------------------------------------------------
// Input: keyboard, mouse orbit, touch joystick
// ---------------------------------------------------------------------------
const keys = {};
const isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
if (isTouch) document.body.classList.add('touch');

window.addEventListener('keydown', (e) => {
  if (e.repeat) return;
  // don't steal keys while typing in inputs
  if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
  keys[e.code] = true;
  if (e.code === 'Escape') { closeAllModals(); return; }
  if (!state.started || state.uiOpen) return;
  if (e.code === 'KeyE' || e.code === 'Enter') tryInteract();
});
window.addEventListener('keyup', (e) => { keys[e.code] = false; });
window.addEventListener('blur', () => { for (const k in keys) keys[k] = false; });

const cam = { yaw: 0, pitch: 0.42, dist: 9.5 };
let dragging = false, lastX = 0, lastY = 0, dragPointerId = null;

canvas.addEventListener('pointerdown', (e) => {
  if (isTouch && joyActive(e)) return;
  if (isDecorating()) return; // decorate mode owns clicks on the canvas
  dragging = true; dragPointerId = e.pointerId;
  lastX = e.clientX; lastY = e.clientY;
  canvas.setPointerCapture(e.pointerId);
});
canvas.addEventListener('pointermove', (e) => {
  if (!dragging || e.pointerId !== dragPointerId) return;
  const dx = e.clientX - lastX, dy = e.clientY - lastY;
  lastX = e.clientX; lastY = e.clientY;
  cam.yaw -= dx * 0.0052;
  cam.pitch = THREE.MathUtils.clamp(cam.pitch + dy * 0.004, 0.12, 1.25);
});
const endDrag = (e) => { if (e.pointerId === dragPointerId) { dragging = false; dragPointerId = null; } };
canvas.addEventListener('pointerup', endDrag);
canvas.addEventListener('pointercancel', endDrag);
canvas.addEventListener('wheel', (e) => {
  cam.dist = THREE.MathUtils.clamp(cam.dist + e.deltaY * 0.01, 4, 16);
}, { passive: true });

const joyEl = document.getElementById('joystick');
const stickEl = document.getElementById('stick');
const joy = { active: false, id: null, x: 0, y: 0 };
function joyActive(e) {
  const r = joyEl.getBoundingClientRect();
  return e.clientX >= r.left - 20 && e.clientX <= r.right + 20 && e.clientY >= r.top - 20 && e.clientY <= r.bottom + 20;
}
joyEl.addEventListener('pointerdown', (e) => {
  joy.active = true; joy.id = e.pointerId;
  joyEl.setPointerCapture(e.pointerId);
  moveStick(e);
});
joyEl.addEventListener('pointermove', (e) => { if (joy.active && e.pointerId === joy.id) moveStick(e); });
const joyEnd = (e) => {
  if (e.pointerId !== joy.id) return;
  joy.active = false; joy.id = null; joy.x = 0; joy.y = 0;
  stickEl.style.transform = 'translate(-50%, -50%)';
};
joyEl.addEventListener('pointerup', joyEnd);
joyEl.addEventListener('pointercancel', joyEnd);
function moveStick(e) {
  const r = joyEl.getBoundingClientRect();
  const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  let dx = (e.clientX - cx) / (r.width / 2), dy = (e.clientY - cy) / (r.height / 2);
  const len = Math.hypot(dx, dy);
  if (len > 1) { dx /= len; dy /= len; }
  joy.x = dx; joy.y = dy;
  stickEl.style.transform = `translate(calc(-50% + ${dx * 36}px), calc(-50% + ${dy * 36}px))`;
}

document.getElementById('btn-interact').addEventListener('click', () => tryInteract());

// ---------------------------------------------------------------------------
// Movement & camera
// ---------------------------------------------------------------------------
const vel = new THREE.Vector3();
let facing = 0;
let walkPhase = 0;
let poseMode = false;

function setPoseMode(on) {
  poseMode = on;
  if (on) {
    // camera stays on its current side (no clipping into scenery);
    // the character turns to face it instead — like a doll on display
    cam.dist = 4.6;
    cam.pitch = 0.22;
  } else {
    cam.dist = 9.5;
    cam.pitch = 0.42;
  }
}

function updatePlayer(dt) {
  let ix = 0, iz = 0;
  if (!state.uiOpen && state.started) {
    if (keys.KeyW || keys.ArrowUp) iz -= 1;
    if (keys.KeyS || keys.ArrowDown) iz += 1;
    if (keys.KeyA || keys.ArrowLeft) ix -= 1;
    if (keys.KeyD || keys.ArrowRight) ix += 1;
    if (joy.active) { ix += joy.x; iz += joy.y; }
  }
  const inputLen = Math.min(1, Math.hypot(ix, iz));
  const running = keys.ShiftLeft || keys.ShiftRight;
  const targetSpeed = inputLen * (running ? 8.6 : 5.4);

  let moveX = 0, moveZ = 0;
  if (inputLen > 0.01) {
    const s = Math.sin(cam.yaw), c = Math.cos(cam.yaw);
    moveX = (ix * c + iz * s) / inputLen;
    moveZ = (-ix * s + iz * c) / inputLen;
  }

  const accel = inputLen > 0.01 ? 22 : 16;
  vel.x = THREE.MathUtils.damp(vel.x, moveX * targetSpeed, accel / 4, dt);
  vel.z = THREE.MathUtils.damp(vel.z, moveZ * targetSpeed, accel / 4, dt);

  player.position.x += vel.x * dt;
  player.position.z += vel.z * dt;

  const PR = 0.45;
  for (const c of colliders) {
    if (!c.r) continue;
    const dx = player.position.x - c.x, dz = player.position.z - c.z;
    const d = Math.hypot(dx, dz);
    const min = c.r + PR;
    if (d < min && d > 0.0001) {
      player.position.x = c.x + (dx / d) * min;
      player.position.z = c.z + (dz / d) * min;
    }
  }
  const dc = Math.hypot(player.position.x, player.position.z);
  if (dc > WALK_R) {
    player.position.x *= WALK_R / dc;
    player.position.z *= WALK_R / dc;
  }

  const speed = Math.hypot(vel.x, vel.z);
  if (poseMode) {
    // always face the camera, even while the user orbits around
    facing = THREE.MathUtils.damp(facingLerpTarget(facing, cam.yaw), cam.yaw, 8, dt);
    player.rotation.y = facing;
  } else if (speed > 0.3) {
    facing = THREE.MathUtils.damp(facingLerpTarget(facing, Math.atan2(vel.x, vel.z)), Math.atan2(vel.x, vel.z), 12, dt);
    player.rotation.y = facing;
  }

  if (charParts) {
    walkPhase += dt * (4 + speed * 2.4);
    const w = Math.min(1, speed / 5.4);
    const { g, arms, feet, skirt, head } = charParts;
    g.position.y = Math.abs(Math.sin(walkPhase)) * 0.09 * w;
    arms[0].rotation.x = Math.sin(walkPhase) * 0.85 * w;
    arms[1].rotation.x = -Math.sin(walkPhase) * 0.85 * w;
    feet[0].position.z = Math.sin(walkPhase) * 0.16 * w;
    feet[1].position.z = -Math.sin(walkPhase) * 0.16 * w;
    feet[0].position.y = 0.13 + Math.max(0, Math.sin(walkPhase)) * 0.1 * w;
    feet[1].position.y = 0.13 + Math.max(0, -Math.sin(walkPhase)) * 0.1 * w;
    if (skirt.rotation) {
      skirt.rotation.y = Math.sin(walkPhase * 0.5) * 0.08 * w;
    }
    const idle = 1 - w;
    g.scale.y = 1 + Math.sin(perfTime * 2.1) * 0.012 * idle;
    head.rotation.z = Math.sin(perfTime * 0.9) * 0.05 * idle;
  }
}

function facingLerpTarget(from, to) {
  let d = to - from;
  while (d > Math.PI) { from += Math.PI * 2; d = to - from; }
  while (d < -Math.PI) { from -= Math.PI * 2; d = to - from; }
  return from;
}

const camTarget = new THREE.Vector3();
function updateCamera(dt) {
  const targetY = poseMode ? 1.15 : 2.1;
  camTarget.set(player.position.x, player.position.y + targetY, player.position.z);
  const cp = Math.cos(cam.pitch), sp = Math.sin(cam.pitch);
  const desired = new THREE.Vector3(
    camTarget.x + Math.sin(cam.yaw) * cp * cam.dist,
    camTarget.y + sp * cam.dist,
    camTarget.z + Math.cos(cam.yaw) * cp * cam.dist
  );
  const k = state.started ? 6 : 1.2;
  camera.position.x = THREE.MathUtils.damp(camera.position.x, desired.x, k, dt);
  camera.position.y = THREE.MathUtils.damp(camera.position.y, desired.y, k, dt);
  camera.position.z = THREE.MathUtils.damp(camera.position.z, desired.z, k, dt);
  camera.lookAt(camTarget);
  const speed = Math.hypot(vel.x, vel.z);
  const targetFov = 55 + THREE.MathUtils.clamp((speed - 5.5) * 2.2, 0, 7);
  const newFov = THREE.MathUtils.damp(camera.fov, targetFov, 4, dt);
  if (Math.abs(newFov - camera.fov) > 0.01) {
    camera.fov = newFov;
    camera.updateProjectionMatrix();
  }
}
camera.position.set(0, 8, 20);

// ---------------------------------------------------------------------------
// Interaction: nearest interactable + prompt
// ---------------------------------------------------------------------------
let nearThing = null;
const promptEl = document.getElementById('prompt');
const btnInteract = document.getElementById('btn-interact');

function updateInteraction() {
  let best = null, bestScore = Infinity;
  for (const it of interactables) {
    const d = Math.hypot(player.position.x - it.pos.x, player.position.z - it.pos.z);
    if (d < it.radius && d < bestScore) { best = it; bestScore = d; }
  }
  if (best !== nearThing) {
    nearThing = best;
    refreshPrompt();
  }
}

function refreshPrompt() {
  if (nearThing && !state.uiOpen && !isDecorating()) {
    const html = nearThing.prompt();
    promptEl.innerHTML = isTouch ? html : `<kbd>E</kbd> ${html}`;
    promptEl.classList.add('show');
    btnInteract.classList.toggle('show', nearThing.available());
  } else {
    promptEl.classList.remove('show');
    btnInteract.classList.remove('show');
  }
}

function clearNear() {
  nearThing = null;
  refreshPrompt();
}

function tryInteract() {
  if (!nearThing || state.uiOpen) return;
  if (!nearThing.available()) return;
  nearThing.action();
  refreshPrompt();
}

// ---------------------------------------------------------------------------
// Stars: collection
// ---------------------------------------------------------------------------
const collectAnims = [];
function updateStars(dt, t) {
  for (let i = stars.length - 1; i >= 0; i--) {
    const s = stars[i];
    if (!s.parent) continue;
    s.rotation.y = t * 1.6 + s.userData.phase;
    s.position.y = s.userData.baseY + Math.sin(t * 2 + s.userData.phase) * 0.18;
    if (state.started && !state.uiOpen) {
      const d = Math.hypot(player.position.x - s.position.x, player.position.z - s.position.z);
      if (d < 1.15) {
        state.collectedStars.push(s.userData.idx);
        state.stars += 1;
        spawnBurst(s.position.clone(), 0xffd166, 18);
        sfxCollect();
        collectAnims.push({ mesh: s, t: 0 });
        updateHUD();
        saveGame();
      }
    }
  }
  for (let i = collectAnims.length - 1; i >= 0; i--) {
    const a = collectAnims[i];
    a.t += dt * 3.5;
    const s = 1 - a.t;
    if (s <= 0) {
      scene.remove(a.mesh);
      collectAnims.splice(i, 1);
    } else {
      a.mesh.scale.setScalar(s);
      a.mesh.position.y += dt * 2.5;
    }
  }
}

function syncStarsWithSave() {
  stars.forEach((s) => {
    const collected = state.collectedStars.includes(s.userData.idx);
    if (collected && s.parent) scene.remove(s);
    if (!collected && !s.parent) {
      scene.add(s);
      s.scale.setScalar(1);
      s.position.y = s.userData.baseY;
    }
  });
}

// ---------------------------------------------------------------------------
// HUD / toast / confetti
// ---------------------------------------------------------------------------
const el = (id) => document.getElementById(id);

function updateHUD() {
  el('stat-hearts').textContent = heartsCount();
  el('stat-hearts-max').textContent = TOTAL_QUESTIONS;
  el('stat-stars').textContent = state.stars;
  const chips = el('zone-chips');
  chips.innerHTML = '';
  ZONES.forEach((z) => {
    const done = state.answered[z.id].length;
    const total = z.questions.length;
    const chip = document.createElement('div');
    chip.className = 'chip' + (done >= total ? ' done' : '');
    chip.innerHTML = `<span>${z.emoji}</span><span class="chip-name">${z.name}</span><span class="dots">${'●'.repeat(done)}${'○'.repeat(total - done)}</span>`;
    chips.appendChild(chip);
  });
  // castle chip
  const chip = document.createElement('div');
  chip.className = 'chip' + (state.escape.escaped ? ' done' : '');
  chip.innerHTML = `<span>🏰</span><span class="chip-name">Forgotten Tower</span><span class="dots">${state.escape.escaped ? '👑' : '🔒'}</span>`;
  chips.appendChild(chip);
}

let toastTimer = null;
function toast(msg, ms = 2600) {
  const t = el('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), ms);
}

function domConfetti(n = 60) {
  const colors = ['#ff2d95', '#a98bf5', '#ffd166', '#7fe3b3', '#ff9f70', '#fff', '#9fd8ff'];
  for (let i = 0; i < n; i++) {
    const bit = document.createElement('div');
    bit.className = 'confetti-bit';
    const size = 6 + Math.random() * 8;
    bit.style.cssText = `left:${Math.random() * 100}vw; top:-20px; width:${size}px; height:${size * (Math.random() > 0.5 ? 1 : 0.4)}px;` +
      `background:${colors[Math.floor(Math.random() * colors.length)]}; border-radius:${Math.random() > 0.5 ? '50%' : '2px'};`;
    document.body.appendChild(bit);
    bit.animate([
      { transform: 'translate(0,0) rotate(0deg)', opacity: 1 },
      { transform: `translate(${(Math.random() - 0.5) * 40}vw, ${100 + Math.random() * 20}vh) rotate(${360 + Math.random() * 720}deg)`, opacity: 0.9 },
    ], { duration: 2200 + Math.random() * 1800, easing: 'cubic-bezier(.2,.6,.4,1)' }).onfinish = () => bit.remove();
  }
}

// ---------------------------------------------------------------------------
// Quote of the day
// ---------------------------------------------------------------------------
function showQuote() {
  el('quote-text').textContent = `“${quoteOfTheDay()}”`;
  const d = new Date();
  el('quote-date').textContent = d.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
  el('quote-modal').classList.remove('hidden');
  state.uiOpen = true;
  state.lastQuoteDate = todayKey();
  saveGame();
  sfxOpen();
}
el('quote-close').addEventListener('click', closeQuote);
el('quote-ok').addEventListener('click', closeQuote);
el('quote-copy').addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(`${quoteOfTheDay()} ✨ — Dreamhouse Kingdom`);
    toast('Copied! Send it to your bestie 💌');
  } catch (e) { toast('Copy not allowed here — screenshot it! 💖'); }
});
function closeQuote() {
  el('quote-modal').classList.add('hidden');
  state.uiOpen = false;
}
el('btn-quote').addEventListener('click', () => { if (state.started && !state.uiOpen) showQuote(); });

// ---------------------------------------------------------------------------
// Quiz UI
// ---------------------------------------------------------------------------
let quizKiosk = null;
let quizQuestionIdx = -1;
let quizHadMiss = false;

function nextUnanswered(zone) {
  for (let i = 0; i < zone.questions.length; i++) {
    if (!state.answered[zone.id].includes(i)) return i;
  }
  return -1;
}

function openQuiz(kiosk) {
  quizKiosk = kiosk;
  const qi = nextUnanswered(kiosk.zone);
  if (qi < 0) return;
  state.uiOpen = true;
  sfxOpen();
  renderQuestion(qi);
  el('quiz').classList.remove('hidden');
  refreshPrompt();
}

function renderQuestion(qi) {
  const zone = quizKiosk.zone;
  quizQuestionIdx = qi;
  quizHadMiss = false;
  const q = zone.questions[qi];
  el('quiz-zone').textContent = `${zone.emoji} ${zone.name}`;
  el('quiz-topic').textContent = `${zone.topic} Trivia`;
  el('quiz-question').textContent = q.q;
  el('quiz-feedback').textContent = '';
  el('quiz-progress').textContent = `Question ${state.answered[zone.id].length + 1} of ${zone.questions.length} · first try = +3 ✨ bonus`;
  const wrap = el('quiz-answers');
  wrap.innerHTML = '';
  q.options.forEach((opt, i) => {
    const btn = document.createElement('button');
    btn.className = 'answer-btn';
    btn.innerHTML = `<span class="letter">${'ABCD'[i]}</span><span>${opt}</span>`;
    btn.addEventListener('click', () => answer(i, btn));
    wrap.appendChild(btn);
  });
}

function answer(i, btn) {
  const zone = quizKiosk.zone;
  const q = zone.questions[quizQuestionIdx];
  if (state.answered[zone.id].includes(quizQuestionIdx)) return;
  if (i === q.answer) {
    state.answered[zone.id].push(quizQuestionIdx);
    btn.classList.add('correct');
    [...el('quiz-answers').children].forEach((b) => (b.disabled = true));
    let bonus = '';
    if (!quizHadMiss) {
      state.stars += 3;
      bonus = ' · flawless! +3 ✨';
    }
    el('quiz-feedback').textContent = `Yes queen! 💖 +1 💗${bonus}`;
    sfxCorrect();
    domConfetti(36);
    spawnBurst(quizKiosk.crystal.getWorldPosition(new THREE.Vector3()), zone.color, 26);
    updateHUD();
    saveGame();
    refreshKioskLook(quizKiosk);

    const zoneDone = nextUnanswered(zone) < 0;
    const allDone = heartsCount() >= TOTAL_QUESTIONS;
    setTimeout(() => {
      if (allDone) {
        closeQuiz();
        crownThePlayer();
      } else if (zoneDone) {
        closeQuiz();
        toast(`${zone.emoji} ${zone.name} complete! 💛`);
      } else {
        renderQuestion(nextUnanswered(zone));
      }
    }, 1500);
  } else {
    quizHadMiss = true;
    btn.classList.add('wrong');
    btn.disabled = true;
    el('quiz-feedback').textContent = 'Not quite, bestie — try again! 💭';
    sfxWrong();
  }
}

function closeQuiz() {
  el('quiz').classList.add('hidden');
  state.uiOpen = false;
  clearNear();
}

function crownThePlayer() {
  state.crowned = true;
  if (charParts) charParts.crown.visible = true;
  saveGame();
  sfxFanfare();
  domConfetti(140);
  el('win-text').innerHTML = `${state.name ? `<b>${state.name}</b>, you` : 'You'} answered every single question — the kingdom officially crowns you.<br/>Your crown is now yours to wear forever. ✨`;
  setTimeout(() => {
    state.uiOpen = true;
    el('win').classList.remove('hidden');
  }, 600);
}

function closeAllModals() {
  ['quiz', 'win', 'help', 'quote-modal', 'escape', 'booth'].forEach((id) => el(id).classList.add('hidden'));
  if (!el('styler').classList.contains('hidden')) toggleStyler(false);
  state.uiOpen = false;
  clearNear();
}

el('quiz-close').addEventListener('click', closeQuiz);
el('win-close').addEventListener('click', () => { el('win').classList.add('hidden'); state.uiOpen = false; });
el('help-close').addEventListener('click', () => { el('help').classList.add('hidden'); state.uiOpen = false; });
el('btn-help').addEventListener('click', () => {
  const h = el('help');
  const showing = h.classList.contains('hidden');
  h.classList.toggle('hidden', !showing);
  state.uiOpen = showing;
});
el('btn-music').addEventListener('click', () => { initAudio(); setMusic(!state.musicOn); });

// ---------------------------------------------------------------------------
// Game snapshot for the photobooth
// ---------------------------------------------------------------------------
function snapGameFrame() {
  renderer.render(scene, camera);
  return renderer.domElement.toDataURL('image/jpeg', 0.92);
}

function nudgeCamera(dyaw, ddist) {
  cam.yaw += dyaw;
  cam.dist = THREE.MathUtils.clamp(cam.dist + ddist, 2.6, 16);
}

// ---------------------------------------------------------------------------
// Title screen
// ---------------------------------------------------------------------------
{
  const hasSave = loadGame();
  buildCharacter(state.look);

  const nameInput = el('name-input');
  nameInput.value = state.name;

  document.querySelectorAll('.vibe').forEach((v) => {
    v.addEventListener('click', () => {
      document.querySelectorAll('.vibe').forEach((x) => x.classList.remove('selected'));
      v.classList.add('selected');
      Object.assign(state.look, VIBE_PRESETS[v.dataset.vibe] || {});
      buildCharacter(state.look);
    });
  });

  const hasProgress = hasSave && (heartsCount() > 0 || state.collectedStars.length > 0 || state.stars > 0 || state.escape.escaped);
  if (hasProgress) {
    el('btn-continue').style.display = 'inline-block';
    el('btn-start').textContent = 'Start a new story ✨';
  }

  el('btn-start').addEventListener('click', () => {
    state.name = nameInput.value.trim();
    ZONES.forEach((z) => (state.answered[z.id] = []));
    state.collectedStars = [];
    state.stars = 0;
    state.crowned = false;
    state.escape = { solved: {}, escaped: false };
    state.unlocks = { midnight: false };
    state.decorations.forEach((d, i) => { if (d && d.colliderIdx !== undefined) colliders[d.colliderIdx].r = 0; });
    // remove already-built decoration meshes by reloading their groups is handled on next boot;
    // simplest: hard reset requires page state — hide via scene removal
    scene.children.filter((o) => o.userData && o.userData.decorIdx !== undefined).forEach((o) => scene.remove(o));
    state.decorations = [];
    if (charParts) charParts.crown.visible = false;
    syncStarsWithSave();
    kiosks.forEach((k) => {
      k.crystalMat.color.set(k.zone.color);
      k.crystalMat.emissive.set(k.zone.color);
      k.glow.material.color.set(k.zone.color);
    });
    saveGame();
    startGame(true);
  });
  el('btn-continue').addEventListener('click', () => {
    state.name = nameInput.value.trim() || state.name;
    syncStarsWithSave();
    kiosks.forEach(refreshKioskLook);
    if (charParts) charParts.crown.visible = state.crowned;
    saveGame();
    startGame(false);
  });

  if (isTouch) {
    el('title-controls').textContent = 'joystick to walk · drag to look · 💬 to interact';
  }
}

function startGame(fresh) {
  initAudio();
  setMusic(state.musicOn);
  state.started = true;
  updateHUD();
  el('title-screen').classList.add('hidden');
  const hello = state.name ? `Welcome, ${state.name}! 💖` : 'Welcome to Dreamhouse Kingdom! 💖';
  toast(`${hello} Find the glowing crystals & the castle!`, 3400);
  // quote of the day — once per day, shortly after entering
  if (state.lastQuoteDate !== todayKey()) {
    setTimeout(() => { if (!state.uiOpen) showQuote(); }, 3800);
  }
}

// ---------------------------------------------------------------------------
// Performance: FPS + adaptive quality
// ---------------------------------------------------------------------------
let fpsAvg = 60;
let fpsFrames = 0;
let fpsWindowStart = performance.now();
let lowFpsStrikes = 0;
const fpsEl = document.getElementById('fps');
const debugMode = new URLSearchParams(location.search).has('debug');
if (debugMode) fpsEl.style.display = 'block';

function updatePerf(now) {
  fpsFrames++;
  const elapsed = now - fpsWindowStart;
  if (elapsed < 2000) return;
  fpsAvg = (fpsFrames * 1000) / elapsed;
  fpsFrames = 0;
  fpsWindowStart = now;

  if (fpsAvg < 38 && !debugMode) {
    lowFpsStrikes++;
    if (pixelRatio > 1) {
      pixelRatio = Math.max(1, pixelRatio - 0.35);
      renderer.setPixelRatio(pixelRatio);
    } else if (lowFpsStrikes >= 3 && sun.castShadow) {
      sun.castShadow = false;
    }
  } else {
    lowFpsStrikes = 0;
  }
  if (debugMode) fpsEl.textContent = `${fpsAvg.toFixed(0)} fps · dpr ${pixelRatio.toFixed(2)} · draws ${renderer.info.render.calls}`;
}

// ---------------------------------------------------------------------------
// Game context shared with feature modules
// ---------------------------------------------------------------------------
const G = {
  THREE, scene, camera, renderer, player, ground,
  state, colliders,
  save: saveGame,
  toast,
  confetti: domConfetti,
  updateHUD,
  clearNear,
  applyLook: () => buildCharacter(state.look),
  setPoseMode,
  snapGameFrame,
  nudgeCamera,
  spawnBurst,
  makeHeartMesh,
  makeStarGeo,
  playTone,
  sfx: { click: sfxClick, open: sfxOpen, collect: sfxCollect, correct: sfxCorrect, wrong: sfxWrong, fanfare: sfxFanfare },
};

initCustomizer(G);
initEscape(G);
initPhotobooth(G);
initDecorate(G);

// Fade name labels out near the camera and fully hide them when faded —
// a sprite centered behind the near plane would otherwise smear across the screen.
const labelTmp = new THREE.Vector3();
function fadeLabel(label, x, y, z) {
  const d = camera.position.distanceTo(labelTmp.set(x, y, z));
  const op = THREE.MathUtils.clamp((d - 2.5) / 3.5, 0, 1);
  label.material.opacity = op;
  label.visible = op > 0.02;
}

// ---------------------------------------------------------------------------
// Main loop — fixed-timestep simulation
// ---------------------------------------------------------------------------
const STEP = 1 / 60;
let perfTime = 0;
let acc = 0;
let lastT = performance.now();

function simulate(dt) {
  perfTime += dt;
  const t = perfTime;

  updatePlayer(dt);
  updateCamera(dt);
  updateInteraction();
  updateStars(dt, t);
  updateBursts(dt);
  updateDecorations(t);

  for (const k of kiosks) {
    k.crystal.position.y = 1.9 + Math.sin(t * 1.5 + k.phase) * 0.14;
    k.crystal.rotation.y = t * 0.9 + k.phase;
    const pulse = 0.45 + Math.sin(t * 2.4 + k.phase) * 0.18;
    k.ring.material.opacity = kioskIsDone(k) ? 0.25 : pulse;
    k.glow.material.opacity = kioskIsDone(k) ? 0.35 : 0.45 + Math.sin(t * 2.4 + k.phase) * 0.15;
    fadeLabel(k.label, k.pos.x, k.label.position.y, k.pos.z);
  }
  // interactable label fade (castle / booth / well share the same trick)
  for (const it of interactables) {
    if (it.label) fadeLabel(it.label, it.label.position.x, it.label.position.y, it.label.position.z);
  }

  for (const b of butterflies) {
    const u = b.userData;
    const a = t * u.speed + u.phase;
    b.position.set(u.cx + Math.cos(a) * u.r, u.h + Math.sin(t * 1.3 + u.phase) * 0.5, u.cz + Math.sin(a) * u.r);
    b.rotation.y = -a;
    const flap = 0.4 + Math.abs(Math.sin(t * 11 + u.phase)) * 0.9;
    u.wl.rotation.y = flap;
    u.wr.rotation.y = -flap;
  }

  for (const c of clouds) {
    c.userData.a += c.userData.speed * dt;
    c.position.set(Math.cos(c.userData.a) * c.userData.r, c.userData.h, Math.sin(c.userData.a) * c.userData.r);
  }

  sparkleField.rotation.y = t * 0.01;
  sparkleField.material.opacity = 0.6 + Math.sin(t * 1.7) * 0.25;

  for (const fn of animatedBits) fn(t);
}

function tick(now) {
  requestAnimationFrame(tick);
  let frame = (now - lastT) / 1000;
  lastT = now;
  if (frame > 0.25) frame = 0.25;
  acc += frame;
  let steps = 0;
  while (acc >= STEP && steps < 8) {
    simulate(STEP);
    acc -= STEP;
    steps++;
  }
  if (acc >= STEP) acc = 0;

  updatePerf(now);
  renderer.render(scene, camera);
}
requestAnimationFrame(tick);
updateHUD();

// ---------------------------------------------------------------------------
// Test hooks (used by automated checks; harmless in production)
// ---------------------------------------------------------------------------
window.__game = {
  state,
  keys,
  vel,
  cam,
  player,
  kiosks,
  interactables,
  get fps() { return fpsAvg; },
  get hearts() { return heartsCount(); },
  get draws() { return renderer.info.render.calls; },
  warp(x, z) { player.position.set(x, 0, z); vel.set(0, 0, 0); },
  interact: tryInteract,
  openZone(id) { const k = kiosks.find((k) => k.zone.id === id); if (k) openQuiz(k); },
  openEscape,
  openBooth,
  toggleStyler,
  toggleDecorate,
  showQuote,
  snapGameFrame,
};
