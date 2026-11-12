#!/usr/bin/env python3
"""Read Canvas with a personal access token. Read-only: it only sends GET requests.

This is the reader any AI (or you) can run from a terminal. It produces the same data as
fetch_canvas.js, which is the alternative for AIs that drive a logged-in browser tab instead.

  python3 canvas_api.py login --host school.instructure.com    # asks for the token; run this yourself
  python3 canvas_api.py status                                 # which Canvas sites are connected
  python3 canvas_api.py courses                                # your active Canvas courses, with ids
  python3 canvas_api.py fetch --out canvas.json                # everything the planner needs
  python3 canvas_api.py download --imports imports.json --out downloads
  python3 canvas_api.py logout --host school.instructure.com

Getting a token: in Canvas, open Account -> Settings -> "+ New access token", give it a name
and an expiry date, and copy it once. Some schools turn this off; then use the browser reader.

The token is stored outside the vault, in ~/.config/obsidian-canvas-sync/config.json, readable
only by you. It is never printed, logged or written into the vault. Anyone holding it can read
your Canvas account, so never paste it into an AI chat; delete it in Canvas to revoke it.
Standard library only.
"""
import argparse, datetime as dt, getpass, json, os, pathlib, re, stat, sys, urllib.error, urllib.parse, urllib.request
from html.parser import HTMLParser

HERE = pathlib.Path(__file__).resolve().parent
CONFIG = pathlib.Path(os.environ.get("CANVAS_SYNC_CONFIG") or pathlib.Path.home() / ".config/obsidian-canvas-sync/config.json")
NEWLINE_AFTER = {"p", "br", "li", "tr", "h1", "h2", "h3", "h4"}


def load_config():
    try:
        return json.loads(CONFIG.read_text())
    except (OSError, ValueError):
        return {"hosts": {}}


def save_config(cfg):
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n")
    try:
        os.chmod(CONFIG, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def clean_host(host):
    host = re.sub(r"^https?://", "", host.strip()).split("/")[0]
    if not re.match(r"^[A-Za-z0-9.-]+(:\d+)?$", host):
        sys.exit(f"That doesn't look like a Canvas address: {host}")
    return host


def token_for(host):
    return (load_config().get("hosts", {}).get(host) or {}).get("token") or os.environ.get("CANVAS_TOKEN")


class Canvas:
    def __init__(self, host, token):
        self.host, self.token = host, token
        scheme = "http" if host.startswith(("127.0.0.1", "localhost")) else "https"  # http only for local tests
        self.base = f"{scheme}://{host}"

    def _open(self, url):
        if not url.startswith(self.base + "/"):
            raise urllib.error.URLError("refusing to send the token to another site")
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"})
        return urllib.request.urlopen(req, timeout=45)

    @staticmethod
    def _parse(raw):
        return json.loads(re.sub(r"^while\(1\);", "", raw.decode("utf-8", "replace")))

    def one(self, path):
        try:
            with self._open(self.base + path) as r:
                return {"data": self._parse(r.read())}
        except urllib.error.HTTPError as e:
            return {"error": e.code}
        except (urllib.error.URLError, OSError, ValueError):
            return {"error": "network"}

    def many(self, path, max_pages=10):
        items, url = [], self.base + path
        for _ in range(max_pages):
            if not url:
                break
            try:
                with self._open(url) as r:
                    data = self._parse(r.read())
                    link = r.headers.get("Link") or ""
            except urllib.error.HTTPError as e:
                return {"error": e.code, "items": items}
            except (urllib.error.URLError, OSError, ValueError):
                return {"error": "network", "items": items}
            if not isinstance(data, list):
                return {"error": "unexpected response", "items": items}
            items += data
            m = re.search(r'<([^>]+)>;\s*rel="next"', link)
            url = m.group(1) if m else None
        return {"items": items}


class _Html(HTMLParser):
    """Mirrors fetch_canvas.js: text() keeps links as "label <url>", links() lists every http link."""

    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base, self.out, self.links, self._a = base, [], [], None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self._a = {"href": urllib.parse.urljoin(self.base, href), "text": []}
        if tag == "br":
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag == "a" and self._a:
            a, self._a = self._a, None
            self.out.append(f" <{a['href']}>")
            if re.match(r"^https?:", a["href"]):
                m = re.search(r"/files/(\d+)", a["href"])
                self.links.append({"text": re.sub(r"\s+", " ", "".join(a["text"])).strip()[:200], "href": a["href"],
                                   "file_id": int(m.group(1)) if m else None})
        if tag in NEWLINE_AFTER and tag != "br":
            self.out.append("\n")

    def handle_data(self, data):
        self.out.append(data)
        if self._a:
            self._a["text"].append(data)


def html_text(html, base):
    p = _Html(base); p.feed(html or ""); p.close()
    t = re.sub(r"[ \t]+", " ", "".join(p.out))
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def html_links(html, base):
    p = _Html(base); p.feed(html or ""); p.close()
    return p.links


def iso(d):
    return d.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def fetch_host(host, course_ids, since_days=21):
    token = token_for(host)
    res = {"version": 2, "host": host, "fetched_at": iso(dt.datetime.now(dt.timezone.utc)), "logged_in": False, "courses": {}}
    if not token:
        return res
    c = Canvas(host, token)
    res["logged_in"] = "data" in c.one("/api/v1/users/self")
    if not res["logged_in"]:
        return res
    now = dt.datetime.now(dt.timezone.utc)
    since, until = iso(now - dt.timedelta(days=since_days or 21)), iso(now + dt.timedelta(days=2))
    today, later = now.strftime("%Y-%m-%d"), (now + dt.timedelta(days=150)).strftime("%Y-%m-%d")
    q = urllib.parse.quote

    def file_info(x, folders, via):
        return {"id": x.get("id"), "name": x.get("display_name"), "updated_at": x.get("updated_at"), "created_at": x.get("created_at"),
                "modified_at": x.get("modified_at"), "size": x.get("size"), "content_type": x.get("content-type") or "",
                "folder": folders.get(x.get("folder_id")) or "", "locked": bool(x.get("locked_for_user")), "hidden": bool(x.get("hidden")),
                "via": via}

    for cid in course_ids:
        base = f"{c.base}/courses/{cid}"
        course = {"id": cid, "errors": {}}
        info = c.one(f"/api/v1/courses/{cid}?include[]=syllabus_body")
        if "error" in info:
            course["errors"]["course"] = info["error"]
        else:
            course["name"] = info["data"].get("name")
            course["syllabus_links"] = html_links(info["data"].get("syllabus_body"), base)

        a = c.many(f"/api/v1/courses/{cid}/assignments?per_page=100&include[]=submission&order_by=due_at")
        if a.get("error"):
            course["errors"]["assignments"] = a["error"]
        course["assignments"] = []
        for x in a["items"]:
            s = x.get("submission")
            course["assignments"].append({
                "id": x.get("id"), "name": re.sub(r"\s+", " ", x.get("name") or "").strip(), "due_at": x.get("due_at"),
                "lock_at": x.get("lock_at"), "unlock_at": x.get("unlock_at"), "points": x.get("points_possible"),
                "types": x.get("submission_types") or [], "published": x.get("published") is not False, "url": x.get("html_url"),
                "submission": {"state": s.get("workflow_state"), "submitted_at": s.get("submitted_at"), "score": s.get("score"),
                               "excused": bool(s.get("excused")), "missing": bool(s.get("missing")), "late": bool(s.get("late"))} if s else None})

        an = c.many(f"/api/v1/announcements?context_codes[]=course_{cid}&start_date={q(since)}&end_date={q(until)}&per_page=50")
        if an.get("error"):
            course["errors"]["announcements"] = an["error"]
        course["announcements"] = [{
            "id": x.get("id"), "title": x.get("title"), "posted_at": x.get("posted_at"), "url": x.get("html_url"),
            "text": html_text(x.get("message"), base)[:6000], "links": html_links(x.get("message"), base),
            "attachments": [{"id": f.get("id"), "name": f.get("display_name"), "size": f.get("size"), "updated_at": f.get("updated_at"),
                             "content_type": f.get("content-type") or ""} for f in (x.get("attachments") or [])]} for x in an["items"]]

        fo = c.many(f"/api/v1/courses/{cid}/folders?per_page=100")
        folders = {f.get("id"): re.sub(r"^course files/?", "", f.get("full_name") or "") for f in fo.get("items") or []}
        f = c.many(f"/api/v1/courses/{cid}/files?per_page=100&sort=updated_at&order=desc")
        if f.get("error"):
            course["errors"]["files"] = f["error"]
        course["files"] = [file_info(x, folders, "files") for x in f["items"][:150]]

        mo = c.many(f"/api/v1/courses/{cid}/modules?include[]=items&per_page=50")
        if mo.get("error") and mo["error"] != 404:
            course["errors"]["modules"] = mo["error"]
        course["modules"] = [{
            "id": m.get("id"), "name": m.get("name"), "position": m.get("position"), "unlock_at": m.get("unlock_at"),
            "items": [{"id": i.get("id"), "title": i.get("title"), "type": i.get("type"), "content_id": i.get("content_id") or None,
                       "url": i.get("external_url") or i.get("html_url") or "", "page_url": i.get("page_url") or None}
                      for i in (m.get("items") or [])]} for m in (mo.get("items") or [])]

        pg = c.many(f"/api/v1/courses/{cid}/pages?per_page=20&sort=updated_at&order=desc")
        course["pages"] = []
        if not pg.get("error"):
            for p in (pg.get("items") or [])[:10]:
                full = c.one(f"/api/v1/courses/{cid}/pages/{q(str(p.get('url')), safe='')}")
                body = full["data"].get("body") if "data" in full else None
                course["pages"].append({"url": p.get("url"), "title": p.get("title"), "updated_at": p.get("updated_at"),
                                        "html_url": p.get("html_url"), "text": html_text(body, base)[:3000] if body else "",
                                        "links": html_links(body, base) if body else []})

        # files linked from the syllabus, announcements, module items and pages that the Files list doesn't show
        known = {str(x["id"]) for x in course["files"]}
        linked = [(l["file_id"], "syllabus") for l in course.get("syllabus_links") or [] if l["file_id"]]
        for x in course["announcements"]:
            linked += [(l["file_id"], f"announcement {x['id']}") for l in x["links"] if l["file_id"]]
            linked += [(t["id"], f"announcement {x['id']}") for t in x["attachments"]]
        for m in course["modules"]:
            linked += [(i["content_id"], f"module {m['name']}") for i in m["items"] if i["type"] == "File" and i["content_id"]]
        for p in course["pages"]:
            linked += [(l["file_id"], f"page {p['title']}") for l in p["links"] if l["file_id"]]
        for fid, via in linked:
            if str(fid) in known:
                continue
            known.add(str(fid))
            one = c.one(f"/api/v1/courses/{cid}/files/{fid}")
            if "data" in one:
                course["files"].append(file_info(one["data"], folders, via))

        ev = c.many(f"/api/v1/calendar_events?context_codes[]=course_{cid}&type=event&start_date={today}&end_date={later}&per_page=100")
        if ev.get("error"):
            course["errors"]["events"] = ev["error"]
        course["events"] = [{"id": x.get("id"), "title": x.get("title"), "start_at": x.get("start_at"), "end_at": x.get("end_at"),
                             "location": x.get("location_name") or "", "text": html_text(x.get("description"), base)[:600]}
                            for x in ev["items"]]
        res["courses"][str(cid)] = course
    return res


def configured_ids(config_path):
    """{host: [course ids]} from courses.json (courses and watch_only)."""
    try:
        cfg = json.loads(pathlib.Path(config_path).read_text())
    except (OSError, ValueError):
        sys.exit(f"Could not read {config_path}. Run: sync.py setup")
    out = {}
    for c in cfg.get("courses", []) + cfg.get("watch_only", []):
        if c.get("host") and c.get("id"):
            out.setdefault(c["host"], []).append(c["id"])
    return out


def fetch_all(config_path, since_days=21):
    return {"hosts": [fetch_host(h, ids, since_days) for h, ids in configured_ids(config_path).items()]}


def list_courses(host):
    c = Canvas(host, token_for(host) or "")
    r = c.many("/api/v1/courses?enrollment_state=active&include[]=term&per_page=100")
    if r.get("error") and not r["items"]:
        return None
    return [{"id": x.get("id"), "code": x.get("course_code") or "", "name": x.get("name") or "",
             "term": (x.get("term") or {}).get("name") or ""} for x in r["items"] if x.get("id") and x.get("name")]


def download(imports_path, out_dir):
    """Download each planned import to <out>/<file id>/<name>. Links are short-lived and never saved."""
    imports = json.loads(pathlib.Path(imports_path).read_text())
    out_dir = pathlib.Path(out_dir)
    ok = True
    for i in imports:
        host, fid, name = i["host"], i["file_id"], i["name"]
        dest = out_dir / str(fid) / name
        if dest.is_file() and (i.get("size") is None or dest.stat().st_size == i["size"]):
            print(f"  have       {name}"); continue
        token = token_for(host)
        link = Canvas(host, token).one(f"/api/v1/files/{fid}/public_url") if token else {"error": "no token"}
        url = (link.get("data") or {}).get("public_url")
        if not url:
            ok = False; print(f"  FAILED     {name}: no download link ({link.get('error')})"); continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            with urllib.request.urlopen(urllib.request.Request(url), timeout=120) as r, open(dest, "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
        except (urllib.error.URLError, OSError) as e:
            ok = False; print(f"  FAILED     {name}: {getattr(e, 'reason', e)}"); continue
        size = dest.stat().st_size
        if i.get("size") is not None and size != i["size"]:
            ok = False; dest.unlink(); print(f"  FAILED     {name}: size {size} doesn't match Canvas ({i['size']})"); continue
        print(f"  downloaded {name} ({size:,} bytes)")
    return ok


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("action", choices=["login", "logout", "status", "courses", "fetch", "download"])
    a.add_argument("--host", help="your school's Canvas address, e.g. school.instructure.com")
    a.add_argument("--token-stdin", action="store_true", help="login: read the token from standard input instead of a prompt")
    a.add_argument("--config", default=str(HERE / "courses.json"))
    a.add_argument("--out")
    a.add_argument("--imports")
    a.add_argument("--since-days", type=int, default=21)
    x = a.parse_args()
    cfg = load_config()
    if x.action == "login":
        if not x.host:
            a.error("login needs --host")
        host = clean_host(x.host)
        token = (sys.stdin.readline() if x.token_stdin else getpass.getpass(f"Paste your Canvas access token for {host} (it stays hidden): ")).strip()
        if not token:
            sys.exit("No token entered.")
        me = Canvas(host, token).one("/api/v1/users/self")
        if "data" not in me:
            sys.exit(f"Canvas at {host} didn't accept that token (error {me.get('error')}). Nothing was saved.")
        cfg.setdefault("hosts", {})[host] = {"token": token}
        save_config(cfg)
        print(f"Connected to {host} as {me['data'].get('short_name') or me['data'].get('name') or 'you'}. Token saved outside the vault.")
    elif x.action == "logout":
        host = clean_host(x.host or "")
        if cfg.get("hosts", {}).pop(host, None):
            save_config(cfg)
        print(f"Removed the saved token for {host}. Also delete it in Canvas (Account -> Settings) to revoke it.")
    elif x.action == "status":
        hosts = list(cfg.get("hosts", {}))
        if not hosts:
            print("No Canvas site is connected. Run: canvas_api.py login --host <your school's Canvas address>")
        for h in hosts:
            good = "data" in Canvas(h, token_for(h)).one("/api/v1/users/self")
            print(f"  {'OK  ' if good else 'FAIL'} {h}: {'token works' if good else 'token rejected or site unreachable; log in again'}")
    elif x.action == "courses":
        for h in ([clean_host(x.host)] if x.host else list(cfg.get("hosts", {}))):
            rows = list_courses(h)
            if rows is None:
                print(f"{h}: could not list courses (log in again)"); continue
            print(h)
            for r in rows:
                print(f"  {r['id']}\t{r['code']}\t{r['name']}\t{r['term']}")
    elif x.action == "fetch":
        if not x.out:
            a.error("fetch needs --out")
        data = fetch_all(x.config, x.since_days)
        pathlib.Path(x.out).write_text(json.dumps(data))
        for h in data["hosts"]:
            print(f"  {'OK  ' if h['logged_in'] else 'FAIL'} {h['host']}: {len(h['courses'])} course(s) read" + ("" if h["logged_in"] else " (not logged in)"))
        sys.exit(0 if data["hosts"] and all(h["logged_in"] for h in data["hosts"]) else 1)
    else:
        if not (x.imports and x.out):
            a.error("download needs --imports and --out")
        sys.exit(0 if download(x.imports, x.out) else 1)


if __name__ == "__main__":
    if os.name == "nt" and not sys.flags.utf8_mode:  # Windows: read and print UTF-8, here and in child scripts
        import subprocess
        sys.exit(subprocess.call([sys.executable, *sys.argv], env={**os.environ, "PYTHONUTF8": "1"}))
    main()
