import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

interface Index {
  tag: string;
  units_per_um: number;
  die_area_dbu: [number, number, number, number];
  stack: Record<string, { base_um: number; thickness_um: number }>;
  default_widths_um: Record<string, number>;
  cell_height_um: number;
  macro: { name: string; origin_dbu: [number, number]; size_um: [number, number];
           pins: { name: string; layer: string; rects: number[][] }[] };
  files: { name: string; bytes: number }[];
}

const LAYERS = ["li1", "met1", "met2", "met3", "met4", "met5"] as const;
const CUTS = ["mcon", "via", "via2", "via3", "via4"] as const;
/* restrained warm-to-cool ramp */
const LCOLOR: Record<string, number> = {
  li1: 0xc9a24a, met1: 0xbd8a55, met2: 0xa07f6f, met3: 0x7d7f96, met4: 0x59789c, met5: 0x3a6a8d,
};
const CCOLOR = [0x8f959d, 0x7a8a70, 0xb08a4a, 0x8a6f8f, 0x3f464d, 0x4a5a66];
const CNAMES = ["logic", "ff", "diode", "clk", "fill", "macro"];

async function fetchI32(base: string, name: string): Promise<Int32Array> {
  const r = await fetch(`${base}/${name}`);
  if (!r.ok) throw new Error(`${name}: ${r.status}`);
  let buf = await r.arrayBuffer();
  // Some hosts serve .gz with Content-Encoding: gzip and the browser has already
  // decompressed the body. Only decompress when the gzip magic bytes are present.
  const b = new Uint8Array(buf);
  if (b[0] === 0x1f && b[1] === 0x8b) {
    buf = await new Response(
      new Blob([buf]).stream().pipeThrough(new DecompressionStream("gzip")),
    ).arrayBuffer();
  }
  return new Int32Array(buf);
}

/** Merge axis-aligned boxes (x0,y0,x1,y1 in DBU) into one indexed geometry at height z..z+t. */
function layerGeom(i32: Int32Array, upm: number, z0: number, t: number): THREE.BufferGeometry {
  const n = i32.length / 4;
  const pos = new Float32Array(n * 8 * 3);
  const idx = new Uint32Array(n * 36);
  for (let i = 0; i < n; i++) {
    const x0 = i32[i * 4]! / upm, y0 = i32[i * 4 + 1]! / upm;
    const x1 = i32[i * 4 + 2]! / upm, y1 = i32[i * 4 + 3]! / upm;
    const v = i * 24, z1 = z0 + t;
    // 8 corners: bottom 0-3, top 4-7  (y-up: y coord = z metal height)
    const P = [
      x0, z0, y0, x1, z0, y0, x1, z0, y1, x0, z0, y1,
      x0, z1, y0, x1, z1, y0, x1, z1, y1, x0, z1, y1,
    ];
    pos.set(P, v);
    const b = i * 8, d = i * 36;
    const F = [
      0, 3, 2, 0, 2, 1,       // bottom (-y)
      4, 5, 6, 4, 6, 7,       // top (+y)
      0, 1, 5, 0, 5, 4,       // -z side
      2, 3, 7, 2, 7, 6,       // +z side
      1, 2, 6, 1, 6, 5,       // +x side
      3, 0, 4, 3, 4, 7,       // -x side
    ];
    for (let k = 0; k < 36; k++) idx[d + k] = b + F[k]!;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setIndex(new THREE.BufferAttribute(idx, 1));
  g.computeVertexNormals();
  return g;
}

/** Via points (x,y DBU pairs) as small boxes spanning the cut layer. */
function viaGeom(i32: Int32Array, upm: number, z0: number, t: number, w: number): THREE.BufferGeometry {
  const n = i32.length / 2;
  const boxes = new Int32Array(n * 4);
  const hw = w * upm / 2;
  for (let i = 0; i < n; i++) {
    const x = i32[i * 2]!, y = i32[i * 2 + 1]!;
    boxes.set([x - hw, y - hw, x + hw, y + hw], i * 4);
  }
  return layerGeom(boxes, upm, z0, t);
}

export interface Labels {
  shown: string; power: string; cells: string;
  ff: string; diode: string; clk: string; fill: string; macro: string;
  grpLayers: string; grpCells: string; scale: string;
  [k: string]: string;
}

export async function start(
  stage: HTMLElement, ui: HTMLElement, url: string,
  L: Labels,
): Promise<void> {
  const idx: Index = await (await fetch(`${url}/index.json`)).json();
  const upm = idx.units_per_um;
  const [dx0, dy0, dx1, dy1] = idx.die_area_dbu.map((v) => v / upm) as [number, number, number, number];
  const DW = dx1 - dx0, DH = dy1 - dy0;
  const cx = (dx0 + dx1) / 2, cz = (dy0 + dy1) / 2;

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.domElement.className = "chip3d-canvas";
  const poster = stage.querySelector<HTMLElement>(".chip3d-poster");
  poster?.remove();
  stage.prepend(renderer.domElement);
  ui.hidden = false;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0e1114);
  scene.add(new THREE.AmbientLight(0xffffff, 0.75));
  const dl = new THREE.DirectionalLight(0xffffff, 1.4);
  dl.position.set(DW * 1.2, 400, DH * 0.6);
  scene.add(dl);
  const dl2 = new THREE.DirectionalLight(0x90a4b8, 0.5);
  dl2.position.set(-DW, 300, -DH);
  scene.add(dl2);

  const world = new THREE.Group();
  scene.add(world);

  const camera = new THREE.PerspectiveCamera(45, 16 / 9, 1, 20000);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = false;
  controls.zoomToCursor = true;

  /* ---- build meshes ---- */
  const groups = new Map<string, THREE.Object3D>();
  const counts = new Map<string, number>();
  const mat = (c: number) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.85, metalness: 0.15 });

  const fileOf = (n: string) => idx.files.some((f) => f.name === n);

  const jobs = LAYERS.map(async (l) => {
    const nm = `wire_${l}.i32.gz`;
    if (!fileOf(nm)) return;
    const arr = await fetchI32(url, nm);
    const s = idx.stack[l]!;
    const mesh = new THREE.Mesh(layerGeom(arr, upm, s.base_um, s.thickness_um), mat(LCOLOR[l]!));
    groups.set(l, mesh); counts.set(l, arr.length / 4); world.add(mesh);
  });
  // power: merge all swire layers into one mesh
  jobs.push((async () => {
    const parts: THREE.BufferGeometry[] = [];
    let n = 0;
    for (const l of LAYERS) {
      const nm = `swire_${l}.i32.gz`;
      if (!fileOf(nm)) continue;
      const arr = await fetchI32(url, nm);
      if (!arr.length) continue;
      n += arr.length / 4;
      const s = idx.stack[l]!;
      parts.push(layerGeom(arr, upm, s.base_um, s.thickness_um));
    }
    if (!parts.length) return;
    const merged = mergeGeos(parts);
    const mesh = new THREE.Mesh(merged, mat(0x9a7f3f));
    groups.set("power", mesh); counts.set("power", n); world.add(mesh);
  })());
  // vias: one merged mesh
  jobs.push((async () => {
    const parts: THREE.BufferGeometry[] = [];
    let n = 0;
    for (const c of CUTS) {
      const nm = `via_${c}.i32.gz`;
      if (!fileOf(nm)) continue;
      const arr = await fetchI32(url, nm);
      if (!arr.length) continue;
      n += arr.length / 2;
      const s = idx.stack[c]!;
      parts.push(viaGeom(arr, upm, s.base_um, s.thickness_um, 0.15));
    }
    if (!parts.length) return;
    const mesh = new THREE.Mesh(mergeGeos(parts), mat(0x6f6a5e));
    groups.set("vias", mesh); counts.set("vias", n); world.add(mesh);
  })());
  // cells: instanced boxes per class
  jobs.push((async () => {
    if (!fileOf("comps.i32.gz")) return;
    const arr = await fetchI32(url, "comps.i32.gz");
    const n = arr.length / 5;
    const per: number[][] = [[], [], [], [], [], []];
    for (let i = 0; i < n; i++) per[arr[i * 5 + 4]!]!.push(i);
    for (let c = 0; c < 5; c++) {
      const list = per[c]!;
      if (!list.length) continue;
      const im = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), mat(CCOLOR[c]!), list.length);
      const m4 = new THREE.Matrix4();
      list.forEach((i, k) => {
        const x = arr[i * 5]! / upm, y = arr[i * 5 + 1]! / upm;
        const w = arr[i * 5 + 2]! / upm, h = arr[i * 5 + 3]! / upm;
        m4.makeScale(w, idx.cell_height_um, h);
        m4.setPosition(x + w / 2, idx.cell_height_um / 2, y + h / 2);
        im.setMatrixAt(k, m4);
      });
      im.count = list.length;
      const key = `cells:${CNAMES[c]}`;
      groups.set(key, im); counts.set(key, list.length); world.add(im);
    }
  })());
  await Promise.all(jobs);

  /* ---- macro box + pins + label ---- */
  const mo = idx.macro;
  const mx = mo.origin_dbu[0] / upm, my = mo.origin_dbu[1] / upm;
  const mMesh = new THREE.Mesh(
    new THREE.BoxGeometry(mo.size_um[0], idx.cell_height_um * 1.2, mo.size_um[1]),
    new THREE.MeshStandardMaterial({ color: 0x3d4750, roughness: 0.9 }),
  );
  mMesh.position.set(mx + mo.size_um[0] / 2, idx.cell_height_um * 0.6, my + mo.size_um[1] / 2);
  world.add(mMesh);
  const pinGeos: THREE.BufferGeometry[] = [];
  const pw = 0.4 * upm;
  for (const p of mo.pins) {
    const s = idx.stack[p.layer];
    const z = s ? s.base_um + s.thickness_um : idx.cell_height_um;
    const ints = new Int32Array(p.rects.length * 4);
    p.rects.forEach((r, i) => ints.set(
      [(mx + r[0]!) * upm - pw, (my + r[1]!) * upm - pw, (mx + r[2]!) * upm + pw, (my + r[3]!) * upm + pw], i * 4));
    pinGeos.push(layerGeom(ints, upm, z, 0.6));
  }
  if (pinGeos.length) world.add(new THREE.Mesh(mergeGeos(pinGeos), mat(0xd0b050)));
  const labelEl = document.createElement("div");
  labelEl.className = "chip3d-macro-label";
  labelEl.textContent = L.macro;
  stage.append(labelEl);
  const labelPos = new THREE.Vector3(
    mx + mo.size_um[0] / 2, idx.cell_height_um * 1.2 + 6, my + mo.size_um[1] / 2);
  const scaleEl = document.createElement("div");
  scaleEl.className = "chip3d-scalebar";
  scaleEl.innerHTML = `<span class="txt"></span><div class="bar"></div>`;
  stage.append(scaleEl);
  const scaleTxt = scaleEl.querySelector<HTMLElement>(".txt")!;
  const scaleBar = scaleEl.querySelector<HTMLElement>(".bar")!;

  /* die outline */
  const dieGeo = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(dx0, 0, dy0), new THREE.Vector3(dx1, 0, dy0),
    new THREE.Vector3(dx1, 0, dy1), new THREE.Vector3(dx0, 0, dy1), new THREE.Vector3(dx0, 0, dy0),
  ]);
  world.add(new THREE.Line(dieGeo, new THREE.LineBasicMaterial({ color: 0x555c64 })));

  /* ---- controls ui ---- */
  const layerBox = ui.querySelector<HTMLElement>("[data-layers]")!;
  const readout = ui.querySelector<HTMLElement>("[data-readout]")!;
  // canonical display order: metals low-to-high, then power, vias, cells
  const order = [...LAYERS, "power", "vias", ...CNAMES.slice(0, 5).map((n) => `cells:${n}`)];
  const keys = order.filter((k) => groups.has(k));
  const pretty = (k: string) =>
    k === "power" ? L.power : k === "vias" ? "vias" : k.startsWith("cells:")
      ? `${L.cells}: ${L[k.slice(6)] ?? k.slice(6)}` : k;
  const shown = new Set(keys);
  const mkGroup = (title: string, ks: string[]) => {
    const g = document.createElement("div");
    g.className = "chip3d-grp";
    const h = document.createElement("span");
    h.className = "chip3d-grplabel";
    h.textContent = title;
    g.append(h);
    for (const k of ks) {
      const lab = document.createElement("label");
      lab.className = "chip3d-ly";
      const cb = document.createElement("input");
      cb.type = "checkbox"; cb.checked = true;
      cb.addEventListener("change", () => {
        const obj = groups.get(k)!;
        obj.visible = cb.checked;
        if (cb.checked) shown.add(k); else shown.delete(k);
        updateReadout(); render();
      });
      lab.append(cb, document.createTextNode(pretty(k)));
      g.append(lab);
    }
    layerBox.append(g);
  };
  mkGroup(L.grpLayers, keys.filter((k) => !k.startsWith("cells:")));
  const cellKeys = keys.filter((k) => k.startsWith("cells:"));
  if (cellKeys.length) mkGroup(L.grpCells, cellKeys);
  function updateReadout() {
    const names = keys.filter((k) => shown.has(k)).map(pretty);
    const segs = keys.filter((k) => shown.has(k)).reduce((s, k) => s + (counts.get(k) ?? 0), 0);
    readout.textContent = `${L.shown}: ${names.join(", ")} — ${segs.toLocaleString()} drawn items`;
  }
  updateReadout();

  /* ---- camera presets ---- */
  // distance so the die spans ~85% of the stage width: half-width / (tan(hfov) * 0.85)
  const hfov = Math.atan(Math.tan((camera.fov * Math.PI / 180) / 2) * (16 / 9));
  // use the die's nearest-corner distance so the apparent span lands ~85% of stage width
  const dDie = (DW / 2) / (Math.tan(hfov) * 0.80);
  const diePos = new THREE.Vector3(
    cx, dDie * Math.sin(Math.PI / 6), cz + dDie * Math.cos(Math.PI / 6));
  const presets: Record<string, [THREE.Vector3, THREE.Vector3]> = {
    die: [diePos, new THREE.Vector3(cx, 0, cz)],
    macro: [new THREE.Vector3(mx + mo.size_um[0] / 2 + 120, 260, my + mo.size_um[1] + 320),
            new THREE.Vector3(mx + mo.size_um[0] / 2, 0, my + mo.size_um[1] / 2)],
    rows: [new THREE.Vector3(dx0 + DW * 0.55, 170, dy0 + DH * 0.98),
           new THREE.Vector3(dx0 + DW * 0.55, 0, dy0 + DH * 0.45)],
    route: [new THREE.Vector3(dx0 + DW * 0.62, 90, dy0 + DH * 0.62),
            new THREE.Vector3(dx0 + DW * 0.55, 0, dy0 + DH * 0.5)],
  };
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  let anim: number | null = null;
  function flyTo(p: THREE.Vector3, t: THREE.Vector3) {
    if (anim) cancelAnimationFrame(anim);
    if (reduced) { camera.position.copy(p); controls.target.copy(t); updateAndRender(); return; }
    const p0 = camera.position.clone(), t0 = controls.target.clone(), t0m = performance.now();
    const step = (now: number) => {
      const k = Math.min(1, (now - t0m) / 300);
      const e = 1 - (1 - k) * (1 - k);
      camera.position.lerpVectors(p0, p, e);
      controls.target.lerpVectors(t0, t, e);
      updateAndRender();
      if (k < 1) anim = requestAnimationFrame(step); else anim = null;
    };
    anim = requestAnimationFrame(step);
  }
  ui.querySelectorAll<HTMLButtonElement>("[data-preset]").forEach((b) =>
    b.addEventListener("click", () => {
      const [p, tgt] = presets[b.dataset.preset!]!;
      flyTo(p, tgt);
    }));
  const z10 = ui.querySelector<HTMLInputElement>("[data-z10]")!;
  z10.addEventListener("change", () => { world.scale.y = z10.checked ? 10 : 1; render(); });

  /* ---- sizing / rendering ---- */
  function resize() {
    const w = stage.clientWidth, h = Math.max(260, Math.min(stage.clientWidth * 9 / 16, innerWidth * 0.8));
    renderer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    render();
  }
  new ResizeObserver(resize).observe(stage);

  let onScreen = true;
  new IntersectionObserver((es) => { onScreen = es[0]!.isIntersecting; }).observe(renderer.domElement);
  const niceSteps = [1, 2, 5];
  function updateOverlays() {
    // macro label follows the projected macro-centre point
    const v = labelPos.clone().applyMatrix4(world.matrixWorld).project(camera);
    if (v.z > 1) {
      labelEl.hidden = true;
    } else {
      labelEl.hidden = false;
      labelEl.style.left = `${((v.x + 1) / 2 * renderer.domElement.clientWidth).toFixed(1)}px`;
      labelEl.style.top = `${((-v.y + 1) / 2 * renderer.domElement.clientHeight).toFixed(1)}px`;
    }
    // scale bar at the controls-target depth plane
    const dist = camera.position.distanceTo(controls.target);
    const wPerPx = (2 * dist * Math.tan((camera.fov * Math.PI / 180) / 2)) /
      Math.max(1, renderer.domElement.clientHeight);
    const target = wPerPx * 90;                    // aim for a ~90px bar
    const mag = Math.pow(10, Math.floor(Math.log10(target)));
    const step = niceSteps.reduce((b, c) =>
      Math.abs(c * mag - target) < Math.abs(b - target) ? c * mag : b, mag);
    scaleBar.style.width = `${(step / wPerPx).toFixed(1)}px`;
    scaleTxt.textContent = L.scale.replace("{v}",
      step >= 1000 ? `${step / 1000} mm` : `${step} µm`);
  }
  function render() {
    if (document.hidden || !onScreen) return;
    renderer.render(scene, camera);
    updateOverlays();
  }
  // controls.update() dispatches 'change'; calling it inside the 'change'
  // listener would recurse, so keep it out of render().
  function updateAndRender() {
    controls.update();
    render();
  }
  controls.addEventListener("change", render);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) render(); });

  camera.position.copy(presets.die![0]);
  controls.target.copy(presets.die![1]);
  resize();
}

function mergeGeos(parts: THREE.BufferGeometry[]): THREE.BufferGeometry {
  let nv = 0, ni = 0;
  for (const g of parts) { nv += g.getAttribute("position")!.count; ni += g.getIndex()!.count; }
  const pos = new Float32Array(nv * 3);
  const nor = new Float32Array(nv * 3);
  const idx = new Uint32Array(ni);
  let vo = 0, io = 0;
  for (const g of parts) {
    const p = g.getAttribute("position") as THREE.BufferAttribute;
    const nrm = g.getAttribute("normal") as THREE.BufferAttribute;
    pos.set(p.array as Float32Array, vo * 3);
    nor.set(nrm.array as Float32Array, vo * 3);
    const gi = g.getIndex()!;
    for (let i = 0; i < gi.count; i++) idx[io + i] = gi.getX(i) + vo;
    vo += p.count; io += gi.count;
    g.dispose();
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  out.setAttribute("normal", new THREE.BufferAttribute(nor, 3));
  out.setIndex(new THREE.BufferAttribute(idx, 1));
  return out;
}
