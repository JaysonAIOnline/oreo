"""Relationship runtime example.

Speak the program, draw the missing handshake, then open pages.
Settings is refused until a line exists.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from parser.architecture.engine import HandshakeError, RelationshipEngine
from parser.architecture.queries import catalog
from parser.architecture.runtime import GraphRuntime


def main() -> None:
    rt = GraphRuntime(use_llm=False)
    engine = RelationshipEngine(rt.graph)

    rt.say("I need a db, three pages and a couple of includes.")
    rt.say("Connect the db to the landing page with a secure auth.")
    rt.say("Make all pages include Header and Footer.")

    print("=== graph ===")
    print(rt.graph.ascii())

    print("\n=== open Landing (has handshake) ===")
    landing = engine.open_page("Landing")
    print(landing.to_dict())

    print("\n=== open Settings (no db line) ===")
    settings = engine.open_page("Settings")
    print(settings.to_dict())

    print("\n=== Landing writes through the graph, not an ORM ===")
    print(engine.write("Landing", "welcome", "hello from Landing"))
    print("read back:", engine.read("Landing", "welcome"))

    print("\n=== Settings cannot write until you draw the line ===")
    try:
        engine.write("Settings", "welcome", "should fail")
    except HandshakeError as exc:
        print("refused:", exc)

    print("\n=== draw Settings -> MainDB ===")
    rt.draw("Settings", "MainDB", secure=True)
    print(engine.open_page("Settings").to_dict())
    print(engine.write("Settings", "theme", "dark"))
    print("Landing still sees the same store:", engine.read("Landing", "theme"))

    print("\n=== render includes ===")
    print(engine.render("Dashboard"))

    save_path = ROOT / "examples" / "architecture" / "app.graph.json"
    engine.save(save_path)
    print("\nsaved", save_path)

    print("\n=== same question in other graph languages ===")
    langs = catalog()["languages"]["neighbors"]
    for name, query in langs.items():
        print(f"\n-- {name} --\n{query}")


if __name__ == "__main__":
    main()
