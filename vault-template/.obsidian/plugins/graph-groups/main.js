'use strict';
/*
 * Graph Groups v4 (live): private plugin for this vault.
 *
 * The graph keeps Obsidian's own live physics (nodes float and settle, you can drag them), but the
 * physics is told which group every note belongs to, so groups come out clean:
 *   - Home sits in the middle; every group branches out from it.
 *   - Each class is its own starburst: its Materials note in the middle, all its files and notes
 *     around it, plus its course map, class note, prep note and exam notes (current classes).
 *   - Current classes branch from School MOC; past classes and the school admin folders branch
 *     from School Library.
 *   - Life groups: AI Chats around AI Chats MOC, calendar and daily notes around Calendar MOC,
 *     projects around Top of Mind, agent notes around AI Agent MOC, fleeting / literature /
 *     permanent notes as three small starbursts around Note-taking MOC, archive notes together,
 *     home dashboards and area maps around Home.
 * How: Obsidian draws every link, but the physics engine only receives the links inside each
 * group plus one link from each note to its group's hub (and from each hub to the next level).
 * Links between groups are still drawn; they just no longer drag groups into each other.
 * When the graph opens, nodes start in a radial arrangement (School to the right, life groups
 * around Home), then the physics takes over. File dots get their group's color, as before.
 * Disable the plugin and the graph returns to Obsidian's normal behaviour.
 */
let obsidian;
try { obsidian = require('obsidian'); } catch (e) {
  class Stub { constructor(app, plugin) { this.app = app; this.plugin = plugin; } }
  obsidian = { Plugin: Stub, Notice: class { constructor() {} }, PluginSettingTab: Stub, Setting: Stub };
}
const { Plugin, Notice, PluginSettingTab, Setting } = obsidian;
const TAU = Math.PI * 2;

const DEFAULT_GROUPS = {
  center: '00 Home/Home.md',
  currentHub: '^12 School/(?!Past Courses/)(?!_)([^/]+)/([^/]+)/[^/]+ Materials\\.md$',
  pastHub: '^12 School/Past Courses/([^/]+)/[^/]+ Materials\\.md$',
  refHub: '^12 School/(_[^/]+)/[^/]+ Materials\\.md$',
  flower: true,                                  // every group branches straight from Home
  currentParent: '04 Maps/School MOC.md',        // (flower off) current classes branch from here
  pastParent: '12 School/School Library.md',     // (flower off) past classes + admin folders branch from here
  satellites: ['04 Maps/{code} MOC.md'],
  currentSatellites: ['13 Calendar/Classes/{code} Class.md', '13 Calendar/Prep/{code} Prep.md',
    're:^13 Calendar/Events/[^/]* - {code}[^/]*\\.md$'],
  // life groups, claimed in this order. hub: a note path, 'center' (Home) or 'auto' (the
  // best-linked member). split: one small starburst per captured value (auto hub each).
  branches: [
    { name: 'AI Chats', hub: '04 Maps/AI Chats MOC.md', match: '^11 AI Chats/' },
    { name: 'Calendar', hub: '04 Maps/Calendar MOC.md', match: '^(13 Calendar/|0[67] (Daily|Weekly)/)' },
    { name: 'Projects', hub: '00 Home/Top of Mind.md', match: '^05 Projects/' },
    { name: 'Agent', hub: '04 Maps/AI Agent MOC.md', match: '^00 Home/Agent/' },
    { name: 'Knowledge', hub: '04 Maps/Note-taking MOC.md', match: '^0[123] ', split: '^(0[123]) ' },
    { name: 'Archive', hub: 'auto', match: '^08 Archive/' },
    { name: 'Home', hub: 'center', match: '^(00 Home/|04 Maps/|[^/]+$)' },
  ],
  // flower: order of groups around Home (clockwise from flowerStart degrees; 0 = right, 90 = down)
  flowerOrder: ['Calendar', 'AI Chats', 'Projects', 'Agent', 'Knowledge', 'Archive', 'Current classes', 'Past classes', 'School admin'],
  flowerStart: 200,
  // (flower off) where branches start around Home when the graph opens
  directions: { School: 0, Calendar: 300, 'AI Chats': 245, Projects: 190, Archive: 150, Knowledge: 115, Agent: 70 },
};

const DEFAULT_SETTINGS = {
  version: 4,
  colorFiles: true,      // file dots take their group's color
  groupPhysics: true,    // physics keeps every group together
  pinCenter: true,       // Home stays in the middle
  seedLayout: true,      // start every graph from the same radial arrangement
  bigCenter: true,       // draw Home as the biggest dot (display only)
  hide: ['^13 Calendar/System/'],
  centerXY: [0, 0],
  groups: DEFAULT_GROUPS,
};

function clone(x) { return JSON.parse(JSON.stringify(x)); }
function re(src) { try { return src ? new RegExp(src) : null; } catch (e) { console.warn('[graph-groups] bad pattern', src); return null; } }
const collator = new Intl.Collator('en', { numeric: true, sensitivity: 'base' });
const naturalCompare = (a, b) => collator.compare(a, b) || (a < b ? -1 : a > b ? 1 : 0);
const codeOf = folder => folder.split(' - ')[0].trim();
const escRe = x => x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

// ------------------------------------------------------------------------------------------
// Groups: who belongs where, and the links the physics engine gets
// ------------------------------------------------------------------------------------------
function buildGroups(idList, adj, settings) {
  const G = Object.assign({}, DEFAULT_GROUPS, (settings && settings.groups) || {});
  const ids = [...idList].sort(naturalCompare);
  const present = new Set(ids);
  const parent = new Map(), group = new Map(), role = new Map(), branch = new Map();
  const deg = id => (adj[id] ? adj[id].size : 0);
  const byDeg = list => list.slice().sort((a, b) => deg(b) - deg(a) || naturalCompare(a, b));
  let center = present.has(G.center) ? G.center : (ids.length ? byDeg(ids)[0] : null);
  if (!center) return { center: null, parent, group, role, branch, links: [] };
  group.set(center, 'Home'); role.set(center, 'center'); branch.set(center, 'Home');
  const owned = id => group.has(id);
  const setNode = (id, grp, par, rl, br) => {
    if (!present.has(id) || owned(id) || id === par) return false;
    group.set(id, grp); parent.set(id, par); role.set(id, rl); branch.set(id, br);
    return true;
  };

  // 1. school
  let schoolHub = present.has(G.currentParent) ? G.currentParent : center;
  let libHub = present.has(G.pastParent) ? G.pastParent : schoolHub;
  if (G.flower) {
    // School MOC and School Library sit right next to Home; every class branches from Home itself
    for (const h of [schoolHub, libHub]) if (h !== center) setNode(h, 'Home', center, 'member', 'Home');
    schoolHub = libHub = center;
  } else {
    if (schoolHub !== center) setNode(schoolHub, 'School', center, 'hub', 'School');
    if (libHub !== schoolHub) setNode(libHub, 'School', schoolHub, 'hub', 'School');
  }
  const curRe = re(G.currentHub), pastRe = re(G.pastHub), refRe = re(G.refHub);
  const courses = [];
  for (const id of ids) {
    let m, kind = null, folder = null;
    if (curRe && (m = curRe.exec(id))) { kind = 'current'; folder = m[2]; }
    else if (pastRe && (m = pastRe.exec(id))) { kind = 'past'; folder = m[1]; }
    else if (refRe && (m = refRe.exec(id))) { kind = 'ref'; folder = m[1]; }
    if (!kind) continue;
    courses.push({ hub: id, kind, folder, folderPath: id.slice(0, id.lastIndexOf('/')), code: codeOf(folder) });
  }
  // a stub folder that shares its code with a bigger class of the same kind joins that class
  const countUnder = c => ids.filter(id => id.startsWith(c.folderPath + '/')).length;
  const byCode = new Map();
  for (const c of courses) if (c.kind !== 'ref') {
    const k = c.kind + '|' + c.code;
    if (!byCode.has(k)) byCode.set(k, []);
    byCode.get(k).push(c);
  }
  for (const list of byCode.values()) {
    if (list.length < 2) continue;
    list.sort((a, b) => countUnder(b) - countUnder(a) || naturalCompare(a.folder, b.folder));
    for (const stub of list.slice(1)) stub.mergedInto = list[0];
  }
  const keyOf = c => 'class:' + (c.mergedInto || c).folderPath;
  for (const c of courses) if (!c.mergedInto) setNode(c.hub, keyOf(c), c.kind === 'current' ? schoolHub : libHub, 'hub', c.kind === 'current' ? 'Current classes' : c.kind === 'past' ? 'Past classes' : 'School admin');
  for (const c of courses) if (c.mergedInto) setNode(c.hub, keyOf(c), c.mergedInto.hub, 'member', 'School');
  const deepest = courses.slice().sort((a, b) => b.folderPath.length - a.folderPath.length);
  for (const id of ids) {
    if (owned(id)) continue;
    const c = deepest.find(c => id.startsWith(c.folderPath + '/'));
    if (c) setNode(id, keyOf(c), (c.mergedInto || c).hub, 'member', 'School');
  }
  for (const c of courses) {
    if (c.mergedInto || c.kind === 'ref') continue;
    const pats = (G.satellites || []).concat(c.kind === 'current' ? (G.currentSatellites || []) : []);
    for (const pat of pats) {
      if (pat.startsWith('re:')) {
        const rx = re(pat.slice(3).split('{code}').join(escRe(c.code) + '(?![-\\w])'));
        if (rx) for (const id of ids) if (rx.test(id)) setNode(id, keyOf(c), c.hub, 'member', 'School');
      } else setNode(pat.split('{code}').join(c.code), keyOf(c), c.hub, 'member', 'School');
    }
  }
  for (const id of ids) if (!owned(id) && id.startsWith('12 School/')) setNode(id, 'School', libHub, 'member', 'School');

  // 2. life groups
  for (const b of G.branches || []) {
    const rx = re(b.match);
    if (!rx) continue;
    let hub = b.hub === 'center' ? center : b.hub;
    const members = ids.filter(id => !owned(id) && id !== hub && rx.test(id));
    if (hub !== center && hub !== 'auto' && !present.has(hub)) hub = 'auto';
    if (hub === 'auto') { hub = byDeg(members)[0]; if (!hub) continue; }
    if (hub !== center) setNode(hub, b.name, b.parent && present.has(b.parent) ? b.parent : center, 'hub', b.name);
    const grp = hub === center ? 'Home' : group.get(hub);
    if (b.split) {
      const sx = re(b.split), buckets = new Map();
      for (const id of members) {
        if (id === hub || owned(id)) continue;
        const m = sx && sx.exec(id), k = m ? m[1] : '';
        if (!buckets.has(k)) buckets.set(k, []);
        buckets.get(k).push(id);
      }
      for (const k of [...buckets.keys()].sort(naturalCompare)) {
        const list = buckets.get(k), sub = byDeg(list)[0], key = b.name + ':' + k;
        setNode(sub, key, hub, 'hub', b.name);
        for (const id of list) setNode(id, key, sub, 'member', b.name);
      }
    } else for (const id of members) setNode(id, grp, hub, 'member', b.name);
  }

  // 3. anything else (attachments of notes, tags if shown): joins the note it is linked with
  for (let pass = 0; pass < 6; pass++) {
    let changed = false;
    for (const id of ids) {
      if (owned(id)) continue;
      const nb = [...(adj[id] || [])].filter(owned).sort((a, b) =>
        (role.get(a) === 'member' ? 0 : 1) - (role.get(b) === 'member' ? 0 : 1) || deg(b) - deg(a) || naturalCompare(a, b));
      if (nb.length && setNode(id, group.get(nb[0]), nb[0], 'member', branch.get(nb[0]))) changed = true;
    }
    if (!changed) break;
  }
  for (const id of ids) setNode(id, 'Other', center, 'member', 'Home');

  // physics links: each node to its hub, plus links inside the same group
  const links = [], seen = new Set();
  const add = (a, b) => {
    if (a === b) return;
    const k = a < b ? a + '\u0000' + b : b + '\u0000' + a;
    if (seen.has(k)) return;
    seen.add(k); links.push([a, b]);
  };
  for (const id of ids) if (parent.has(id)) add(id, parent.get(id));
  for (const id of ids) for (const t of adj[id] || []) if (present.has(t) && group.get(id) === group.get(t)) add(id, t);
  return { center, parent, group, role, branch, links };
}

// ------------------------------------------------------------------------------------------
// Starting arrangement (radial): every hub's own notes on a ring around it, sub-hubs further out
// ------------------------------------------------------------------------------------------
function seedPositions(model, settings, linkDistance) {
  const pos = new Map();
  const { center, parent } = model;
  if (!center) return pos;
  const G = Object.assign({}, DEFAULT_GROUPS, (settings && settings.groups) || {});
  const v = Math.max(60, linkDistance || 250);
  const kids = new Map();
  for (const [id, p] of parent) { if (!kids.has(p)) kids.set(p, []); kids.get(p).push(id); }
  for (const list of kids.values()) list.sort(naturalCompare);
  const isHub = id => kids.has(id);
  const leavesOf = id => (kids.get(id) || []).filter(k => !isHub(k));
  const hubsOf = id => (kids.get(id) || []).filter(isHub);
  const ringR = id => Math.max(v * 0.8, leavesOf(id).length * 46 / TAU);
  const reachMemo = new Map();
  const reach = id => {   // radius of a hub's whole subtree
    if (reachMemo.has(id)) return reachMemo.get(id);
    let r = ringR(id);
    const hs = hubsOf(id);
    if (hs.length) {
      const sum = hs.reduce((s, h) => s + 2 * reach(h), 0);
      r = Math.max(r + v + Math.max(...hs.map(reach)) * 2, sum / Math.PI);
    }
    reachMemo.set(id, r);
    return r;
  };
  const sizeMemo = new Map();
  const size = id => { if (sizeMemo.has(id)) return sizeMemo.get(id); let s = 1; for (const k of kids.get(id) || []) s += size(k); sizeMemo.set(id, s); return s; };
  const c0 = (settings && settings.centerXY) || [0, 0];

  const place = (id, x, y, dir, fan) => {
    pos.set(id, [x, y]);
    const leaves = leavesOf(id), hubs = hubsOf(id);
    const R = ringR(id);
    // own notes: a full ring (the center) or a ring that opens toward the parent
    leaves.forEach((k, i) => {
      const t = dir == null ? (i + 0.5) * TAU / leaves.length : dir + Math.PI + (i + 1) * TAU / (leaves.length + 1);
      pos.set(k, [x + R * Math.cos(t), y + R * Math.sin(t)]);
    });
    if (!hubs.length) return;
    // sub-hubs: spread over the fan, the biggest in the middle
    const order = hubs.slice().sort((a, b) => naturalCompare(a, b));
    const big = order.reduce((m, h) => (size(h) > size(m) ? h : m), order[0]);
    const rest = order.filter(h => h !== big);
    const arranged = rest.slice(0, Math.floor(rest.length / 2)).concat([big], rest.slice(Math.floor(rest.length / 2)));
    const w = arranged.map(h => Math.sqrt(size(h)) + 1), W = w.reduce((s, a) => s + a, 0);
    let a = dir - fan / 2;
    arranged.forEach((h, i) => {
      const t = a + fan * w[i] / W / 2;
      a += fan * w[i] / W;
      const d = R + v + reach(h);
      place(h, x + d * Math.cos(t), y + d * Math.sin(t), t, Math.min(TAU * 0.75, Math.max(Math.PI / 3, hubsOf(h).length * 0.35)));
    });
  };

  // the center: its own notes on a ring, branches in their configured directions
  pos.set(center, c0.slice());
  const leaves = leavesOf(center), hubs = hubsOf(center);
  const R0 = ringR(center);
  leaves.forEach((k, i) => { const t = (i + 0.5) * TAU / leaves.length; pos.set(k, [c0[0] + R0 * Math.cos(t), c0[1] + R0 * Math.sin(t)]); });
  if (G.flower) {
    // one ring of groups around Home, in this order: life groups, current classes, past classes, admin
    const order = G.flowerOrder || [];
    const rank = h => { const b = model.branch.get(h); const i = order.indexOf(b); return i < 0 ? order.length : i; };
    const ring = hubs.slice().sort((a, b) => rank(a) - rank(b) || naturalCompare(a, b));
    const w = ring.map(h => 2 * reach(h) + v * 0.5), W = w.reduce((s, a) => s + a, 0);
    const Rr = Math.max(R0 + v + Math.max(...ring.map(reach)), W / TAU);
    let a = (G.flowerStart || 200) * Math.PI / 180;
    ring.forEach((h, i) => {
      const t = a + Math.PI * w[i] / W;
      a += TAU * w[i] / W;
      place(h, c0[0] + Rr * Math.cos(t), c0[1] + Rr * Math.sin(t), t, Math.PI / 2);
    });
    return pos;
  }
  const dirs = G.directions || {};
  const known = hubs.filter(h => dirs[model.branch.get(h)] != null);
  const unknown = hubs.filter(h => dirs[model.branch.get(h)] == null);
  const used = known.map(h => dirs[model.branch.get(h)]);
  unknown.forEach((h, i) => used.push((i + 0.5) * 360 / Math.max(1, unknown.length)));
  known.concat(unknown).forEach((h, i) => {
    const t = used[i] * Math.PI / 180;
    const d = R0 + v + reach(h);
    const fan = model.branch.get(h) === 'School' ? Math.PI * 0.9 : Math.PI / 2;
    place(h, c0[0] + d * Math.cos(t), c0[1] + d * Math.sin(t), t, fan);
  });
  return pos;
}

// ------------------------------------------------------------------------------------------
// Plugin
// ------------------------------------------------------------------------------------------
class GraphGroupsPlugin extends Plugin {
  async onload() {
    this.settings = this.migrate((await this.loadData()) || {});
    this.compile();
    this.patch = null;
    this.app.workspace.onLayoutReady(() => this.attachAll(true));
    this.registerEvent(this.app.workspace.on('layout-change', () => this.attachAll(false)));
    this.addCommand({ id: 'rearrange', name: 'Rearrange the map (start again from the circle)', callback: () => this.rearrangeAll() });
    this.addCommand({ id: 'toggle-group-physics', name: 'Turn "keep groups together" on/off', callback: async () => {
      this.settings.groupPhysics = !this.settings.groupPhysics; await this.saveData(this.settings); this.rearrangeAll();
      new Notice('Graph Groups: keep groups together ' + (this.settings.groupPhysics ? 'on' : 'off')); } });
    this.addCommand({ id: 'toggle-file-colors', name: 'Turn group colors for file dots on/off', callback: async () => {
      this.settings.colorFiles = !this.settings.colorFiles; await this.saveData(this.settings); this.attachAll(true); } });
    this.addCommand({ id: 'center-home', name: 'Put Home back in the middle', callback: async () => {
      this.settings.centerXY = [0, 0]; await this.saveData(this.settings); this.rearrangeAll(); } });
    this.addSettingTab(new GraphGroupsSettingTab(this.app, this));
  }

  migrate(saved) {
    const s = Object.assign(clone(DEFAULT_SETTINGS), saved || {});
    if (!saved || !saved.version || saved.version < 4) {
      // v1-v3 pinned every node into a fixed layout; v4 uses live physics. Keep the file-color and
      // hide choices, drop the fixed-layout settings (backups of v3 stay in _Organizer).
      for (const k of ['anchors', 'assign', 'legacyAnchors', 'layout', 'pinLayout', 'keepDraggedHubs', 'regionLabels', 'slots', 'discs', 'courseMaps', 'hubDiscs', 'defaultAnchors']) delete s[k];
      s.groups = clone(DEFAULT_GROUPS);
      s.centerXY = [0, 0];
      s.version = 4;
      setTimeout(() => this.saveData(this.settings), 0);
    }
    if (!s.groups) s.groups = clone(DEFAULT_GROUPS);
    return s;
  }

  onunload() {
    if (this.patch) { this.patch.proto.setData = this.patch.orig; this.patch = null; }
    for (const view of this.graphViews()) {
      const r = view.renderer;
      try {
        if (r && r.worker) {
          const post = r.worker.__ggOrig || r.worker.postMessage.bind(r.worker);
          if (r.worker.__ggOrig) { delete r.worker.postMessage; delete r.worker.__ggOrig; }
          if (r.__ggModel && r.__ggModel.center && r.nodeLookup[r.__ggModel.center]) post({ forceNode: { id: r.__ggModel.center, x: null, y: null } });
          // give the physics all links back
          const links = (r.links || []).map(l => [l.source.id, l.target.id]);
          const nodes = {}; for (const n of r.nodes || []) nodes[n.id] = false;
          post({ nodes, links, alpha: 0.3, run: true });
        }
        if (r) { delete r.__ggModel; delete r.__ggSeeds; delete r.__gg4Pin; delete r.__gg4Seen; }
        if (view.dataEngine) view.dataEngine.render();
      } catch (e) { console.error('[graph-groups] unload', e); }
    }
  }

  compile() { this.hideRes = (this.settings.hide || []).map(re).filter(Boolean); }

  graphViews() {
    const ws = this.app.workspace;
    return [...ws.getLeavesOfType('graph'), ...ws.getLeavesOfType('localgraph')].map(l => l.view).filter(v => v && v.renderer && v.dataEngine);
  }
  isGlobal(view) { return view.getViewType && view.getViewType() === 'graph'; }

  attachAll(rerender) {
    const views = this.graphViews();
    if (!views.length) return;
    if (!this.patch) this.patchRenderer(Object.getPrototypeOf(views[0].renderer));
    for (const v of views) {
      const first = !v.renderer.__gg4Seen;
      if (rerender || first) {
        v.renderer.__gg4Seen = true;
        try { v.dataEngine.render(); } catch (e) { console.error('[graph-groups] render', e); }
        if (first && this.isGlobal(v)) setTimeout(() => this.rearrange(v), 50);
      }
    }
  }

  patchRenderer(proto) {
    const orig = proto && proto.setData;
    if (typeof orig !== 'function') { console.warn('[graph-groups] graph renderer not recognised; plugin idle'); return; }
    const plugin = this;
    proto.setData = function (data) {
      let view = null;
      try {
        view = plugin.graphViews().find(v => v.renderer === this) || null;
        if (view && data && data.nodes) plugin.prepareData(view, data);
        if (view && plugin.isGlobal(view)) plugin.wrapWorker(view);
      } catch (e) { console.error('[graph-groups] prepare', e); }
      const result = orig.apply(this, arguments);
      try { if (view && plugin.isGlobal(view)) plugin.pinCenter(view); } catch (e) { console.error('[graph-groups] pin', e); }
      return result;
    };
    this.patch = { proto, orig };
  }

  prepareData(view, data) {
    const nodes = data.nodes;
    if (this.hideRes.length) {
      const gone = new Set();
      for (const id in nodes) if (this.hideRes.some(r => r.test(id))) { gone.add(id); delete nodes[id]; }
      if (gone.size) for (const id in nodes) { const l = nodes[id].links; if (l) for (const g of gone) delete l[g]; }
    }
    if (this.isGlobal(view)) {
      const adj = {};
      for (const id in nodes) adj[id] = adj[id] || new Set();
      for (const id in nodes) for (const t in nodes[id].links || {}) { if (!nodes[t] || t === id) continue; adj[id].add(t); (adj[t] = adj[t] || new Set()).add(id); }
      if (this.settings.bigCenter && data.weights === undefined) {
        // the renderer sizes dots by link count unless it is given weights: keep every dot's
        // usual size and make Home (the center) the biggest
        const cid = (this.settings.groups && this.settings.groups.center) || DEFAULT_GROUPS.center;
        if (nodes[cid]) {
          const w = {}; let max = 0;
          for (const id in nodes) { w[id] = adj[id].size; if (w[id] > max) max = w[id]; }
          w[cid] = Math.max(max, 100);
          data.weights = w;
        }
      }
      try {
        const model = buildGroups(Object.keys(nodes), adj, this.settings);
        view.renderer.__ggModel = model;
        view.renderer.__ggSeeds = seedPositions(model, this.settings, this.linkDistance(view));
      } catch (e) { console.error('[graph-groups] groups', e); view.renderer.__ggModel = null; }
    }
    if (!this.settings.colorFiles) return;
    const groups = (view.dataEngine.searchQueries || []).filter(q => q && q.color && q.query && typeof q.query.matchFilename === 'function');
    if (!groups.length) return;
    for (const id in nodes) {
      const n = nodes[id];
      if (!n || n.type !== 'attachment' || n.color) continue;
      for (const q of groups) {
        let hit = false;
        try { hit = !!q.query.matchFilename(id); } catch (e) { hit = false; }
        if (hit) { n.color = q.color; break; }
      }
    }
  }

  linkDistance(view) {
    try { const o = view.dataEngine.getOptions(); return o.linkDistance || 250; } catch (e) { return 250; }
  }

  // intercept what the renderer sends to the physics engine
  wrapWorker(view) {
    const r = view.renderer, w = r.worker;
    if (!w || w.__ggOrig) return;
    const orig = w.postMessage.bind(w);
    w.__ggOrig = orig;
    const plugin = this;
    w.postMessage = function (msg) {
      try {
        const model = r.__ggModel, s = plugin.settings;
        if (msg && model && model.center) {
          if (msg.links && s.groupPhysics) msg = Object.assign({}, msg, { links: model.links });
          if (msg.nodes && s.seedLayout && r.__ggSeeds) {
            const ids = Object.keys(msg.nodes), fresh = ids.filter(id => msg.nodes[id]);
            if (fresh.length) {
              const nodes = Object.assign({}, msg.nodes);
              const whole = fresh.length > ids.length / 2;
              for (const id of fresh) {
                let p = null;
                if (whole) p = r.__ggSeeds.get(id);
                else {
                  // a note added later starts next to its hub
                  const par = model.parent.get(id), pn = par && r.nodeLookup[par];
                  if (pn && pn.x != null) { const t = Math.random() * TAU; p = [pn.x + 60 * Math.cos(t), pn.y + 60 * Math.sin(t)]; }
                }
                if (p) nodes[id] = [p[0], p[1]];
              }
              msg = Object.assign({}, msg, { nodes });
            }
          }
          const fn = msg.forceNode;
          if (fn && fn.id === model.center && fn.x === null && s.pinCenter) {
            // Home was dragged and let go: it stays where it was dropped
            const n = r.nodeLookup[fn.id];
            if (n && n.x != null) { s.centerXY = [Math.round(n.x), Math.round(n.y)]; plugin.queueSave(); }
            msg = Object.assign({}, msg, { forceNode: { id: fn.id, x: s.centerXY[0], y: s.centerXY[1] } });
          }
        }
      } catch (e) { console.error('[graph-groups] worker', e); }
      return orig.apply(null, arguments.length > 1 ? [msg].concat([].slice.call(arguments, 1)) : [msg]);
    };
  }

  pinCenter(view) {
    const r = view.renderer, model = r.__ggModel;
    if (!r.worker || !model || !model.center || !r.nodeLookup[model.center]) return;
    const post = r.worker.__ggOrig || r.worker.postMessage.bind(r.worker);
    const xy = this.settings.pinCenter ? this.settings.centerXY : [null, null];
    const pin = r.__gg4Pin;
    if (pin && pin.x === xy[0] && pin.y === xy[1] && pin.id === model.center && pin.worker === r.worker) return;
    post({ forceNode: { id: model.center, x: xy[0], y: xy[1] } });
    r.__gg4Pin = { x: xy[0], y: xy[1], id: model.center, worker: r.worker };
  }

  // send every node back to the radial starting arrangement and let the physics settle again
  rearrange(view) {
    const r = view.renderer;
    if (!r || !r.worker) return;
    this.wrapWorker(view);
    const post = r.worker.__ggOrig;
    const model = r.__ggModel;
    const nodes = {};
    for (const n of r.nodes) {
      const p = this.settings.seedLayout && r.__ggSeeds && r.__ggSeeds.get(n.id);
      nodes[n.id] = p ? [p[0], p[1]] : false;
    }
    const links = model && this.settings.groupPhysics ? model.links : r.links.map(l => [l.source.id, l.target.id]);
    r.__gg4Pin = null;
    this.pinCenter(view);
    post({ nodes, links, alpha: 1, run: true });
  }

  rearrangeAll() {
    for (const v of this.graphViews()) if (this.isGlobal(v)) {
      try { v.dataEngine.render(); this.rearrange(v); } catch (e) { console.error('[graph-groups] rearrange', e); }
    }
  }

  queueSave() { clearTimeout(this.saveTimer); this.saveTimer = setTimeout(() => this.saveData(this.settings), 800); }
}

class GraphGroupsSettingTab extends PluginSettingTab {
  constructor(app, plugin) { super(app, plugin); this.plugin = plugin; }
  display() {
    const { containerEl } = this, p = this.plugin;
    containerEl.empty();
    containerEl.createEl('p', { text: 'Keeps Obsidian\'s live graph, with Home in the middle and every group (each class, AI Chats, Calendar, Projects ...) gathered in its own starburst. All links are still drawn.' });
    new Setting(containerEl).setName('Keep groups together').setDesc('The physics only pulls notes toward their own group.')
      .addToggle(t => t.setValue(p.settings.groupPhysics).onChange(async v => { p.settings.groupPhysics = v; await p.saveData(p.settings); p.rearrangeAll(); }));
    new Setting(containerEl).setName('Home stays in the middle')
      .addToggle(t => t.setValue(p.settings.pinCenter).onChange(async v => { p.settings.pinCenter = v; await p.saveData(p.settings); p.rearrangeAll(); }));
    new Setting(containerEl).setName('Start from the same circle').setDesc('Each time the graph opens, nodes start in the same radial arrangement before the physics takes over.')
      .addToggle(t => t.setValue(p.settings.seedLayout).onChange(async v => { p.settings.seedLayout = v; await p.saveData(p.settings); }));
    new Setting(containerEl).setName('Make Home the biggest dot')
      .addToggle(t => t.setValue(p.settings.bigCenter).onChange(async v => { p.settings.bigCenter = v; await p.saveData(p.settings); p.attachAll(true); }));
    new Setting(containerEl).setName('Color file dots by group')
      .addToggle(t => t.setValue(p.settings.colorFiles).onChange(async v => { p.settings.colorFiles = v; await p.saveData(p.settings); p.attachAll(true); }));
    new Setting(containerEl).setName('Rearrange the map').setDesc('Start again from the circle.')
      .addButton(b => b.setButtonText('Rearrange').onClick(() => p.rearrangeAll()));
  }
}

GraphGroupsPlugin.buildGroups = buildGroups;
GraphGroupsPlugin.seedPositions = seedPositions;
GraphGroupsPlugin.DEFAULT_SETTINGS = DEFAULT_SETTINGS;
module.exports = GraphGroupsPlugin;
