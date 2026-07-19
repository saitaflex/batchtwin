const STAGE_ORDER = ["fabrication", "cond_primaire", "cond_secondaire", "qualite", "liberation"];
/* BatchTwin — Mode poste (atelier). Mobile-first, scan-to-act. */
const $ = (s) => document.querySelector(s);
const M = $("#main");
const T = (k) => (window.t ? window.t(k) : k);
const TF = (k, v) => (window.tf ? window.tf(k, v) : k);
/* One authenticated client for every page (frontend/session.js). This page had
   its own copy and silently died on 401 when the API moved behind a login. */
const api = (u, b) => bt.api(u, b);
const num = (v, d = 1) => v == null ? "—" : Number(v).toLocaleString("fr-FR", {minimumFractionDigits: d, maximumFractionDigits: d});
let TOASTT;
function toast(msg) { const t = $("#toast"); t.textContent = msg; t.classList.add("show"); clearTimeout(TOASTT); TOASTT = setTimeout(() => t.classList.remove("show"), 2200); }
function buzz() { if (navigator.vibrate) navigator.vibrate(60); }

/* Identity comes from the SESSION, exactly as on /app. The picker that used to
   live here let anyone claim any role -- meaningless now that the server derives
   the actor from the token, and misleading while it stayed on screen. */
const ROLE_LONG = {
  r_prod: "R. PROD · Responsable Production",
  r_cq: "R. CQ · Responsable Contrôle Qualité",
  smq: "SMQ · Assurance Qualité",
  prt: "PRT · Pharmacien Responsable Technique",
};
const STAGE_LABEL = (name) => T(`stage_${name}`);
const STAGE_ROLE = {fabrication: "r_prod", cond_primaire: "r_prod",
                    cond_secondaire: "r_prod", qualite: "r_cq", liberation: "prt"};
const SIGN_MEANING = (stage) => T(`sign_${stage}`);

const S = {user: null, bid: null, data: null, codes: null, screen: "home", matId: null};
/* The body's actor is ignored server-side; this keeps the shape callers expect. */
const me = () => ({user: S.user.username, role: S.user.role});

function paintWhoami() {
  const u = S.user;
  $("#me-av").textContent = (u.full_name || u.username).trim().charAt(0).toUpperCase();
  $("#me-name").textContent = u.full_name || u.username;
  $("#me-role").textContent = ROLE_LONG[u.role] || u.role;
}

async function boot() {
  S.user = await bt.me();
  if (!S.user) return;              // bt.me() has already sent us to the gate
  paintWhoami();
  $("#logout").onclick = async () => {
    try { await api("/api/logout?token=" + encodeURIComponent(bt.token()), {}); } catch (e) {}
    localStorage.removeItem(bt.TOKEN_KEY);
    location.replace("/app");
  };
  $("#theme").onclick = () => {
    const r = document.documentElement;
    const next = r.getAttribute("data-theme") === "light" ? "dark" : "light";
    r.setAttribute("data-theme", next);
    localStorage.setItem("bt_theme", next);
  };
  let list = await api("/api/batches");
  if (!list.length) { await api("/api/seed?reset=true", {}); list = await api("/api/batches"); }
  S.batches = list;
  S.bid = list[0].id;
  await reload();
}
async function reload() {
  S.data = await api(`/api/batch/${S.bid}`);
  S.codes = await api(`/api/batch/${S.bid}/codes`);
  render();
}
function go(screen) { stopCamera(); S.screen = screen; render(); }

/* ---------------- scan ---------------- */
let scanStream = null, scanRAF = null;
/* Two readers, same as the product form: BarcodeDetector where it exists,
 * otherwise the vendored decoders. Station codes are QR, so before qr.js was
 * added this screen was unusable on Firefox, Safari and every iPad. */
function makeFloorReader() {
  if ("BarcodeDetector" in window) {
    const det = new BarcodeDetector({formats: ["qr_code", "code_128", "ean_13"]});
    return async (video) => {
      const cs = await det.detect(video);
      return cs.length ? cs[0].rawValue : null;
    };
  }
  if (!window.BTQr && !window.BTBarcode) return null;
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d", {willReadFrequently: true});
  return (video) => {
    const vw = video.videoWidth, vh = video.videoHeight;
    if (!vw || !vh) return null;
    const w = Math.min(720, vw);            // enough for a QR, cheap enough per frame
    const h = Math.round(vh * (w / vw));
    canvas.width = w; canvas.height = h;
    ctx.drawImage(video, 0, 0, w, h);
    const img = ctx.getImageData(0, 0, w, h);
    // QR first: floor codes are QR, and a 1D pass over a QR is wasted work.
    return (window.BTQr && window.BTQr.decodeImageData(img)) ||
           (window.BTBarcode && window.BTBarcode.decodeImageData(img)) || null;
  };
}

async function startCamera(video, onCode) {
  const read = makeFloorReader();
  if (!read) { toast(T("floor_code_not_supported")); return; }
  try {
    scanStream = await navigator.mediaDevices.getUserMedia({video: {facingMode: "environment"}});
    video.srcObject = scanStream; await video.play();
    const loop = async () => {
      if (!scanStream) return;
      try {
        const code = await read(video);
        if (code) { buzz(); stopCamera(); onCode(code); return; }
      } catch (e) {}
      scanRAF = requestAnimationFrame(loop);
    };
    loop();
  } catch (e) { toast(T("floor_code_unavailable")); }
}
function stopCamera() { if (scanRAF) cancelAnimationFrame(scanRAF); scanRAF = null; if (scanStream) { scanStream.getTracks().forEach(t => t.stop()); scanStream = null; } }

function handleCode(data) {
  data = (data || "").trim();
  if (!data.startsWith("BT:")) { toast(TF("floor_code_unknown", {data})); return; }
  const [, kind, val] = data.split(":");
  if (kind === "LOT") { S.bid = +val; reload().then(() => toast(T("floor_sign_loaded"))); return; }
  if (kind === "ST") { const st = {vide: "vide", pesee: "pesee", qc: "qc", sign: "sign"}[val]; if (st) return go(st); }
  if (kind === "MAT") { S.matId = +val; return go("weigh"); }
  toast(TF("floor_code_unknown", {data}));
}

/* ---------------- render ---------------- */
function render() {
  const scr = {home, vide, pesee, weigh, qc, sign, codes}[S.screen] || home;
  M.innerHTML = ""; scr();
}
function header(title, sub) {
  const b = document.createElement("button");
  b.className = "back"; b.innerHTML = `‹ ${T("floor_back")}`; b.onclick = () => go("home");
  const h = document.createElement("div"); h.className = "card";
  h.innerHTML = `<h2>${title}</h2><div class="cap">${sub || ""}</div>`;
  M.append(b, h); return h;
}
function el(html) { const d = document.createElement("div"); d.innerHTML = html.trim(); return d.firstChild; }

function home() {
  const b = S.data.batch;
  const relBadge = b.state === "released" ? `<span class="pill released">${T("floor_lot_status_released")}</span>` : `<span class="pill open">${T("floor_lot_status_open")}</span>`;
  M.append(el(`<div class="lotbar"><div><b>${T("floor_lot_label")} ${b.lot_name}</b><div class="s">${b.product} · ${b.qty_target} u.</div></div>${relBadge}</div>`));
  if (S.batches && S.batches.length > 1) {
    const sel = el(`<select class="lotsel" style="width:100%;min-height:56px;font:inherit;font-size:16px;
      padding:0 14px;border-radius:14px;background:var(--fill);color:var(--ink);
      border:1px solid var(--border)">
      ${S.batches.map(x => `<option value="${x.id}" ${x.id === S.bid ? "selected" : ""}>Lot ${x.lot_name} — ${x.product}</option>`).join("")}</select>`);
    sel.onchange = (e) => { S.bid = +e.target.value; reload(); };
    M.append(sel);
  }

  // scan card
  const scan = el(`<div class="card">
    <h2>${T("floor_scan_title")}</h2><div class="cap">${T("floor_scan_sub")}</div>
    <div class="scanbox" id="sb" style="display:none"><video id="vid" playsinline muted></video><div class="frame"></div></div>
    <div style="display:flex;gap:8px;margin:10px 0"><button class="btn teal" id="cam">📷 ${T("floor_scan_btn")}</button></div>
    <div class="manual"><input id="mc" placeholder="${T("floor_scan_placeholder")}" autocomplete="off" autocapitalize="off"><button class="btn" id="mcgo">${T("floor_scan_manual")}</button></div>
    <div class="hint" style="margin-top:8px">${T("floor_scan_hint")}</div>
  </div>`);
  M.append(scan);
  $("#cam").onclick = () => { $("#sb").style.display = "block"; startCamera($("#vid"), handleCode); };
  const mc = $("#mc"); mc.addEventListener("keydown", e => { if (e.key === "Enter") { handleCode(mc.value); mc.value = ""; } });
  $("#mcgo").onclick = () => { handleCode(mc.value); mc.value = ""; };

  // station tiles (tap = scan)
  const done = stationDone();
  const tiles = S.codes.stations.map(s => {
    const code = s.data.split(":")[2];
    return `<div class="tile ${done[code] ? "done" : ""}" data-st="${code}">
      <div class="ic">${s.icon}</div><div class="lb">${T(s.key)}</div><div class="st">${done[code] ? T("floor_station_done") : T("floor_station_open")}</div></div>`;
  }).join("");
  const grid = el(`<div class="grid">${tiles}</div>`);
  grid.querySelectorAll(".tile").forEach(t => t.onclick = () => go(t.dataset.st));
  M.append(grid);
  M.append(el(`<button class="btn ghost" id="qrbtn">⧉ ${T("floor_qr_title")}</button>`));
  $("#qrbtn").onclick = () => go("codes");
}
function stationDone() {
  const b = S.data.batch;
  return {
    vide: b.checklist.length && b.checklist.every(c => c.ok === 1),
    pesee: b.dispense.length && b.dispense.every(d => d.qty_dispensed != null),
    qc: b.qc.length > 0,
    sign: b.state === "released",
  };
}

function vide() {
  header("🧹 " + T("floor_vide_title"), T("floor_vide_sub"));
  const b = S.data.batch;
  const card = el(`<div class="card"></div>`);
  b.checklist.forEach(c => {
    const row = el(`<div class="signrow"><span class="dot" style="background:${c.ok === 1 ? "var(--good)" : c.ok === 0 ? "var(--crit)" : "var(--muted)"}"></span>
      <div class="nm">${c.label}${c.ok === 0 ? `<div class="tg" style="color:var(--crit)">${T("floor_vide_escalated")} ${c.escalated_to || T("floor_vide_responsible")}</div>` : ""}</div>
      <button class="btn ${c.ok === 1 ? "good" : "ghost"}" style="width:auto;min-height:44px;padding:0 16px">${c.ok === 1 ? "✓" : "OK"}</button></div>`);
    row.querySelector("button").onclick = async () => {
      const nv = c.ok === 1 ? false : true;
      const body = {...me(), ok: nv}; if (!nv) { body.note = "non conforme"; body.escalate_to = "responsable.production"; }
      await api(`/api/batch/${S.bid}/checklist/${c.id}`, body); await reload();
    };
    card.append(row);
  });
  M.append(card);
}

function pesee() {
  header("⚖️ " + T("floor_pesee_title"), T("floor_pesee_sub"));
  const b = S.data.batch;
  const card = el(`<div class="card"></div>`);
  b.dispense.forEach(d => {
    const done = d.qty_dispensed != null;
    const row = el(`<div class="matrow ${done ? "done" : ""}">
      <div class="nm">${d.material}<div class="tg">cible ${num(d.qty_target, 2)} ${d.unit}${done ? ` · pesé ${num(d.qty_dispensed, 2)}` : ""}</div></div>
      <button class="btn ${done ? "good" : ""}" style="width:auto;min-height:46px;padding:0 18px">${done ? "✓" : "Peser"}</button></div>`);
    row.querySelector("button").onclick = () => { S.matId = d.id; go("weigh"); };
    card.append(row);
  });
  M.append(card);
}

function weigh() {
  const d = S.data.batch.dispense.find(x => x.id === S.matId);
  if (!d) return go("pesee");
  header("⚖️ " + d.material, `${T("floor_weigh_target")} ${num(d.qty_target, 2)} ${d.unit}`);
  const card = el(`<div class="card">
    <label class="fld">${T("floor_weigh_title")} (${d.unit})</label>
    <input class="num" id="disp" type="number" inputmode="decimal" value="${d.qty_dispensed ?? d.qty_target}">
    <label class="fld">${T("floor_weigh_loss")} (${d.unit})</label>
    <input class="num" id="loss" type="number" inputmode="decimal" value="${d.qty_loss ?? (d.qty_target * 0.004).toFixed(3)}">
    <div style="display:flex;gap:10px;margin-top:14px">
      <button class="btn ghost" id="cancel" style="flex:1">${T("floor_weigh_cancel")}</button>
      <button class="btn good" id="ok" style="flex:2">✓ ${T("floor_weigh_validate")}</button></div>
  </div>`);
  M.append(card);
  $("#cancel").onclick = () => go("pesee");
  $("#ok").onclick = async () => {
    const dispensed = parseFloat($("#disp").value), loss = parseFloat($("#loss").value) || 0;
    if (isNaN(dispensed)) return toast(T("floor_weigh_required"));
    await api(`/api/batch/${S.bid}/dispense/${d.id}`, {...me(), dispensed, loss});
    S.data = await api(`/api/batch/${S.bid}`); toast(T("floor_weigh_saved")); go("pesee");
  };
}

function qc() {
  const b = S.data.batch;
  const u = b.fill_unit || "mL";
  const noun = u === "mg" ? "gélules — poids" : "flacons — remplissage";
  header("🔬 " + T("floor_qc_title"), `10 ${noun} (${u})`);
  const tgt = b.target_fill_g || 200;
  const grid = Array.from({length: 10}, (_, i) =>
    `<input class="num" style="font-size:18px;padding:10px" id="q${i}" type="number" inputmode="decimal" value="${tgt}">`).join("");
  const card = el(`<div class="card">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">${grid}</div>
    <div style="display:flex;gap:10px;margin-top:14px">
      <button class="btn ghost" id="simu" style="flex:1">⚡ ${T("floor_qc_auto")}</button>
      <button class="btn" id="val" style="flex:2">${T("floor_qc_validate")}</button></div>
    <div id="vout"></div>
  </div>`);
  M.append(card);
  $("#simu").onclick = async () => { const r = await api(`/api/batch/${S.bid}/qc/simulate`, {...me(), drift: false}); showVerdict(r); S.data = await api(`/api/batch/${S.bid}`); };
  $("#val").onclick = async () => {
    const vals = Array.from({length: 10}, (_, i) => parseFloat($("#q" + i).value)).filter(v => !isNaN(v));
    if (vals.length < 2) return toast(T("floor_qc_required"));
    const r = await api(`/api/batch/${S.bid}/qc`, {...me(), measurements: vals}); showVerdict(r);
    S.data = await api(`/api/batch/${S.bid}`);
  };
  function showVerdict(r) { $("#vout").innerHTML = `<div class="verdict ${r.verdict}">${r.verdict === "PASS" ? T("floor_qc_pass") : T("floor_qc_fail")}<div style="font-size:15px;font-weight:600;margin-top:4px">moyenne ${num(r.mean, 1)} ${u} · étendue ${num(r.range, 1)} ${u}</div></div>`; buzz(); }
}

function sign() {
  header("✍️ " + T("floor_sign_title"), `${T("floor_sign_connected")} ${S.user.name}`);
  const b = S.data.batch;
  const signed = {}; b.signatures.forEach(s => signed[s.stage] = s);
  const order = STAGE_ORDER;
  const card = el(`<div class="card"></div>`);
  order.forEach((st, i) => {
    const isSigned = b.stages.find(x => x.name === st).status === "signed";
    const prevOk = i === 0 || b.stages.find(x => x.name === order[i - 1]).status === "signed";
    const canRole = [S.user.role].includes(STAGE_ROLE[st]);
    const enabled = !isSigned && prevOk && canRole && b.state !== "released";
    const dot = isSigned ? "var(--good)" : prevOk ? "var(--series)" : "var(--muted)";
    const sub = isSigned ? `${T("floor_sign_signed")} — ${signed[st].user}` : canRole ? (prevOk ? T("floor_sign_ready") : T("floor_sign_required")) : TF("floor_sign_role", {role: STAGE_ROLE[st]});
    const row = el(`<div class="signrow"><span class="dot" style="background:${dot}"></span>
      <div class="nm">${i + 1}. ${STAGE_LABEL(st)}<div class="tg">${sub}</div></div>
      <button class="btn ${isSigned ? "good" : "warn"}" style="width:auto;min-height:46px;padding:0 18px" ${enabled ? "" : "disabled"}>${isSigned ? "✓" : T("floor_sign_title")}</button></div>`);
    if (enabled) row.querySelector("button").onclick = async () => {
      try { await api(`/api/batch/${S.bid}/sign`, {user: S.user.id, role: STAGE_ROLE[st], stage: st, meaning: SIGN_MEANING(st)}); toast(st === "liberation" ? T("floor_sign_release") : T("floor_sign_signed_msg")); await reload(); go("sign"); }
      catch (e) { toast(T("floor_sign_refused") + e.message); }
    };
    card.append(row);
  });
  M.append(card);
}

function codes() {
  header("⧉ " + T("floor_qr_title"), T("floor_qr_sub"));
  const all = [S.codes.lot, ...S.codes.stations, ...S.codes.materials];
  const grid = el(`<div class="qrgrid">${all.map(c =>
    `<div class="qrcard"><img src="/api/qr?data=${encodeURIComponent(c.data)}&scale=4" alt="${c.label}"><div class="lb">${c.label}</div></div>`
  ).join("")}</div>`);
  M.append(grid);
  M.append(el(`<div class="hint">${T("floor_qr_hint")}</div>`));
}

window.onLangChange = () => {
  // The operator's name comes from their account, so it does not translate --
  // only their role label and the screen around it do.
  if (S.user) paintWhoami();
  render();
};

boot();
