/* Lore Weave AI dashboard: vanilla JS, no build step. */
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

let META = null, P = null, selChar = 0, selChapter = null, saveTimer = null, job = null;

function toast(msg, ms = 3500) { const t = $("#toast"); t.textContent = msg; t.classList.add("show"); clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), ms); }

async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts, body: opts.body ? JSON.stringify(opts.body) : undefined });
  if (!r.ok) { let m = r.statusText; try { m = (await r.json()).detail || m; } catch {} throw new Error(m); }
  return r.headers.get("content-type")?.includes("json") ? r.json() : r.text();
}

async function busyBtn(btn, label, fn) {
  const old = btn.textContent; btn.disabled = true; btn.textContent = label;
  try { return await fn(); } catch (e) { toast(e.message, 6000); } finally { btn.disabled = false; btn.textContent = old; }
}

/* ---------- binding helpers ---------- */
const getPath = (o, p) => p.split(".").reduce((a, k) => (a == null ? a : a[k]), o);
function setPath(o, p, v) { const ks = p.split("."); const last = ks.pop(); ks.reduce((a, k) => (a[k] ??= {}), o)[last] = v; }
function readInput(el) {
  const t = el.dataset.type;
  if (t === "bool") return el.checked;
  if (t === "int") return parseInt(el.value || "0", 10);
  if (t === "float") return parseFloat(el.value || "0");
  if (t === "list") return el.value.split(",").map((s) => s.trim()).filter(Boolean);
  if (t === "lines") return el.value.split("\n").map((s) => s.trim()).filter(Boolean);
  return el.value;
}
function writeInput(el, v) {
  const t = el.dataset.type;
  if (t === "bool") el.checked = !!v;
  else if (t === "list") el.value = (v || []).join(", ");
  else if (t === "lines") el.value = (v || []).join("\n");
  else el.value = v ?? "";
}
function bindAll(root = document, target = () => P, onChange = scheduleSave) {
  $$("[data-bind]", root).forEach((el) => {
    if (root === document && el.closest("#charEditor")) return; // character fields bind to the selected character
    writeInput(el, getPath(target(), el.dataset.bind));
    el.oninput = el.onchange = () => { setPath(target(), el.dataset.bind, readInput(el)); onChange(el); };
  });
}
function scheduleSave() {
  $("#saveState").textContent = "Unsaved changes...";
  clearTimeout(saveTimer); saveTimer = setTimeout(save, 700);
}
async function save() {
  if (!P) return;
  try {
    const { plan, warnings, ...body } = P;
    await api(`/api/projects/${P.id}`, { method: "PUT", body });
    const fresh = await api(`/api/projects/${P.id}`);
    P.plan = fresh.plan; P.warnings = fresh.warnings;
    $("#saveState").textContent = "Saved"; renderSetupInfo();
  } catch (e) { $("#saveState").textContent = "Save failed: " + e.message; }
}
async function reload() { P = await api(`/api/projects/${P.id}`); renderAll(); }

/* ---------- projects ---------- */
async function loadProjects(selectId) {
  const list = await api("/api/projects");
  const pick = $("#projectPicker");
  pick.innerHTML = list.map((p) => `<option value="${p.id}">${esc(p.title)} (${p.chapters}/${p.planned || "?"} ch)</option>`).join("");
  if (!list.length) { P = null; showEmpty(true); return; }
  showEmpty(false);
  const id = selectId || localStorage.getItem("lw.project") || list[0].id;
  pick.value = list.some((p) => p.id === id) ? id : list[0].id;
  await openProject(pick.value);
}
async function openProject(id) {
  try { localStorage.setItem("lw.project", id); } catch {}
  P = await api(`/api/projects/${id}`); selChar = 0; selChapter = null; renderAll(); attachRunningJob();
}
async function newProject() {
  const p = await api("/api/projects", { method: "POST", body: { title: "Untitled story", genres: ["fantasy"] } });
  await loadProjects(p.id); showTab("setup");
}
window.newProject = newProject;
function showEmpty(on) { $("#empty").classList.toggle("hidden", !on); $$(".tab").forEach((t) => on && t.classList.add("hidden")); }

/* ---------- tabs ---------- */
function showTab(name) {
  if (!P) return;
  $$("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  $$(".tab").forEach((t) => t.classList.toggle("hidden", t.id !== "tab-" + name));
  try { localStorage.setItem("lw.tab", name); } catch {}
  if (name === "export") renderExport();
}

function renderAll() {
  if (!P) return;
  bindAll();
  renderGenres(); renderSetupInfo(); renderChars(); renderWorld(); renderStyle(); renderOutline(); renderChapters();
  $("#arVal").textContent = Math.round((P.conflict.action_ratio || 0) * 100) + "%";
  let t = "setup"; try { t = localStorage.getItem("lw.tab") || t; } catch {}
  showTab(t);
}

/* ---------- setup ---------- */
function renderGenres() {
  const known = META.genres.map((g) => g.key);
  $("#genreChips").innerHTML = META.genres.map((g) => `<span class="chip ${P.genres.includes(g.key) ? "on" : ""}" data-g="${g.key}">${esc(g.label)}</span>`).join("");
  $$("#genreChips .chip").forEach((c) => (c.onclick = () => {
    const g = c.dataset.g; P.genres = P.genres.includes(g) ? P.genres.filter((x) => x !== g) : [...P.genres, g];
    if (!P.genres.length) P.genres = [g];
    renderGenres(); scheduleSave();
  }));
  const ci = $("#customGenres"); ci.value = P.genres.filter((g) => !known.includes(g)).join(", ");
  ci.onchange = () => { P.genres = [...P.genres.filter((g) => known.includes(g)), ...ci.value.split(",").map((s) => s.trim()).filter(Boolean)]; scheduleSave(); };
}
function renderSetupInfo() {
  if (!P.plan) return;
  const words = P.target_pages * P.words_per_page;
  $("#planInfo").textContent = `About ${words.toLocaleString()} words, planned as ${P.plan.chapters} chapters of ~${P.plan.words_per_chapter.toLocaleString()} words in ${P.plan.acts} acts.` +
    (P.length_mode === "ultra" ? " Ultra mode adds rotating POVs, braided subplots and character milestones." : "");
  $("#warnings").innerHTML = (P.warnings || []).map((w) => `<p class="${w.startsWith("BLOCKING") ? "bad" : "warn"} small">${esc(w)}</p>`).join("");
}

/* ---------- characters ---------- */
const CHAR_FIELDS = [
  ["name", "Name"], ["role", "Role", "select:protagonist,deuteragonist,antagonist,supporting,npc"], ["age", "Age", "int"], ["pronouns", "Pronouns"],
  ["archetype", "Archetype", "archetype"], ["is_pov", "POV character", "bool"], ["appearance", "Appearance", "text"],
  ["cultural_background", "Cultural background", "text"], ["backstory", "Backstory", "text"], ["motivation", "Motivation", "text"],
  ["fear", "Fear"], ["wound", "Wound (formative hurt)"], ["want_vs_need", "Want vs need"], ["psychology", "Psychological profile", "text"],
  ["voice", "Voice / speech patterns", "text"], ["skills", "Skills", "list"], ["flaws", "Flaws", "list"], ["arc", "Arc", "text"],
];
function renderChars() {
  $("#charList").innerHTML = P.characters.map((c, i) => `<div class="card ${i === selChar ? "sel" : ""}" data-i="${i}">
    <div class="t">${esc(c.name)}${c.is_pov ? '<span class="badge">POV</span>' : ""}${c.age != null && c.age < 18 ? '<span class="badge warn">minor</span>' : ""}</div>
    <div class="s">${esc(c.role)}${c.archetype ? " / " + esc(c.archetype.replace(/_/g, " ")) : ""}</div></div>`).join("") || '<p class="muted small">No characters yet.</p>';
  $$("#charList .card").forEach((el) => (el.onclick = () => { selChar = +el.dataset.i; renderChars(); }));
  const c = P.characters[selChar];
  const ed = $("#charEditor");
  if (!c) { ed.innerHTML = ""; return; }
  const archOpts = ['<option value="">(none)</option>', ...META.archetypes.map((a) => `<option value="${a.key}">${a.key.replace(/_/g, " ")}</option>`)].join("");
  ed.innerHTML = '<div class="grid2">' + CHAR_FIELDS.map(([k, label, t]) => {
    if (t?.startsWith("select:")) return `<label>${label}<select data-bind="${k}">${t.slice(7).split(",").map((o) => `<option>${o}</option>`).join("")}</select></label>`;
    if (t === "archetype") return `<label>${label}<select data-bind="${k}">${archOpts}</select></label>`;
    if (t === "bool") return `<label class="check"><input type="checkbox" data-bind="${k}" data-type="bool"> ${label}</label>`;
    if (t === "text") return `<label style="grid-column:1/-1">${label}<textarea rows="2" data-bind="${k}"></textarea></label>`;
    return `<label>${label}<input data-bind="${k}" ${t ? `data-type="${t}"` : ""}></label>`;
  }).join("") + `</div>
    <label>Relationships (one per line: Target | kind | dynamic)<textarea id="relEd" rows="3"></textarea></label>
    <label>Milestones (one per line, optional "ch12: " prefix)<textarea id="msEd" rows="3"></textarea></label>
    <div class="toolbar"><button class="danger" id="delChar">Delete character</button></div>`;
  bindAll(ed, () => P.characters[selChar], (el) => { if (["name", "role", "archetype", "is_pov", "age"].includes(el.dataset.bind)) renderCharsListOnly(); scheduleSave(); });
  $("#relEd").value = c.relationships.map((r) => [r.target, r.kind, r.dynamic].join(" | ")).join("\n");
  $("#relEd").oninput = (e) => { c.relationships = e.target.value.split("\n").filter((l) => l.trim()).map((l) => { const [target, kind = "", dynamic = ""] = l.split("|").map((s) => s.trim()); return { target, kind, dynamic }; }); scheduleSave(); };
  $("#msEd").value = c.milestones.map((m) => (m.chapter ? `ch${m.chapter}: ` : "") + m.description).join("\n");
  $("#msEd").oninput = (e) => { c.milestones = e.target.value.split("\n").filter((l) => l.trim()).map((l) => { const m = l.match(/^ch(\d+):\s*(.*)$/i); return m ? { chapter: +m[1], description: m[2] } : { chapter: null, description: l.trim() }; }); scheduleSave(); };
  $("#delChar").onclick = () => { if (!confirmInline("#delChar")) return; P.characters.splice(selChar, 1); selChar = 0; renderChars(); scheduleSave(); };
}
function renderCharsListOnly() { const keep = $("#charEditor").scrollTop; const e = document.activeElement?.dataset?.bind; renderChars(); $("#charEditor").scrollTop = keep; if (e) $(`#charEditor [data-bind="${e}"]`)?.focus(); }
function confirmInline(sel) { const b = $(sel); if (b.dataset.armed) return true; b.dataset.armed = 1; b.textContent = "Click again to confirm"; setTimeout(() => { delete b.dataset.armed; b.textContent = "Delete character"; }, 3000); return false; }

/* ---------- world ---------- */
const WORLD_FIELDS = [["name", "Name"], ["era", "Era / time period"], ["premise", "Setting premise", "text"], ["geography", "Geography", "text"],
  ["politics", "Politics", "text"], ["economy", "Economy", "text"], ["mythology", "Mythology & faith", "text"], ["magic_or_tech", "Magic / technology system", "text"],
  ["cultural_norms", "Cultural norms", "text"], ["languages", "Languages"], ["history", "History", "text"], ["sensory_palette", "Sensory palette"]];
function renderWorld() {
  const f = $("#worldForm");
  f.innerHTML = '<div class="grid2">' + WORLD_FIELDS.map(([k, l, t]) => t === "text" ? `<label>${l}<textarea rows="3" data-bind="world.${k}"></textarea></label>` : `<label>${l}<input data-bind="world.${k}"></label>`).join("") + "</div>" +
    `<label>Hard rules the story must never break (one per line)<textarea rows="3" data-bind="world.power_rules" data-type="lines"></textarea></label>
     <label>Locations (Name | description | significance)<textarea rows="4" id="locEd"></textarea></label>
     <label>Factions (Name | goals | methods | relations)<textarea rows="4" id="facEd"></textarea></label>`;
  bindAll(f);
  const lines = (arr, keys) => arr.map((o) => keys.map((k) => o[k] || "").join(" | ")).join("\n");
  const parse = (v, keys) => v.split("\n").filter((l) => l.trim()).map((l) => Object.fromEntries(l.split("|").map((s) => s.trim()).map((s, i) => [keys[i], s]).filter(([k]) => k)));
  const L = ["name", "description", "significance"], F = ["name", "goals", "methods", "relations"];
  $("#locEd").value = lines(P.world.locations, L); $("#locEd").oninput = (e) => { P.world.locations = parse(e.target.value, L); scheduleSave(); };
  $("#facEd").value = lines(P.world.factions, F); $("#facEd").oninput = (e) => { P.world.factions = parse(e.target.value, F); scheduleSave(); };
}

/* ---------- style ---------- */
const STYLE_FIELDS = [["summary", "Overall voice"], ["sentence_structure", "Sentence structure"], ["vocabulary", "Vocabulary"], ["pacing", "Pacing"],
  ["dialogue", "Dialogue"], ["imagery", "Imagery"], ["narrative_voice", "Narrative voice"]];
function renderStyle() {
  $("#stInfluences").value = (P.style.influences || []).join(", ");
  $("#presetChips").innerHTML = Object.keys(META.style_presets).map((k) => `<span class="chip" data-p="${k}">${k.replace(/_/g, " ")}</span>`).join("");
  $$("#presetChips .chip").forEach((c) => (c.onclick = async () => { await save(); P.style = await api(`/api/projects/${P.id}/style/analyze`, { method: "POST", body: { preset: c.dataset.p, influences: P.style.influences } }); renderStyle(); toast("Preset applied"); }));
  const f = $("#styleForm");
  f.innerHTML = STYLE_FIELDS.map(([k, l]) => `<label>${l}<textarea rows="2" data-bind="style.${k}"></textarea></label>`).join("") +
    `<label>Signature devices (comma separated)<input data-bind="style.signature_devices" data-type="list"></label>
     <label>Avoid (comma separated)<input data-bind="style.avoid" data-type="list"></label>`;
  bindAll(f);
}

/* ---------- plot ---------- */
function renderOutline() {
  const o = P.outline, v = $("#outlineView");
  $("#plInfo").textContent = P.plan ? `Will plan ${P.plan.chapters} chapters (${P.length_mode} mode).${P.chapters.length ? " Regenerating the plot does not delete written chapters, but they may no longer match." : ""}` : "";
  if (!o.chapters.length) { v.innerHTML = '<p class="muted">No outline yet. Build your cast and world first for the best results, then architect the plot.</p>'; return; }
  const povs = P.characters.map((c) => c.name);
  v.innerHTML = `<div class="grid2">
      <label>Logline<textarea rows="2" data-bind="outline.logline"></textarea></label>
      <label>Central question<textarea rows="2" data-bind="outline.central_question"></textarea></label>
      <label>Themes<input data-bind="outline.themes" data-type="list"></label>
      <label>Structure<input data-bind="outline.structure"></label>
      <label>Twists (one per line)<textarea rows="3" data-bind="outline.twists" data-type="lines"></textarea></label>
      <label>Climax &amp; ending<textarea rows="3" data-bind="outline.climax"></textarea></label></div>
    <h3>Subplots</h3>${o.subplots.map((s) => `<p class="small"><b>${esc(s.name)}</b>: ${esc(s.description)} <span class="muted">-> ${esc(s.resolution)}</span></p>`).join("") || '<p class="muted small">None</p>'}
    <h3>Branch points</h3>${o.branch_points.map((b, bi) => `<div class="branch"><div><b>After chapter ${b.after_chapter}:</b> ${esc(b.question)}</div>
      <div class="toolbar">${b.options.map((op, oi) => `<button class="${b.chosen === oi ? "on" : ""}" data-b="${bi}" data-o="${oi}" title="${esc(op.consequence)}">${esc(op.label)}</button>`).join("")}</div>
      <div class="muted small">${b.chosen != null ? "Chosen: " + esc(b.options[b.chosen].consequence) + " Later chapters were re-planned." : "Pick an option to re-plan the chapters after this point."}</div></div>`).join("") || '<p class="muted small">None</p>'}
    <h3>Chapters</h3>
    <table class="outline"><tr><th>#</th><th>Title / POV</th><th>Summary &amp; beats</th></tr>
    ${o.chapters.map((c, i) => `<tr><td>${c.number}<br><span class="muted small">act ${c.act}</span>${c.has_action ? '<br><span class="badge">action</span>' : ""}</td>
      <td><input data-bind="outline.chapters.${i}.title"><select data-bind="outline.chapters.${i}.pov">${[c.pov, ...povs.filter((n) => n !== c.pov)].map((n) => `<option>${esc(n)}</option>`).join("")}</select></td>
      <td><textarea rows="2" data-bind="outline.chapters.${i}.summary"></textarea><textarea rows="2" class="small" data-bind="outline.chapters.${i}.beats" data-type="lines"></textarea>
      ${c.milestones.length ? `<div class="small muted">Milestones: ${esc(c.milestones.join("; "))}</div>` : ""}</td></tr>`).join("")}</table>`;
  bindAll(v);
  $$(".branch button", v).forEach((b) => (b.onclick = () => busyBtn(b, "Re-planning...", async () => {
    await save(); P.outline = await api(`/api/projects/${P.id}/outline/branch`, { method: "POST", body: { index: +b.dataset.b, option: +b.dataset.o } }); renderOutline(); toast("Branch chosen; later chapters re-planned.");
  })));
}

/* ---------- writing ---------- */
function renderChapters() {
  const planned = P.outline.chapters;
  const written = Object.fromEntries(P.chapters.map((c) => [c.number, c]));
  $("#chapterList").innerHTML = planned.map((pl) => {
    const c = written[pl.number]; const iss = c?.issues || [];
    const sev = iss.some((i) => i.severity === "high") ? "bad" : iss.length ? "warn" : "";
    return `<div class="card ${selChapter === pl.number ? "sel" : ""}" data-n="${pl.number}"><div class="t">${pl.number}. ${esc(pl.title)}</div>
      <div class="s">${esc(pl.pov)} · ${c ? c.word_count.toLocaleString() + " words" : "not written"}${c?.revised ? " · revised" : ""}${iss.length ? `<span class="badge ${sev}">${iss.length} note${iss.length > 1 ? "s" : ""}</span>` : ""}</div></div>`;
  }).join("") || '<p class="muted small">Architect the plot first (or press Write and it will be done for you).</p>';
  $$("#chapterList .card").forEach((el) => (el.onclick = () => { if (job) return; selChapter = +el.dataset.n; showChapter(selChapter); renderChapters(); }));
  const total = planned.length || 1; $("#wrBar").style.width = Math.round((P.chapters.length / total) * 100) + "%";
  $("#wrStatus").textContent = `${P.chapters.reduce((a, c) => a + c.word_count, 0).toLocaleString()} words written`;
}
function showChapter(n) {
  const c = P.chapters.find((x) => x.number === n);
  $("#liveOut").textContent = c ? c.text : "";
  $("#chapterTools").classList.toggle("hidden", !c);
  $("#chapterMeta").innerHTML = c ? `<b>Summary:</b> ${esc(c.summary)}` + (c.issues || []).map((i) => `<div class="issue ${i.severity}"><b>${i.severity}</b>: ${esc(i.description)} ${i.suggestion ? `<span class="muted">${esc(i.suggestion)}</span>` : ""}</div>`).join("") : "Not written yet.";
}
function attachRunningJob() { api(`/api/projects/${P.id}/job`).then((j) => { if (j.job_id && !j.done) followJob(j.job_id); }).catch(() => {}); }

function followJob(id) {
  job = id; $("#wrGo").disabled = true; $("#wrStop").disabled = false;
  const out = $("#liveOut"); let current = null;
  const es = new EventSource(`/api/jobs/${id}/events`);
  es.onmessage = (m) => {
    const ev = JSON.parse(m.data);
    if (ev.type === "delta") { out.textContent += ev.text; if (out.scrollHeight - out.scrollTop - out.clientHeight < 200) out.scrollTop = out.scrollHeight; }
    else if (ev.type === "chapter_start") { current = ev.chapter; selChapter = ev.chapter; out.textContent = ""; $("#chapterMeta").textContent = `Writing chapter ${ev.chapter}: ${ev.title} (POV ${ev.pov}, ~${ev.target_words} words)`; }
    else if (ev.type === "status" || ev.type === "warning") $("#wrStatus").textContent = ev.message;
    else if (ev.type === "outline") reload();
    else if (ev.type === "revised") out.textContent = ev.text;
    else if (ev.type === "issues") toast(`Chapter ${ev.chapter}: ${ev.issues.length} continuity note(s)`);
    else if (ev.type === "chapter_done") { api(`/api/projects/${P.id}`).then((p) => { P = p; renderChapters(); }); }
    else if (ev.type === "error") toast("Error: " + ev.message, 8000);
    else if (ev.type === "closed" || ev.type === "done" || ev.type === "stopped") {
      if (ev.type === "closed") { es.close(); job = null; $("#wrGo").disabled = false; $("#wrStop").disabled = true; reload().then(() => current && showChapter(current)); }
    }
  };
  es.onerror = () => { if (!job) es.close(); };
}

/* ---------- export ---------- */
function renderExport() {
  const words = P.chapters.reduce((a, c) => a + c.word_count, 0);
  $("#exportInfo").textContent = `${P.chapters.length} chapters, ${words.toLocaleString()} words (~${Math.round(words / P.words_per_page)} pages).`;
  for (const [id, f] of [["exMd", "md"], ["exTxt", "txt"], ["exHtml", "html"], ["exEpub", "epub"]]) $("#" + id).href = `/api/projects/${P.id}/export?format=${f}`;
  const L = P.ledger;
  $("#ledgerView").innerHTML = `${L.story_so_far ? `<p><b>Story so far (ch 1-${L.compressed_through}):</b> ${esc(L.story_so_far)}</p>` : ""}
    <p><b>Characters:</b></p><ul>${Object.values(L.characters).map((s) => `<li>${esc(s.name)}: ${esc(s.status)}${s.location ? ", " + esc(s.location) : ""}${s.condition ? "; " + esc(s.condition) : ""}</li>`).join("")}</ul>
    <p><b>Open threads:</b></p><ul>${L.open_threads.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>
    <p><b>Facts (${L.facts.length}):</b></p><ul>${L.facts.slice(-30).map((t) => `<li>${esc(t)}</li>`).join("")}</ul>`;
}

/* ---------- SSE over POST (preview) ---------- */
async function streamPost(path, body, onEvent) {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
  const reader = r.body.getReader(); const dec = new TextDecoder(); let buf = "";
  for (;;) {
    const { value, done } = await reader.read(); if (done) break;
    buf += dec.decode(value, { stream: true });
    let i; while ((i = buf.indexOf("\n\n")) >= 0) { const line = buf.slice(0, i); buf = buf.slice(i + 2); if (line.startsWith("data: ")) onEvent(JSON.parse(line.slice(6))); }
  }
}

/* ---------- wire up ---------- */
async function init() {
  META = await api("/api/meta");
  $("#backendPicker").value = META.backend;
  $("#backendPicker").onchange = async (e) => { try { const s = await api("/api/settings", { method: "PUT", body: { backend: e.target.value } }); toast("Engine: " + (s.model || s.name)); } catch (err) { toast(err.message, 7000); e.target.value = "mock"; } };
  $("#cgArchetype").innerHTML += META.archetypes.map((a) => `<option value="${a.key}">${a.key.replace(/_/g, " ")} (${a.family})</option>`).join("");
  $("#cgArchetype").onchange = (e) => { const a = META.archetypes.find((x) => x.key === e.target.value); $("#archetypeInfo").textContent = a ? `${a.surface} Underneath: ${a.core}` : ""; };
  $$("#tabs button").forEach((b) => (b.onclick = () => showTab(b.dataset.tab)));
  $("#projectPicker").onchange = (e) => openProject(e.target.value);
  $("#newProject").onclick = newProject;
  $$("[data-bind='conflict.action_ratio']").forEach((el) => el.addEventListener("input", () => ($("#arVal").textContent = Math.round(el.value * 100) + "%")));
  $$("[data-bind='length_mode']").forEach((el) => el.addEventListener("change", () => { if (el.value === "ultra" && P.target_pages < 200) { P.target_pages = 220; bindAll(); } if (el.value === "standard" && P.target_pages > 150) { P.target_pages = 75; bindAll(); } }));

  $("#cgGo").onclick = (e) => busyBtn(e.target, "Creating...", async () => {
    await save();
    const made = await api(`/api/projects/${P.id}/characters/generate`, { method: "POST", body: { count: +$("#cgCount").value || 1, hints: $("#cgHints").value, archetype: $("#cgArchetype").value || null, role: $("#cgRole").value || null } });
    await reload(); selChar = P.characters.length - made.length; renderChars(); showTab("characters"); toast(`Added ${made.map((c) => c.name).join(", ")}`);
  });
  $("#cgBlank").onclick = () => { P.characters.push({ name: "New character", role: "supporting", age: null, pronouns: "", archetype: "", appearance: "", cultural_background: "", backstory: "", motivation: "", fear: "", wound: "", want_vs_need: "", psychology: "", voice: "", skills: [], flaws: [], arc: "", relationships: [], milestones: [], is_pov: false }); selChar = P.characters.length - 1; renderChars(); scheduleSave(); };
  $("#wgGo").onclick = (e) => busyBtn(e.target, "Building world...", async () => { await save(); P.world = await api(`/api/projects/${P.id}/world/generate`, { method: "POST", body: { hints: $("#wgHints").value } }); renderWorld(); toast("World built"); });
  $("#stGo").onclick = (e) => busyBtn(e.target, "Analyzing...", async () => {
    await save(); const infl = $("#stInfluences").value.split(",").map((s) => s.trim()).filter(Boolean);
    P.style = await api(`/api/projects/${P.id}/style/analyze`, { method: "POST", body: { influences: infl, sample: $("#stSample").value } }); renderStyle(); toast("Style profile ready");
  });
  $("#plGo").onclick = (e) => busyBtn(e.target, "Architecting (this can take a minute)...", async () => { await save(); P.outline = await api(`/api/projects/${P.id}/outline/generate`, { method: "POST" }); await reload(); showTab("plot"); toast(`Planned ${P.outline.chapters.length} chapters`); });
  $("#pvGo").onclick = (e) => busyBtn(e.target, "Writing preview...", async () => {
    await save(); const out = $("#previewOut"); out.textContent = "";
    await streamPost(`/api/projects/${P.id}/preview`, { instruction: $("#pvInstr").value }, (ev) => { if (ev.type === "delta") out.textContent += ev.text; if (ev.type === "error") toast(ev.message, 7000); });
  });
  $("#wrGo").onclick = (e) => busyBtn(e.target, "Starting...", async () => {
    await save(); const start = +$("#wrStart").value || 1; const end = +$("#wrEnd").value || null;
    if (start <= P.chapters.length && P.chapters.length) toast(`Rewriting from chapter ${start}; later chapters will be regenerated.`);
    const r = await api(`/api/projects/${P.id}/write`, { method: "POST", body: { start, end } }); followJob(r.job_id);
  });
  $("#wrStop").onclick = () => job && api(`/api/jobs/${job}/stop`, { method: "POST" }).then(() => toast("Stopping; the partial chapter is kept."));
  $("#rvGo").onclick = (e) => busyBtn(e.target, "Revising...", async () => { await api(`/api/projects/${P.id}/chapters/${selChapter}/revise`, { method: "POST", body: { notes: $("#rvNotes").value } }); await reload(); showTab("write"); showChapter(selChapter); toast("Chapter revised"); });

  await loadProjects();
}
init().catch((e) => toast(e.message, 8000));
