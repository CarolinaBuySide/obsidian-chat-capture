/*
 * Monthly to-do calendar for this vault: assignments, exams, pre-class prep and dated to-dos.
 *
 * Use in a note:
 *   ```dataviewjs
 *   await dv.view("13 Calendar/System/task-calendar", {mode: "month"})
 *   ```
 * Modes: "month" (default; month: "2026-11" starts on that month), "day" (date: "2026-10-13";
 * defaults to the note's `date`, then today) and "upcoming" (days: 7).
 *
 * What it shows (read live, nothing is copied):
 *   - Tasks with [due:: YYYY-MM-DD] (deadlines) or [scheduled:: YYYY-MM-DD] (suggested dates, drawn lighter)
 *     in 04 Maps, 05 Projects, 11 AI Chats, 13 Calendar, 00 Home, 06 Daily and 07 Weekly.
 *   - Optional task fields: [kind:: assignment|prep|exam|todo], [course:: ECON 101], [time:: 15:30].
 *     Without them, the kind and course are worked out from the note and the text.
 *   - Exam events and university breaks from event notes in 13 Calendar. Classes stay on the Weekly Calendar.
 * Pre-class prep lives in "13 Calendar/Prep/<course> Prep.md"; other dated to-dos in a chat note or "13 Calendar/To-Do.md".
 * Rules for people and agents: AGENTS.md section 10 and "00 Home/Agent/Skills/Skill - Calendar Update.md".
 */

const { DateTime } = dv.luxon;
const app = dv.app;
const opt = Object.assign({ mode: "month" }, (input && typeof input === "object") ? input : {});
const here = dv.current ? dv.current() : null;
const herePath = (here && here.file && here.file.path) || "";

const SOURCES = '"04 Maps" or "05 Projects" or "11 AI Chats" or "13 Calendar" or "00 Home" or "06 Daily" or "07 Weekly"';
const SKIP_PATH = /^(00 Home\/Agent\/|09 Templates\/|08 Archive\/)/;
const PREP_DIR = "13 Calendar/Prep";
const TODO_NOTE = "13 Calendar/To-Do.md";
const WEEK_NOTE = "00 Home/Weekly Calendar.md";
const ADDED_HEADING = "## Added from the Monthly Calendar";
const RANK = { "04 Maps": 0, "05 Projects": 1, "13 Calendar": 2, "06 Daily": 3, "07 Weekly": 3, "00 Home": 3, "11 AI Chats": 4 };
const PALETTE = {
  indigo: "#5A67D8", magenta: "#B83DBA", amber: "#D4A017", emerald: "#10B981", coral: "#FF7F50",
  red: "#C0504D", lime: "#84CC16", cyan: "#06B6D4", gray: "#8A8F98", grey: "#8A8F98",
  blue: "#4A90D9", green: "#3FA66B", purple: "#8E6BD1", orange: "#E07B39", teal: "#2BA3A3",
  pink: "#D6589B", gold: "#E0A526", violet: "#7B61C9", brown: "#8C7B6B", slate: "#6B7A8F",
  "carolina blue": "#4B9CD3",
};
const PERSONAL = "#D6589B";
const PROJECT = "#E07B39";
const EXAM = "#C0504D";
const KIND = {
  exam: { order: 0, tag: "Exam", label: "Exams" },
  assignment: { order: 1, tag: "Due", label: "Assignments" },
  prep: { order: 2, tag: "Prep", label: "Pre-class prep" },
  todo: { order: 3, tag: "To-do", label: "To-dos" },
  event: { order: 4, tag: "Event", label: "Events" },
};
const FILTERS = [
  ["work", "Assignments & exams", true],
  ["prep", "Pre-class prep", true],
  ["todo", "To-dos", true],
  ["soft", "Optional & suggested", true],
  ["events", "Other events", false],
  ["done", "Done", true],
];
const FILTER_KEY = "marc-task-calendar-filters";
const MAX_CHIPS = 4;
const PAST_DUE_DAYS = 21;
const DAYMAP = {
  m: 1, mo: 1, mon: 1, monday: 1, t: 2, tu: 2, tue: 2, tues: 2, tuesday: 2, w: 3, we: 3, wed: 3, wednesday: 3,
  r: 4, th: 4, thu: 4, thur: 4, thurs: 4, thursday: 4, f: 5, fr: 5, fri: 5, friday: 5,
  s: 6, sa: 6, sat: 6, saturday: 6, u: 7, su: 7, sun: 7, sunday: 7,
};
const MONTHS = "jan feb mar apr may jun jul aug sep sept oct nov dec january february march april june july august september october november december".split(" ");
const STOP = new Set(("the a an to of for and or in on at by with from your my our this that is are be due submit take complete "
  + "do canvas am pm mon tue tues wed thu thur thurs fri sat sun monday tuesday wednesday thursday friday saturday sunday "
  + "before class read today tomorrow tentative " + MONTHS.join(" ")).split(" "));
const DATE_MENTION = /,?\s*\b(?:mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)[a-z]*\.?,?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{1,2}\b(?:,?\s*\d{4})?/i;

/* ---------- small helpers ---------- */

const pad = (n) => String(n).padStart(2, "0");
const dt = (s) => DateTime.fromISO(s);
const todayISO = () => DateTime.local().toISODate();
const basename = (p) => String(p).split("/").pop().replace(/\.md$/i, "");
const esc = (s) => String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const toArr = (v) => {
  if (v === null || v === undefined || v === "") return [];
  if (Array.isArray(v)) return v;
  if (typeof v === "object" && typeof v.array === "function") return v.array();
  return [v];
};
function iso(v) {
  if (Array.isArray(v)) return iso(v[0]);
  if (!v) return null;
  if (DateTime.isDateTime(v)) return v.isValid ? v.toISODate() : null;
  if (v instanceof Date) return DateTime.fromJSDate(v).toISODate();
  if (typeof v === "object") return null;
  const m = String(v).trim().match(/^(\d{4}-\d{2}-\d{2})/);
  return m ? m[1] : null;
}
function toMin(v) {
  if (v === null || v === undefined || v === "") return null;
  if (typeof v === "number" && isFinite(v)) return v >= 0 && v <= 1440 ? Math.round(v) : null;
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
function fmtTime(min) {
  const h = Math.floor(min / 60) % 24, m = min % 60;
  const ap = h >= 12 ? "pm" : "am";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return m ? `${h12}:${pad(m)} ${ap}` : `${h12} ${ap}`;
}
function fmtShortTime(min) {
  const h = Math.floor(min / 60) % 24, m = min % 60;
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}${m ? ":" + pad(m) : ""}${h >= 12 ? "p" : "a"}`;
}
function fmtRange(s, e) {
  if (s === null || s === undefined) return "";
  if (e === null || e === undefined) return fmtTime(s);
  const same = (s >= 720) === (e >= 720);
  const a = fmtTime(s), b = fmtTime(e);
  return same ? `${a.replace(/ (am|pm)$/, "")}–${b}` : `${a}–${b}`;
}
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
function plain(s) {
  return String(s)
    .replace(/\[([^\]]+)\]\((?:[^)\s]+)\)/g, "$1")
    .replace(/\[\[([^\]|#]+)(?:#[^\]|]*)?\|([^\]]+)\]\]/g, "$2")
    .replace(/\[\[([^\]|#]+)(?:#[^\]|]*)?\]\]/g, "$1")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\s+/g, " ").trim();
}
function tokens(s) {
  return new Set(plain(s).toLowerCase().replace(/[^a-z0-9 ]+/g, " ").split(/\s+/)
    .filter((w) => w.length > 2 && !STOP.has(w) && !/^\d+$/.test(w)));
}
function sharedCount(a, b) { let n = 0; for (const w of a) if (b.has(w)) n++; return n; }
function overlap(a, b) { return !a.size || !b.size ? 0 : sharedCount(a, b) / Math.min(a.size, b.size); }
function cleanText(text) {
  return String(text || "")
    .replace(/\[[\w-]+::[^\]]*\]/g, "")
    .replace(/\([\w-]+::[^)]*\)/g, "")
    .replace(/\s+/g, " ").trim();
}
function dueTime(text) {
  const s = plain(text);
  const m = s.match(DATE_MENTION);
  const after = m ? m.index + m[0].length : 0;
  const re = /\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?(?:\s*[–-]\s*(\d{1,2})(?::(\d{2}))?)?\s*(am|pm)\b/gi;
  let r, first = null;
  while ((r = re.exec(s))) {
    let min;
    if (r[4] !== undefined) {
      // a range like "3:00–3:30 pm" or "11 am–1 pm": the start counts
      const endMer = r[6].toLowerCase();
      let startMer = r[3] ? r[3].toLowerCase() : endMer;
      if (!r[3] && endMer === "pm" && Number(r[1]) !== 12 && Number(r[1]) > Number(r[4]) && Number(r[4]) !== 12) startMer = "am";
      min = toMin(`${r[1]}${r[2] ? ":" + r[2] : ""} ${startMer}`);
    } else min = toMin(`${r[1]}${r[2] ? ":" + r[2] : ""} ${r[6]}`);
    if (min === null) continue;
    if (first === null) first = min;
    if (m && r.index >= after) return min;
  }
  return m ? null : first;
}
function splitLabel(text, code) {
  const m = text.match(DATE_MENTION);
  let main = m && m.index > 2 ? text.slice(0, m.index) : text;
  let rest = m && m.index > 2 ? text.slice(m.index + m[0].length) : "";
  main = main.replace(/\s+/g, " ").replace(/[\s,;:–-]+$/, "").trim();
  rest = rest.replace(/^\s*(?:,?\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)(?:\s*[–-]\s*\d{1,2}(?::\d{2})?\s*(?:am|pm))?)/i, "").replace(/^[\s,;:–-]+/, "").trim();
  if (code) main = main.replace(new RegExp("^\\s*" + esc(code) + "\\s*[:·,–—-]?\\s*", "i"), "");
  return { label: main || text, detail: rest };
}
function state(key) {
  const all = (window.__marcTaskCal = window.__marcTaskCal || {});
  const today = todayISO();
  let s = all[key];
  if (!s || s.day !== today) s = all[key] = { offset: 0, selected: null, form: null, flash: "", day: today, open: {} };
  return s;
}
function loadFilters() {
  const f = {};
  for (const [k, , d] of FILTERS) f[k] = d;
  try { Object.assign(f, JSON.parse(window.localStorage.getItem(FILTER_KEY) || "{}")); } catch (e) { /* defaults */ }
  return f;
}
function saveFilters(f) { try { window.localStorage.setItem(FILTER_KEY, JSON.stringify(f)); } catch (e) { /* ignore */ } }
const shortCode = (code) => (code ? String(code).replace(/^[A-Z]{3,4}\s+/, "") : "");

/* ---------- data ---------- */

function loadCourses() {
  const map = new Map();
  let maps = [];
  try { maps = dv.pages('"04 Maps"'); } catch (e) { maps = []; }
  for (const p of maps) {
    const tags = toArr(p.file.tags).map(String);
    if (!tags.some((t) => t.startsWith("#course"))) continue;
    const code = p.file.name.replace(/\s+MOC$/i, "");
    map.set(code, { code, path: p.file.path, color: colorOf(p.color) || PALETTE.violet, active: String(p.status || "") === "active", start: null, days: [], from: null, to: null });
  }
  let classes = [];
  try { classes = dv.pages('"13 Calendar/Classes"'); } catch (e) { classes = []; }
  for (const p of classes) {
    const cp = linkPath(p.course, p.file.path);
    const code = cp ? basename(cp).replace(/\s+MOC$/i, "") : null;
    if (!code || !map.has(code)) continue;
    Object.assign(map.get(code), { start: toMin(p["start-time"]), days: parseDays(p.days), from: iso(p.date), to: iso(p["end-date"]) });
  }
  return map;
}

function courseFromValue(v, courses, from) {
  if (!v) return null;
  const s = String(typeof v === "object" && v.path ? v.path : v);
  const lp = /\[\[|\.md$|\//.test(s) || (typeof v === "object" && v.path) ? linkPath(v, from) : null;
  const name = lp ? basename(lp).replace(/\s+MOC$/i, "") : s.replace(/\s+MOC$/i, "").trim();
  if (courses.has(name)) return name;
  const hit = [...courses.keys()].find((c) => c.toLowerCase() === name.toLowerCase());
  return hit || null;
}

function loadEvents(courses) {
  const exams = [], marks = [], other = [];
  let pages = [];
  try { pages = dv.pages('"13 Calendar"'); } catch (e) { pages = []; }
  for (const p of pages) {
    if (String(p.type || "").toLowerCase() !== "event") continue;
    if (String(p.repeat || "").toLowerCase() === "weekly") continue;
    const kind = String(p.kind || "other").toLowerCase();
    const status = String(p.status || "confirmed").toLowerCase();
    if (status === "cancelled" || kind === "class") continue;
    const date = iso(p.date);
    if (!date) continue;
    const code = courseFromValue(p.course, courses, p.file.path);
    const ev = {
      path: p.file.path, kind, status, date, end: iso(p["end-date"]) || date, course: code,
      title: p.title ? String(p.title) : p.file.name.replace(/^\d{4}-\d{2}-\d{2}\s*-\s*/, ""),
      color: (code && courses.get(code).color) || colorOf(p.color) || (kind === "exam" ? EXAM : PALETTE.slate),
      start: toMin(p["start-time"]), stop: toMin(p["end-time"]), location: p.location ? String(p.location) : "",
    };
    if (kind === "exam") exams.push(ev);
    else if (kind === "break" || kind === "academic") marks.push(ev);
    else other.push(ev);
  }
  return { exams, marks, other };
}

function inferKind(raw, folder, pageKind, hasCourse) {
  if (KIND[pageKind]) return pageKind;
  const s = plain(raw);
  if (/\b(final exam|mid-?mod exam|midterm|exam)\b/i.test(s)) return "exam";
  if (/^(read|watch|listen|review|prepare|prep|print)\b/i.test(s) || /\b(readings?|pre-?reads?|videos?|before class|podcasts?|bring)\b/i.test(s)) return hasCourse ? "prep" : "todo";
  if (folder === "04 Maps" && hasCourse) return "assignment";
  if (hasCourse && /\b(quiz|assignment|case|paper|memo|essay|problem set|report|brief|presentation|submit|peer)\b/i.test(s)) return "assignment";
  return "todo";
}

function loadTasks(courses, exams) {
  const items = [], undated = [];
  const codes = [...courses.keys()].sort((a, b) => b.length - a.length);
  const codeRe = codes.length ? new RegExp("\\b(" + codes.map(esc).join("|") + ")\\b", "i") : null;
  const examKeys = new Set(exams.filter((e) => e.course).map((e) => `${e.course}|${e.date}`));
  let pages = [];
  try { pages = dv.pages(SOURCES); } catch (e) { pages = []; }
  for (const p of pages) {
    const path = p.file.path;
    if (SKIP_PATH.test(path)) continue;
    const tasks = p.file.tasks;
    if (!tasks || !tasks.length) continue;
    const folder = path.split("/")[0];
    const isPrep = path.startsWith(PREP_DIR + "/");
    const isTodo = path === TODO_NOTE;
    const tags = toArr(p.file.tags).map(String);
    const mapCourse = folder === "04 Maps" && tags.some((t) => t.startsWith("#course")) ? p.file.name.replace(/\s+MOC$/i, "") : null;
    const pageCourse = (mapCourse && courses.has(mapCourse) ? mapCourse : null) || courseFromValue(p.course, courses, path);
    const pageKind = String(p["task-kind"] || "").toLowerCase();
    for (const t of tasks) {
      const due = iso(t.due), sch = iso(t.scheduled);
      const date = due || sch;
      const isChild = t.parent !== undefined && t.parent !== null;
      if (!date && (!(isPrep || isTodo) || isChild)) continue;
      const raw = cleanText(t.text);
      if (!raw) continue;
      const textCode = codeRe ? (plain(raw).match(codeRe) || [])[1] : null;
      const code = courseFromValue(t.course, courses, path) || pageCourse || (textCode ? codes.find((c) => c.toLowerCase() === textCode.toLowerCase()) : null);
      const course = code ? courses.get(code) : null;
      const explicit = String(t.kind || "").toLowerCase().trim();
      const kind = KIND[explicit] ? explicit : (!date ? "todo" : inferKind(raw, folder, pageKind, !!course));
      if (kind === "exam" && code && date && examKeys.has(`${code}|${date}`)) continue; // drawn from the exam event instead
      const { label, detail } = splitLabel(raw, code);
      const kids = toArr(t.children).filter((c) => c && c.task);
      const item = {
        id: `${path}#${t.line}`, path, line: t.line, src: String(t.text || ""), folder, rank: RANK[folder] ?? 5,
        date, soft: !due && !!sch, kind, course: code, active: course ? course.active : true,
        color: course ? course.color : (folder === "05 Projects" ? PROJECT : PERSONAL),
        text: raw, label, detail, completed: !!t.completed,
        time: toMin(t.time) ?? dueTime(raw), beforeClass: false,
        tentative: /\btentative\b/i.test(raw) || String(t.status || "").toLowerCase() === "tentative",
        kids: kids.length, kidsDone: kids.filter((c) => c.completed).length,
        source: basename(path), tok: tokens(label), norm: plain(label).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim(),
      };
      if (item.time === null && kind === "prep" && course && course.start !== null && date) {
        const x = dt(date);
        if (course.days.includes(x.weekday) && (!course.from || date >= course.from) && (!course.to || date <= course.to)) {
          item.time = course.start; item.beforeClass = true;
        }
      }
      if (!date) { if (!item.completed) undated.push(item); continue; }
      items.push(item);
    }
  }
  return { items: dedupe(items), undated };
}

function dedupe(items) {
  const isLoose = (x) => x.folder === "11 AI Chats" || x.path.startsWith(PREP_DIR + "/") || x.path === TODO_NOTE;
  const sorted = items.slice().sort((a, b) => a.rank - b.rank || b.kids - a.kids || b.text.length - a.text.length);
  const kept = [];
  for (const c of sorted) {
    const k = kept.find((k) => {
      if (k.date !== c.date) return false;
      const samePath = k.path === c.path;
      const scope = samePath || (k.course && k.course === c.course) || (!k.course && !c.course) || isLoose(k) || isLoose(c);
      if (!scope) return false;
      if (k.norm === c.norm) return true;
      return k.cluster.some((tk) => {
        const ov = overlap(tk, c.tok);
        if (samePath) return Math.min(tk.size, c.tok.size) >= 2 && ov >= 0.8;
        return (Math.min(tk.size, c.tok.size) >= 2 && ov >= 0.6) || (k.folder !== c.folder && sharedCount(tk, c.tok) >= 3);
      });
    });
    if (k) {
      k.also.push(c); k.cluster.push(c.tok);
      if (c.completed) k.anyDone = true;
      if (c.label !== k.label && !k.notes.includes(c.label) && c.label.length > 4) k.notes.push(c.label);
      continue;
    }
    c.also = []; c.cluster = [c.tok]; c.notes = []; c.anyDone = c.completed;
    kept.push(c);
  }
  for (const k of kept) k.completed = k.completed || k.anyDone;
  return kept;
}

function getData() {
  const courses = loadCourses();
  const events = loadEvents(courses);
  const { items, undated } = loadTasks(courses, events.exams);
  return { courses, events, items, undated };
}

function examItem(e) {
  return {
    id: e.path, path: e.path, line: 0, kind: "exam", event: true, date: e.date, course: e.course, color: e.color,
    label: e.title.replace(new RegExp("^" + esc(e.course || "") + "\\s*", "i"), "") || e.title,
    detail: e.location && !/tbd/i.test(e.location) ? e.location : "", time: e.start, stop: e.stop,
    tentative: e.status === "tentative", completed: false, soft: false, active: true, kids: 0, notes: [], also: [], source: basename(e.path),
  };
}
function eventItem(e, d) {
  return {
    id: `${e.path}|${d}`, path: e.path, line: 0, kind: "event", event: true, date: d, course: e.course, color: e.color,
    label: e.title, detail: e.location, time: e.start, stop: e.stop, tentative: e.status === "tentative",
    completed: false, soft: false, active: true, kids: 0, notes: [], also: [], source: basename(e.path),
  };
}

function visible(it, F) {
  if (it.completed && !F.done) return false;
  if (it.kind === "event") return F.events;
  if (it.soft) return F.soft;
  if (it.kind === "exam" || it.kind === "assignment") return F.work;
  if (it.kind === "prep") return F.prep;
  return F.todo;
}
function sortItems(a, b) {
  return (a.completed - b.completed) || (KIND[a.kind].order - KIND[b.kind].order) || (a.soft - b.soft)
    || ((a.time ?? 1500) - (b.time ?? 1500)) || a.label.localeCompare(b.label);
}
function byDay(data, days, F) {
  const want = new Set(days);
  const out = {};
  for (const d of days) out[d] = { items: [], marks: [] };
  for (const it of data.items) if (want.has(it.date) && visible(it, F)) out[it.date].items.push(it);
  if (F.work) for (const e of data.events.exams) if (want.has(e.date)) out[e.date].items.push(examItem(e));
  if (F.events) for (const e of data.events.other) for (const d of span(e.date, e.end)) if (want.has(d)) out[d].items.push(eventItem(e, d));
  for (const e of data.events.marks) for (const d of span(e.date, e.end)) if (want.has(d)) out[d].marks.push(e);
  for (const d of days) out[d].items.sort(sortItems);
  return out;
}

/* ---------- actions ---------- */

function open(path, ev) { app.workspace.openLinkText(path, herePath, !!(ev && (ev.metaKey || ev.ctrlKey))); }
async function openAt(path, line, ev) {
  const f = app.vault.getAbstractFileByPath(path);
  if (!f) return;
  const leaf = app.workspace.getLeaf(ev && (ev.metaKey || ev.ctrlKey) ? "tab" : false);
  await leaf.openFile(f, { eState: { line } });
}
const CHECKBOX = /^(\s*(?:[-*+]|\d+[.)])\s+\[)(.)(\])/;
async function setDone(it, done) {
  for (const c of [it].concat(it.also || [])) {
    const f = app.vault.getAbstractFileByPath(c.path);
    if (!f || c.event) continue;
    let ok = false;
    await app.vault.process(f, (txt) => {
      const lines = txt.split("\n");
      const probe = c.src.slice(0, 40);
      let i = c.line;
      if (!(lines[i] !== undefined && CHECKBOX.test(lines[i]) && lines[i].includes(probe))) {
        const hits = lines.map((l, n) => (CHECKBOX.test(l) && l.includes(c.src) ? n : -1)).filter((n) => n >= 0);
        if (hits.length !== 1) return txt;
        i = hits[0];
      }
      ok = true;
      lines[i] = lines[i].replace(CHECKBOX, `$1${done ? "x" : " "}$3`);
      return lines.join("\n");
    });
    if (!ok && c === it) throw new Error(`couldn't find that task line in ${c.source}; open the note and check it off there`);
    if (ok) c.completed = done;
  }
  it.completed = done;
}
async function ensureFolder(dir) {
  if (!dir || app.vault.getAbstractFileByPath(dir)) return;
  const parts = dir.split("/");
  for (let i = 1; i <= parts.length; i++) {
    const p = parts.slice(0, i).join("/");
    if (!app.vault.getAbstractFileByPath(p)) await app.vault.createFolder(p);
  }
}
function noteTemplate(path, code) {
  const now = DateTime.local().toFormat("yyyy-LL-dd'T'HH:mm");
  if (code) {
    return ["---", "type: task-list", `summary: "Pre-class readings, prep and other dated to-dos for ${code}, shown on the Monthly Calendar."`,
      `course: "[[${code} MOC]]"`, "task-kind: prep", `created: ${now}`, "tags:", "  - task-list", "  - calendar", "---",
      `# ${code} Prep`, `← [[Monthly Calendar]] · [[${code} MOC]]`, "", ADDED_HEADING, ""].join("\n");
  }
  return ["---", "type: task-list", 'summary: "Dated to-dos that don\'t belong to a course, project or chat note, shown on the Monthly Calendar."',
    `created: ${now}`, "tags:", "  - task-list", "  - calendar", "---", "# To-Do", "← [[Monthly Calendar]] · [[Calendar MOC]]", "", "## To-dos", ""].join("\n");
}
async function appendTask(v) {
  const code = v.course || "";
  const path = code ? `${PREP_DIR}/${code} Prep.md` : TODO_NOTE;
  let f = app.vault.getAbstractFileByPath(path);
  if (!f) { await ensureFolder(path.split("/").slice(0, -1).join("/")); f = await app.vault.create(path, noteTemplate(path, code)); }
  const parts = [`- [ ] ${v.text.replace(/\s+/g, " ").trim()}`];
  const tm = toMin(v.time);
  if (tm !== null) parts[0] += `, ${fmtTime(tm)}`;
  parts.push(v.soft ? `[scheduled:: ${v.date}]` : `[due:: ${v.date}]`);
  if (v.kind && v.kind !== (code ? "prep" : "todo")) parts.push(`[kind:: ${v.kind}]`);
  const line = parts.join(" ");
  await app.vault.process(f, (txt) => {
    let out = txt.replace(/\s*$/, "\n");
    if (code && !out.includes(ADDED_HEADING)) out += `\n${ADDED_HEADING}\n`;
    return out + line + "\n";
  });
  return path;
}

/* ---------- rendering ---------- */

function renderInline(el, s) {
  const re = /\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)|\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]|\*\*([^*]+)\*\*|`([^`]+)`/g;
  let last = 0, m;
  while ((m = re.exec(s))) {
    if (m.index > last) el.appendChild(document.createTextNode(s.slice(last, m.index)));
    if (m[2]) {
      const a = el.createEl("a", { text: m[1], cls: "external-link", href: m[2] });
      a.setAttr("target", "_blank"); a.setAttr("rel", "noopener");
      a.addEventListener("click", (ev) => ev.stopPropagation());
    } else if (m[3]) {
      const target = m[3];
      const a = el.createEl("a", { text: m[4] || m[3], cls: "internal-link" });
      a.addEventListener("click", (ev) => { ev.preventDefault(); ev.stopPropagation(); open(target, ev); });
    } else if (m[5]) el.createEl("strong", { text: m[5] });
    else if (m[6]) el.createEl("code", { text: m[6] });
    last = re.lastIndex;
  }
  if (last < s.length) el.appendChild(document.createTextNode(s.slice(last)));
}
function button(parent, text, title, onClick, cls) {
  const b = parent.createEl("button", { text, cls: cls || "" });
  b.setAttr("aria-label", title);
  b.addEventListener("click", (ev) => { ev.preventDefault(); ev.stopPropagation(); onClick(ev); });
  return b;
}

// ---- Canvas sync bar (month view) ----
// Shows when Canvas was last synced (procedure: 00 Home/Agent/Skills/Skill - Canvas Sync.md) and a
// "Copy sync request" button: paste the copied request into any AI that can run commands on this computer.
// Optional: if ~/.config/perplexity/canvas-sync.json holds a Perplexity automation webhook (url and token,
// kept outside the vault and never shown), the button starts that automation instead.
const SYNC_STATE = "13 Calendar/System/canvas-sync/state.json";
const SYNC_SKILL = "00 Home/Agent/Skills/Skill - Canvas Sync.md";
const SYNC_ASKED = "canvas-sync-requested";
const SYNC_WAIT = 20 * 60000;
function syncConfig() {
  try {
    const req = window.require;
    const path = req("path"), os = req("os"), fs = req("fs");
    const file = path.join(os.homedir(), ".config", "perplexity", "canvas-sync.json");
    if (!fs.existsSync(file)) return null;
    const cfg = JSON.parse(fs.readFileSync(file, "utf8"));
    return cfg && cfg.url && cfg.token ? cfg : null;
  } catch (e) { return null; }
}
function notify(msg) {
  try { const { Notice } = window.require("obsidian"); new Notice(msg, 8000); } catch (e) { /* no notices on this device */ }
}
function syncAsked() { const v = Number(window.localStorage.getItem(SYNC_ASKED) || 0); return Number.isFinite(v) ? v : 0; }
function clock(t) { return t.toFormat("h:mm a").replace(":00 ", " ").toLowerCase(); }
function renderSyncBar(root) {
  // Hidden in vaults without the Canvas sync (no skill note, no past sync, no webhook config).
  if (!syncConfig() && !app.vault.getAbstractFileByPath(SYNC_STATE) && !app.vault.getAbstractFileByPath(SYNC_SKILL)) return async () => {};
  const bar = root.createDiv({ cls: "mtc-sync" });
  const status = bar.createSpan({ cls: "mtc-sync-status", text: "Canvas: checking the last sync…" });
  const cfg = syncConfig();
  let btn = null;
  const paint = (st) => {
    const asked = syncAsked();
    const ran = st && st.last_run ? DateTime.fromISO(st.last_run) : null;
    const ranMs = ran && ran.isValid ? ran.toMillis() : 0;
    const running = !!asked && ranMs < asked && Date.now() - asked < SYNC_WAIT;
    let s = "Canvas hasn't been synced yet.", stale = false;
    if (running) {
      s = `Canvas sync started at ${clock(DateTime.fromMillis(asked))}. Perplexity is updating your notes and will notify you when it's done.`;
    } else if (ranMs) {
      const days = Math.floor(DateTime.local().diff(ran, "days").days);
      s = `Canvas synced ${ran.toFormat("ccc LLL d")}, ${clock(ran)}`;
      if (st.summary) s += ` · ${st.summary}`;
      if (days >= 3) { s += ` · ${days} days ago`; stale = true; }
    }
    status.textContent = s;
    status.classList.toggle("is-stale", stale);
    if (btn) { btn.disabled = running; btn.textContent = running ? "Sync running…" : "Sync from Canvas"; }
  };
  const load = async () => {
    let st = null;
    try { if (await app.vault.adapter.exists(SYNC_STATE)) st = JSON.parse(await app.vault.adapter.read(SYNC_STATE)); } catch (e) { st = null; }
    paint(st);
  };
  if (cfg) {
    btn = button(bar, "Sync from Canvas", "Ask Perplexity to pull new Canvas deadlines, readings and class changes into your notes", async () => {
      btn.disabled = true; btn.textContent = "Starting…";
      try {
        const request = window.requestUrl || window.require("obsidian").requestUrl;
        const r = await request({
          url: cfg.url, method: "POST", contentType: "application/json", throw: false,
          headers: { "X-Pplx-Automation-Webhook-Token": cfg.token, "x-pplx-webhook-delivery-id": `obsidian-${Date.now()}` },
          body: JSON.stringify({ source: "Obsidian Monthly Calendar", requested_at: new Date().toISOString() }),
        });
        if (r.status >= 200 && r.status < 300) {
          window.localStorage.setItem(SYNC_ASKED, String(Date.now()));
          notify("Canvas sync started. Perplexity will update your calendar and notify you when it's done.");
        } else notify(`Canvas sync didn't start (error ${r.status}). You can run it from the Automations page in Perplexity.`);
      } catch (e) { notify(`Canvas sync didn't start: ${e && e.message ? e.message : e}`); }
      load();
    }, "mod-cta");
  } else {
    if (app.vault.getAbstractFileByPath(SYNC_SKILL)) {
      button(bar, "Copy sync request", "Copy a request to paste into any AI that can run commands on this computer", async () => {
        const base = app.vault.adapter && app.vault.adapter.basePath ? app.vault.adapter.basePath : app.vault.getName();
        const ask = `Sync my Obsidian vault from Canvas. The vault is at "${base}". Read "00 Home/Agent/Skills/Skill - Canvas Sync.md" in it and follow it exactly, then tell me what changed.`;
        try { await navigator.clipboard.writeText(ask); notify("Copied. Paste it into your AI to sync from Canvas."); }
        catch (e) { notify("Couldn't copy. Ask your AI to follow the Canvas Sync skill note."); }
      });
      const how = bar.createSpan({ cls: "mtc-sync-how", text: "How to sync" });
      how.addEventListener("click", (ev) => open(SYNC_SKILL, ev));
    }
  }
  load();
  return load;
}
function whenText(it) {
  if (it.kind === "exam" || it.kind === "event") return it.time !== null && it.time !== undefined ? fmtRange(it.time, it.stop) : "All day";
  if (it.time === null || it.time === undefined) return it.soft ? "Suggested" : "Any time";
  if (it.beforeClass) return `Before ${fmtTime(it.time)}`;
  return it.kind === "todo" ? fmtTime(it.time) : `Due ${fmtTime(it.time)}`;
}
function tipText(it) {
  const lines = [(it.course ? `${it.course}: ` : "") + plain(it.label)];
  lines.push(`${dt(it.date).toFormat("cccc, LLL d")} · ${whenText(it)}`);
  if (it.detail) lines.push(plain(it.detail));
  for (const n of it.notes || []) lines.push(`Also: ${plain(n)}`);
  lines.push(`From ${it.source}`);
  return lines.join("\n");
}
function chip(cell, it, onPick) {
  const c = cell.createDiv({ cls: `mtc-chip k-${it.kind}` + (it.soft ? " is-soft" : "") + (it.completed ? " is-done" : "") + (it.tentative ? " is-tentative" : "") });
  c.style.setProperty("--ev", it.color);
  if (it.kind === "exam") c.createSpan({ cls: "mtc-chip-tag", text: "Exam" });
  else if (it.time !== null && it.time !== undefined && !it.beforeClass) c.createSpan({ cls: "mtc-chip-time", text: fmtShortTime(it.time) });
  if (it.course) c.createSpan({ cls: "mtc-chip-code", text: shortCode(it.course) });
  c.createSpan({ cls: "mtc-chip-text", text: plain(it.label) });
  c.setAttr("title", tipText(it) + "\nClick for the day's list. Cmd/Ctrl-click opens the note.");
  c.addEventListener("click", (ev) => {
    ev.stopPropagation();
    if (ev.metaKey || ev.ctrlKey) { it.event ? open(it.path, ev) : openAt(it.path, it.line, ev); return; }
    onPick();
  });
}
function row(list, it, redraw, showDate) {
  const li = list.createDiv({ cls: `mtc-row k-${it.kind}` + (it.completed ? " is-done" : "") + (it.soft ? " is-soft" : "") + (it.tentative ? " is-tentative" : "") });
  li.style.setProperty("--ev", it.color);
  const box = li.createDiv({ cls: "mtc-row-box" });
  if (!it.event) {
    const cb = box.createEl("input", { type: "checkbox", cls: "task-list-item-checkbox mtc-check" });
    cb.checked = !!it.completed;
    cb.setAttr("aria-label", it.completed ? "Mark as not done" : "Mark as done");
    cb.addEventListener("click", (ev) => ev.stopPropagation());
    cb.addEventListener("change", async () => {
      try { await setDone(it, cb.checked); } catch (e) {
        cb.checked = !cb.checked;
        li.addClass("is-error");
        li.setAttr("title", `Couldn't update: ${e.message}`);
        return;
      }
      redraw();
    });
  } else box.createSpan({ cls: "mtc-row-dot" });
  const when = li.createDiv({ cls: "mtc-row-when" });
  if (showDate) when.createDiv({ cls: "mtc-row-date", text: dt(it.date).toFormat("ccc LLL d") });
  when.createDiv({ text: whenText(it) });
  const body = li.createDiv({ cls: "mtc-row-body" });
  const top = body.createDiv({ cls: "mtc-row-top" });
  top.createSpan({ cls: `mtc-tag k-${it.kind}`, text: it.soft ? (it.kind === "prep" ? "Optional" : "Suggested") : KIND[it.kind].tag });
  if (it.course) { const cc = top.createSpan({ cls: "mtc-row-course", text: it.course }); cc.style.setProperty("--ev", it.color); }
  const name = top.createSpan({ cls: "mtc-row-name" });
  renderInline(name, it.label);
  if (it.tentative) top.createSpan({ cls: "mtc-row-flag", text: "tentative" });
  const meta = [];
  if (it.detail) meta.push(it.detail);
  if (it.kids) meta.push(`${it.kidsDone}/${it.kids} steps done`);
  for (const n of it.notes || []) meta.push(`Also: ${n}`);
  if (meta.length) { const m = body.createDiv({ cls: "mtc-row-meta" }); renderInline(m, meta.join(" · ")); }
  const src = body.createDiv({ cls: "mtc-row-src", text: it.source });
  src.setAttr("title", "Open the note this comes from");
  src.addEventListener("click", (ev) => { ev.stopPropagation(); it.event ? open(it.path, ev) : openAt(it.path, it.line, ev); });
  return li;
}
function dayList(parent, items, redraw, opts) {
  const list = parent.createDiv({ cls: "mtc-list" });
  for (const it of items) row(list, it, redraw, opts && opts.showDate);
  return list;
}
function quickAdd(parent, date, S, redraw) {
  const wrap = parent.createDiv({ cls: "mtc-quick" });
  const inp = wrap.createEl("input", { type: "text", cls: "mtc-quick-input" });
  inp.placeholder = `Add a to-do for ${dt(date).toFormat("ccc, LLL d")}…`;
  const go = async () => {
    const text = inp.value.trim();
    if (!text) return;
    try {
      const path = await appendTask({ text, date, kind: "todo" });
      S.flash = `Added to ${basename(path)}: “${text}” (${dt(date).toFormat("ccc, LLL d")}).`;
      inp.value = "";
      window.setTimeout(redraw, 600);
    } catch (e) { err.setText(`Couldn't add it: ${e.message}`); }
  };
  inp.addEventListener("keydown", (ev) => { if (ev.key === "Enter") { ev.preventDefault(); go(); } });
  button(wrap, "Add", "Add this to-do", go);
  const err = wrap.createSpan({ cls: "mtc-fmsg" });
}

function renderForm(root, S, data, redraw) {
  const v = S.form;
  const f = root.createDiv({ cls: "mtc-form" });
  const field = (label, el, wide) => {
    const r = f.createDiv({ cls: "mtc-frow" + (wide ? " wide" : "") });
    r.createEl("label", { text: label });
    r.appendChild(el);
    return el;
  };
  const input = (type, value, ph) => { const i = createEl("input", { type }); i.value = value || ""; if (ph) i.placeholder = ph; return i; };
  const select = (opts, value) => {
    const s = createEl("select", { cls: "dropdown" });
    for (const [val, text] of opts) s.createEl("option", { text, value: val });
    s.value = value || "";
    return s;
  };
  const what = field("What needs doing", input("text", v.text, "Read chapter 5, email Professor Boyer, buy the case pack…"), true);
  const date = field("Date", input("date", v.date));
  const time = field("Time (optional)", input("time", v.time));
  const active = [...data.courses.values()].filter((c) => c.active).map((c) => c.code).sort();
  const course = field("Course (optional)", select([["", "None"]].concat(active.map((c) => [c, c])), v.course || ""));
  const kind = field("Type", select([["todo", "To-do"], ["prep", "Pre-class prep"], ["assignment", "Assignment"]], v.kind || "todo"));
  const softWrap = createDiv({ cls: "mtc-soft" });
  const soft = softWrap.createEl("input", { type: "checkbox" });
  soft.checked = !!v.soft;
  softWrap.createSpan({ text: " Suggested date, not a deadline" });
  field("Deadline?", softWrap);
  const sync = () => Object.assign(S.form, { text: what.value, date: date.value, time: time.value, course: course.value, kind: kind.value, soft: soft.checked });
  for (const el of [what, date, time, course, kind, soft]) { el.addEventListener("input", sync); el.addEventListener("change", sync); }
  const actions = f.createDiv({ cls: "mtc-factions" });
  const msg = createSpan({ cls: "mtc-fmsg" });
  button(actions, "Save to-do", "Save this to-do", async () => {
    sync();
    const val = S.form;
    if (!val.text || !val.text.trim()) { msg.setText("Say what needs doing."); return; }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(val.date || "")) { msg.setText("Pick a date."); return; }
    try {
      const path = await appendTask(val);
      S.form = null;
      S.selected = val.date;
      S.offset = Math.round(dt(val.date).startOf("month").diff(S.base, "months").months);
      S.flash = `Added to ${basename(path)}: “${val.text.trim()}” (${dt(val.date).toFormat("ccc, LLL d")}).`;
      window.setTimeout(redraw, 600);
    } catch (e) { msg.setText(`Couldn't save: ${e.message}`); }
  }, "mod-cta");
  button(actions, "Cancel", "Close without saving", () => { S.form = null; redraw(); });
  actions.appendChild(msg);
  window.setTimeout(() => { if (what.isConnected && !what.value) what.focus(); }, 0);
}

function headLabel(d, today) {
  const x = dt(d);
  const diff = Math.round(x.diff(dt(today), "days").days);
  const name = x.toFormat("cccc, LLL d");
  if (diff === 0) return `Today · ${name}`;
  if (diff === 1) return `Tomorrow · ${name}`;
  if (diff === -1) return `Yesterday · ${name}`;
  return name;
}
function countText(items) {
  const open = items.filter((i) => !i.completed && i.kind !== "event");
  const firm = open.filter((i) => !i.soft).length, soft = open.length - firm;
  if (!open.length) return items.length ? "all done" : "";
  return `${firm} to do` + (soft ? ` · ${soft} optional` : "");
}

function renderMonth() {
  const root = dv.container.createDiv({ cls: "mtc mtc-month" });
  const S = state(`month:${herePath}:${opt.month || ""}`);
  let base = opt.month ? DateTime.fromISO(`${String(opt.month).trim()}-01`) : DateTime.local().startOf("month");
  if (!base.isValid) base = DateTime.local().startOf("month");
  S.base = base;
  const F = loadFilters();
  // keep the Canvas sync line fresh: when a run saves its state, and every 20 seconds while a run is going
  let syncLoad = null;
  const syncTick = (f) => { if ((!f || f.path === SYNC_STATE) && syncLoad) syncLoad(); };
  if (dv.component && dv.component.registerEvent) {
    dv.component.registerEvent(app.vault.on("modify", syncTick));
    dv.component.registerEvent(app.vault.on("create", syncTick));
    dv.component.registerInterval(window.setInterval(() => { if (Date.now() - syncAsked() < SYNC_WAIT) syncTick(null); }, 20000));
  }

  const draw = () => {
    root.empty();
    const month = base.plus({ months: S.offset });
    const first = month.startOf("month"), last = month.endOf("month");
    const firstISO = first.toISODate(), lastISO = last.toISODate();
    const days = span(first.startOf("week").toISODate(), last.endOf("week").toISODate());
    const today = todayISO();
    if (!S.selected || S.selected < days[0] || S.selected > days[days.length - 1]) S.selected = today >= firstISO && today <= lastISO ? today : firstISO;
    const data = getData();
    const grid = byDay(data, days, F);

    // header
    const head = root.createDiv({ cls: "mtc-head" });
    const title = head.createDiv({ cls: "mtc-title" });
    title.createSpan({ cls: "mtc-month-name", text: month.toFormat("LLLL yyyy") });
    const inMonth = data.items.filter((i) => i.date >= firstISO && i.date <= lastISO && !i.completed && !i.soft);
    const count = (k) => inMonth.filter((i) => i.kind === k).length;
    const exams = data.events.exams.filter((e) => e.date >= firstISO && e.date <= lastISO).length;
    const sum = [];
    if (count("assignment")) sum.push(`${count("assignment")} assignments`);
    if (exams + count("exam")) sum.push(`${exams + count("exam")} exam${exams + count("exam") === 1 ? "" : "s"}`);
    if (count("prep")) sum.push(`${count("prep")} prep`);
    if (count("todo")) sum.push(`${count("todo")} to-dos`);
    title.createSpan({ cls: "mtc-summary", text: sum.length ? `Open this month: ${sum.join(" · ")}` : "Nothing open this month" });
    const nav = head.createDiv({ cls: "mtc-nav" });
    button(nav, "‹", "Previous month", () => { S.offset--; S.selected = null; draw(); });
    button(nav, "Today", "Jump to today", () => { S.offset = Math.round(DateTime.local().startOf("month").diff(base, "months").months); S.selected = today; draw(); });
    button(nav, "›", "Next month", () => { S.offset++; S.selected = null; draw(); });
    button(nav, S.form ? "Close form" : "+ Add to-do", "Add a dated to-do", () => {
      S.form = S.form ? null : { date: S.selected || today, kind: "todo" };
      draw();
    }, "mod-cta");
    const wk = nav.createSpan({ cls: "mtc-weeklink", text: "Week view →" });
    wk.addEventListener("click", (ev) => open(WEEK_NOTE, ev));
    syncLoad = renderSyncBar(root);
    if (S.flash) { root.createDiv({ cls: "mtc-flash", text: S.flash }); S.flash = ""; }
    if (S.form) renderForm(root, S, data, draw);

    // filters
    const fb = root.createDiv({ cls: "mtc-filters" });
    for (const [key, label] of FILTERS) {
      const b = fb.createEl("button", { cls: "mtc-filter" + (F[key] ? " is-on" : ""), text: label });
      b.setAttr("aria-pressed", F[key] ? "true" : "false");
      b.addEventListener("click", (ev) => { ev.preventDefault(); F[key] = !F[key]; saveFilters(F); draw(); });
    }

    // legend: colors on screen this month
    const seen = new Map();
    for (const d of days) for (const it of grid[d].items) {
      const key = it.course || (it.color === PROJECT ? "Projects" : it.kind === "exam" ? "Exams" : "Personal");
      if (!seen.has(key)) seen.set(key, it.color);
    }
    if (seen.size) {
      const lg = root.createDiv({ cls: "mtc-legend" });
      for (const [label, color] of [...seen].sort((a, b) => a[0].localeCompare(b[0]))) { const s = lg.createSpan({ text: label }); s.style.setProperty("--ev", color); }
    }

    // grid
    const scroll = root.createDiv({ cls: "mtc-scroll" });
    const g = scroll.createDiv({ cls: "mtc-grid" });
    for (const name of ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]) g.createDiv({ cls: "mtc-dow", text: name });
    for (const d of days) {
      const x = dt(d);
      const cellData = grid[d];
      const cls = ["mtc-cell"];
      if (d < firstISO || d > lastISO) cls.push("is-out");
      if (d === today) cls.push("is-today");
      if (d < today) cls.push("is-past");
      if (d === S.selected) cls.push("is-selected");
      if (x.weekday >= 6) cls.push("is-weekend");
      if (cellData.marks.length) cls.push("has-mark");
      const cell = g.createDiv({ cls: cls.join(" ") });
      cell.setAttr("role", "button");
      cell.setAttr("aria-label", `${x.toFormat("cccc, LLLL d")}: ${countText(cellData.items) || "nothing due"}`);
      const top = cell.createDiv({ cls: "mtc-cell-top" });
      top.createSpan({ cls: "mtc-dom", text: x.day === 1 ? x.toFormat("LLL d") : String(x.day) });
      const openCount = cellData.items.filter((i) => !i.completed && !i.soft && i.kind !== "event").length;
      if (openCount) top.createSpan({ cls: "mtc-count" + (openCount >= 3 ? " is-busy" : ""), text: String(openCount) });
      for (const m of cellData.marks.slice(0, 1)) cell.createDiv({ cls: "mtc-mark", text: m.title });
      const pick = () => { S.selected = d; draw(); };
      for (const it of cellData.items.slice(0, MAX_CHIPS)) chip(cell, it, pick);
      if (cellData.items.length > MAX_CHIPS) cell.createDiv({ cls: "mtc-more", text: `+${cellData.items.length - MAX_CHIPS} more` });
      cell.addEventListener("click", pick);
    }

    // panels: selected day, next 7 days, past due, no date
    const panels = root.createDiv({ cls: "mtc-panels" });
    const sel = panels.createDiv({ cls: "mtc-panel mtc-day-panel" });
    const selItems = (grid[S.selected] || byDay(data, [S.selected], F)[S.selected]).items;
    const sh = sel.createDiv({ cls: "mtc-panel-head" });
    sh.createSpan({ cls: "mtc-panel-title", text: headLabel(S.selected, today) });
    const ct = countText(selItems);
    if (ct) sh.createSpan({ cls: "mtc-panel-count", text: ct });
    const marks = (grid[S.selected] || { marks: [] }).marks;
    if (marks.length) sel.createDiv({ cls: "mtc-panel-mark", text: marks.map((m) => m.title).join(" · ") });
    if (selItems.length) dayList(sel, selItems, draw);
    else sel.createDiv({ cls: "mtc-empty", text: "Nothing due this day." });
    quickAdd(sel, S.selected, S, draw);

    const up = panels.createDiv({ cls: "mtc-panel mtc-upcoming" });
    up.createDiv({ cls: "mtc-panel-head" }).createSpan({ cls: "mtc-panel-title", text: "Day by day: the next 7 days" });
    const next = span(today, dt(today).plus({ days: 6 }).toISODate());
    const nextGrid = byDay(data, next, F);
    for (const d of next) {
      const box = up.createDiv({ cls: "mtc-aday" + (d === today ? " is-today" : "") });
      const h = box.createDiv({ cls: "mtc-aday-head" });
      const hl = h.createSpan({ cls: "mtc-aday-name", text: headLabel(d, today) });
      hl.addEventListener("click", () => { S.selected = d; S.offset = Math.round(dt(d).startOf("month").diff(base, "months").months); draw(); });
      const c2 = countText(nextGrid[d].items);
      if (c2) h.createSpan({ cls: "mtc-panel-count", text: c2 });
      if (nextGrid[d].marks.length) box.createDiv({ cls: "mtc-panel-mark", text: nextGrid[d].marks.map((m) => m.title).join(" · ") });
      if (nextGrid[d].items.length) dayList(box, nextGrid[d].items, draw);
      else box.createDiv({ cls: "mtc-empty", text: "Nothing due." });
    }

    const cutoff = dt(today).minus({ days: PAST_DUE_DAYS }).toISODate();
    const late = data.items.filter((i) => !i.completed && !i.soft && i.date < today && i.date >= cutoff && i.active && i.kind !== "exam")
      .sort((a, b) => b.date.localeCompare(a.date) || sortItems(a, b));
    if (late.length) {
      const det = panels.createEl("details", { cls: "mtc-panel mtc-late" });
      if (S.open.late) det.setAttr("open", "");
      det.addEventListener("toggle", () => { S.open.late = det.open; });
      det.createEl("summary", { text: `Past due and not checked off (${late.length})` });
      det.createDiv({ cls: "mtc-hint", text: `From the last ${PAST_DUE_DAYS} days. Some may already be done: check them off, or open the note to update the date.` });
      dayList(det, late, draw, { showDate: true });
    }
    if (data.undated.length) {
      const det = panels.createEl("details", { cls: "mtc-panel mtc-undated" });
      if (S.open.undated) det.setAttr("open", "");
      det.addEventListener("toggle", () => { S.open.undated = det.open; });
      det.createEl("summary", { text: `No date yet (${data.undated.length})` });
      dayList(det, data.undated.map((i) => Object.assign(i, { date: today, time: null })).sort((a, b) => (a.course || "~").localeCompare(b.course || "~") || a.label.localeCompare(b.label)), draw);
    }
    root.createDiv({ cls: "mtc-hint", text: "Click a day to see its list. Check items off here or in their notes. Cmd/Ctrl-click an item to open its note. Classes and meetings stay on the Week view." });
  };
  draw();
}

function renderDay() {
  const root = dv.container.createDiv({ cls: "mtc mtc-dayview" });
  const d = iso(opt.date) || iso(here && here.date) || iso(here && here.file && here.file.day) || todayISO();
  const F = loadFilters();
  const draw = () => {
    root.empty();
    const data = getData();
    const items = byDay(data, [d], F)[d].items;
    const head = root.createDiv({ cls: "mtc-panel-head" });
    head.createSpan({ cls: "mtc-panel-title", text: `To do · ${dt(d).toFormat("cccc, LLL d")}` });
    const link = head.createSpan({ cls: "mtc-weeklink", text: "Month view →" });
    link.addEventListener("click", (ev) => open("00 Home/Monthly Calendar.md", ev));
    if (items.length) dayList(root, items, draw);
    else root.createDiv({ cls: "mtc-empty", text: "Nothing due." });
  };
  draw();
}

function renderUpcoming() {
  const root = dv.container.createDiv({ cls: "mtc mtc-dayview" });
  const n = Math.max(1, Math.min(31, Number(opt.days) || 7));
  const F = loadFilters();
  const draw = () => {
    root.empty();
    const today = todayISO();
    const days = span(today, dt(today).plus({ days: n - 1 }).toISODate());
    const data = getData();
    const grid = byDay(data, days, F);
    for (const d of days) {
      if (!grid[d].items.length) continue;
      const box = root.createDiv({ cls: "mtc-aday" + (d === today ? " is-today" : "") });
      box.createDiv({ cls: "mtc-aday-head" }).createSpan({ cls: "mtc-aday-name", text: headLabel(d, today) });
      dayList(box, grid[d].items, draw);
    }
    if (!root.children.length) root.createDiv({ cls: "mtc-empty", text: `Nothing due in the next ${n} days.` });
  };
  draw();
}

try {
  const mode = String(opt.mode).toLowerCase();
  if (mode === "day") renderDay();
  else if (mode === "upcoming") renderUpcoming();
  else renderMonth();
} catch (err) {
  dv.container.createEl("pre", { text: `Monthly calendar error: ${err && err.stack ? err.stack : err}` });
}
