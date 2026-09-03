"""Emit a tiny runnable app from GraphLang lines."""

from __future__ import annotations

import json
from pathlib import Path

from .store import InMemoryGraph


APP_TEMPLATE = '''"""Generated from GraphLang lines. Do not edit by hand unless you mean it."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from urllib.parse import parse_qs, urlparse

GRAPH = json.loads({graph_literal!r})

STORE = {{}}


def pages():
    return [n for n in GRAPH["nodes"] if n.get("label") == "Page"]


def node_by_id(nid):
    for n in GRAPH["nodes"]:
        if n.get("id") == nid:
            return n
    return None


def rels_from(page_id, typ):
    return [r for r in GRAPH["relationships"] if r.get("from") == page_id and r.get("type") == typ]


def open_page(name: str) -> dict:
    page = next((n for n in pages() if n.get("name") == name), None)
    if page is None:
        return {{"ok": False, "status": 404, "reason": f"No page {{name}}"}}
    includes = [r.get("to_name") for r in sorted(rels_from(page["id"], "INCLUDES"), key=lambda r: (r.get("props") or {{}}).get("order", 0))]
    connects = rels_from(page["id"], "CONNECTS_TO")
    auths = rels_from(page["id"], "AUTHENTICATES_WITH")
    if not connects:
        return {{
            "ok": False,
            "status": 403,
            "page": name,
            "includes": includes,
            "reason": "No CONNECTS_TO line. Draw a handshake first.",
        }}
    conn = connects[0]
    secure = bool((conn.get("props") or {{}}).get("secure"))
    if secure and not auths:
        return {{
            "ok": False,
            "status": 401,
            "page": name,
            "includes": includes,
            "reason": "Secure connection requires AUTHENTICATES_WITH.",
        }}
    return {{
        "ok": True,
        "status": 200,
        "page": name,
        "path": page.get("path") or ("/" if name.lower() in {{"landing", "home"}} else f"/{{name.lower()}}"),
        "includes": includes,
        "database": conn.get("to_name"),
        "auth": auths[0].get("to_name") if auths else None,
        "secure": secure,
    }}


def render(name: str) -> dict:
    opened = open_page(name)
    header = " | ".join(opened.get("includes") or [])
    body = f"{{opened.get('page')}} talking to {{opened.get('database') or 'nowhere'}}"
    if opened.get("auth"):
        body += f" via {{opened['auth']}}"
    opened["html"] = f"<header>{{header}}</header><main>{{body}}</main><footer>{{header}}</footer>"
    return opened


ROUTES = json.loads({routes_literal!r})


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload: dict) -> None:
        body = json.dumps(payload, indent=2).encode()
        self.send_response(payload.get("status", 200 if payload.get("ok") else 400))
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/__graph":
            self._send({{"ok": True, "status": 200, "graph": GRAPH}})
            return
        page = ROUTES.get(path)
        if not page:
            self._send({{"ok": False, "status": 404, "reason": f"No route {{path}}"}})
            return
        result = render(page)
        qs = parse_qs(parsed.query)
        if "key" in qs:
            if not result.get("ok"):
                self._send(result)
                return
            result["value"] = STORE.get(result["database"], {{}}).get(qs["key"][0])
        self._send(result)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        page = ROUTES.get(path)
        if not page:
            self._send({{"ok": False, "status": 404, "reason": f"No route {{path}}"}})
            return
        opened = open_page(page)
        if not opened.get("ok"):
            self._send(opened)
            return
        length = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(length) or b"{{}}")
        db = opened["database"]
        STORE.setdefault(db, {{}}).update(payload)
        opened["written"] = payload
        self._send(opened)

    def log_message(self, fmt, *args):
        return


def main(host="127.0.0.1", port=8787):
    print("Generated GraphLang app")
    for path, page in ROUTES.items():
        print(f"  GET  {{path}}  -> {{page}}")
    print(f"http://{{host}}:{{port}}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
'''


def _routes(graph: InMemoryGraph) -> dict[str, str]:
    routes = {}
    for node in graph.nodes.values():
        if node.label != "Page":
            continue
        name = node.props.get("name") or node.id
        path = node.props.get("path") or ("/" if str(name).lower() in {"landing", "home"} else f"/{str(name).lower()}")
        routes[path] = name
    return routes


def emit_app(graph: InMemoryGraph, dest: str | Path) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    snapshot = graph.snapshot()
    routes = _routes(graph)
    source = APP_TEMPLATE.format(
        graph_literal=json.dumps(snapshot, indent=2),
        routes_literal=json.dumps(routes, indent=2),
    )
    dest.write_text(source, encoding="utf-8")
    return dest
