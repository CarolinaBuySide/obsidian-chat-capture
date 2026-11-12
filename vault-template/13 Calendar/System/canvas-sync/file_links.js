async (fileIds) => {
  // Temporary download links for Canvas files, for the Canvas sync (see "00 Home/Agent/Skills/Skill - Canvas Sync.md").
  // Run in a logged-in tab on the Canvas host that owns the files, as:  (<this file>)([file ids from imports.json])
  // Read-only: GET requests only. Each link works without a login for a few minutes, so download right away
  // (curl -L -o <downloads>/<id>/<name> <url>) and check the size. Never save the links anywhere.
  const headers = { Accept: "application/json" };
  const parse = async (r) => JSON.parse((await r.text()).replace(/^while\(1\);/, ""));
  const out = {};
  for (const id of fileIds) {
    const meta = await fetch(`/api/v1/files/${id}`, { credentials: "same-origin", headers }).catch(() => null);
    const link = await fetch(`/api/v1/files/${id}/public_url`, { credentials: "same-origin", headers }).catch(() => null);
    const m = meta && meta.status === 200 ? await parse(meta) : {};
    const l = link && link.status === 200 ? await parse(link) : {};
    out[id] = { name: m.display_name || null, size: m.size ?? null, updated_at: m.updated_at || null,
      url: l.public_url || null, error: l.public_url ? null : (link ? link.status : "network") };
  }
  return out;
}
