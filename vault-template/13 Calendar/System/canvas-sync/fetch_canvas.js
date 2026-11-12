async (courseIds, sinceDays) => {
  // Canvas reader for the Canvas sync (see "00 Home/Agent/Skills/Skill - Canvas Sync.md"). Version 2.
  // Run in a logged-in Canvas tab, once per Canvas host, as:  (<this file>)([course ids], 21)
  // Read-only: it only sends GET requests to the Canvas API of the page it runs on.
  // v2 also reads files with their folders, files linked from the syllabus, announcements, modules and pages,
  // module items (readings posted as links) and the last few wiki pages, so new lecture notes and readings
  // can be imported into the vault.
  const res = { version: 2, host: location.host, fetched_at: new Date().toISOString(), logged_in: false, courses: {} };
  const headers = { Accept: "application/json" };
  const parse = async (r) => JSON.parse((await r.text()).replace(/^while\(1\);/, ""));
  const getOne = async (path) => {
    const r = await fetch(path, { credentials: "same-origin", headers }).catch(() => null);
    if (!r) return { error: "network" };
    if (r.status !== 200) return { error: r.status };
    return { data: await parse(r) };
  };
  const get = async (path) => {
    const items = [];
    let url = path;
    for (let page = 0; url && page < 10; page++) {
      const r = await fetch(url, { credentials: "same-origin", headers }).catch(() => null);
      if (!r) return { error: "network", items };
      if (r.status !== 200) return { error: r.status, items };
      const data = await parse(r);
      if (!Array.isArray(data)) return { error: "unexpected response", items };
      items.push(...data);
      const next = (r.headers.get("Link") || "").match(/<([^>]+)>;\s*rel="next"/);
      url = next ? next[1] : null;
    }
    return { items };
  };
  const text = (html) => {
    const d = document.createElement("div");
    d.innerHTML = html || "";
    d.querySelectorAll("a[href]").forEach((a) => { a.textContent = `${a.textContent} <${a.href}>`; });
    d.querySelectorAll("p, br, li, tr, h1, h2, h3, h4").forEach((el) => el.append("\n"));
    return d.textContent.replace(/[ \t]+/g, " ").replace(/\n\s*\n+/g, "\n").trim();
  };
  const links = (html) => {
    const d = document.createElement("div");
    d.innerHTML = html || "";
    return [...d.querySelectorAll("a[href]")].map((a) => {
      const m = a.href.match(/\/files\/(\d+)/);
      return { text: a.textContent.replace(/\s+/g, " ").trim().slice(0, 200), href: a.href, file_id: m ? Number(m[1]) : null };
    }).filter((l) => /^https?:/.test(l.href));
  };
  const me = await fetch("/api/v1/users/self", { credentials: "same-origin", headers }).catch(() => null);
  res.logged_in = !!me && me.status === 200;
  if (!res.logged_in) return res;
  const since = new Date(Date.now() - (sinceDays || 21) * 86400000).toISOString();
  const until = new Date(Date.now() + 2 * 86400000).toISOString();
  const today = new Date().toISOString().slice(0, 10);
  const later = new Date(Date.now() + 150 * 86400000).toISOString().slice(0, 10);
  const fileInfo = (x, folders, via) => ({
    id: x.id, name: x.display_name, updated_at: x.updated_at, created_at: x.created_at, modified_at: x.modified_at,
    size: x.size, content_type: x["content-type"] || "", folder: folders[x.folder_id] || "", locked: !!x.locked_for_user,
    hidden: !!x.hidden, via,
  });
  for (const id of courseIds) {
    const c = { id, errors: {} };
    const info = await getOne(`/api/v1/courses/${id}?include[]=syllabus_body`);
    if (info.error) c.errors.course = info.error;
    else { c.name = info.data.name; c.syllabus_links = links(info.data.syllabus_body); }

    const a = await get(`/api/v1/courses/${id}/assignments?per_page=100&include[]=submission&order_by=due_at`);
    if (a.error) c.errors.assignments = a.error;
    c.assignments = a.items.map((x) => ({
      id: x.id, name: (x.name || "").replace(/\s+/g, " ").trim(), due_at: x.due_at, lock_at: x.lock_at, unlock_at: x.unlock_at,
      points: x.points_possible, types: x.submission_types || [], published: x.published !== false, url: x.html_url,
      submission: x.submission ? { state: x.submission.workflow_state, submitted_at: x.submission.submitted_at, score: x.submission.score,
        excused: !!x.submission.excused, missing: !!x.submission.missing, late: !!x.submission.late } : null,
    }));

    const an = await get(`/api/v1/announcements?context_codes[]=course_${id}&start_date=${since}&end_date=${until}&per_page=50`);
    if (an.error) c.errors.announcements = an.error;
    c.announcements = an.items.map((x) => ({
      id: x.id, title: x.title, posted_at: x.posted_at, url: x.html_url, text: text(x.message).slice(0, 6000), links: links(x.message),
      attachments: (x.attachments || []).map((f) => ({ id: f.id, name: f.display_name, size: f.size, updated_at: f.updated_at, content_type: f["content-type"] || "" })),
    }));

    const fo = await get(`/api/v1/courses/${id}/folders?per_page=100`);
    const folders = {};
    for (const f of fo.items || []) folders[f.id] = (f.full_name || "").replace(/^course files\/?/, "");
    const f = await get(`/api/v1/courses/${id}/files?per_page=100&sort=updated_at&order=desc`);
    if (f.error) c.errors.files = f.error;
    c.files = f.items.slice(0, 150).map((x) => fileInfo(x, folders, "files"));

    const mo = await get(`/api/v1/courses/${id}/modules?include[]=items&per_page=50`);
    if (mo.error && mo.error !== 404) c.errors.modules = mo.error;
    c.modules = (mo.items || []).map((m) => ({
      id: m.id, name: m.name, position: m.position, unlock_at: m.unlock_at,
      items: (m.items || []).map((i) => ({ id: i.id, title: i.title, type: i.type, content_id: i.content_id || null,
        url: i.external_url || i.html_url || "", page_url: i.page_url || null })),
    }));

    const pg = await get(`/api/v1/courses/${id}/pages?per_page=20&sort=updated_at&order=desc`);
    c.pages = [];
    if (!pg.error) {
      for (const p of (pg.items || []).slice(0, 10)) {
        const full = await getOne(`/api/v1/courses/${id}/pages/${encodeURIComponent(p.url)}`);
        c.pages.push({ url: p.url, title: p.title, updated_at: p.updated_at, html_url: p.html_url,
          text: full.data ? text(full.data.body).slice(0, 3000) : "", links: full.data ? links(full.data.body) : [] });
      }
    }

    // files linked from the syllabus, announcements, module items and pages that the Files list doesn't show
    const known = new Set(c.files.map((x) => String(x.id)));
    const linked = [];
    for (const l of c.syllabus_links || []) if (l.file_id) linked.push([l.file_id, "syllabus"]);
    for (const x of c.announcements) {
      for (const l of x.links) if (l.file_id) linked.push([l.file_id, `announcement ${x.id}`]);
      for (const t of x.attachments) linked.push([t.id, `announcement ${x.id}`]);
    }
    for (const m of c.modules) for (const i of m.items) if (i.type === "File" && i.content_id) linked.push([i.content_id, `module ${m.name}`]);
    for (const p of c.pages) for (const l of p.links) if (l.file_id) linked.push([l.file_id, `page ${p.title}`]);
    for (const [fid, via] of linked) {
      if (known.has(String(fid))) continue;
      known.add(String(fid));
      const one = await getOne(`/api/v1/courses/${id}/files/${fid}`);
      if (one.data) c.files.push(fileInfo(one.data, folders, via));
    }

    const ev = await get(`/api/v1/calendar_events?context_codes[]=course_${id}&type=event&start_date=${today}&end_date=${later}&per_page=100`);
    if (ev.error) c.errors.events = ev.error;
    c.events = ev.items.map((x) => ({ id: x.id, title: x.title, start_at: x.start_at, end_at: x.end_at, location: x.location_name || "", text: text(x.description).slice(0, 600) }));
    res.courses[id] = c;
  }
  return res;
}
