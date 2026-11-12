/*
 * Weekly calendar for this vault.
 *
 * Use in a note:
 *   ```dataviewjs
 *   await dv.view("13 Calendar/System/calendar-view", {mode: "week"})
 *   ```
 * Options: mode "week" (default) or "day"; week "2026-W42" (week mode starts on that ISO week);
 * date "2026-10-12" (day mode; defaults to the note's `date` property, then today).
 *
 * Data, all read live:
 *   - Event notes (type: event) anywhere in "13 Calendar". Recurring notes have `repeat: weekly`.
 *   - Tasks with [due:: YYYY-MM-DD] in course maps, projects, AI chats and the calendar folder.
 * Rules for people and agents: "04 Maps/Calendar MOC.md" and "00 Home/Agent/Skills/Skill - Calendar Update.md".
 */

const { DateTime } = dv.luxon;
const app = dv.app;
const opt = Object.assign({ mode: "week" }, (input && typeof input === "object") ? input : {});
const here = dv.current ? dv.current() : null;
const herePath = (here && here.file && here.file.path) || "";

const CAL = "13 Calendar";
const NEW_DIR = "13 Calendar/Events";
const LOG = "04 Maps/Calendar MOC.md";
const WEEK_NOTE = "00 Home/Weekly Calendar.md";
const TASK_FROM = '"04 Maps" or "05 Projects" or "11 AI Chats" or "13 Calendar"';
const RANK = { "04 Maps": 0, "05 Projects": 1, "13 Calendar": 2, "11 AI Chats": 3 };
const PALETTE = {
  indigo: "#5A67D8", magenta: "#B83DBA", amber: "#D4A017", emerald: "#10B981", coral: "#FF7F50",
  red: "#C0504D", lime: "#84CC16", cyan: "#06B6D4", gray: "#8A8F98", grey: "#8A8F98",
  blue: "#4A90D9", green: "#3FA66B", purple: "#8E6BD1", orange: "#E07B39", teal: "#2BA3A3",
  pink: "#D6589B", gold: "#E0A526", violet: "#7B61C9", brown: "#8C7B6B", slate: "#6B7A8F",
  "carolina blue": "#4B9CD3",
};
const KINDS = {
  class: { color: "#7B61C9", label: "Class" },
  exam: { color: "#C0504D", label: "Exam" },
  call: { color: "#3B6FD8", label: "Call" },
  meeting: { color: "#2BA3A3", label: "Meeting" },
  interview: { color: "#3B6FD8", label: "Interview" },
  appointment: { color: "#E07B39", label: "Appointment" },
  club: { color: "#8E6BD1", label: "Club" },
  work: { color: "#C0504D", label: "Work" },
  personal: { color: "#3FA66B", label: "Personal" },
  travel: { color: "#4A90D9", label: "Travel" },
  break: { color: "#8A8F98", label: "No classes" },
  academic: { color: "#4B9CD3", label: "School dates" },
  other: { color: "#6B7A8F", label: "Event" },
};
const FORM_KINDS = ["call", "meeting", "interview", "appointment", "class", "exam", "club", "work", "personal", "travel", "other"];
const ALLDAY_ORDER = ["break", "academic", "exam", "travel", "interview", "call", "meeting", "appointment", "class", "club", "work", "personal", "other"];
const DAYMAP = {
  m: 1, mo: 1, mon: 1, monday: 1, t: 2, tu: 2, tue: 2, tues: 2, tuesday: 2, w: 3, we: 3, wed: 3, wednesday: 3,
  r: 4, th: 4, thu: 4, thur: 4, thurs: 4, thursday: 4, f: 5, fr: 5, fri: 5, friday: 5,
  s: 6, sa: 6, sat: 6, saturday: 6, u: 7, su: 7, sun: 7, sunday: 7,
};
const MONTHS = "jan feb mar apr may jun jul aug sep sept oct nov dec january february march april june july august september october november december".split(" ");
const STOP = new Set(("the a an to of for and or in on at by with from your my our this that is are be due submit take complete "
  + "do canvas am pm mon tue tues wed thu thur thurs fri sat sun monday tuesday wednesday thursday friday saturday sunday "
  + MONTHS.join(" ")).split(" "));
const DATE_MENTION = /,?\s*\b(?:mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)[a-z]*\.?,?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}\b(?:,?\s*\d{4})?/i;

/* ---------- small helpers ---------- */

const pad = (n) => String(n).padStart(2, "0");
const dt = (s) => DateTime.fromISO(s);
const todayISO = () => DateTime.local().toISODate();
const basename = (p) => String(p).split("/").pop().replace(/\.md$/i, "");
const toArr = (v) => {
  if (v === null || v === undefined || v === "") return [];
  if (Array.isArray(v)) return v;
  if (typeof v === "object" && typeof v.array === "function") return v.array();
  return [v];
};
function iso(v) {
  if (!v) return null;
  if (DateTime.isDateTime(v)) return v.isValid ? v.toISODate() : null;
  if (v instanceof Date) return DateTime.fromJSDate(v).toISODate();
  if (typeof v === "object") return null;
  const m = String(v).trim().match(/^(\d{4}-\d{2}-\d{2})/);
  return m ? m[1] : null;
}
function toMin(v) {
  if (v === null || v === undefined || v === "") return null;
  if (typeof v === "number" && isFinite(v)) return v >= 0 && v <= 1440 ? Math.round(v) : null; // YAML 1.1 sexagesimal
  if (DateTime.isDateTime(v)) return v.hour * 60 + v.minute;
  const s = String(v).trim().toLowerCase().replace(/\./g, "");
  if (s === "noon") return 720;
  if (s === "midnight") return 0;
  const m = s.match(/^(\d{1,2})(?::(\d{2}))?\s*(am|pm|a|p)?$/);
  if (!m) return null;
  let h = Number(m[1]);
  const mi = m[2] ? Number(m[2]) : 0;
  if (m[3]) { if (h === 12) h = 0; if (m[3][0] === "p") h += 12; }
  if (h > 24 || mi > 59) return null;
  return h * 60 + mi;
}
const hhmm = (min) => `${pad(Math.floor(min / 60) % 24)}:${pad(min % 60)}`;
function fmtTime(min) {
  const h = Math.floor(min / 60) % 24, m = min % 60;
  const ap = h >= 12 ? "pm" : "am";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return m ? `${h12}:${pad(m)} ${ap}` : `${h12} ${ap}`;
}
function fmtRange(s, e) {
  if (s === null || s === undefined) return "";
  if (e === null || e === undefined) return fmtTime(s);
  const same = (s >= 720) === (e >= 720);
  const a = fmtTime(s), b = fmtTime(e);
  return same ? `${a.replace(/ (am|pm)$/, "")}–${b}` : `${a}–${b}`;
}
function fmtShort(s, e) {
  const t = (min) => { const h = Math.floor(min / 60) % 24, m = min % 60; return `${h % 12 === 0 ? 12 : h % 12}${m ? ":" + pad(m) : ""}`; };
  return `${t(s)}–${t(e)}`;
}
const fmtHour = (min) => {
  const h = Math.floor(min / 60) % 24;
  if (h === 0) return "12 am";
  if (h === 12) return "Noon";
  return h < 12 ? `${h} am` : `${h - 12} pm`;
};
function colorOf(v) {
  if (!v) return null;
  const s = String(v).trim();
  if (/^#[0-9a-f]{3,8}$/i.test(s)) return s;
  return PALETTE[s.toLowerCase()] || null;
}
function linkPath(v, from) {
  if (!v) return null;
  let t = null;
  if (typeof v === "object" && v.path) t = v.path;
  else {
    const m = String(v).match(/\[\[([^\]|#]+)/);
    t = m ? m[1] : String(v).trim();
  }
  if (!t) return null;
  const f = app.metadataCache.getFirstLinkpathDest(t, from || "");
  return f ? f.path : null;
}
function parseDays(v) {
  const raw = toArr(v).flatMap((x) => String(x).split(/[\s,/]+/));
  return [...new Set(raw.map((x) => DAYMAP[x.trim().toLowerCase()]).filter(Boolean))];
}
function span(a, b) {
  const out = [];
  let x = dt(a);
  const end = dt(b || a);
  for (let i = 0; x <= end && i < 400; i++) { out.push(x.toISODate()); x = x.plus({ days: 1 }); }
  return out;
}
function tokens(s) {
  return new Set(String(s).toLowerCase().replace(/[^a-z0-9 ]+/g, " ").split(/\s+/)
    .filter((w) => w.length > 2 && !STOP.has(w) && !/^\d+$/.test(w)));
}
function overlap(a, b) {
  if (!a.size || !b.size) return 0;
  let n = 0;
  for (const w of a) if (b.has(w)) n++;
  return n / Math.min(a.size, b.size);
}
function state(key) {
  const all = (window.__marcWeekCal = window.__marcWeekCal || {});
  let s = all[key];
  const today = todayISO();
  if (!s || s.day !== today) s = all[key] = { offset: 0, form: null, flash: "", day: today };
  return s;
}

/* ---------- data ---------- */

function loadEvents() {
  const recurring = [], single = [];
  let pages = [];
  try { pages = dv.pages(`"${CAL}"`); } catch (e) { pages = []; }
  for (const p of pages) {
    if (String(p.type || "").toLowerCase() !== "event") continue;
    const path = p.file.path;
    const kind = KINDS[String(p.kind || "").toLowerCase()] ? String(p.kind).toLowerCase() : "other";
    const coursePath = linkPath(p.course, path);
    const coursePage = coursePath ? dv.page(coursePath) : null;
    const ev = {
      path, kind,
      status: String(p.status || "confirmed").toLowerCase(),
      title: p.title ? String(p.title) : p.file.name.replace(/^\d{4}-\d{2}-\d{2}\s*-\s*/, ""),
      location: p.location ? String(p.location) : "",
      coursePath,
      courseCode: coursePath ? basename(coursePath).replace(/\s+MOC$/i, "") : "",
      color: colorOf(p.color) || colorOf(coursePage && coursePage.color) || KINDS[kind].color,
      date: iso(p.date),
      endDate: iso(p["end-date"]),
      start: toMin(p["start-time"]),
      end: toMin(p["end-time"]),
      allDay: p["all-day"] === true,
      noClass: p["no-class"] === true,
      replaces: linkPath(p.replaces, path),
      skip: toArr(p.skip).map(iso).filter(Boolean),
      days: parseDays(p.days),
      repeat: String(p.repeat || "").toLowerCase(),
    };
    if (!ev.date) continue;
    if (ev.start === null) ev.allDay = true;
    if (!ev.allDay) {
      if (ev.end === null || ev.end <= ev.start) ev.end = Math.min(ev.start + 60, 1440);
    }
    if (ev.repeat === "weekly" && ev.days.length) recurring.push(ev);
    else single.push(ev);
  }
  return { recurring, single };
}

function expand(days, data) {
  const want = new Set(days);
  const out = {};
  for (const d of days) out[d] = { timed: [], allDay: [] };
  const noClass = new Set(), replaced = new Set();
  for (const e of data.single) {
    if (e.noClass && e.status !== "cancelled") for (const d of span(e.date, e.endDate)) noClass.add(d);
    if (e.replaces) replaced.add(`${e.replaces}|${e.date}`);
  }
  for (const e of data.single) {
    const last = e.endDate && e.endDate > e.date ? e.endDate : e.date;
    for (const d of span(e.date, last)) {
      if (!want.has(d)) continue;
      const multi = last !== e.date;
      const o = Object.assign({}, e, { day: d, multi, isFirst: d === e.date, isLast: d === last });
      (e.allDay || multi ? out[d].allDay : out[d].timed).push(o);
    }
  }
  for (const e of data.recurring) {
    for (const d of days) {
      if (d < e.date || (e.endDate && d > e.endDate)) continue;
      if (!e.days.includes(dt(d).weekday)) continue;
      if (e.skip.includes(d) || replaced.has(`${e.path}|${d}`)) continue;
      if (e.kind === "class" && noClass.has(d)) continue;
      const o = Object.assign({}, e, { day: d, recurring: true });
      (e.allDay ? out[d].allDay : out[d].timed).push(o);
    }
  }
  return out;
}

function dueTime(text) {
  const m = text.match(DATE_MENTION);
  const after = m ? m.index + m[0].length : 0;
  const re = /\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b/gi;
  let r, first = null;
  while ((r = re.exec(text))) {
    const min = toMin(r[0]);
    if (first === null) first = min;
    if (r.index >= after && m) return min;
  }
  return m ? null : first;
}

function dueLabel(text) {
  const m = text.match(DATE_MENTION);
  let s = m && m.index > 2 ? text.slice(0, m.index) : text;
  s = s.replace(/\s+/g, " ").replace(/[\s,;:–-]+$/, "").trim();
  return s || text;
}

function loadDue(days, data) {
  const first = days[0], last = days[days.length - 1];
  const out = {};
  for (const d of days) out[d] = [];
  let tasks = [];
  try { tasks = dv.pages(TASK_FROM).file.tasks; } catch (e) { tasks = []; }
  const exams = new Set(data.single.filter((e) => e.kind === "exam" && e.coursePath).map((e) => `${e.coursePath}|${e.date}`));
  const cands = [];
  for (const t of tasks) {
    const due = iso(t.due);
    if (!due || due < first || due > last) continue;
    const raw = String(t.text || "").replace(/\[[\w-]+::[^\]]*\]/g, "").replace(/\([\w-]+::[^)]*\)/g, "").replace(/\s+/g, " ").trim();
    if (!raw) continue;
    if (/\bexams?\b/i.test(raw) && exams.has(`${t.path}|${due}`)) continue; // shown as an exam block instead
    const folder = t.path.split("/")[0];
    const page = dv.page(t.path);
    const isCourse = folder === "04 Maps" && page && (colorOf(page.color) || toArr(page.file.tags).some((x) => String(x).startsWith("#course")));
    const notePath = !isCourse && page && page.course ? linkPath(page.course, t.path) : null; // prep notes in 13 Calendar/Prep name their course
    const notePage = notePath ? dv.page(notePath) : null;
    cands.push({
      due, raw, folder, path: t.path, line: t.line, completed: !!t.completed,
      time: dueTime(raw), label: dueLabel(raw),
      prefix: isCourse ? basename(t.path).replace(/\s+MOC$/i, "") : (notePath ? basename(notePath).replace(/\s+MOC$/i, "") : ""),
      color: (isCourse && colorOf(page.color)) || (notePage && colorOf(notePage.color)) || (folder === "05 Projects" ? PALETTE.orange : folder === "11 AI Chats" ? PALETTE.pink : "#D6589B"),
      tok: tokens(raw),
      norm: raw.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim(),
    });
  }
  cands.sort((a, b) => (RANK[a.folder] ?? 9) - (RANK[b.folder] ?? 9) || b.raw.length - a.raw.length);
  const kept = [];
  for (const c of cands) {
    const loose = (x) => x.folder === "11 AI Chats" || x.path.startsWith("13 Calendar/Prep/"); // chat and prep notes often restate a course-map deadline
    const dup = kept.some((k) => k.due === c.due
      && (k.path === c.path || loose(k) || loose(c))
      && (k.norm === c.norm || (Math.min(k.tok.size, c.tok.size) >= 2 && overlap(k.tok, c.tok) >= 0.6)));
    if (!dup) kept.push(c);
  }
  for (const k of kept) out[k.due].push(k);
  for (const d of days) out[d].sort((a, b) => (a.time ?? 1439) - (b.time ?? 1439) || a.label.localeCompare(b.label));
  return out;
}

function activeCourses() {
  try {
    return dv.pages('"04 Maps"')
      .where((p) => String(p.status || "") === "active" && toArr(p.file.tags).some((t) => String(t).startsWith("#course")))
      .map((p) => p.file.name).array().sort();
  } catch (e) { return []; }
}

/* ---------- actions ---------- */

function open(path, ev) {
  app.workspace.openLinkText(path, herePath, !!(ev && (ev.metaKey || ev.ctrlKey)));
}
async function openAt(path, line, ev) {
  const f = app.vault.getAbstractFileByPath(path);
  if (!f) return;
  const leaf = app.workspace.getLeaf(ev && (ev.metaKey || ev.ctrlKey) ? "tab" : false);
  await leaf.openFile(f, { eState: { line } });
}
function linkify(el, path, root) {
  el.addClass("mwc-click");
  el.addEventListener("click", (ev) => { ev.stopPropagation(); open(path, ev); });
  el.addEventListener("mouseover", (ev) => {
    if (!(ev.metaKey || ev.ctrlKey)) return; // preview only with Cmd/Ctrl held, so it never covers the grid
    try {
      app.workspace.trigger("hover-link", { event: ev, source: "preview", hoverParent: dv.component || root, targetEl: el, linktext: path, sourcePath: herePath });
    } catch (e) { /* hover preview is optional */ }
  });
}
function whenText(date, start, end) {
  const d = dt(date).toFormat("ccc, LLL d, yyyy");
  return start === null || start === undefined ? `${d} (all day)` : `${d} · ${fmtRange(start, end)}`;
}
async function logLine(line) {
  const f = app.vault.getAbstractFileByPath(LOG);
  if (!f) return;
  await app.vault.process(f, (txt) => txt.replace(/\s*$/, "\n") + line + "\n");
}
async function createEvent(v) {
  if (!app.vault.getAbstractFileByPath(NEW_DIR)) await app.vault.createFolder(NEW_DIR);
  const title = v.title.replace(/\s+/g, " ").trim();
  const safe = title.replace(/[\\/:*?"<>|#^[\]]/g, " ").replace(/\s+/g, " ").trim().slice(0, 80);
  let path = `${NEW_DIR}/${v.date} - ${safe}.md`;
  for (let n = 2; app.vault.getAbstractFileByPath(path); n++) path = `${NEW_DIR}/${v.date} - ${safe} (${n}).md`;
  const s = toMin(v.start), e = toMin(v.end);
  const fm = ["---", "type: event", `kind: ${v.kind}`, `date: ${v.date}`];
  if (s !== null) fm.push(`start-time: "${hhmm(s)}"`);
  if (s !== null && e !== null && e > s) fm.push(`end-time: "${hhmm(e)}"`);
  if (v.location) fm.push(`location: ${JSON.stringify(v.location)}`);
  if (v.course) fm.push(`course: "[[${v.course}]]"`);
  fm.push(`status: ${v.status}`, 'source: "Added in the Weekly Calendar"', `created: ${DateTime.local().toFormat("yyyy-LL-dd'T'HH:mm")}`, "tags:", "  - event", "---");
  const when = whenText(v.date, s, e !== null && s !== null && e > s ? e : null);
  const body = ["", `# ${title}`, "← [[Weekly Calendar]] · [[Calendar MOC]]", "", `**When:** ${when}`];
  if (v.location) body.push(`**Where:** ${v.location}`);
  if (v.course) body.push(`**Course:** [[${v.course}]]`);
  if (v.status === "tentative") body.push("**Status:** tentative");
  if (v.notes) body.push("", "## Notes", v.notes.trim());
  await app.vault.create(path, fm.concat(body).join("\n") + "\n");
  await logLine(`- ${todayISO()} · added [[${basename(path)}]] · ${v.kind} · ${when} · from [[Weekly Calendar]]`);
  return path;
}

/* ---------- rendering ---------- */

function tip(e) {
  const lines = [(e.courseCode && !e.title.includes(e.courseCode) ? `${e.courseCode} · ` : "") + e.title];
  const day = dt(e.day || e.date).toFormat("cccc, LLL d");
  lines.push(e.allDay || e.start === null ? (e.multi ? `${dt(e.date).toFormat("LLL d")} – ${dt(e.endDate).toFormat("LLL d")}` : `${day} · all day`) : `${day} · ${fmtRange(e.start, e.end)}`);
  if (e.location) lines.push(e.location);
  if (e.status !== "confirmed") lines.push(`Status: ${e.status}`);
  if (e.recurring) lines.push("Repeats weekly");
  lines.push(e.path);
  return lines.join("\n");
}
function button(parent, text, title, onClick, cls) {
  const b = parent.createEl("button", { text, cls: cls || "" });
  b.setAttr("aria-label", title);
  b.addEventListener("click", (ev) => { ev.preventDefault(); onClick(ev); });
  return b;
}
function chipEvent(cell, e, root) {
  const c = cell.createDiv({ cls: `mwc-chip kind-${e.kind} st-${e.status}` });
  if (e.multi) { c.addClass("is-multi"); if (!e.isFirst) c.addClass("cont-left"); if (!e.isLast) c.addClass("cont-right"); }
  c.style.setProperty("--ev", e.color);
  const time = !e.multi && e.start !== null && !e.allDay ? `${fmtRange(e.start, e.end)} · ` : "";
  c.createSpan({ cls: "mwc-chip-text", text: time + e.title + (e.status === "tentative" ? " (tentative)" : "") });
  c.setAttr("title", tip(e));
  linkify(c, e.path, root);
}
function chipDue(cell, t) {
  const c = cell.createDiv({ cls: "mwc-chip mwc-due" + (t.completed ? " is-done" : "") });
  c.style.setProperty("--ev", t.color);
  const meta = [t.completed ? "Done" : "Due"];
  if (t.time !== null) meta.push(fmtTime(t.time));
  c.createDiv({ cls: "mwc-due-meta", text: meta.join(" ") });
  c.createDiv({ cls: "mwc-chip-text", text: t.label });
  c.setAttr("title", `${t.prefix ? t.prefix + ": " : ""}${t.raw}\nFrom ${basename(t.path)} (click to open)`);
  c.addClass("mwc-click");
  c.addEventListener("click", (ev) => { ev.stopPropagation(); openAt(t.path, t.line, ev); });
}
function layout(evs) {
  evs.sort((a, b) => a.start - b.start || b.end - a.end);
  let group = [], groupEnd = -1;
  const flush = () => {
    const cols = [];
    for (const e of group) {
      let i = cols.findIndex((end) => end <= e.start);
      if (i < 0) { i = cols.length; cols.push(0); }
      cols[i] = e.end; e._col = i;
    }
    for (const e of group) e._n = cols.length;
    group = []; groupEnd = -1;
  };
  for (const e of evs) {
    if (group.length && e.start >= groupEnd) flush();
    group.push(e); groupEnd = Math.max(groupEnd, e.end);
  }
  if (group.length) flush();
}
function block(col, e, lo, px, root) {
  const el = col.createDiv({ cls: `mwc-ev kind-${e.kind} st-${e.status}` });
  const h = Math.max((e.end - e.start) * px, 22);
  el.style.top = `${(e.start - lo) * px}px`;
  el.style.height = `${h}px`;
  const w = 100 / (e._n || 1);
  el.style.left = `calc(${w * (e._col || 0)}% + 2px)`;
  el.style.width = `calc(${w}% - 4px)`;
  el.style.setProperty("--ev", e.color);
  const flag = e.status === "tentative" ? " · tent." : e.status === "cancelled" ? " · cancelled" : "";
  el.createDiv({ cls: "mwc-ev-time", text: fmtShort(e.start, e.end) + flag });
  el.createDiv({ cls: "mwc-ev-title", text: e.title });
  if (e.location && h >= 44) el.createDiv({ cls: "mwc-ev-loc", text: e.location });
  if (h < 44) el.addClass("is-short");
  if (h >= 84) el.addClass("is-tall");
  el.setAttr("title", tip(e));
  linkify(el, e.path, root);
}
function nowLine(col, lo, hi, px) {
  const ln = col.createDiv({ cls: "mwc-now" });
  const place = () => {
    const n = DateTime.local();
    const m = n.hour * 60 + n.minute;
    ln.style.display = m < lo || m > hi ? "none" : "";
    ln.style.top = `${(m - lo) * px}px`;
  };
  place();
  const timer = window.setInterval(() => { if (!ln.isConnected) { window.clearInterval(timer); return; } place(); }, 60000);
}
function itemsFor(d, occ, due) {
  const all = occ[d].allDay.slice().sort((a, b) => ALLDAY_ORDER.indexOf(a.kind) - ALLDAY_ORDER.indexOf(b.kind) || a.title.localeCompare(b.title));
  const timed = occ[d].timed.slice().sort((a, b) => a.start - b.start || a.end - b.end);
  return { all, timed, due: due[d] || [] };
}
function agendaList(parent, d, occ, due, root) {
  const { all, timed, due: dues } = itemsFor(d, occ, due);
  const ul = parent.createEl("ul", { cls: "mwc-list" });
  const add = (when, e, text, where, onClick) => {
    const li = ul.createEl("li");
    if (e && e.status) li.addClass(`st-${e.status}`);
    li.createSpan({ cls: "mwc-when", text: when });
    const what = li.createSpan({ cls: "mwc-what" });
    const dot = what.createSpan({ cls: "mwc-dot" });
    dot.style.setProperty("--ev", e.color);
    what.createSpan({ cls: "mwc-name", text });
    if (where) what.createSpan({ cls: "mwc-where", text: ` · ${where}` });
    li.addClass("mwc-click");
    li.addEventListener("click", onClick);
  };
  const named = (e) => (e.courseCode && !e.title.includes(e.courseCode) ? `${e.courseCode} · ` : "") + e.title;
  for (const e of all) add(e.multi ? "All day ↔" : (e.start !== null && !e.allDay ? fmtRange(e.start, e.end) : "All day"), e, named(e) + (e.status === "tentative" ? " (tentative)" : ""), e.location, (ev) => open(e.path, ev));
  for (const e of timed) add(fmtRange(e.start, e.end), e, named(e) + (e.status === "tentative" ? " (tentative)" : e.status === "cancelled" ? " (cancelled)" : ""), e.location, (ev) => open(e.path, ev));
  for (const t of dues) add(t.time !== null ? `Due ${fmtTime(t.time)}` : "Due", { color: t.color, status: t.completed ? "done" : "" }, (t.prefix ? `${t.prefix} · ` : "") + t.label, "", (ev) => openAt(t.path, t.line, ev));
  return all.length + timed.length + dues.length;
}

function renderWeek() {
  const root = dv.container.createDiv({ cls: "mwc mwc-week" });
  const S = state(`week:${herePath}:${opt.week || ""}`);
  let base = opt.week ? DateTime.fromISO(`${String(opt.week).trim()}-1`) : DateTime.local().startOf("week");
  if (!base.isValid) base = DateTime.local().startOf("week");
  const thisWeekOffset = () => Math.round(DateTime.local().startOf("week").diff(base, "weeks").weeks);

  const draw = () => {
    root.empty();
    const start = base.plus({ weeks: S.offset });
    const days = [...Array(7).keys()].map((i) => start.plus({ days: i }).toISODate());
    const today = todayISO();
    const data = loadEvents();
    const occ = expand(days, data);
    const due = loadDue(days, data);

    // header
    const end = start.plus({ days: 6 });
    const head = root.createDiv({ cls: "mwc-head" });
    const title = head.createDiv({ cls: "mwc-title" });
    title.createSpan({ cls: "mwc-range", text: start.month === end.month ? `${start.toFormat("LLLL d")} – ${end.toFormat("d, yyyy")}` : `${start.toFormat("LLL d")} – ${end.toFormat("LLL d, yyyy")}` });
    const isThis = days.includes(today);
    title.createSpan({ cls: "mwc-weekno", text: `Week ${start.weekNumber}${isThis ? " · this week" : ""}` });
    const nav = head.createDiv({ cls: "mwc-nav" });
    button(nav, "‹", "Previous week", () => { S.offset--; draw(); });
    button(nav, "Today", "Jump to this week", () => { S.offset = thisWeekOffset(); draw(); });
    button(nav, "›", "Next week", () => { S.offset++; draw(); });
    button(nav, S.form ? "Close form" : "+ Add event", "Add a call, meeting or other event", () => {
      S.form = S.form ? null : { date: isThis ? today : days[0], start: "", end: "", kind: "meeting", status: "confirmed" };
      draw();
    }, "mod-cta");
    if (S.flash) { root.createDiv({ cls: "mwc-flash", text: S.flash }); S.flash = ""; }
    if (S.form) renderForm(root, S, draw, base);

    // legend: colors that appear this week
    const seen = new Map();
    for (const d of days) {
      for (const e of occ[d].timed.concat(occ[d].allDay)) {
        const label = e.courseCode || KINDS[e.kind].label;
        if (!seen.has(label)) seen.set(label, e.color);
      }
    }
    if (days.some((d) => due[d].length)) seen.set("Due", "#D6589B");
    if (seen.size) {
      const lg = root.createDiv({ cls: "mwc-legend" });
      for (const [label, color] of seen) { const s = lg.createSpan({ text: label }); s.style.setProperty("--ev", color); }
    }

    // grid
    let lo = 8 * 60, hi = 19 * 60;
    for (const d of days) for (const e of occ[d].timed) { lo = Math.min(lo, Math.floor(e.start / 60) * 60); hi = Math.max(hi, Math.ceil(e.end / 60) * 60); }
    lo = Math.max(0, lo); hi = Math.min(1440, hi);
    const px = 0.9;
    const scroll = root.createDiv({ cls: "mwc-scroll" });
    const g = scroll.createDiv({ cls: "mwc-grid" });
    g.createDiv({ cls: "mwc-corner" });
    for (const d of days) {
      const x = dt(d);
      const hd = g.createDiv({ cls: "mwc-dayhead" + (d === today ? " is-today" : "") + (x.weekday >= 6 ? " is-weekend" : "") });
      hd.createSpan({ cls: "mwc-dow", text: x.toFormat("ccc") });
      hd.createSpan({ cls: "mwc-dom", text: x.toFormat("d") });
      if (x.day === 1 || d === days[0]) hd.createSpan({ cls: "mwc-mon", text: x.toFormat("LLL") });
      const daily = app.vault.getAbstractFileByPath(`06 Daily/${x.toFormat("yyyy/LL")}/${d}.md`);
      if (daily) { hd.addClass("mwc-click"); hd.setAttr("title", "Open this day's daily note"); hd.addEventListener("click", (ev) => open(daily.path, ev)); }
    }
    g.createDiv({ cls: "mwc-allday-label", text: "All day" });
    for (const d of days) {
      const cell = g.createDiv({ cls: "mwc-allday" + (d === today ? " is-today" : "") });
      const { all, due: dues } = itemsFor(d, occ, due);
      for (const e of all) chipEvent(cell, e, root);
      for (const t of dues) chipDue(cell, t);
    }
    const times = g.createDiv({ cls: "mwc-times" });
    times.style.height = `${(hi - lo) * px}px`;
    for (let m = lo; m < hi; m += 60) {
      const l = times.createDiv({ cls: "mwc-hour", text: fmtHour(m) });
      l.style.top = `${(m - lo) * px}px`;
      if (m === lo) l.addClass("is-first");
    }
    for (const d of days) {
      const col = g.createDiv({ cls: "mwc-col" + (d === today ? " is-today" : "") + (dt(d).weekday >= 6 ? " is-weekend" : "") });
      col.style.height = `${(hi - lo) * px}px`;
      col.setAttr("title", "Double-click to add an event");
      for (let m = lo; m < hi; m += 30) {
        const ln = col.createDiv({ cls: "mwc-line" + (m % 60 ? " half" : "") });
        ln.style.top = `${(m - lo) * px}px`;
      }
      const evs = occ[d].timed.slice();
      layout(evs);
      for (const e of evs) block(col, e, lo, px, root);
      if (d === today) nowLine(col, lo, hi, px);
      col.addEventListener("dblclick", (ev) => {
        if (ev.target !== col && !ev.target.classList.contains("mwc-line")) return;
        const rect = col.getBoundingClientRect();
        const min = Math.max(lo, Math.min(hi - 30, lo + Math.round((ev.clientY - rect.top) / px / 30) * 30));
        S.form = { date: d, start: hhmm(min), end: hhmm(Math.min(min + 60, 1439)), kind: "meeting", status: "confirmed" };
        draw();
      });
    }

    // agenda
    const ag = root.createDiv({ cls: "mwc-agenda" });
    ag.createDiv({ cls: "mwc-agenda-title", text: "Day by day" });
    let any = 0;
    for (const d of days) {
      const box = createDiv({ cls: "mwc-aday" + (d === today ? " is-today" : "") });
      box.createDiv({ cls: "mwc-aday-head", text: dt(d).toFormat("cccc, LLL d") });
      if (agendaList(box, d, occ, due, root)) { ag.appendChild(box); any++; }
    }
    if (!any) ag.createDiv({ cls: "mwc-empty", text: "Nothing scheduled this week." });
    root.createDiv({ cls: "mwc-hint", text: "Click anything to open its note. Double-click an empty slot to add an event. Classes skip university breaks automatically." });
  };
  draw();
}

function renderForm(root, S, draw, base) {
  const v = S.form;
  const f = root.createDiv({ cls: "mwc-form" });
  const field = (label, el, wide) => {
    const r = f.createDiv({ cls: "mwc-frow" + (wide ? " wide" : "") });
    r.createEl("label", { text: label });
    r.appendChild(el);
    return el;
  };
  const input = (type, value, ph) => { const i = createEl("input", { type }); i.value = value || ""; if (ph) i.placeholder = ph; return i; };
  const select = (opts, value) => {
    const s = createEl("select", { cls: "dropdown" });
    for (const o of opts) s.createEl("option", { text: o ? o.replace(/ MOC$/, "") : "None", value: o });
    s.value = value || "";
    return s;
  };
  const title = field("Title", input("text", v.title, "Call with …"), true);
  const date = field("Date", input("date", v.date));
  const start = field("Start (blank = all day)", input("time", v.start));
  const end = field("End", input("time", v.end));
  const where = field("Where", input("text", v.location, "Room, Zoom link, address"));
  const kind = field("Type", select(FORM_KINDS, v.kind || "meeting"));
  const course = field("Course (optional)", select([""].concat(activeCourses()), v.course || ""));
  const status = field("Status", select(["confirmed", "tentative"], v.status || "confirmed"));
  const notes = createEl("textarea");
  notes.value = v.notes || "";
  notes.rows = 2;
  field("Notes", notes, true);
  const sync = () => Object.assign(S.form, { title: title.value, date: date.value, start: start.value, end: end.value, location: where.value, kind: kind.value, course: course.value, status: status.value, notes: notes.value });
  for (const el of [title, date, start, end, where, kind, course, status, notes]) { el.addEventListener("input", sync); el.addEventListener("change", sync); }
  const actions = f.createDiv({ cls: "mwc-factions" });
  const msg = createSpan({ cls: "mwc-fmsg" });
  button(actions, "Save event", "Save this event", async () => {
    sync();
    const val = S.form;
    if (!val.title || !val.title.trim()) { msg.setText("Add a title."); return; }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(val.date || "")) { msg.setText("Pick a date."); return; }
    try {
      const path = await createEvent(val);
      S.form = null;
      S.flash = `Added “${basename(path).replace(/^\d{4}-\d{2}-\d{2} - /, "")}” to ${dt(val.date).toFormat("ccc, LLL d")}.`;
      S.offset = Math.floor(dt(val.date).startOf("week").diff(base, "weeks").weeks + 0.5);
      window.setTimeout(draw, 400);
    } catch (e) { msg.setText(`Could not save: ${e.message}`); }
  }, "mod-cta");
  button(actions, "Cancel", "Close without saving", () => { S.form = null; draw(); });
  actions.appendChild(msg);
  window.setTimeout(() => { if (title.isConnected && !title.value) title.focus(); }, 0);
}

function renderDay() {
  const root = dv.container.createDiv({ cls: "mwc mwc-day" });
  const d = iso(opt.date) || iso(here && here.date) || iso(here && here.file && here.file.day) || todayISO();
  const data = loadEvents();
  const occ = expand([d], data);
  const due = loadDue([d], data);
  const head = root.createDiv({ cls: "mwc-dayhead-row" });
  head.createSpan({ cls: "mwc-day-title", text: `${dt(d).toFormat("cccc, LLL d")}` });
  const link = head.createSpan({ cls: "mwc-weeklink", text: "Week view →" });
  link.addClass("mwc-click");
  link.addEventListener("click", (ev) => open(WEEK_NOTE, ev));
  const n = agendaList(root, d, occ, due, root);
  if (!n) root.createDiv({ cls: "mwc-empty", text: "Nothing scheduled." });
}

try {
  if (String(opt.mode).toLowerCase() === "day") renderDay();
  else renderWeek();
} catch (err) {
  dv.container.createEl("pre", { text: `Calendar error: ${err && err.stack ? err.stack : err}` });
}
