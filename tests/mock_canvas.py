#!/usr/bin/env python3
"""A tiny fake Canvas for testing the sync without a real school account.

  python3 tests/mock_canvas.py --port 8765 --files <folder with the fixture files>

Serves the read-only API calls canvas_api.py and fetch_canvas.js make, for two courses
(ECON 325 id 101, FIN 410 id 202). Accepts the token "test-token" or a same-origin page.
"""
import argparse, datetime as dt, json, os, re, sys, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

A = argparse.ArgumentParser(); A.add_argument("--port", type=int, default=8765); A.add_argument("--files", required=True)
A.add_argument("--stage", type=int, default=1, help="2 = Canvas after a change (moved due date, new deck)")
X = A.parse_args()
NOW = dt.datetime.now(dt.timezone.utc)
def day(n, h=16): return (NOW + dt.timedelta(days=n)).replace(hour=h, minute=59, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
HOST = f"127.0.0.1:{X.port}"
def size(name): return os.path.getsize(os.path.join(X.files, name))
def f(fid, name, folder, ctype): return {"id": fid, "display_name": name, "updated_at": day(-1), "created_at": day(-1), "modified_at": day(-1),
    "size": size(name), "content-type": ctype, "folder_id": folder, "locked_for_user": False, "hidden": False}
PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
FILES = {
  101: [f(9001, "Lecture 1 - Finding Opportunities.pptx", 11, PPTX), f(9002, "Syllabus.pdf", 10, "application/pdf"), f(9003, "banner.png", 10, "image/png")],
  202: [f(9101, "Reading - Options Basics.pdf", 21, "application/pdf")],
}
HIDDEN = {9004: (101, f(9004, "Case - Lemonade Stand.pdf", 12, "application/pdf"))}  # only linked from an announcement
if X.stage >= 2:
    FILES[101].insert(0, f(9005, "Lecture 2 - Customer Discovery.pptx", 11, PPTX))
FOLDERS = {101: [{"id": 10, "full_name": "course files"}, {"id": 11, "full_name": "course files/Lectures"}, {"id": 12, "full_name": "course files/Cases"}],
           202: [{"id": 20, "full_name": "course files"}, {"id": 21, "full_name": "course files/Readings"}]}
def asg(i, name, due, state=None, cid=101):
    return {"id": i, "name": name, "due_at": due, "lock_at": None, "unlock_at": None, "points_possible": 100, "submission_types": ["online_upload"],
            "published": True, "html_url": f"http://{HOST}/courses/{cid}/assignments/{i}",
            "submission": {"workflow_state": state or "unsubmitted", "submitted_at": day(-2) if state else None, "score": None, "excused": False, "missing": False, "late": False}}
ASSIGN = {101: [asg(501, "Problem Interview Memo", day(-5), "submitted"), asg(502, "Business Model Canvas", day(9 if X.stage >= 2 else 6)), asg(503, "Attendance Week 3", day(2)),
                asg(504, "Final Pitch Deck", day(30))],
          202: [asg(601, "Problem Set 1", day(4), cid=202)]}
ANN = {101: [{"id": 701, "title": "Case for Thursday", "posted_at": day(-1), "html_url": f"http://{HOST}/courses/101/discussion_topics/701",
              "message": f'<p>Please read the <a href="/courses/101/files/9004/download">Lemonade Stand case</a> before class.</p><p>Also see <a href="https://example.com/lean">this article</a>.<br>Bring a laptop.</p>',
              "attachments": []}], 202: []}
MODULES = {101: [{"id": 801, "name": "Week 1", "position": 1, "unlock_at": None, "items": [
              {"id": 1, "title": "Lecture 1", "type": "File", "content_id": 9001, "html_url": f"http://{HOST}/courses/101/modules/items/1"},
              {"id": 2, "title": "Steve Blank on customer development", "type": "ExternalUrl", "external_url": "https://example.com/blank", "html_url": f"http://{HOST}/courses/101/modules/items/2"}]}], 202: []}
PAGES = {101: [{"url": "start-here", "title": "Start here", "updated_at": day(-3), "html_url": f"http://{HOST}/courses/101/pages/start-here",
                "body": '<h2>Welcome</h2><ul><li>Office hours Tue 2pm</li><li><a href="/courses/101/files/9002">Syllabus</a></li></ul>'}], 202: []}
EVENTS = {101: [{"id": 901, "title": "Midterm review session", "start_at": day(12, 22), "end_at": day(12, 23), "location_name": "Room 12", "description": "<p>Optional review.</p>"}], 202: []}
COURSES = {101: {"id": 101, "name": "ECON 325.001 Entrepreneurship", "course_code": "ECON325.001.FA26", "term": {"name": "Fall 2026"},
                 "syllabus_body": '<p>Syllabus: <a href="/courses/101/files/9002/download">download</a></p>'},
           202: {"id": 202, "name": "Derivatives", "course_code": "FIN-410-01", "term": {"name": "Fall 2026"}, "syllabus_body": ""}}
ALL_FILES = {x["id"]: x for v in FILES.values() for x in v}; ALL_FILES.update({k: v[1] for k, v in HIDDEN.items()})

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, obj, code=200, link=None, raw=None, ctype="application/json"):
        body = raw if raw is not None else json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body)))
        if link: self.send_header("Link", link)
        self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); p = u.path; q = urllib.parse.parse_qs(u.query)
        m = re.match(r"^/dl/(\d+)$", p)
        if m:
            return self.send(None, raw=open(os.path.join(X.files, ALL_FILES[int(m.group(1))]["display_name"]), "rb").read(), ctype="application/octet-stream")
        if not p.startswith("/api/"):
            return self.send(None, raw=b"<html><body>fake canvas</body></html>", ctype="text/html")
        same_origin = HOST in (self.headers.get("Referer") or "")
        if self.headers.get("Authorization") != "Bearer test-token" and not same_origin:
            return self.send({"errors": [{"message": "Invalid access token."}]}, 401)
        def cid():
            return int(re.search(r"/courses/(\d+)", p).group(1))
        ctx = int(re.sub(r"\D", "", (q.get("context_codes[]") or ["0"])[0]) or 0)
        if p == "/api/v1/users/self": return self.send({"id": 1, "name": "Test Student", "short_name": "Test"})
        if p == "/api/v1/courses": return self.send([{k: v for k, v in c.items() if k != "syllabus_body"} for c in COURSES.values()])
        if p == "/api/v1/announcements": return self.send(ANN.get(ctx, []))
        if p == "/api/v1/calendar_events": return self.send(EVENTS.get(ctx, []))
        m = re.match(r"^/api/v1/files/(\d+)(/public_url)?$", p)
        if m:
            x = ALL_FILES.get(int(m.group(1)))
            if not x: return self.send({}, 404)
            return self.send({"public_url": f"http://{HOST}/dl/{x['id']}"} if m.group(2) else x)
        if not re.match(r"^/api/v1/courses/\d+", p) or cid() not in COURSES: return self.send({}, 404)
        c = cid(); rest = re.sub(r"^/api/v1/courses/\d+", "", p)
        if rest == "": return self.send(COURSES[c])
        if rest == "/assignments":  # two pages, to exercise the Link header
            page = int((q.get("page") or ["1"])[0]); items = ASSIGN[c]
            if page == 1 and len(items) > 2:
                return self.send(items[:2], link=f'<http://{HOST}{p}?per_page=100&page=2>; rel="next"')
            return self.send(items[2:] if len(items) > 2 else items)
        if rest == "/folders": return self.send(FOLDERS[c])
        if rest == "/files": return self.send(FILES[c])
        m = re.match(r"^/files/(\d+)$", rest)
        if m:
            x = ALL_FILES.get(int(m.group(1)))
            return self.send(x) if x else self.send({}, 404)
        if rest == "/modules": return self.send(MODULES[c])
        if rest == "/pages": return self.send([{k: v for k, v in pg.items() if k != "body"} for pg in PAGES[c]])
        m = re.match(r"^/pages/(.+)$", rest)
        if m:
            pg = next((pg for pg in PAGES[c] if pg["url"] == urllib.parse.unquote(m.group(1))), None)
            return self.send(pg) if pg else self.send({}, 404)
        return self.send({}, 404)

ThreadingHTTPServer(("127.0.0.1", X.port), H).serve_forever()
