"""Build a tiny app from the graph, then hit the generated routes."""

from pathlib import Path
import json
import sys
import threading
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from parser.architecture.emit import emit_app
from parser.architecture.runtime import GraphRuntime


def get(url: str) -> dict:
    from urllib.error import HTTPError
    try:
        with urlopen(url) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as exc:
        return json.loads(exc.read().decode())


def post(url: str, payload: dict) -> dict:
    req = Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    rt = GraphRuntime(use_llm=False)
    rt.say("I need a db, three pages and a couple of includes.")
    rt.say("Connect the db to the landing page with a secure auth.")
    rt.say("Make all pages include Header and Footer.")
    rt.draw("Dashboard", "MainDB", secure=True)

    dest = ROOT / "examples" / "architecture" / "generated_app.py"
    emit_app(rt.graph, dest)
    print("emitted", dest)

    import importlib.util

    spec = importlib.util.spec_from_file_location("generated_app", dest)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    server = threading.Thread(target=lambda: mod.main("127.0.0.1", 8787), daemon=True)
    server.start()
    import time
    time.sleep(0.3)

    print("GET /", get("http://127.0.0.1:8787/"))
    print("GET /dashboard", get("http://127.0.0.1:8787/dashboard"))
    print("GET /settings (no line)", get("http://127.0.0.1:8787/settings"))
    print("POST /", post("http://127.0.0.1:8787/", {"welcome": "from generated app"}))
    print("GET /?key=welcome", get("http://127.0.0.1:8787/?key=welcome"))


if __name__ == "__main__":
    main()
