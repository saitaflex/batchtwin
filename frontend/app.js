const $ = (s) => document.querySelector(s);
const loc = () => ({fr: "fr-FR", en: "en-US", ar: "en-US"}[window.i18n ? window.i18n.lang : "fr"] || "fr-FR");
const money = (v) => v == null ? "—" : "€" + Number(v).toLocaleString(loc(), {minimumFractionDigits: 2, maximumFractionDigits: 2});
const num = (v, d = 1) => v == null ? "—" : Number(v).toLocaleString(loc(), {minimumFractionDigits: d, maximumFractionDigits: d});
const T = (k) => window.t ? window.t(k) : k;
const TF = (k, v) => window.tf ? window.tf(k, v) : k;

let BID = null;
let FILL_UNIT = "mL";

/* ---------------- identity ----------------
   ME is established by a real login and is the ONLY source of who is acting.
   There is no role dropdown any more: you cannot act as someone you are not. */
let ME = null;
const actor = () => ({user: ME.username, role: ME.role});
const api = async (url, body) => {
  const r = await fetch(url, body ? {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)} : {});
  if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || r.status); }
  return r.json();
};

const STAGE_LABEL = (name) => T("stage_" + name);
const SIGN_MEANING = (stage) => T("sign_" + stage);
/* short signatory labels — the real Medicka roles, never the raw key */
const ROLE_SHORT = {r_prod: "R. PROD", r_cq: "R. CQ", smq: "SMQ", prt: "PRT"};
const roleShort = (r) => ROLE_SHORT[r] || r;
/* The lifecycle, in order. Packaging is two dossiers (DCOI, DCOII) signed separately. */
const STAGE_ORDER = ["fabrication", "cond_primaire", "cond_secondaire", "qualite", "liberation"];
const CHIP_KEYS = ["chip_next", "chip_blocked", "chip_summary", "chip_quality", "chip_loss", "chip_carbon"];

/* ---------------- login gate ---------------- */
const TOKEN_KEY = "bt_token";

async function startSession() {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    try {
      ME = await api(`/api/me?token=${encodeURIComponent(token)}`);
      return true;
    } catch (e) { localStorage.removeItem(TOKEN_KEY); }
  }
  return false;
}

function showGate(msg) {
  $("#gate").hidden = false;
  $("#app-wrap").hidden = true;
  const err = $("#lg-err");
  if (msg) { err.textContent = msg; err.hidden = false; } else { err.hidden = true; }
  $("#lg-pass").value = "";
}

function showApp() {
  $("#gate").hidden = true;
  $("#app-wrap").hidden = false;
  $("#whoami").hidden = false;
  $("#me-av").textContent = (ME.full_name || ME.username).trim().charAt(0).toUpperCase();
  $("#me-name").textContent = ME.full_name;
  $("#me-role").textContent = ROLE_LONG[ME.role] || ME.role;
}

const ROLE_LONG = {
  r_prod: "R. PROD · Responsable Production",
  r_cq: "R. CQ · Responsable Contrôle Qualité",
  smq: "SMQ · Assurance Qualité",
  prt: "PRT · Pharmacien Responsable Technique",
};

function initLogin() {
  $("#login-form").onsubmit = async (e) => {
    e.preventDefault();
    const btn = $("#lg-go");
    btn.disabled = true;
    try {
      const r = await api("/api/login", {
        username: $("#lg-user").value.trim(), password: $("#lg-pass").value});
      localStorage.setItem(TOKEN_KEY, r.token);
      ME = {username: r.username, full_name: r.full_name, role: r.role};
      showApp();
      await boot();
    } catch (err) {
      showGate(err.message);
    } finally { btn.disabled = false; }
  };
  $("#logout").onclick = async () => {
    const t = localStorage.getItem(TOKEN_KEY);
    try { await api(`/api/logout?token=${encodeURIComponent(t)}`, {}); } catch (e) {}
    localStorage.removeItem(TOKEN_KEY);
    ME = null;
    $("#whoami").hidden = true;
    showGate();
  };
}

/* --- re-authentication before every signature (21 CFR Part 11.200) --- */
function askPassword(what, whoLine) {
  return new Promise((resolve) => {
    const m = $("#pwmodal"), form = $("#pw-form"), err = $("#pw-err");
    $("#pw-what").textContent = what;
    $("#pw-who").textContent = whoLine;
    $("#pw-pass").value = ""; err.hidden = true;
    m.hidden = false;
    setTimeout(() => $("#pw-pass").focus(), 50);
    const close = (value) => { m.hidden = true; form.onsubmit = null; resolve(value); };
    form.onsubmit = (e) => { e.preventDefault(); close($("#pw-pass").value); };
    $("#pw-cancel").onclick = () => close(null);
  });
}

async function boot() {
  const list = await api("/api/batches");
  if (!list.length) { await api("/api/seed?reset=true", {}); }
  const l2 = await api("/api/batches");
  BID = l2[0].id;
  await populateLots();
  await loadCatalog();
  await refresh();
  initAI();
  initTabs();
  initDropdowns();
  initChangeForm();
  initOffline();
  window.onLangChange = () => { renderChips(); refresh(); };
}

async function populateLots() {
  const list = await api("/api/batches");
  $("#lotpick").innerHTML = list.map(b =>
    `<option value="${b.id}" data-sub="${esc(b.product)}" ${b.id === BID ? "selected" : ""}>${esc(b.lot_name)}</option>`).join("");
  $("#lotpick").onchange = async (e) => {
    BID = +e.target.value;
    AI_HISTORY.length = 0; $("#ai-log").innerHTML = "";
    await refresh();
  };
  syncDropdown("#dd-lot");
}

const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));

/* ---- rich dropdown driven by a hidden native <select> (tablet friendly) ----
   The <select> stays the single source of truth, so every existing read of
   #lotpick.value keeps working untouched. */
function syncDropdown(sel) {
  const dd = $(sel);
  if (!dd) return;
  const native = dd.querySelector("select");
  const opts = [...native.options];
  const cur = opts[native.selectedIndex] || opts[0];
  const initial = (t) => (t || "?").trim().charAt(0).toUpperCase();
  const av = dd.querySelector("[data-dd-av]");
  if (av) av.textContent = initial(cur && cur.textContent);
  dd.querySelector("[data-dd-main]").textContent = cur ? cur.textContent : "—";
  const sub = dd.querySelector("[data-dd-sub]");
  if (cur && cur.dataset.sub) { sub.textContent = cur.dataset.sub; sub.removeAttribute("data-i18n"); }
  dd.querySelector("[data-dd-opts]").innerHTML = opts.map((o, i) => `
    <button class="opt" type="button" role="option" data-i="${i}" aria-selected="${i === native.selectedIndex}">
      <span class="av">${esc(initial(o.textContent))}</span>
      <span class="tx"><b>${esc(o.textContent)}</b><small>${esc(o.dataset.sub || "")}</small></span>
    </button>`).join("");
  dd.querySelectorAll(".opt").forEach((b) => b.onclick = () => {
    native.selectedIndex = +b.dataset.i;
    native.dispatchEvent(new Event("change"));
    closeMenus();
    syncDropdown(sel);
  });
}

function closeMenus() {
  document.querySelectorAll(".dd.open").forEach(d => {
    d.classList.remove("open");
    d.querySelector(".dd-btn").setAttribute("aria-expanded", "false");
  });
}

function initDropdowns() {
  document.querySelectorAll(".dd").forEach((dd) => {
    dd.querySelector(".dd-btn").onclick = (e) => {
      e.stopPropagation();
      const open = dd.classList.contains("open");
      closeMenus();
      dd.classList.toggle("open", !open);
      dd.querySelector(".dd-btn").setAttribute("aria-expanded", String(!open));
    };
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeMenus(); });
}

/* ============ digitalised dossiers: the real .docx, rendered fillable ============
   The backend parses dossier/*.docx into a section/table spec where every blank
   cell of the paper form is a typed field. We render exactly that layout, so an
   operator sees the document they know -- but on a tablet, and audited. */
let FORMS = [], FORM_DOC = null, FORM_STATE = {};

async function loadForms() {
  try {
    const ix = await api(`/api/forms?batch_id=${BID}`);
    FORMS = ix.forms; FORM_SAVED_ROWS = ix.paper_rows_eliminated;
    const prog = ix.progress || {};
    if (!FORM_DOC || !FORMS.some(f => f.doc_key === FORM_DOC)) FORM_DOC = FORMS[0] && FORMS[0].doc_key;
    $("#frm-saved").textContent = TF("frm_saved_rows", {n: ix.paper_rows_eliminated});
    $("#frm-saved").className = "badge good";
    $("#frm-tabs").innerHTML = FORMS.map(f => {
      const p = prog[f.doc_key] || {pct: 0, filled: 0, total: f.field_count};
      return `<button class="frm-tab ${f.doc_key === FORM_DOC ? "active" : ""}" data-doc="${f.doc_key}" type="button">
        <b>${f.doc_key} · ${esc(T("frm_" + f.doc_key) || f.label)}</b>
        <small>${p.filled}/${p.total} ${T("frm_fields")} · ${p.pct}%</small>
        <span class="pg"><span style="width:${p.pct}%"></span></span>
      </button>`;
    }).join("");
    $("#frm-tabs").querySelectorAll(".frm-tab").forEach(b => b.onclick = () => {
      FORM_DOC = b.dataset.doc; loadForms();
    });
    await renderForm(FORM_DOC);
  } catch (e) { $("#frm-body").innerHTML = `<div class="note">⚠ ${e.message}</div>`; }
}
let FORM_SAVED_ROWS = 0;

async function renderForm(doc) {
  if (!doc) return;
  const d = await api(`/api/batch/${BID}/form/${doc}`);
  FORM_STATE = d;
  const v = d.values || {};
  const lock = d.locked
    ? `<div class="frm-lock">🔒 ${TF("frm_locked", {stage: STAGE_LABEL(d.stage)})}</div>` : "";
  const meta = `<div class="frm-meta">${esc(d.form.title.slice(0, 150))} · ${esc(d.form.file)}</div>`;

  const cell = (c, ri) => {
    if (c.type === "label") return `<td class="lbl">${esc(c.text)}</td>`;
    const key = c.key, val = v[key] || "";
    const dis = d.locked ? "disabled" : "";
    if (c.type === "choice") {
      return `<td><span class="frm-choice" data-key="${key}">` + c.options.map(o =>
        `<button type="button" data-v="${o}" class="${val === o ? "on" : ""}" ${dis}
          title="${esc(c.hint || "")}">${o}</button>`).join("") + `</span></td>`;
    }
    const type = c.type === "date" ? "date" : c.type === "time" ? "time" : "text";
    const ph = c.prefix ? esc(c.prefix) : (c.type === "text" ? "…" : "");
    return `<td><input class="frm-in ${val ? "filled" : ""}" type="${type}" data-key="${key}"
      value="${esc(val)}" placeholder="${ph}" ${dis}></td>`;
  };

  const body = d.form.sections.map(s => {
    const blocks = s.blocks.map(b => {
      if (b.kind === "note") return `<div class="frm-note">${esc(b.text)}</div>`;
      const head = b.header
        ? `<thead><tr>${b.header.map(h => `<th>${esc(h)}</th>`).join("")}</tr></thead>` : "";
      const rows = b.rows.map((r, ri) => `<tr>${r.map(c => cell(c, ri)).join("")}</tr>`).join("");
      const add = (b.repeatable && !d.locked)
        ? `<button class="frm-addrow" type="button" data-addrow="${b.index}">＋ ${T("frm_addrow")}</button>` : "";
      const was = b.repeatable
        ? `<div class="frm-meta">${TF("frm_paper_rows", {n: b.paper_rows})}</div>` : "";
      return `<div class="frm-tblwrap"><table class="frm">${head}<tbody>${rows}</tbody></table></div>${add}${was}`;
    }).join("");
    return `<div class="frm-sec">${s.heading ? `<h3>${esc(s.heading)}</h3>` : ""}${blocks}</div>`;
  }).join("");

  $("#frm-body").innerHTML = lock + meta + body;
  wireForm(doc, d.locked);
}

function wireForm(doc, locked) {
  if (locked) return;
  const save = async (key, value, el) => {
    try {
      await api(`/api/batch/${BID}/form/${doc}`, {...actor(), field_key: key, value});
      if (el) el.classList.toggle("filled", !!value);
    } catch (e) { alert("⚠ " + e.message); }
  };
  $("#frm-body").querySelectorAll(".frm-in").forEach(i =>
    i.addEventListener("change", () => save(i.dataset.key, i.value, i)));
  $("#frm-body").querySelectorAll(".frm-choice").forEach(g =>
    g.querySelectorAll("button").forEach(b => b.onclick = () => {
      const on = b.classList.contains("on");
      g.querySelectorAll("button").forEach(x => x.classList.remove("on"));
      if (!on) b.classList.add("on");
      save(g.dataset.key, on ? "" : b.dataset.v);
    }));
  // paper pre-prints 90 blank lines; here you add one when you need one
  $("#frm-body").querySelectorAll("[data-addrow]").forEach(btn => btn.onclick = () => {
    const wrap = btn.previousElementSibling.querySelector("tbody");
    const tpl = wrap.rows[wrap.rows.length - 1];
    const clone = tpl.cloneNode(true);
    const n = wrap.rows.length;
    clone.querySelectorAll("[data-key]").forEach(el => {
      el.dataset.key = el.dataset.key.replace(/#\d+$/, "") + "#" + n;
      if (el.tagName === "INPUT") { el.value = ""; el.classList.remove("filled"); }
      else el.querySelectorAll("button").forEach(b => b.classList.remove("on"));
    });
    wrap.appendChild(clone);
    wireForm(doc, locked);
  });
}

/* ---------------- formula change control ---------------- */
let CATALOG = [], CHG_TOL = 5, CHG_QA = ["smq", "prt"], CHG_REQ = ["r_prod", "smq", "prt"];

async function loadCatalog() {
  try {
    const m = await api("/api/materials");
    CATALOG = m.materials; CHG_TOL = m.tolerance_pct;
    CHG_QA = m.qa_roles; CHG_REQ = m.requester_roles;
    $("#chg-mat").innerHTML = CATALOG.map(x =>
      `<option value="${esc(x.code)}">${esc(x.name)} · ${esc(x.unit)} · ${money(x.unit_cost)}/${esc(x.unit)}</option>`).join("");
  } catch (e) {}
}

function renderChanges(d) {
  const me = actor();
  const list = d.batch.changes || [];
  const pending = list.filter(c => c.status === "pending");
  const badge = $("#chg-badge");
  if (pending.length) {
    badge.style.display = ""; badge.className = "badge warn";
    badge.textContent = TF("chg_pending_n", {n: pending.length});
  } else { badge.style.display = "none"; }

  const canDecide = CHG_QA.includes(me.role);
  $("#changes").innerHTML = list.map(c => {
    const kind = T("chg_kind_" + c.kind);
    const qty = c.kind === "remove" ? `${num(c.old_qty, 2)} → —`
      : c.kind === "add" ? `— → ${num(c.new_qty, 2)}`
      : `${num(c.old_qty, 2)} → ${num(c.new_qty, 2)} (${c.delta_pct == null ? "" : num(c.delta_pct, 1) + "%"})`;
    const who = `${esc(c.requested_by)} · ${roleShort(c.requested_role)}`;
    const decided = c.decided_by
      ? TF("chg_decided", {who: esc(c.decided_by) + " · " + roleShort(c.decided_role), when: new Date(c.decided_at).toLocaleString(loc())})
      : T("chg_await_qa");
    const route = c.route === "minor" ? ` · <span style="color:var(--good-ink)">${TF("chg_minor", {p: CHG_TOL})}</span>` : "";
    const acts = (c.status === "pending" && canDecide && c.requested_by !== me.user)
      ? `<div class="acts">
           <button class="ok" onclick="decideChange(${c.id}, true)">${T("chg_approve")}</button>
           <button class="no" onclick="decideChange(${c.id}, false)">${T("chg_reject")}</button>
         </div>`
      : (c.status === "pending" && canDecide)
        ? `<div class="acts"><span class="cap" style="max-width:120px">${T("chg_self")}</span></div>` : "";
    return `<div class="chg ${c.status}">
      <div class="body">
        <b>${kind} — ${esc(c.material)}</b>
        <div class="meta">${qty} ${esc(c.unit || "")}${route}<br>
          «${esc(c.reason)}» — ${who}<br>${decided}</div>
      </div>${acts}</div>`;
  }).join("");
}

async function decideChange(id, approve) {
  const me = actor();
  const note = approve ? "" : (prompt(T("chg_reject_note")) || "");
  try { await api(`/api/batch/${BID}/changes/${id}`, {...me, approve, note}); }
  catch (e) { alert("⚠ " + e.message); }
  refresh();
}

async function requestChange(payload) {
  const me = actor();
  try {
    const r = await api(`/api/batch/${BID}/changes`, {...me, ...payload});
    if (r.status === "pending") alert(T("chg_sent_qa"));
  } catch (e) { alert("⚠ " + e.message); }
  refresh();
}

async function amendMaterial(id, oldQty, unit) {
  const v = prompt(TF("chg_amend_prompt", {old: num(oldQty, 3), unit: unit || ""}), oldQty);
  if (v === null) return;
  const q = parseFloat(v);
  if (isNaN(q) || q <= 0) { alert(T("chg_bad_qty")); return; }
  const reason = prompt(T("chg_reason_prompt"));
  if (!reason || !reason.trim()) { alert(T("chg_need_reason")); return; }
  requestChange({kind: "amend", dispense_id: id, new_qty: q, reason: reason.trim()});
}

async function removeMaterial(id, name) {
  const reason = prompt(TF("chg_remove_prompt", {m: name}));
  if (!reason || !reason.trim()) return;
  requestChange({kind: "remove", dispense_id: id, reason: reason.trim()});
}

/* ---------------- AI copilot ---------------- */
const AI_HISTORY = [];
async function aiHealth() {
  try {
    const h = await api("/api/assistant/health");
    const b = $("#ai-health");
    b.className = "badge " + (h.available ? "good" : "crit");
    b.textContent = h.available ? `● ${h.chat_model}` : T("ai_offline");
  } catch (e) {}
}
function aiPush(role, text) {
  const log = $("#ai-log");
  const d = document.createElement("div");
  d.className = "ai-b " + (role === "user" ? "user" : "bot");
  d.textContent = text; log.appendChild(d); log.scrollTop = log.scrollHeight;
  return d;
}
async function aiAsk(msg) {
  if (!msg) return;
  aiPush("user", msg); AI_HISTORY.push({role: "user", content: msg});
  const t = aiPush("bot", "…"); t.classList.add("think");
  const log = $("#ai-log");
  try {
    const r = await fetch("/api/assistant/chat/stream", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({batch_id: BID, message: msg, history: AI_HISTORY.slice(0, -1), lang: window.i18n ? window.i18n.lang : "fr"}),
    });
    if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || r.status); }
    const sources = (r.headers.get("X-Sources") || "").split(",").filter(Boolean);
    t.classList.remove("think"); t.textContent = "";
    const reader = r.body.getReader(), dec = new TextDecoder();
    let full = "";
    for (;;) {
      const {value, done} = await reader.read();
      if (done) break;
      full += dec.decode(value, {stream: true});
      t.textContent = full; log.scrollTop = log.scrollHeight;
    }
    if (sources.length) { const s = document.createElement("span"); s.className = "src"; s.textContent = T("ai_sources") + sources.join(", "); t.appendChild(s); }
    AI_HISTORY.push({role: "assistant", content: full});
  } catch (e) { t.classList.remove("think"); t.textContent = "⚠ " + e.message; }
  log.scrollTop = log.scrollHeight;
}
function renderChips() {
  $("#ai-chips").innerHTML = CHIP_KEYS.map(k => `<span class="chip">${T(k)}</span>`).join("");
  $("#ai-chips").querySelectorAll(".chip").forEach(c => c.onclick = () => aiAsk(c.textContent));
}
function initAI() {
  aiHealth();
  renderChips();
  $("#ai-send").onclick = () => { const m = $("#ai-msg").value.trim(); $("#ai-msg").value = ""; aiAsk(m); };
  $("#ai-msg").addEventListener("keydown", e => { if (e.key === "Enter") { const m = e.target.value.trim(); e.target.value = ""; aiAsk(m); } });
  $("#ai-report").onclick = async () => {
    const t = aiPush("bot", T("ai_report_gen")); t.classList.add("think");
    try { const r = await api(`/api/assistant/report?batch_id=${BID}&lang=${window.i18n ? window.i18n.lang : "fr"}`, {}); t.classList.remove("think"); t.textContent = r.report; }
    catch (e) { t.classList.remove("think"); t.textContent = "⚠ " + e.message; }
  };
}

function initTabs() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.onclick = () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b === btn));
      document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.toggle("active", panel.dataset.panel === btn.dataset.tab));
    };
  });
}

async function refresh() {
  const [d, a, dossier] = await Promise.all([
    api(`/api/batch/${BID}`),
    api(`/api/audit?batch_id=${BID}`),
    api("/api/dossier"),
  ]);
  render(d, a, dossier.documents || [], dossier.tasks || []);
  refreshEquipment();
  loadForms();
}

const STATUS_COLOR = {running: "var(--good)", warning: "var(--warning)", alarm: "var(--critical)"};
async function refreshEquipment() {
  let e;
  try { e = await api(`/api/batch/${BID}/equipment`); } catch (err) { return; }
  const s = e.summary;
  const sum = `<div class="eqsum">
    <span class="pill" style="color:var(--good);border-color:var(--good)">● ${s.running} ${T("st_running")}</span>
    ${s.warning ? `<span class="pill" style="color:var(--warning);border-color:var(--warning)">● ${s.warning} ${T("st_warning")}</span>` : ""}
    ${s.alarm ? `<span class="pill" style="color:var(--critical);border-color:var(--critical)">● ${s.alarm} ${T("st_alarm")}</span>` : ""}
  </div>`;
  const cards = e.machines.map(m => {
    const col = STATUS_COLOR[m.status];
    const tel = m.telemetry.map(t =>
      `<span class="tv ${t.ok ? "" : "bad"}"><b>${num(t.value, 2)}</b> ${t.unit} · ${t.label}</span>`).join("");
    return `<div class="eqcard" style="--edge:${col}">
      <div class="eh">
        <div><div class="nm">${m.id} · ${m.name}</div><div class="md">${m.brand} ${m.model}</div></div>
        <span class="sdot" style="background:${col}"></span>
      </div>
      <span class="proto">⇄ ${m.protocol}</span>
      <div class="tel">${tel}</div>
      <div class="cal">🛠 ${TF("eq_cal", {n: m.cal_due_days})} · ${m.cal_date}</div>
    </div>`;
  }).join("");
  $("#equipment").innerHTML = sum + `<div class="eqgrid">${cards}</div>`;
}

function formatBytes(n) {
  if (n == null) return "—";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let v = n;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i += 1; }
  return `${v.toFixed(v < 10 && i > 0 ? 1 : 0)} ${units[i]}`;
}

function renderWorkflow(d, docs, tasks) {
  const wf = d.workflow || {};
  const statusText = wf.headline || "Draft dossier";
  const progress = wf.progress || 0;
  const badgeClass = wf.status === "released" ? "good" : wf.status === "quality_review" ? "warn" : wf.status === "draft" ? "neutral" : "neutral";
  $("#workflow-status").className = `badge ${badgeClass}`;
  $("#workflow-status").textContent = statusText;
  $("#workflow-headline").innerHTML = `<strong>${statusText}</strong><div style="color:var(--muted);font-size:12px;margin-top:3px">${wf.status || "draft"}</div>`;
  $("#workflow-progress-bar").style.width = `${progress}%`;
  $("#workflow-doc-count").textContent = `${docs.length} docs`;
  const notesMarkup = (wf.notifications || []).map(item => `<div class="item">${item}</div>`).join("");
  const taskMarkup = tasks.map(task => `<div class="item"><strong>${task.title}</strong><div style="color:var(--muted);margin-top:3px">${task.detail}</div></div>`).join("");
  $("#workflow-notes-inline").innerHTML = notesMarkup || taskMarkup || `<div class="item">No pending actions.</div>`;
  $("#workflow-notes-panel").innerHTML = taskMarkup || notesMarkup || `<div class="item">No pending actions.</div>`;
  const docMarkup = docs.length
    ? docs.slice(0, 6).map(doc => `<a class="doc-pill" href="/dossier/${encodeURIComponent(doc.name)}" target="_blank" rel="noopener"><strong>${doc.name}</strong><small>${doc.kind.toUpperCase()} · ${formatBytes(doc.size_bytes)}</small></a>`).join("")
    : `<div class="item">Dossier pack is being prepared.</div>`;
  $("#workflow-docs-inline").innerHTML = docMarkup;
  $("#workflow-docs-panel").innerHTML = docMarkup;
}

function renderRoleFocus(d) {
  const role = (actor().role || "").toLowerCase();
  const wf = d.workflow || {};
  const pending = (wf.notifications || []).length;
  const stages = d.batch?.stages || [];
  const stageMap = Object.fromEntries(stages.map(s => [s.name, s]));
  const tasks = [];

  if (role === "r_prod") {
    tasks.push({title: T("role_task_clearance"), detail: T("role_task_clearance_detail")});
    if (stageMap.fabrication?.status !== "signed") {
      tasks.push({title: T("role_task_weighing"), detail: T("role_task_weighing_detail")});
    }
  } else if (role === "r_cq") {
    tasks.push({title: T("role_task_quality"), detail: T("role_task_quality_detail")});
    if (pending) {
      tasks.push({title: T("role_task_release"), detail: TF("role_task_release_detail", {n: pending})});
    }
  } else if (role === "smq") {
    tasks.push({title: T("role_task_review"), detail: T("role_task_review_detail")});
  } else {
    tasks.push({title: T("role_task_overview"), detail: T("role_task_overview_detail")});
  }

  if (stageMap.quality?.status !== "signed") {
    tasks.push({title: T("role_task_sign"), detail: T("role_task_sign_detail")});
  }

  const badgeText = role === "r_prod" ? T("role_prod") : role === "r_cq" ? T("role_cq") : role === "smq" ? T("role_smq") : role === "prt" ? T("role_prt") : T("role_other");
  $("#role-badge").textContent = badgeText;
  $("#role-list").innerHTML = tasks.slice(0, 4).map(task => `
    <div class="role-item">
      <div class="role-mark"></div>
      <div>
        <strong>${task.title}</strong>
        <span>${task.detail}</span>
      </div>
    </div>`).join("");
}

function render(d, a, docs, tasks) {
  const b = d.batch;
  renderWorkflow(d, docs, tasks);
  renderRoleFocus(d);
  $("#lotname").textContent = `${T("lbl_lot")} ${b.lot_name}`;
  const dates = b.mfg_date ? ` · ${T("lbl_mfg")} ${b.mfg_date} · ${T("lbl_expiry")} ${b.expiry_date}` : "";
  $("#lotsub").textContent = `${b.product} · OF ${b.of_ref} · OC ${b.oc_ref} · ${T("lbl_order")} ${b.sale_order} · ${T("lbl_target")} ${b.qty_target} ${T("lbl_units")}${dates}`;
  $("#lotstate").innerHTML = b.state === "released"
    ? `<span class="badge good">${T("state_released")}</span>`
    : `<span class="badge warn">${T("state_open")}</span>`;

  FILL_UNIT = b.fill_unit || "mL";
  renderTiles(d);
  renderStepper(b, d.energy);
  renderChecklist(b);
  renderDispense(d);
  renderChanges(d);
  renderDeviations(d);
  renderPackaging(d);
  renderSPC(d.spc);
  renderEnergy(d.energy);
  renderAudit(a);
}

function renderEnergy(e) {
  if (!e.complete) {
    $("#energy").innerHTML = `<div class="note">${T("en_empty")}</div>`;
    return;
  }
  const byStage = {};
  e.per_stage.forEach(s => byStage[s.stage] = s);
  const order = STAGE_ORDER;
  const rows = order.map(st => {
    const s = byStage[st] || {kwh: 0, co2_kg: 0};
    return `<tr><td>${STAGE_LABEL(st)}</td><td>${num(s.kwh, 2)}</td><td>${num(s.co2_kg, 2)}</td></tr>`;
  }).join("");
  $("#energy").innerHTML = `
    <div class="tiles" style="grid-template-columns:1fr 1fr;margin-bottom:12px">
      <div class="tile"><div class="k">${T("en_per_unit")}</div><div class="v">${num(e.kwh_per_unit, 3)} <span style="font-size:14px">kWh</span></div><div class="d">${TF("en_total", {v: num(e.total_kwh, 1)})}</div></div>
      <div class="tile"><div class="k">${T("en_co2_unit")}</div><div class="v">${num(e.co2_g_per_unit, 0)} <span style="font-size:14px">g</span></div><div class="d">${TF("en_co2_batch", {v: num(e.total_co2_kg, 1)})}</div></div>
    </div>
    <table><tr><th>${T("en_th_dossier")}</th><th>kWh</th><th>kg CO₂</th></tr>${rows}</table>
    <div class="cap" style="margin-top:8px">${TF("en_factor", {v: e.co2_factor})}</div>`;
}

function renderTiles(d) {
  const k = d.kpis, mb = d.mass_balance;
  const gap = mb.cost_gap;
  const gapBadge = gap == null ? "" :
    `<div class="d" style="color:${gap > 0 ? 'var(--critical)' : 'var(--good-ink)'}">${gap > 0 ? '▲' : '▼'} ${money(Math.abs(gap))} ${T("tile_vs_odoo")}</div>`;
  const tiles = [
    {k: T("tile_unit_cost"), v: k.true_unit_material_cost == null ? "—" : money(k.true_unit_material_cost), d: k.good_units ? TF("tile_unit_cost_d", {n: k.good_units}) : T("tile_pending_cond")},
    {k: T("tile_loss"), v: money(mb.loss_cost), d: mb.loss_cost == null ? T("tile_loss_incomplete") : T("tile_loss_kpi")},
    {k: T("tile_yield"), v: k.yield_pct == null ? "—" : num(k.yield_pct, 1) + " %", d: k.good_units == null ? "—" : `${k.good_units}/${k.target_units}`},
    {k: T("tile_total_cost"), v: money(mb.real_cost), d: gapBadge ? "" : T("tile_weighing"), extra: gapBadge},
  ];
  $("#tiles").innerHTML = tiles.map(t =>
    `<div class="tile"><div class="k">${t.k}</div><div class="v">${t.v}</div><div class="d">${t.d}</div>${t.extra || ""}</div>`
  ).join("");
}

function renderStepper(b, energy) {
  const sigByStage = {};
  b.signatures.forEach(s => sigByStage[s.stage] = s);
  const kwhByStage = {};
  (energy && energy.per_stage || []).forEach(s => kwhByStage[s.stage] = s.kwh);
  const me = actor();
  const order = STAGE_ORDER;
  $("#stepper").innerHTML = order.map((name, i) => {
    const stage = b.stages.find(s => s.name === name);
    const signed = stage.status === "signed";
    const sig = sigByStage[name];
    const active = !signed && (i === 0 || b.stages.find(s => s.name === order[i - 1]).status === "signed");
    const canSign = active && !signed && b.state !== "released";
    let inner = "";
    if (signed) {
      inner = `<div class="sig">✍ <b>${sig.user}</b> — ${sig.meaning}<br>${new Date(sig.signed_at).toLocaleString(loc())}
               <br><span class="hash">#${sig.record_hash.slice(0, 24)}…</span></div>`;
    } else {
      inner = `<button class="btn" ${canSign ? "" : "disabled"} onclick="signStage('${name}')">${TF("st_sign", {role: roleShort(me.role)})}</button>`;
    }
    const badge = signed ? `<span class="dot" style="background:var(--good)"></span>`
      : active ? `<span class="dot" style="background:var(--series)"></span>`
      : `<span class="dot" style="background:var(--axis)"></span>`;
    const kwh = kwhByStage[name];
    const kwhTag = kwh ? `<span class="badge neutral" style="font-size:10px">⚡ ${kwh.toFixed(1)} kWh</span>` : "";
    return `<div class="step ${signed ? "signed" : ""} ${active ? "active" : ""}">
      <div class="bar"></div>
      <h3>${badge} ${i + 1}. ${STAGE_LABEL(name)}</h3>
      <div class="sub">${signed ? T("st_signed") : active ? T("st_active") : T("st_waiting")} ${kwhTag}</div>
      ${inner}
    </div>`;
  }).join("");
}

function renderChecklist(b) {
  const done = b.checklist.filter(c => c.ok === 1).length;
  const fail = b.checklist.some(c => c.ok === 0);
  const badge = $("#clr-badge");
  badge.className = "badge " + (fail ? "crit" : done === b.checklist.length ? "good" : "neutral");
  badge.textContent = fail ? T("clr_anomaly") : `${done}/${b.checklist.length}`;
  $("#checklist").innerHTML = b.checklist.map(c => `
    <div class="chk">
      <input type="checkbox" ${c.ok === 1 ? "checked" : ""} onchange="toggleChk(${c.id}, this.checked)">
      <span class="lbl">${c.label}</span>
      ${c.ok === 0 ? `<span class="esc">⚠ ${T("clr_escalated")} ${c.escalated_to || T("clr_responsible")}</span>` : ""}
    </div>`).join("");
}

function renderDispense(d) {
  const mb = d.mass_balance;
  const me = actor();
  // the formula is editable only before the fabrication signature, and only by
  // a manufacturing/QA role — R. CQ controls the product, it never reformulates.
  const fabSigned = (d.batch.stages.find(s => s.name === "fabrication") || {}).status === "signed";
  const canEdit = !fabSigned && d.batch.state !== "released" && CHG_REQ.includes(me.role);
  $("#add-mat").disabled = !canEdit;
  $("#add-mat").title = canEdit ? "" : (fabSigned ? T("chg_locked") : T("chg_no_right"));
  if (!canEdit) $("#chgform").classList.remove("open");

  const head = `<tr><th>${T("th_material")}</th><th>${T("th_theo")}</th><th>${T("th_weighed")}</th><th>${T("th_loss")}</th><th>${T("th_lossp")}</th><th>${T("th_linecost")}</th><th></th></tr>`;
  const rows = d.batch.dispense.map((r, i) => {
    const l = mb.lines[i];
    const lossCol = l.loss_pct == null ? "—" : `<span style="color:${l.loss_pct > 1.5 ? 'var(--serious)' : 'var(--ink-2)'}">${num(l.loss_pct, 2)}%</span>`;
    const sub = r.supplier ? `${r.unit} · ${r.supplier} · ${T("lbl_rmlot")} ${r.rm_lot} · ${T("lbl_exp")} ${r.rm_expiry}` : r.unit;
    return `<tr>
      <td>${r.material}<div style="color:var(--muted);font-size:10.5px">${sub}</div></td>
      <td>${num(r.qty_target, 2)}</td>
      <td><input class="num" type="number" step="0.001" value="${r.qty_dispensed ?? ""}" id="disp-${r.id}" placeholder="${num(r.qty_target, 2)}"></td>
      <td><input class="num" type="number" step="0.001" value="${r.qty_loss ?? 0}" id="loss-${r.id}"></td>
      <td>${lossCol}</td>
      <td>${l.line_cost == null ? "—" : money(l.line_cost)}</td>
      <td>${canEdit ? `<span class="mat-act">
        <button title="${T("chg_amend")}" onclick="amendMaterial(${r.id}, ${r.qty_target}, '${esc(r.unit)}')">✎</button>
        <button title="${T("chg_remove")}" onclick="removeMaterial(${r.id}, '${esc(r.material).replace(/'/g, "")}')">✕</button>
      </span>` : ""}</td>
    </tr>`;
  }).join("");
  const foot = `<tr style="font-weight:700"><td>${T("word_total")}</td><td></td><td></td><td></td><td></td>
    <td>${mb.real_cost == null ? money(mb.theoretical_cost) + " (" + T("word_theo") + ")" : money(mb.real_cost)}</td><td></td></tr>`;
  $("#disp").innerHTML = head + rows + foot;
  d.batch.dispense.forEach(r => {
    const save = () => saveDispense(r.id);
    $(`#disp-${r.id}`).addEventListener("change", save);
    $(`#loss-${r.id}`).addEventListener("change", save);
  });
  $("#mb-note").innerHTML = mb.complete
    ? TF("mb_done", {theo: money(mb.theoretical_cost), real: money(mb.real_cost), gap: money(mb.cost_gap), loss: money(mb.loss_cost)})
    : T("mb_todo");
}

function driftToward(s) { return s && s.includes("LSL") ? T("dir_lsl") : T("dir_usl"); }
function ruleLabel(s) {
  if (!s) return s;
  if (s.includes("3 sigma") || s.includes("3σ")) return T("rule_3sigma");
  if (s.includes("2/3")) return T("rule_2of3");
  if (s.includes("6 points") || s.includes("derive") || s.includes("dérive")) return T("rule_drift6");
  return s;
}

/* ---------- SPC control chart (SVG, single series = subgroup mean) ---------- */
function renderSPC(spc) {
  const W = 520, H = 240, m = {t: 14, r: 14, b: 26, l: 40};
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const pts = spc.points;
  const cl = spc.control_limits;
  const ys = [spc.lsl, spc.usl, spc.norm];
  pts.forEach(p => ys.push(p.mean));
  if (cl) ys.push(cl.x_ucl, cl.x_lcl);
  let lo = Math.min(...ys), hi = Math.max(...ys);
  const pad = (hi - lo) * 0.15 || 5; lo -= pad; hi += pad;
  const x = (i) => m.l + (pts.length <= 1 ? iw / 2 : iw * i / (pts.length - 1));
  const y = (v) => m.t + ih * (1 - (v - lo) / (hi - lo));

  const refLine = (v, color, dash, label) => `
    <line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}" stroke="${color}" stroke-width="1.5" stroke-dasharray="${dash}"/>
    <text x="${W - m.r}" y="${y(v) - 3}" text-anchor="end" font-size="10" fill="var(--muted)">${label} ${num(v, 0)}</text>`;

  let refs = "";
  refs += refLine(spc.usl, "var(--critical)", "5 4", "USL");
  refs += refLine(spc.lsl, "var(--critical)", "5 4", "LSL");
  refs += refLine(spc.norm, "var(--axis)", "2 3", T("spc_target"));
  if (cl) { refs += refLine(cl.x_ucl, "var(--axis)", "1 3", "UCL"); refs += refLine(cl.x_lcl, "var(--axis)", "1 3", "LCL"); }

  const sigIdx = new Set(spc.signals.map(s => s.idx));
  const path = pts.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.mean).toFixed(1)}`).join(" ");
  const dots = pts.map((p, i) => {
    const bad = sigIdx.has(i) || p.verdict === "FAIL";
    return `<circle cx="${x(i).toFixed(1)}" cy="${y(p.mean).toFixed(1)}" r="5"
      fill="${bad ? "var(--critical)" : "var(--series)"}" stroke="var(--surface)" stroke-width="2">
      <title>${new Date(p.at).toLocaleTimeString(loc())} — X̄ ${num(p.mean, 1)} ${FILL_UNIT}, ${T("th_loss")} ${num(p.range, 1)} ${FILL_UNIT}, ${p.verdict}</title>
    </circle>`;
  }).join("");

  const body = pts.length === 0
    ? `<text x="${W / 2}" y="${H / 2}" text-anchor="middle" fill="var(--muted)" font-size="12">${T("spc_empty")}</text>`
    : `${refs}<path d="${path}" fill="none" stroke="var(--series)" stroke-width="2"/>${dots}`;

  $("#spc").innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" dir="ltr">
    <text x="${m.l}" y="11" font-size="10" fill="var(--muted)">${FILL_UNIT}</text>${body}</svg>`;

  const f = spc.forecast;
  $("#spc-forecast").innerHTML = f
    ? `<div class="note forecast">${TF("spc_forecast", {toward: driftToward(f.toward), n: num(f.samples_to_spec_breach, 0), min: num(f.minutes_to_spec_breach, 0)})}</div>`
    : (spc.signals.length ? `<div class="note forecast">${TF("spc_signals", {list: spc.signals.map(s => ruleLabel(s.rule)).join(", ")})}</div>` : "");
}

function renderAudit(a) {
  const ok = a.integrity.valid;
  const badge = $("#integ");
  badge.className = "badge " + (ok ? "good" : "crit");
  badge.textContent = ok ? TF("int_ok", {n: a.integrity.entries}) : TF("int_broken", {id: a.integrity.broken_at});
  $("#audit").innerHTML = a.entries.slice().reverse().map(e => `
    <div class="e">
      <div class="at">${new Date(e.at).toLocaleTimeString(loc())}<br><span style="color:var(--ink-2)">${e.user}</span></div>
      <div><b>${e.action}</b> <span style="color:var(--ink-2)">${fmtDetail(e.detail)}</span>
        <div class="ha">#${e.hash.slice(0, 32)}…</div></div>
    </div>`).join("");
}
function fmtDetail(d) { try { const o = JSON.parse(d); return Object.entries(o).map(([k, v]) => `${k}=${v}`).join(", "); } catch { return d; } }

/* ---------------- actions ---------------- */
async function signStage(stage) {
  const me = actor();
  // A signature is never one click: the password is re-entered every time.
  const password = await askPassword(
    TF("auth_sign_what", {stage: STAGE_LABEL(stage)}),
    `${ME.full_name} · ${ROLE_LONG[ME.role] || ME.role}`);
  if (password === null) return;
  try {
    const r = await api(`/api/batch/${BID}/sign`,
                        {...me, stage, meaning: SIGN_MEANING(stage), password});
    toast(TF("auth_signed", {who: r.signed_by, stage: STAGE_LABEL(stage)}));
  } catch (e) { alert(T("sign_refused") + e.message); }
  refresh();
}

function toast(msg) {
  const d = document.createElement("div");
  d.textContent = msg;
  d.style.cssText = "position:fixed;left:50%;bottom:24px;transform:translateX(-50%);z-index:300;" +
    "padding:12px 18px;border-radius:12px;font-weight:600;font-size:13px;color:#fff;" +
    "background:linear-gradient(100deg,#6C63FF,#38BDF8);box-shadow:0 12px 32px rgba(0,0,0,.35)";
  document.body.appendChild(d);
  setTimeout(() => d.remove(), 3200);
}

/* ---------------- deviations / CAPA ---------------- */
const SEV_ORDER = {critical: 0, major: 1, minor: 2};

function renderDeviations(d) {
  const list = (d.batch.deviations || []).slice()
    .sort((a, b) => (a.status === b.status ? SEV_ORDER[a.severity] - SEV_ORDER[b.severity]
                                          : a.status === "open" ? -1 : 1));
  const open = list.filter(x => x.status === "open").length;
  const badge = $("#dev-badge");
  badge.className = "badge " + (open ? "crit" : list.length ? "good" : "neutral");
  badge.textContent = open ? TF("dev_open_n", {n: open})
                           : list.length ? T("dev_all_closed") : T("dev_none");

  const canClose = CHG_QA.includes(ME.role);
  $("#deviations").innerHTML = list.length ? list.map(x => {
    const closed = x.status === "closed";
    const closure = closed
      ? `<div class="meta"><b style="display:inline">${T("dev_cause")}</b> ${esc(x.root_cause)}<br>
           <b style="display:inline">CAPA</b> ${esc(x.capa)}<br>
           ${TF("dev_closed_by", {who: esc(x.closed_by), when: new Date(x.closed_at).toLocaleString(loc())})}
           — <b style="display:inline">${T("dispo_" + x.disposition)}</b></div>`
      : (canClose
          ? `<button class="btn" style="margin-top:8px;font-size:12px;padding:7px 12px"
               onclick="openDevForm(${x.id})">${T("dev_close")}</button>
             <form class="devform" id="devf-${x.id}" onsubmit="return closeDev(event,${x.id})">
               <label><span>${T("dev_disposition")}</span>
                 <select id="devd-${x.id}">
                   <option value="accept">${T("dispo_accept")}</option>
                   <option value="rework">${T("dispo_rework")}</option>
                   <option value="reject">${T("dispo_reject")}</option>
                 </select></label>
               <label><span>${T("dev_cause")}</span><textarea id="devc-${x.id}" required></textarea></label>
               <label><span>${T("dev_capa")}</span><textarea id="deva-${x.id}" required></textarea></label>
               <div class="row">
                 <button class="btn" type="submit">${T("dev_confirm")}</button>
                 <button class="btn ghost" type="button" onclick="openDevForm(${x.id})">${T("chg_cancel")}</button>
               </div>
             </form>`
          : `<div class="meta">${T("dev_await_qa")}</div>`);
    return `<div class="dev ${closed ? "closed" : ""}">
      <span class="sev ${x.severity}">${T("sev_" + x.severity)}</span>
      <div class="body">
        <span class="ref">${x.ref}</span>
        <b>${esc(x.title)}</b>
        <div class="meta">${esc(x.detail || "")}<br>
          ${TF("dev_opened", {who: esc(x.opened_by), when: new Date(x.opened_at).toLocaleString(loc())})}</div>
        ${closure}
      </div></div>`;
  }).join("") : `<div class="note">${T("dev_none_note")}</div>`;
}

function openDevForm(id) { $(`#devf-${id}`).classList.toggle("open"); }

async function closeDev(ev, id) {
  ev.preventDefault();
  const disposition = $(`#devd-${id}`).value;
  const root_cause = $(`#devc-${id}`).value.trim();
  const capa = $(`#deva-${id}`).value.trim();
  if (!root_cause || !capa) { alert(T("dev_need_all")); return false; }
  // Closing a deviation is a signed act too.
  const password = await askPassword(T("dev_close_what"),
                                     `${ME.full_name} · ${ROLE_LONG[ME.role]}`);
  if (password === null) return false;
  try {
    await api(`/api/batch/${BID}/deviation/${id}/close`,
              {...actor(), password, disposition, root_cause, capa});
    toast(T("dev_closed_ok"));
  } catch (e) { alert("⚠ " + e.message); }
  refresh();
  return false;
}

/* ---------------- packaging article reconciliation ---------------- */
const PKG_FIELDS = ["issued", "used", "returned", "waste"];

function renderPackaging(d) {
  const pk = d.batch.packaging || {lines: []};
  const badge = $("#pkg-badge");
  if (!pk.lines.length) { badge.textContent = "—"; badge.className = "badge neutral"; }
  else if (pk.balanced) { badge.textContent = T("pkg_balanced"); badge.className = "badge good"; }
  else if (pk.complete) { badge.textContent = TF("pkg_variance", {p: pk.worst_variance_pct}); badge.className = "badge crit"; }
  else { badge.textContent = T("pkg_incomplete"); badge.className = "badge neutral"; }

  const stages = ["cond_primaire", "cond_secondaire"];
  const signed = Object.fromEntries(d.batch.stages.map(s => [s.name, s.status === "signed"]));
  $("#packaging").innerHTML = stages.map(st => {
    const rows = pk.lines.filter(l => l.stage === st);
    if (!rows.length) return "";
    const lock = signed[st];
    return `<h4>${STAGE_LABEL(st)}${lock ? " 🔒" : ""}</h4>
      <div style="overflow-x:auto"><table class="pkg-t">
        <tr><th>${T("pkg_code")}</th><th>${T("pkg_article")}</th>
          ${PKG_FIELDS.map(f => `<th>${T("pkg_" + f)}</th>`).join("")}
          <th>${T("pkg_var")}</th></tr>
        ${rows.map(r => `<tr>
          <td style="font-family:ui-monospace,monospace;font-size:11px">${esc(r.code)}</td>
          <td>${esc(r.label)}</td>
          ${PKG_FIELDS.map(f => `<td><input type="number" step="1" min="0" inputmode="numeric"
             value="${r[f] ?? ""}" data-code="${esc(r.code)}" data-field="${f}"
             ${lock ? "disabled" : ""}></td>`).join("")}
          <td class="pkg-var ${r.ok === null ? "" : r.ok ? "ok" : "bad"}">
            ${r.variance === null ? "—" : (r.variance > 0 ? "+" : "") + num(r.variance, 0)}
            ${r.variance === null ? "" : `<div style="font-size:10px;font-weight:400;color:var(--muted)">${num(r.variance_pct, 2)}%</div>`}
          </td></tr>`).join("")}
      </table></div>`;
  }).join("");

  $("#packaging").querySelectorAll("input:not([disabled])").forEach(i =>
    i.addEventListener("change", async () => {
      const v = parseFloat(i.value);
      if (isNaN(v) || v < 0) { alert(T("chg_bad_qty")); return; }
      try {
        await api(`/api/batch/${BID}/packaging`,
                  {...actor(), code: i.dataset.code, field: i.dataset.field, value: v});
      } catch (e) { alert("⚠ " + e.message); }
      refresh();
    }));
}

/* ---------------- offline capture queue ----------------
   Signing is intentionally absent: verifying a password offline would mean
   caching credentials on a shared tablet. Capture queues; signature waits. */
const OUTBOX_KEY = "bt_outbox";
const outbox = {
  all: () => { try { return JSON.parse(localStorage.getItem(OUTBOX_KEY) || "[]"); } catch { return []; } },
  save: (q) => localStorage.setItem(OUTBOX_KEY, JSON.stringify(q)),
  add(kind, batch_id, payload) {
    const q = this.all();
    q.push({op_id: (crypto.randomUUID ? crypto.randomUUID() : String(Date.now() + Math.random())),
            kind, batch_id, client_at: new Date().toISOString(), payload});
    this.save(q);
    paintOffline();
  },
};

function paintOffline() {
  const n = outbox.all().length;
  const bar = $("#offline-bar");
  bar.classList.toggle("on", !navigator.onLine || n > 0);
  $("#off-count").textContent = n;
}

async function flushOutbox() {
  const q = outbox.all();
  if (!q.length || !navigator.onLine || !ME) return;
  try {
    const r = await api("/api/sync", {...actor(), ops: q});
    const done = new Set([...r.applied, ...r.skipped]);
    outbox.save(q.filter(op => !done.has(op.op_id)));
    if (r.applied.length) toast(TF("off_synced", {n: r.applied.length}));
    if (r.failed.length) console.warn("sync failures", r.failed);
    paintOffline();
    refresh();
  } catch (e) { /* still offline; keep the queue */ }
}

function initOffline() {
  addEventListener("online", () => { paintOffline(); flushOutbox(); });
  addEventListener("offline", paintOffline);
  paintOffline();
  flushOutbox();
}
async function toggleChk(id, checked) {
  const me = actor();
  const body = {...me, ok: checked};
  if (!checked) { body.note = "non conforme"; body.escalate_to = "responsable.production"; }
  await api(`/api/batch/${BID}/checklist/${id}`, body); refresh();
}
async function saveDispense(id) {
  const me = actor();
  const dispensed = parseFloat($(`#disp-${id}`).value); const loss = parseFloat($(`#loss-${id}`).value) || 0;
  if (isNaN(dispensed)) return;
  await api(`/api/batch/${BID}/dispense/${id}`, {...me, dispensed, loss}); refresh();
}

$("#simdisp").onclick = async () => {
  const me = actor(); const d = await api(`/api/batch/${BID}`);
  for (const r of d.batch.dispense) {
    const t = r.qty_target;
    const dispensed = +(t * (0.997 + Math.random() * 0.004)).toFixed(3);
    const loss = +(t * (0.002 + Math.random() * 0.006)).toFixed(4);
    await api(`/api/batch/${BID}/dispense/${r.id}`, {...me, dispensed, loss});
  }
  const tgt = d.batch.qty_target || 800;
  await api(`/api/batch/${BID}/units`, {...me, good_units: tgt - 3 - Math.floor(Math.random() * 10)});
  refresh();
};
$("#eq-refresh").onclick = () => refreshEquipment();
$("#simenergy").onclick = async () => { await api(`/api/batch/${BID}/energy/simulate`, {...actor()}); refresh(); };
$("#qc1").onclick = async () => { await api(`/api/batch/${BID}/qc/simulate`, {...actor(), drift: false}); refresh(); };
$("#qcdrift").onclick = async () => { await api(`/api/batch/${BID}/qc/simulate`, {...actor(), drift: true}); refresh(); };
$("#tamper").onclick = async () => {
  const a = await api(`/api/audit?batch_id=${BID}`);
  if (!a.entries.length) return;
  await api(`/api/demo/tamper/${a.entries[3] ? a.entries[3].id : a.entries[0].id}`, {});
  refresh();
};
$("#pdf").onclick = () => { window.open(`/api/batch/${BID}/report.pdf`, "_blank"); };
$("#reset").onclick = async () => { await api("/api/seed?reset=true", {}); boot(); };
document.addEventListener("click", closeMenus);
document.querySelectorAll(".dd-menu").forEach(m => m.addEventListener("click", e => e.stopPropagation()));

function initChangeForm() {
  const form = $("#chgform");
  const hint = () => {
    const me = actor();
    $("#chg-hint").textContent = CHG_QA.includes(me.role)
      ? TF("chg_hint_qa", {role: roleShort(me.role)}) : T("chg_hint_prod");
  };
  $("#add-mat").onclick = () => { form.classList.toggle("open"); hint(); };
  $("#chg-cancel").onclick = () => form.classList.remove("open");
  $("#chg-submit").onclick = async () => {
    const code = $("#chg-mat").value;
    const m = CATALOG.find(x => x.code === code);
    const q = parseFloat($("#chg-qty").value);
    const reason = $("#chg-reason").value.trim();
    if (!m) return;
    if (isNaN(q) || q <= 0) { alert(T("chg_bad_qty")); return; }
    if (!reason) { alert(T("chg_need_reason")); return; }
    const today = new Date();
    const exp = new Date(today.getTime() + (m.shelf_days || 730) * 864e5);
    await requestChange({
      kind: "add", material: m.name, unit: m.unit, unit_cost: m.unit_cost,
      supplier: m.supplier, new_qty: q, reason,
      rm_lot: `${m.code}-${today.toISOString().slice(2, 10).replace(/-/g, "")}`,
      rm_expiry: exp.toISOString().slice(0, 10),
    });
    $("#chg-qty").value = ""; $("#chg-reason").value = "";
    form.classList.remove("open");
  };
}
/* Theme: dark is the default look, the choice persists across pages. */
function setTheme(mode) {
  document.documentElement.setAttribute("data-theme", mode);
  try { localStorage.setItem("bt_theme", mode); } catch (e) {}
}
setTheme(localStorage.getItem("bt_theme") || "dark");
$("#theme").onclick = () =>
  setTheme(document.documentElement.getAttribute("data-theme") === "light" ? "dark" : "light");

/* ---------------- entry point ----------------
   No identity, no application: the gate resolves first. */
initLogin();
startSession().then(ok => {
  if (ok) { showApp(); boot(); } else { showGate(); }
});
