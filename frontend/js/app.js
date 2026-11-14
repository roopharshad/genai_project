// DocRestore AI frontend: hash router + pages. No build step required.

const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmtBytes = (n) => (n < 1024 ? `${n} B` : n < 1048576 ? `${(n / 1024).toFixed(1)} KB` : `${(n / 1048576).toFixed(2)} MB`);
const fmtDate = (t) => new Date(t * 1000).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

// ---------- line icons ----------
const P = {
  overview: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="M21 16l-5-5-9 9"/>',
  layers: '<path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5"/>',
  layout: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M9 9v11"/>',
  book: '<path d="M4 5a2 2 0 012-2h13v16H6a2 2 0 00-2 2V5z"/><path d="M4 19a2 2 0 012-2h13"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
  upload: '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v3a1 1 0 001 1h14a1 1 0 001-1v-3"/>',
  download: '<path d="M12 4v12M7 11l5 5 5-5"/><path d="M4 20h16"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  play: '<path d="M7 5l11 7-11 7V5z"/>',
  reset: '<path d="M3 12a9 9 0 109-9 9 9 0 00-6.4 2.6L3 8"/><path d="M3 3v5h5"/>',
  alert: '<circle cx="12" cy="12" r="9"/><path d="M12 7v6M12 16h.01"/>',
  check: '<path d="M5 12l5 5 9-10"/>',
  sparkle: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3z"/>',
  file: '<path d="M14 3H6a1 1 0 00-1 1v16a1 1 0 001 1h12a1 1 0 001-1V8l-5-5z"/><path d="M14 3v5h5"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
  shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z"/>',
  server: '<rect x="3" y="4" width="18" height="7" rx="1"/><rect x="3" y="13" width="18" height="7" rx="1"/><path d="M7 7.5h.01M7 16.5h.01"/>',
  db: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  monitor: '<rect x="3" y="4" width="18" height="12" rx="1"/><path d="M8 20h8M12 16v4"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
};
const icon = (name, cls = "i") => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${P[name] || ""}</svg>`;

// ---------- navigation ----------
const NAV = [
  { id: "overview", label: "Overview", icon: "overview" },
  { id: "restore", label: "Image Restoration", icon: "image" },
  { id: "assets", label: "Asset Recovery", icon: "layers" },
  { id: "ui", label: "UI Reconstruction", icon: "layout" },
  { id: "learn", label: "Concepts & Learning", icon: "book" },
  { id: "stats", label: "Statistics & Results", icon: "chart" },
  { id: "about", label: "About Project", icon: "info" },
];
$("#nav").innerHTML = NAV.map((n, i) =>
  `<li><a href="#/${n.id}" data-id="${n.id}">${icon(n.icon)}<span>${n.label}</span><span class="num">${String(i + 1).padStart(2, "0")}</span></a></li>`
).join("");

const sidebar = $("#sidebar"), toggle = $("#menuToggle"), scrim = $("#scrim");
const setMenu = (open) => {
  sidebar.classList.toggle("open", open);
  scrim.hidden = !open;
  toggle.setAttribute("aria-expanded", String(open));
};
toggle.addEventListener("click", () => setMenu(!sidebar.classList.contains("open")));
scrim.addEventListener("click", () => setMenu(false));

// ---------- api ----------
async function api(path, opts = {}) {
  let res;
  try {
    res = await fetch(path, opts);
  } catch {
    throw new Error("Cannot reach the DocRestore server. Is the backend running?");
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = body.detail;
    throw new Error(typeof d === "string" ? d : `Request failed (${res.status}).`);
  }
  return body;
}
let OPTIONS = null;
const getOptions = async () => (OPTIONS ??= await api("/api/options"));

async function checkService() {
  const el = $("#serviceStatus");
  try {
    const h = await api("/api/health");
    const ok = h.ai_service?.available;
    el.className = `service-status ${ok ? "ok" : "down"}`;
    el.innerHTML = `<span class="dot"></span>${ok ? "AI service online" : "AI service unavailable"}`;
  } catch {
    el.className = "service-status down";
    el.innerHTML = '<span class="dot"></span>Server offline';
  }
}

// ---------- shared UI pieces ----------
const statusBox = (type, html) => {
  const ic = type === "info" ? '<span class="spinner" aria-hidden="true"></span>' : icon(type === "error" ? "alert" : "check");
  return `<div class="status ${type}" role="${type === "error" ? "alert" : "status"}">${ic}<div>${html}</div></div>`;
};

const head = (title, lede, eyebrow) => `
  <header class="page-head">
    ${eyebrow ? `<span class="eyebrow">${esc(eyebrow)}</span>` : ""}
    <h1 class="page-title">${title}</h1>
    <p class="lede">${lede}</p>
  </header>`;

function readImageMeta(file) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => resolve({ url, width: img.naturalWidth, height: img.naturalHeight });
    img.onerror = () => resolve({ url, width: null, height: null });
    img.src = url;
  });
}

/** Wires a dropzone + hidden input. onFile(file) is called for each accepted file. */
function bindDropzone(zone, input, onFile) {
  zone.addEventListener("click", (e) => { if (e.target.tagName !== "BUTTON") input.click(); });
  zone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
  zone.querySelector("button")?.addEventListener("click", () => input.click());
  input.addEventListener("change", () => { if (input.files[0]) onFile(input.files[0]); input.value = ""; });
  ["dragenter", "dragover"].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add("drag"); }));
  ["dragleave", "drop"].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.remove("drag"); }));
  zone.addEventListener("drop", (e) => { const f = e.dataTransfer.files[0]; if (f) onFile(f); });
}

const dropzoneHTML = (id, formats, accept) => `
  <div class="dropzone" id="${id}" tabindex="0" role="button" aria-label="Upload file: drag and drop or press Enter to choose">
    <div class="icon-box">${icon("upload")}</div>
    <p><strong>Drag &amp; drop</strong> a file here</p>
    <p class="formats">${formats}</p>
    <button type="button" class="btn outline">Choose file</button>
    <input type="file" id="${id}-input" accept="${accept}" hidden>
  </div>`;

const IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
const IMAGE_ACCEPT = ".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp";

function previewCard(title, body, info = "") {
  return `<div class="card preview"><div class="head"><h4>${title}</h4><span class="info">${info}</span></div><div class="body">${body}</div></div>`;
}
const emptyPreview = (msg) => `<div class="empty">${icon("image")}${msg}</div>`;

function sliderHTML(before, after) {
  return `
  <div class="slider-wrap">
    <h3 class="section-title" style="margin-top:28px">Comparison slider</h3>
    <div class="card slider" id="slider">
      <img src="${after}" alt="" aria-hidden="true" style="visibility:hidden">
      <img src="${before}" alt="Original" style="position:absolute;inset:0;width:100%;height:100%;object-fit:fill">
      <div class="top"><img src="${after}" alt="Restored"></div>
      <div class="handle"></div>
      <span class="lbl l">Original</span><span class="lbl r">Restored</span>
      <input type="range" min="0" max="100" value="50" aria-label="Comparison position">
    </div>
  </div>`;
}
function bindSlider(root) {
  const s = $("#slider", root);
  if (!s) return;
  const range = $("input", s), top = $(".top", s), handle = $(".handle", s);
  const set = () => { top.style.clipPath = `inset(0 0 0 ${range.value}%)`; handle.style.left = `${range.value}%`; };
  range.addEventListener("input", set);
  set();
}

/**
 * Generic "upload image -> process -> before/after" workspace used by
 * Image Restoration and UI Reconstruction.
 */
function imageWorkspace(root, cfg) {
  const state = { file: null, meta: null, result: null, busy: false };
  root.innerHTML = `
    ${head(cfg.title, cfg.lede, cfg.eyebrow)}
    <div class="workspace">
      <section class="card pad panel" aria-labelledby="up-h">
        <h3 id="up-h">${cfg.uploadTitle}</h3>
        <p class="sub">${cfg.uploadSub}</p>
        ${dropzoneHTML("dz", `JPG, JPEG, PNG or WEBP · up to <span id="maxmb">10</span> MB`, IMAGE_ACCEPT)}
        <div id="fileMeta"></div>
        <form id="controls">${cfg.controls}</form>
        <button class="btn block lg" id="run" disabled>${icon("sparkle")}${cfg.runLabel}</button>
        <div id="status" aria-live="polite"></div>
      </section>
      <section aria-label="Results">
        <div class="compare" id="compare"></div>
        <div id="after"></div>
      </section>
    </div>`;

  getOptions().then((o) => { $("#maxmb", root).textContent = o.max_upload_mb; cfg.onOptions?.(o, root); }).catch(() => {});

  const runBtn = $("#run", root), statusEl = $("#status", root);

  const renderCompare = () => {
    const o = state.meta, r = state.result;
    const left = o ? `<img src="${o.url}" alt="Original uploaded image">` : emptyPreview("Upload an image to preview it here.");
    let right;
    if (r) right = `<img src="${r.result.url}" alt="${cfg.resultLabel} image">`;
    else if (state.busy) right = `<div class="empty"><span class="spinner" style="margin:0 auto 10px;width:26px;height:26px"></span>Processing…</div>`;
    else right = emptyPreview(`The ${cfg.resultLabel.toLowerCase()} image will appear here.`);
    $("#compare", root).innerHTML =
      previewCard("Original Image", left, o?.width ? `${o.width} × ${o.height}` : "") +
      `<div class="arrow"><span>${icon("arrow")}</span></div>` +
      previewCard(`${cfg.resultLabel} Image`, right, r ? `${r.result.width} × ${r.result.height}` : "");

    const after = $("#after", root);
    if (!r) { after.innerHTML = ""; return; }
    after.innerHTML = `
      <div class="card result-bar">
        <div class="meta">
          <strong>${esc(r.filename)}</strong> · processed in ${r.duration}s ·
          ${r.original.width}×${r.original.height} (${fmtBytes(r.original.size)}) → ${r.result.width}×${r.result.height} (${fmtBytes(r.result.size)})
          ${r.engine ? ` · ${esc(r.engine)}` : ""}
        </div>
        <div class="actions">
          <a class="btn" href="${r.result.url}?download=true" download>${icon("download")}Download ${cfg.resultLabel.toLowerCase()} image</a>
          <button class="btn ghost" id="another">${icon("upload")}Upload another</button>
          <button class="btn ghost" id="reset">${icon("reset")}Reset</button>
        </div>
      </div>
      ${r.resized_for_processing ? `<p class="note">The image was larger than the processing limit and was scaled to ${r.processed_size.width}×${r.processed_size.height} before processing. Your original file is preserved unchanged.</p>` : ""}
      ${sliderHTML(r.original.url, r.result.url)}`;
    bindSlider(after);
    $("#reset", root).onclick = reset;
    $("#another", root).onclick = () => $("#dz-input", root).click();
  };

  const reset = () => {
    if (state.meta?.url) URL.revokeObjectURL(state.meta.url);
    Object.assign(state, { file: null, meta: null, result: null, busy: false });
    $("#fileMeta", root).innerHTML = "";
    statusEl.innerHTML = "";
    runBtn.disabled = true;
    renderCompare();
  };

  const accept = async (file) => {
    if (state.busy) return;
    const max = (OPTIONS?.max_upload_mb ?? 10) * 1048576;
    if (!IMAGE_TYPES.includes(file.type)) { statusEl.innerHTML = statusBox("error", "Unsupported format. Please choose a JPG, JPEG, PNG or WEBP image."); return; }
    if (file.size > max) { statusEl.innerHTML = statusBox("error", `This file is ${fmtBytes(file.size)}. The limit is ${fmtBytes(max)}.`); return; }
    if (state.meta?.url) URL.revokeObjectURL(state.meta.url);
    state.file = file;
    state.meta = await readImageMeta(file);
    state.result = null;
    $("#fileMeta", root).innerHTML = `
      <div class="file-meta"><img src="${state.meta.url}" alt="">
        <div><div class="name" title="${esc(file.name)}">${esc(file.name)}</div>
        <div class="info">${state.meta.width ?? "?"} × ${state.meta.height ?? "?"} px · ${fmtBytes(file.size)}</div></div></div>`;
    statusEl.innerHTML = "";
    runBtn.disabled = false;
    renderCompare();
  };

  bindDropzone($("#dz", root), $("#dz-input", root), accept);

  runBtn.addEventListener("click", async () => {
    if (!state.file || state.busy) return;
    state.busy = true; state.result = null; runBtn.disabled = true;
    renderCompare();
    const started = Date.now();
    const tick = () => {
      if (!state.busy) return;
      const s = Math.round((Date.now() - started) / 1000);
      statusEl.innerHTML = statusBox("info", `${cfg.busyText} <span class="muted">(${s}s)</span><br><span class="small">${cfg.busyHint}</span><div class="progress"><span></span></div>`);
    };
    tick();
    const timer = setInterval(tick, 1000);
    try {
      const fd = new FormData($("#controls", root));
      fd.append("file", state.file);
      state.result = await api(cfg.endpoint, { method: "POST", body: fd });
      statusEl.innerHTML = statusBox("success", `Completed in ${state.result.duration}s.`);
    } catch (err) {
      statusEl.innerHTML = statusBox("error", esc(err.message));
    } finally {
      clearInterval(timer);
      state.busy = false; runBtn.disabled = !state.file;
      renderCompare();
    }
  });

  renderCompare();
}

// ---------- pages ----------
const heroScene = `
<svg class="scene" viewBox="0 0 400 300" role="img" aria-label="Illustration: a faded, scratched picture becoming clear">
  <defs>
    <filter id="aged" x="0" y="0" width="100%" height="100%">
      <feColorMatrix type="matrix" values=".45 .45 .2 0 .08  .38 .42 .18 0 .06  .3 .32 .16 0 .04  0 0 0 1 0"/>
      <feGaussianBlur stdDeviation="1.6"/>
      <feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" result="n"/>
      <feColorMatrix in="n" type="saturate" values="0" result="g"/>
      <feBlend in="SourceGraphic" in2="g" mode="multiply" result="b"/>
      <feComponentTransfer in="b"><feFuncR type="linear" slope=".9" intercept=".12"/><feFuncG type="linear" slope=".9" intercept=".1"/><feFuncB type="linear" slope=".85" intercept=".08"/></feComponentTransfer>
    </filter>
    <clipPath id="L"><rect width="200" height="300"/></clipPath>
    <clipPath id="R"><rect x="200" width="200" height="300"/></clipPath>
    <g id="land">
      <rect width="400" height="300" fill="#EAF1EA"/>
      <circle cx="300" cy="80" r="30" fill="#F2D9A6"/>
      <path d="M0 200 Q90 140 180 190 T400 170 V300 H0z" fill="#9DBF9F"/>
      <path d="M0 235 Q120 190 240 230 T400 220 V300 H0z" fill="#5E8D6C"/>
      <path d="M0 270 Q160 245 400 265 V300 H0z" fill="#315F49"/>
      <rect x="92" y="150" width="8" height="62" fill="#5C4A36"/>
      <circle cx="96" cy="140" r="30" fill="#4C7C5C"/><circle cx="78" cy="152" r="20" fill="#5E8D6C"/><circle cx="116" cy="150" r="22" fill="#4C7C5C"/>
      <rect x="250" y="168" width="64" height="44" fill="#F7F6F1"/><path d="M244 170 L282 140 L320 170z" fill="#A2462F"/>
      <rect x="276" y="188" width="12" height="24" fill="#5C4A36"/><rect x="258" y="178" width="12" height="10" fill="#B9D3E0"/><rect x="294" y="178" width="12" height="10" fill="#B9D3E0"/>
    </g>
  </defs>
  <g clip-path="url(#L)">
    <use href="#land" filter="url(#aged)"/>
    <g stroke="#FFFDF5" stroke-opacity=".75" stroke-linecap="round" fill="none">
      <path d="M30 20 L70 120 L60 180" stroke-width="1.4"/><path d="M150 40 L120 110" stroke-width="1"/><path d="M20 230 L110 260" stroke-width="1.2"/>
    </g>
    <path d="M0 0 H200 V300 H0z" fill="#8A6A3A" fill-opacity=".08"/>
    <path d="M170 0 L200 0 L200 46 Q186 30 170 0z" fill="#F7F1E2"/>
  </g>
  <g clip-path="url(#R)"><use href="#land"/></g>
  <line x1="200" y1="0" x2="200" y2="300" stroke="#fff" stroke-width="3"/>
  <circle cx="200" cy="150" r="15" fill="#fff" stroke="#E4E1D8"/>
  <path d="M194 150h12M202 145l5 5-5 5" stroke="#315F49" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</svg>`;

const PAGES = {};

PAGES.overview = (root) => {
  const features = [
    { id: "restore", icon: "image", title: "Image Restoration", text: "Repair noise, blur and compression damage in old photographs and portraits using AI Image Restoration." },
    { id: "assets", icon: "layers", title: "Asset Recovery", text: "Extract icons, graphics and images embedded in legacy documents, archives, markup and screenshots." },
    { id: "ui", icon: "layout", title: "UI Reconstruction", text: "Rebuild low-resolution interface screenshots at a higher resolution for documentation and redesign." },
  ];
  root.innerHTML = `
  <section class="hero">
    <div>
      <span class="eyebrow">Generative AI · Legacy Asset Preservation</span>
      <h1 class="display">DocRestore<em>AI</em></h1>
      <p class="lede">Legacy UI Asset Restorer</p>
      <p class="muted" style="max-width:46ch">Preserving the past, restoring the future. An intelligent solution for recovering and enhancing visual assets from legacy applications.</p>
      <div class="chips">
        <div class="chip"><div class="icon-box">${icon("image")}</div><div><strong>JPG · PNG · WEBP</strong><span>Image inputs</span></div></div>
        <div class="chip"><div class="icon-box">${icon("file")}</div><div><strong>DOCX · PPTX · ZIP</strong><span>Asset sources</span></div></div>
        <div class="chip"><div class="icon-box">${icon("chart")}</div><div><strong>Tracked</strong><span>Every job logged</span></div></div>
      </div>
      <div class="actions">
        <a class="btn lg" href="#/restore">${icon("play")}Explore project</a>
        <a class="btn outline lg" href="#/about">${icon("book")}About project</a>
      </div>
    </div>
    <figure class="card hero-visual" style="margin:0">
      <div class="frame">${heroScene}<span class="tag l">Damaged</span><span class="tag r">Restored</span></div>
      <figcaption><span class="k1">Legacy asset</span><span class="k2">Recovered asset</span></figcaption>
    </figure>
  </section>
  <h2 class="section-title"><span class="n">01</span>Core capabilities</h2>
  <div class="grid c3">
    ${features.map((f, i) => `
      <article class="card pad feature">
        <span class="num-tag">0${i + 2}</span>
        <div class="icon-box">${icon(f.icon)}</div>
        <h3>${f.title}</h3>
        <p>${f.text}</p>
        <a class="link-btn" href="#/${f.id}">Explore ${icon("arrow")}</a>
      </article>`).join("")}
  </div>`;
};

PAGES.restore = (root) => imageWorkspace(root, {
  eyebrow: "02 · AI Image Restoration",
  title: "Image Restoration",
  lede: "Bring old, damaged and low-quality images back to life.",
  uploadTitle: "Upload image",
  uploadSub: "Works best on photographs and portraits. Faces receive dedicated restoration; the rest of the image is enhanced and upscaled.",
  controls: `
    <fieldset class="field"><legend>Restoration mode</legend><div class="options" id="modes"><p class="small muted">Loading options…</p></div></fieldset>
    <div class="field"><label for="scale">Output scale</label>
      <select id="scale" name="scale"><option value="1">1× (same size)</option><option value="2" selected>2× (recommended)</option><option value="3">3×</option><option value="4">4×</option></select></div>`,
  onOptions: (o, root) => {
    $("#modes", root).innerHTML = o.restoration_modes.map((m) => `
      <label class="opt"><input type="radio" name="mode" value="${m.id}" ${m.id === o.default_mode ? "checked" : ""}>
      <div><strong>${esc(m.label)}</strong><span>${esc(m.description)}</span></div></label>`).join("");
  },
  runLabel: "Restore image",
  busyText: "Restoring your image…",
  busyHint: "This usually takes 20–90 seconds. Please keep this page open.",
  resultLabel: "Restored",
  endpoint: "/api/restore",
});

PAGES.ui = (root) => imageWorkspace(root, {
  eyebrow: "04 · UI Reconstruction",
  title: "UI Reconstruction",
  lede: "Rebuild legacy interface screenshots with cleaner detail and higher resolution.",
  uploadTitle: "Upload UI screenshot",
  uploadSub: "Upload a screenshot of a legacy application window, web page or dialog.",
  controls: `
    <fieldset class="field"><legend>Reconstruction engine</legend><div class="options">
      <label class="opt"><input type="radio" name="engine" value="ai" checked><div><strong>AI enhancement</strong><span>Learned denoising and super-resolution applied to the whole screenshot.</span></div></label>
      <label class="opt"><input type="radio" name="engine" value="classical"><div><strong>Classical enhancement</strong><span>Offline: denoise, Lanczos upscale, sharpening and contrast correction. No AI.</span></div></label>
    </div></fieldset>
    <div class="field"><label for="uscale">Output scale</label>
      <select id="uscale" name="scale"><option value="2" selected>2×</option><option value="3">3×</option><option value="4">4×</option></select></div>
    <p class="note">The output is an enhanced raster image of the interface. It does not generate source code or editable layouts.</p>`,
  runLabel: "Reconstruct interface",
  busyText: "Reconstructing interface…",
  busyHint: "AI enhancement usually takes 20–90 seconds; classical enhancement takes a few seconds.",
  resultLabel: "Reconstructed",
  endpoint: "/api/ui/reconstruct",
});

PAGES.assets = (root) => {
  root.innerHTML = `
    ${head("Asset Recovery", "Recover the icons, graphics and images locked inside legacy files.", "03 · Asset Recovery")}
    <div class="workspace">
      <section class="card pad panel">
        <h3>Upload source</h3>
        <p class="sub">Assets are extracted from the file you upload. Nothing is generated.</p>
        ${dropzoneHTML("adz", "PNG/JPG/WEBP screenshots · DOCX, PPTX, XLSX, ODT, ZIP · HTML, CSS, SVG", ".png,.jpg,.jpeg,.webp,.docx,.pptx,.xlsx,.odt,.odp,.ods,.zip,.html,.htm,.css,.svg")}
        <div id="afile"></div>
        <button class="btn block lg" id="arun" disabled>${icon("search")}Recover assets</button>
        <div id="astatus" aria-live="polite"></div>
        <div class="note">
          <strong>How it works</strong><br>
          Documents and archives: embedded image files are extracted.<br>
          Markup: inline base64 images are decoded.<br>
          Screenshots: separate elements are cropped from the background.<br>
          Categories are assigned from each asset's size and shape.
        </div>
      </section>
      <section aria-label="Recovered assets" id="aresults">
        <div class="card pad empty" style="padding:60px 20px">${icon("layers")}Recovered assets will be listed here.</div>
      </section>
    </div>`;

  let file = null, busy = false;
  const status = $("#astatus", root), run = $("#arun", root);
  bindDropzone($("#adz", root), $("#adz-input", root), (f) => {
    if (busy) return;
    file = f;
    $("#afile", root).innerHTML = `<div class="file-meta"><div class="icon-box" style="margin:0 auto">${icon("file")}</div><div><div class="name">${esc(f.name)}</div><div class="info">${fmtBytes(f.size)}</div></div></div>`;
    status.innerHTML = ""; run.disabled = false;
  });

  run.addEventListener("click", async () => {
    if (!file || busy) return;
    busy = true; run.disabled = true;
    status.innerHTML = statusBox("info", "Scanning file for assets…");
    try {
      const fd = new FormData(); fd.append("file", file);
      const r = await api("/api/assets/recover", { method: "POST", body: fd });
      status.innerHTML = statusBox(r.assets.length ? "success" : "warn", r.assets.length ? `Recovered ${r.assets.length} asset${r.assets.length > 1 ? "s" : ""} in ${r.duration}s.` : "No image assets were found in this file.");
      renderAssets(r);
    } catch (e) {
      status.innerHTML = statusBox("error", esc(e.message));
    } finally { busy = false; run.disabled = !file; }
  });

  function renderAssets(r) {
    const out = $("#aresults", root);
    if (!r.assets.length) { out.innerHTML = `<div class="card pad empty" style="padding:60px 20px">${icon("search")}No assets found in <strong>${esc(r.filename)}</strong>.</div>`; return; }
    const cats = ["All", ...new Set(r.assets.map((a) => a.category))];
    out.innerHTML = `
      <div class="card result-bar" style="margin-top:0;margin-bottom:16px">
        <div class="meta"><strong>${esc(r.filename)}</strong> · ${esc(r.method)} · ${r.assets.length} assets</div>
        <a class="btn" href="${r.zip_url}" download>${icon("download")}Download all (ZIP)</a>
      </div>
      <div class="toolbar" role="group" aria-label="Filter by category">${cats.map((c, i) => `<button class="pill" aria-pressed="${i === 0}" data-cat="${esc(c)}">${esc(c)} (${c === "All" ? r.assets.length : r.assets.filter((a) => a.category === c).length})</button>`).join("")}</div>
      <div class="asset-grid" id="agrid"></div>`;
    const grid = $("#agrid", out);
    const draw = (cat) => {
      grid.innerHTML = r.assets.filter((a) => cat === "All" || a.category === cat).map((a) => `
        <article class="card asset">
          <div class="thumb"><img src="${a.url}" alt="${esc(a.category)} ${a.width}×${a.height}" loading="lazy"></div>
          <div class="cap">
            <div class="row"><span class="cat">${esc(a.category)}</span><a class="dl" href="${a.url}?download=true" download aria-label="Download ${esc(a.name)}">${icon("download")}</a></div>
            <div class="muted" style="margin-top:6px">${a.width} × ${a.height} · ${fmtBytes(a.size)}</div>
            <div class="muted" title="${esc(a.source)}" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(a.source)}</div>
          </div>
        </article>`).join("");
    };
    out.querySelectorAll(".pill").forEach((b) => b.addEventListener("click", () => {
      out.querySelectorAll(".pill").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
      draw(b.dataset.cat);
    }));
    draw("All");
  }
};

PAGES.learn = (root) => {
  const concepts = [
    ["Legacy software systems", "Older applications that remain in use, or must be preserved, long after their original tools, source files and designers are gone.", "Their visual assets (icons, splash screens, toolbar graphics, photographs) often survive only as low-resolution screenshots, compressed images or files embedded inside old documents."],
    ["Image restoration", "Restoration tries to reverse damage: noise, blur, compression artefacts, scratches and fading. The goal is to estimate what the image looked like before it degraded.", "AI Image Restoration uses a neural network trained on pairs of clean and artificially degraded images. Faces get special treatment because the network has learned strong priors about facial structure."],
    ["Image enhancement", "Enhancement improves perceived quality without claiming to recover the true original. Examples are upscaling, sharpening and contrast correction.", "Classical enhancement uses fixed mathematical filters (Lanczos resampling, median filtering, unsharp masking). It is predictable but cannot invent missing detail. Learned super-resolution can synthesise plausible detail."],
    ["Asset recovery", "Recovery locates and extracts individual assets from containers that hide them.", "Office documents and ZIP archives store images as separate files that can be extracted losslessly. HTML and CSS can embed images as base64 text. In screenshots, elements are separated from the background by comparing each pixel with the dominant border colour and grouping connected regions."],
    ["UI reconstruction", "Reconstruction produces a cleaner, higher-resolution rendition of a legacy interface for documentation, redesign reference or archiving.", "This project reconstructs the interface as an image. It does not generate source code or editable layouts."],
  ];
  const steps = [["upload", "Upload", "Image or legacy file"], ["shield", "Validate", "Format, size, integrity"], ["sparkle", "Process", "Restore, extract or rebuild"], ["image", "Compare", "Original vs result"], ["download", "Export", "PNG or ZIP download"]];
  root.innerHTML = `
    ${head("Concepts &amp; Learning", "The ideas behind restoring and recovering legacy visual assets.", "05 · Concepts & Learning")}
    <div class="grid" style="gap:16px">
      ${concepts.map((c, i) => `<article class="card concept"><div class="n">${String(i + 1).padStart(2, "0")}</div><div><h3>${c[0]}</h3><p>${c[1]}</p><p>${c[2]}</p></div></article>`).join("")}
    </div>
    <h2 class="section-title"><span class="n">06</span>Project workflow</h2>
    <div class="card flow">
      ${steps.map((s, i) => `${i ? `<div class="sep">${icon("arrow")}</div>` : ""}<div class="step"><div class="icon-box">${icon(s[0])}</div><strong>${s[1]}</strong><span>${s[2]}</span></div>`).join("")}
    </div>
    <h2 class="section-title"><span class="n">07</span>Restoration vs enhancement</h2>
    <div class="card table-wrap"><table>
      <thead><tr><th>Aspect</th><th>Classical enhancement</th><th>AI Image Restoration</th></tr></thead>
      <tbody>
        <tr><td>Method</td><td>Fixed filters and resampling</td><td>Neural network trained on degraded/clean pairs</td></tr>
        <tr><td>New detail</td><td>No, only sharpens existing edges</td><td>Yes, synthesises plausible detail</td></tr>
        <tr><td>Predictability</td><td>Fully deterministic</td><td>May alter fine features</td></tr>
        <tr><td>Best for</td><td>Text-heavy UI screenshots</td><td>Photographs and faces</td></tr>
        <tr><td>Speed</td><td>Seconds, offline</td><td>20–90 s, needs connection</td></tr>
      </tbody></table></div>`;
};

PAGES.stats = async (root) => {
  root.innerHTML = `${head("Statistics &amp; Results", "Live figures recorded by this installation. Every processing request is logged.", "06 · Statistics & Results")}<div id="sbody">${statusBox("info", "Loading statistics…")}</div>`;
  const body = $("#sbody", root);
  try {
    const [s, h] = await Promise.all([api("/api/stats"), api("/api/history?limit=50")]);
    const k = (n) => s.by_kind[n] || { success: 0, failed: 0, assets: 0, avg_duration: null };
    const rs = k("restoration"), ar = k("asset_recovery"), ui = k("ui_reconstruction");
    const images = rs.success + rs.failed + ui.success + ui.failed;
    const ok = rs.success + ui.success, bad = rs.failed + ui.failed;
    const LABEL = { restoration: "Image restoration", asset_recovery: "Asset recovery", ui_reconstruction: "UI reconstruction" };
    const rows = Object.keys(LABEL).map((key) => {
      const x = k(key), t = x.success + x.failed;
      return `<div class="bar-row"><span>${LABEL[key]}</span><div class="bar" title="${x.success} succeeded, ${x.failed} failed">${t ? `<span class="ok" style="width:${(x.success / t) * 100}%"></span><span class="bad" style="width:${(x.failed / t) * 100}%"></span>` : ""}</div><span class="muted">${t} job${t === 1 ? "" : "s"}</span></div>`;
    }).join("");
    body.innerHTML = `
      <div class="grid c4">
        <div class="card stat"><div class="label">Images processed</div><div class="value">${images}</div><div class="small muted">Restoration + reconstruction</div></div>
        <div class="card stat"><div class="label">Successful</div><div class="value green">${ok}</div><div class="small muted">${images ? Math.round((ok / images) * 100) : 0}% success rate</div></div>
        <div class="card stat"><div class="label">Failed</div><div class="value">${bad}</div><div class="small muted">Service or input errors</div></div>
        <div class="card stat"><div class="label">Assets recovered</div><div class="value green">${ar.assets}</div><div class="small muted">From ${ar.success} file${ar.success === 1 ? "" : "s"}</div></div>
      </div>
      <div class="two-col" style="margin-top:20px">
        <div class="card pad"><h3 style="font-size:22px;margin-bottom:18px">Jobs by feature</h3>${rows}
          <p class="small muted" style="margin:14px 0 0"><span style="color:var(--primary)">■</span> succeeded &nbsp; <span style="color:#C9826E">■</span> failed</p></div>
        <div class="card pad"><h3 style="font-size:22px;margin-bottom:18px">Average processing time</h3>
          ${[["Image restoration", rs], ["UI reconstruction", ui], ["Asset recovery", ar]].map(([n, x]) => `<div class="bar-row" style="grid-template-columns:150px 1fr"><span>${n}</span><strong style="font-weight:500">${x.avg_duration != null ? `${x.avg_duration}s` : "—"}</strong></div>`).join("")}
          <p class="small muted" style="margin:14px 0 0">Successful jobs only.</p></div>
      </div>
      <h2 class="section-title"><span class="n">—</span>Processing history</h2>
      ${h.length ? `<div class="card table-wrap"><table>
        <thead><tr><th>Date</th><th>Feature</th><th>File</th><th>Status</th><th>Time</th><th>Details</th></tr></thead>
        <tbody>${h.map((j) => `<tr>
          <td>${fmtDate(j.created_at)}</td><td>${LABEL[j.kind] || esc(j.kind)}</td>
          <td style="max-width:220px;overflow-wrap:anywhere">${esc(j.filename)}</td>
          <td><span class="badge ${j.status}">${j.status === "success" ? "Success" : "Failed"}</span></td>
          <td>${j.duration != null ? `${j.duration}s` : "—"}</td>
          <td class="muted">${j.status === "failed" ? esc(j.error) : j.kind === "asset_recovery" ? `${j.assets_count} assets · ${esc(j.meta.method || "")}` : j.meta.resized ? "Scaled for processing" : ""}</td>
        </tr>`).join("")}</tbody></table></div>` : `<div class="card pad empty">${icon("clock")}No jobs have been processed yet. Results will appear here after your first upload.</div>`}`;
  } catch (e) {
    body.innerHTML = statusBox("error", esc(e.message));
  }
};

PAGES.about = (root) => {
  root.innerHTML = `
    ${head("About Project", "DocRestore AI: an applied generative AI project for preserving the visual heritage of legacy software.", "07 · About Project")}
    <div class="prose">
      <h2 class="section-title" style="margin-top:0"><span class="n">01</span>Introduction</h2>
      <p>Organisations replacing old software often lose its visual identity. Original artwork files are missing, and what remains are blurry screenshots, scanned manuals and documents with embedded graphics. DocRestore AI brings restoration, extraction and reconstruction together in one workspace.</p>
      <h2 class="section-title"><span class="n">02</span>Problem statement</h2>
      <p>Visual assets from legacy applications are typically low-resolution, compressed, noisy or hidden inside container files. Recreating them manually is slow and inconsistent, and generic image editors cannot recover embedded assets or restore degraded photographs convincingly.</p>
      <h2 class="section-title"><span class="n">03</span>Objectives</h2>
      <ul>
        <li>Restore degraded photographs and portraits with AI Image Restoration.</li>
        <li>Extract embedded image assets from documents, archives, markup and screenshots without loss.</li>
        <li>Produce higher-resolution reconstructions of legacy interface screenshots.</li>
        <li>Show honest before-and-after comparisons and record every result for evaluation.</li>
      </ul>
      <h2 class="section-title"><span class="n">04</span>Proposed solution</h2>
      <p>A web application with a Python backend. Uploads are validated, the original is stored unchanged, and the file is routed to the correct pipeline: AI Image Restoration, asset extraction or UI reconstruction. Results are returned for side-by-side comparison and download, and every job is logged to a local database.</p>
    </div>
    <h2 class="section-title"><span class="n">05</span>System architecture</h2>
    <div class="arch">
      <div class="card layer"><div class="icon-box">${icon("monitor")}</div><h4>Presentation layer</h4><ul><li>Single-page web interface</li><li>Upload, preview and comparison</li><li>Responsive layout</li></ul></div>
      <div class="card layer"><div class="icon-box">${icon("server")}</div><h4>Application layer</h4><ul><li>REST API</li><li>Validation and size limits</li><li>Restoration, recovery and reconstruction services</li></ul></div>
      <div class="card layer"><div class="icon-box">${icon("db")}</div><h4>Data layer</h4><ul><li>Job database (SQLite)</li><li>Original and result file storage</li><li>Automatic cleanup of expired jobs</li></ul></div>
    </div>
    <h2 class="section-title"><span class="n">06</span>Technologies used</h2>
    <div class="tech">${["Python", "FastAPI", "Uvicorn", "Pillow", "NumPy", "SQLite", "PyTorch-based restoration model", "HTML5", "CSS3", "JavaScript (ES modules)"].map((t) => `<span>${t}</span>`).join("")}</div>
    <h2 class="section-title"><span class="n">07</span>Project workflow</h2>
    <div class="card flow">
      ${[["upload", "Upload"], ["shield", "Validate"], ["sparkle", "Process"], ["image", "Compare"], ["download", "Export"], ["chart", "Log"]].map((s, i) => `${i ? `<div class="sep">${icon("arrow")}</div>` : ""}<div class="step"><div class="icon-box">${icon(s[0])}</div><strong>${s[1]}</strong></div>`).join("")}
    </div>
    <div class="prose">
      <h2 class="section-title"><span class="n">08</span>Future scope</h2>
      <ul>
        <li>Fully local, GPU-accelerated restoration for offline use.</li>
        <li>Text-aware enhancement and OCR for interface screenshots.</li>
        <li>Vectorisation of recovered icons to SVG.</li>
        <li>Batch processing and project workspaces.</li>
        <li>Generating editable UI layouts from reconstructed screenshots.</li>
      </ul>
    </div>`;
};

// ---------- router ----------
function route() {
  const id = (location.hash.replace(/^#\/?/, "") || "overview").split("?")[0];
  const page = PAGES[id] ? id : "overview";
  document.querySelectorAll("#nav a").forEach((a) => a.toggleAttribute("aria-current", false) || (a.dataset.id === page && a.setAttribute("aria-current", "page")));
  const nav = NAV.find((n) => n.id === page);
  document.title = `${nav.label} · DocRestore AI`;
  const el = $("#page");
  el.style.animation = "none"; void el.offsetWidth; el.style.animation = "";
  PAGES[page](el);
  setMenu(false);
  window.scrollTo({ top: 0 });
  $("#main").focus({ preventScroll: true });
}
window.addEventListener("hashchange", route);
route();
checkService();
