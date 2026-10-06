"""graphlang command line."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runtime import GraphRuntime

DEFAULT_GRAPH = Path("graphlang.json")


def _rt(args) -> GraphRuntime:
    bolt = None
    if getattr(args, "bolt", False) or getattr(args, "vendor", None):
        try:
            from .bolt import BoltStore

            bolt = BoltStore(vendor=getattr(args, "vendor", None) or "neo4j")
        except Exception as exc:
            print(f"bolt disabled: {exc}")
    rt = GraphRuntime(use_llm=not args.no_llm, neo4j=bolt)
    graph_path = Path(args.graph)
    if graph_path.exists():
        rt.load(graph_path)
    return rt


def _persist(rt: GraphRuntime, args) -> None:
    rt.save(args.graph)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="graphlang", description="Speak or draw a program as a graph.")
    parser.add_argument("--graph", default=str(DEFAULT_GRAPH), help="json snapshot path")
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--vendor", choices=["neo4j", "memgraph"], help="also execute Cypher on Bolt")
    parser.add_argument("--bolt", action="store_true", help="use Bolt with default vendor neo4j")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_say = sub.add_parser("say")
    p_say.add_argument("text", nargs="+")

    p_draw = sub.add_parser("draw")
    p_draw.add_argument("src")
    p_draw.add_argument("dst")
    p_draw.add_argument("--insecure", action="store_true")

    p_open = sub.add_parser("open")
    p_open.add_argument("page")

    p_emit = sub.add_parser("emit")
    p_emit.add_argument("dest", nargs="?", default="generated_app")

    p_imp = sub.add_parser("import")
    p_imp.add_argument("path")

    p_call = sub.add_parser("call")
    p_call.add_argument("function")
    p_call.add_argument("--page")

    sub.add_parser("ascii")
    sub.add_parser("lint")
    sub.add_parser("audit")
    p_save = sub.add_parser("save")
    p_save.add_argument("path", nargs="?")
    p_load = sub.add_parser("load")
    p_load.add_argument("path")
    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--port", type=int, default=8765)

    args = parser.parse_args(argv)
    rt = _rt(args)

    if args.cmd == "say":
        result = rt.say(" ".join(args.text))
        print(result["ascii"])
        print("intents:", [i["action"] for i in result["intents"]])
        _persist(rt, args)
        return 0
    if args.cmd == "draw":
        result = rt.draw(args.src, args.dst, secure=not args.insecure)
        print(result["ascii"])
        _persist(rt, args)
        return 0
    if args.cmd == "open":
        print(json.dumps(rt.open(args.page).to_dict(), indent=2))
        return 0
    if args.cmd == "emit":
        path = rt.emit(args.dest)
        print(path)
        return 0
    if args.cmd == "import":
        from .importer import import_path

        intents = import_path(args.path)
        result = rt._commit(f"import {args.path}", intents)
        print(result["ascii"])
        _persist(rt, args)
        return 0
    if args.cmd == "call":
        print(rt.call(args.function, page=args.page))
        return 0
    if args.cmd == "ascii":
        print(rt.graph.ascii())
        return 0
    if args.cmd == "audit":
        print(json.dumps(rt.audit(), indent=2))
        return 0
    if args.cmd == "lint":
        missing = [
            n.props.get("name")
            for n in rt.graph.nodes.values()
            if n.label == "Page" and not any(r.src == n.id and r.type == "CONNECTS_TO" for r in rt.graph.rels)
        ]
        print(json.dumps({"pages_without_db": missing}))
        return 0
    if args.cmd == "save":
        print(rt.save(args.path or args.graph))
        return 0
    if args.cmd == "load":
        rt.load(args.path)
        rt.save(args.graph)
        print(rt.graph.ascii())
        return 0
    if args.cmd == "serve":
        from .visual import serve

        serve(port=args.port)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
