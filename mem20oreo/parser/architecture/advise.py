"""Voice advisor: notice what the graph is becoming, then offer a pack of nodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .parser import Intent, Ref
from .store import InMemoryGraph


SECURE_HINTS = ("secure", "auth", "login", "checkout", "pay", "account", "admin", "private")

STOREFRONT = ("shop", "store", "cart", "product", "catalog", "checkout", "order", "merch", "storefront")
FAN = ("fan", "fandom", "band", "artist", "tour", "club", "wiki", "fansite")
BLOG = ("blog", "post", "article", "newsletter", "journal")
GALLERY = ("photo", "picture", "gallery", "portfolio", "image")
SAAS = ("dashboard", "workspace", "saas", "admin panel")
MOBILE = ("mobile", "ios", "android", "flutter", "react native")
DESKTOP = ("desktop", "electron", "tauri", "windows app", "mac app")
API = ("api", "backend", "rest", "graphql", "endpoint")
MICRO = ("microservice", "microservices", "service mesh", "saga", "cqrs")
STATE = ("state management", "redux", "event sourcing", "session store", "sync engine")
CLI = ("cli", "command line", "terminal tool", "command-line")
GAME = ("game", "player", "level", "sprite", "unity", "godot")
PIPELINE = ("pipeline", "etl", "kafka", "stream", "warehouse", "airflow")
ML = ("training", "dataset", "inference", "machine learning", "ml model", "model zoo")
BOT = ("bot", "discord", "slack bot", "telegram")
IOT = ("sensor", "iot", "firmware", "mqtt", "device farm")
LIBRARY = ("library", "package", "sdk", "crate", "pip module")
PLUGIN = ("plugin", "extension", "vscode", "browser extension")
SOFTWARE = ("software", "application", "program", "building an app", "native app")


@dataclass
class Suggestion:
    code: str
    spoken: str
    intent: Intent
    intents: list[Intent] = field(default_factory=list)
    page: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.intents:
            self.intents = [self.intent]

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "spoken": self.spoken,
            "page": self.page,
            "intent": self.intent.to_dict(),
            "intents": [i.to_dict() for i in self.intents],
            "details": self.details,
        }


def _name(node) -> str:
    return str(node.props.get("name") or node.id)


def _purpose(node) -> str:
    return str(node.props.get("purpose") or "").lower()


def _blob(graph: InMemoryGraph, extra: str = "") -> str:
    parts = []
    for node in graph.nodes.values():
        parts.append(_name(node).lower())
        parts.append(_purpose(node))
    return " ".join(parts + [extra.lower()])


def _has(graph: InMemoryGraph, name: str) -> bool:
    return graph.find_by_name(None, name) is not None


def _wants_secure(node) -> bool:
    blob = f"{_name(node)} {_purpose(node)}".lower()
    return any(hint in blob for hint in SECURE_HINTS)


def _hits(blob: str, words: tuple[str, ...]) -> bool:
    return any(word in blob for word in words)


def _nodes(*pairs: tuple[str, str, dict | None]) -> Intent:
    refs = []
    for label, name, props in pairs:
        refs.append(Ref(label=label, name=name, props=props or {}))
    return Intent(action="create_node", nodes=refs, raw="scene pack")


def _secure(page: str, db: str = "MainDB") -> Intent:
    return Intent(
        action="connect_with_auth",
        source=Ref(label="Page", name=page),
        target=Ref(label="Database", name=db),
        auth=Ref(label="Auth", name="SecureJWT", props={"method": "jwt", "level": "secure", "requires_https": True}),
        raw=f"secure handshake for {page}",
    )


def _include(page: str, *names: str) -> Intent:
    return Intent(
        action="include",
        source=Ref(label="Page", name=page),
        includes=[Ref(label="Include", name=n) for n in names],
        raw=f"include {', '.join(names)} on {page}",
    )


def scene_suggestions(graph: InMemoryGraph, extra: str = "") -> list[Suggestion]:
    blob = _blob(graph, extra)
    out: list[Suggestion] = []

    if _hits(blob, STOREFRONT) and not (_has(graph, "Checkout") and _has(graph, "PictureStore")):
        missing = [name for name in ("MainDB", "Checkout", "PictureStore", "DesignLLM") if not _has(graph, name)]
        spoken = (
            "Oh — this is reading like a storefront. "
            "Want nodes for a database, a secure checkout, a picture store, "
            "and an LLM we can call for design ideas?"
        )
        intents = [
            _nodes(
                ("Page", "Shop", {"purpose": "storefront"}),
                ("Database", "MainDB", {"engine": "neo4j", "purpose": "orders and inventory"}),
                ("Page", "Checkout", {"purpose": "secure checkout"}),
                ("Database", "PictureStore", {"engine": "object", "purpose": "product photos"}),
                ("Service", "DesignLLM", {"purpose": "design ideas for listings"}),
            ),
            _secure("Checkout", "MainDB"),
        ]
        out.append(Suggestion(code="scene_storefront", spoken=spoken, intent=intents[0], intents=intents, details={"missing": missing}))

    if _hits(blob, FAN) and not (_has(graph, "Forum") and _has(graph, "MailingList")):
        spoken = (
            "Hey — this looks like a fan site. "
            "Want nodes for a forum, a mailing list, and user logins?"
        )
        intents = [
            _nodes(
                ("Page", "Forum", {"purpose": "fan discussion"}),
                ("Service", "MailingList", {"purpose": "updates to fans"}),
                ("Page", "Login", {"purpose": "user logins"}),
                ("Database", "FansDB", {"purpose": "accounts and posts"}),
            ),
            _secure("Login", "FansDB"),
            _secure("Forum", "FansDB"),
        ]
        out.append(Suggestion(code="scene_fan", spoken=spoken, intent=intents[0], intents=intents))

    if _hits(blob, BLOG) and not _has(graph, "Comments"):
        spoken = (
            "This is leaning blog. "
            "I can add a posts database, comments, and an author login."
        )
        intents = [
            _nodes(
                ("Database", "PostsDB", {"purpose": "articles"}),
                ("Page", "Comments", {"purpose": "readers talking back"}),
                ("Page", "AuthorLogin", {"purpose": "writers only"}),
            ),
            _secure("AuthorLogin", "PostsDB"),
        ]
        out.append(Suggestion(code="scene_blog", spoken=spoken, intent=intents[0], intents=intents))

    if _hits(blob, GALLERY) and not _has(graph, "PictureStore"):
        spoken = (
            "Gallery energy. Want a picture store and a public grid page, "
            "with a private upload path?"
        )
        intents = [
            _nodes(
                ("Database", "PictureStore", {"purpose": "images"}),
                ("Page", "Grid", {"purpose": "public pictures"}),
                ("Page", "Upload", {"purpose": "private uploads"}),
            ),
            _secure("Upload", "PictureStore"),
        ]
        out.append(Suggestion(code="scene_gallery", spoken=spoken, intent=intents[0], intents=intents))

    if _hits(blob, MOBILE) and not _has(graph, "PushService"):
        spoken = (
            "This is reading like a mobile app. "
            "Want a home screen, secure account, local cache, and push notifications?"
        )
        intents = [
            _nodes(
                ("Page", "HomeScreen", {"purpose": "mobile home"}),
                ("Page", "Account", {"purpose": "secure account"}),
                ("Database", "LocalCache", {"engine": "sqlite", "purpose": "offline cache"}),
                ("Service", "PushService", {"purpose": "notifications"}),
                ("Database", "Users", {"purpose": "accounts"}),
            ),
            _secure("Account", "Users"),
        ]
        out.append(Suggestion(code="scene_mobile", spoken=spoken, intent=intents[0], intents=intents))

    if _hits(blob, DESKTOP) and not _has(graph, "AutoUpdate"):
        spoken = (
            "Desktop software. I can add a main window, preferences, "
            "a local store, and an auto-update service."
        )
        intents = [
            _nodes(
                ("Page", "MainWindow", {"purpose": "desktop shell"}),
                ("Page", "Preferences", {"purpose": "settings"}),
                ("Database", "LocalStore", {"engine": "sqlite", "purpose": "user files"}),
                ("Service", "AutoUpdate", {"purpose": "ship new builds"}),
            ),
            _secure("Preferences", "LocalStore"),
        ]
        out.append(Suggestion(code="scene_desktop", spoken=spoken, intent=intents[0], intents=intents))

    if _hits(blob, API) and not _has(graph, "APIGateway"):
        spoken = (
            "This looks like a backend. "
            "Want an API gateway, a service registry, auth tokens, and a data store?"
        )
        intents = [
            _nodes(
                ("Service", "APIGateway", {"purpose": "public API"}),
                ("Service", "Registry", {"purpose": "microservices"}),
                ("Auth", "TokenAuth", {"method": "jwt", "level": "secure", "purpose": "tokens"}),
                ("Database", "CoreDB", {"engine": "neo4j", "purpose": "domain data"}),
            ),
            _secure("APIGateway", "CoreDB"),
        ]
        out.append(Suggestion(code="scene_api", spoken=spoken, intent=intents[0], intents=intents))

    if _hits(blob, MICRO) and not _has(graph, "EventBus"):
        spoken = (
            "Microservices. Each capability should own its data. "
            "Want a gateway, an event bus, two services with their own databases, "
            "token auth, and a saga if the work spans services?"
        )
        intents = [
            _nodes(
                ("Service", "APIGateway", {"purpose": "front door"}),
                ("Service", "EventBus", {"purpose": "facts, not calls"}),
                ("Service", "Orders", {"purpose": "order capability"}),
                ("Database", "OrdersDB", {"purpose": "orders own this data"}),
                ("Service", "Payments", {"purpose": "payment capability"}),
                ("Database", "PaymentsDB", {"purpose": "payments own this data"}),
                ("Service", "Saga", {"purpose": "orchestrate multi-step work"}),
                ("Auth", "TokenAuth", {"method": "jwt", "level": "secure"}),
            ),
            _secure("APIGateway", "OrdersDB"),
            _secure("Orders", "OrdersDB"),
            _secure("Payments", "PaymentsDB"),
        ]
        out.append(Suggestion(code="scene_microservices", spoken=spoken, intent=intents[0], intents=intents))

    if _hits(blob, STATE) and not _has(graph, "EventLog"):
        spoken = (
            "State management. Keep widget state local. "
            "Want a session store, an event log, and a projection cache — "
            "the same fold-the-log idea as Redux or event sourcing?"
        )
        intents = [
            _nodes(
                ("Resource", "SessionStore", {"purpose": "auth and theme only"}),
                ("Database", "EventLog", {"purpose": "what happened"}),
                ("Database", "Projection", {"purpose": "what we show"}),
                ("Function", "Fold", {"purpose": "event plus state becomes next state"}),
            )
        ]
        out.append(Suggestion(code="scene_state", spoken=spoken, intent=intents[0], intents=intents))

    if _hits(blob, CLI) and not _has(graph, "Commands"):
        spoken = (
            "Command-line tool. Add a commands node, config file store, and a logger?"
        )
        intents = [
            _nodes(
                ("Function", "Commands", {"purpose": "cli verbs"}),
                ("Database", "Config", {"engine": "file", "purpose": "flags and profile"}),
                ("Service", "Logger", {"purpose": "stderr and files"}),
            )
        ]
        out.append(Suggestion(code="scene_cli", spoken=spoken, intent=intents[0], intents=intents))

    if _hits(blob, GAME) and not _has(graph, "GameLoop"):
        spoken = (
            "Game shape. Want a game loop, player save, levels, and an asset store?"
        )
        intents = [
            _nodes(
                ("Service", "GameLoop", {"purpose": "tick"}),
                ("Page", "Player", {"purpose": "avatar"}),
                ("Database", "Saves", {"purpose": "progress"}),
                ("Database", "AssetStore", {"purpose": "sprites and audio"}),
                ("Function", "Levels", {"purpose": "worlds"}),
            ),
            _secure("Player", "Saves"),
        ]
        out.append(Suggestion(code="scene_game", spoken=spoken, intent=intents[0], intents=intents))

    if _hits(blob, PIPELINE) and not _has(graph, "Ingest"):
        spoken = (
            "This is a data pipeline. "
            "I can add ingest, a transform function, a warehouse, and a quality check."
        )
        intents = [
            _nodes(
                ("Service", "Ingest", {"purpose": "arrive"}),
                ("Function", "Transform", {"purpose": "clean"}),
                ("Database", "Warehouse", {"engine": "column", "purpose": "facts"}),
                ("Function", "QualityCheck", {"purpose": "do not ship bad rows"}),
            )
        ]
        out.append(Suggestion(code="scene_pipeline", spoken=spoken, intent=intents[0], intents=intents))

    if _hits(blob, ML) and not _has(graph, "Inference"):
        spoken = (
            "ML product. Want a dataset, a training job, a model registry, and an inference service?"
        )
        intents = [
            _nodes(
                ("Database", "Dataset", {"purpose": "examples"}),
                ("Function", "Train", {"purpose": "fit"}),
                ("Database", "ModelRegistry", {"purpose": "versions"}),
                ("Service", "Inference", {"purpose": "serve predictions"}),
            )
        ]
        out.append(Suggestion(code="scene_ml", spoken=spoken, intent=intents[0], intents=intents))

    if _hits(blob, BOT) and not _has(graph, "Bot"):
        spoken = (
            "Chat bot. Add a bot service, command functions, and a secure user store?"
        )
        intents = [
            _nodes(
                ("Service", "Bot", {"purpose": "talks in chat"}),
                ("Function", "BotCommands", {"purpose": "slash commands"}),
                ("Database", "ChatUsers", {"purpose": "who is who"}),
            ),
            _secure("Bot", "ChatUsers"),
        ]
        out.append(Suggestion(code="scene_bot", spoken=spoken, intent=intents[0], intents=intents))

    if _hits(blob, IOT) and not _has(graph, "DeviceTwin"):
        spoken = (
            "IoT. Want device twins, a telemetry store, firmware updates, and a live dashboard?"
        )
        intents = [
            _nodes(
                ("Service", "DeviceTwin", {"purpose": "each device"}),
                ("Database", "Telemetry", {"purpose": "sensor stream"}),
                ("Function", "Firmware", {"purpose": "updates"}),
                ("Page", "LiveDash", {"purpose": "operators"}),
            )
        ]
        out.append(Suggestion(code="scene_iot", spoken=spoken, intent=intents[0], intents=intents))

    if _hits(blob, LIBRARY) and not _has(graph, "PublicAPI"):
        spoken = (
            "This is a library. Add a public API surface, tests, and package metadata?"
        )
        intents = [
            _nodes(
                ("Function", "PublicAPI", {"purpose": "what callers see"}),
                ("Function", "Tests", {"purpose": "do not break callers"}),
                ("Resource", "PackageMeta", {"purpose": "version and license"}),
            )
        ]
        out.append(Suggestion(code="scene_library", spoken=spoken, intent=intents[0], intents=intents))

    if _hits(blob, PLUGIN) and not _has(graph, "HostAPI"):
        spoken = (
            "Plugin or extension. I can add a host API, a settings page, and sandboxed storage."
        )
        intents = [
            _nodes(
                ("Service", "HostAPI", {"purpose": "talk to the host"}),
                ("Page", "PluginSettings", {"purpose": "options"}),
                ("Database", "SandboxStore", {"purpose": "extension data"}),
            )
        ]
        out.append(Suggestion(code="scene_plugin", spoken=spoken, intent=intents[0], intents=intents))

    if _hits(blob, SOFTWARE) and not _has(graph, "AppCore") and not _hits(blob, MOBILE + DESKTOP + API):
        spoken = (
            "You're building software, not just pages. "
            "Want an app core, a module loader, user prefs, and a crash log?"
        )
        intents = [
            _nodes(
                ("Service", "AppCore", {"purpose": "runtime"}),
                ("Function", "Modules", {"purpose": "load features"}),
                ("Database", "Prefs", {"purpose": "user choices"}),
                ("Service", "CrashLog", {"purpose": "what broke"}),
            )
        ]
        out.append(Suggestion(code="scene_software", spoken=spoken, intent=intents[0], intents=intents))

    if _hits(blob, SAAS) and not _has(graph, "Users"):
        spoken = (
            "This is starting to feel like an app. "
            "Add users, a secure settings page, and an audit log?"
        )
        intents = [
            _nodes(
                ("Database", "Users", {"purpose": "accounts"}),
                ("Page", "Settings", {"purpose": "secure account settings"}),
                ("Page", "Audit", {"purpose": "who changed what"}),
            ),
            _secure("Settings", "Users"),
        ]
        out.append(Suggestion(code="scene_saas", spoken=spoken, intent=intents[0], intents=intents))

    pages = [n for n in graph.nodes.values() if n.label == "Page"]
    dbs = [n for n in graph.nodes.values() if n.label == "Database"]
    if pages and not dbs and not out:
        spoken = (
            f"You have {len(pages)} pages and nowhere to put data. "
            "Want a MainDB and a secure path from the first page?"
        )
        first = _name(pages[0])
        intents = [_nodes(("Database", "MainDB", {"engine": "neo4j"})), _secure(first, "MainDB")]
        out.append(Suggestion(code="scene_needs_db", spoken=spoken, intent=intents[0], intents=intents, page=first))

    return out


def line_suggestions(graph: InMemoryGraph) -> list[Suggestion]:
    pages = [n for n in graph.nodes.values() if n.label == "Page"]
    dbs = [n for n in graph.nodes.values() if n.label == "Database"]
    includes = [n for n in graph.nodes.values() if n.label == "Include"]
    default_db = dbs[0] if dbs else None
    suggestions: list[Suggestion] = []

    def has_rel(src_id: str, typ: str) -> bool:
        return any(r.src == src_id and r.type == typ for r in graph.rels)

    def connect_rel(src_id):
        for r in graph.rels:
            if r.src == src_id and r.type == "CONNECTS_TO":
                return r
        return None

    for page in pages:
        pname = _name(page)
        conn = connect_rel(page.id)
        authed = has_rel(page.id, "AUTHENTICATES_WITH")
        db_name = _name(default_db) if default_db else "MainDB"
        db_ref = Ref(label="Database", name=str(db_name), id=default_db.id if default_db else None)
        auth_ref = Ref(label="Auth", name="SecureJWT", props={"method": "jwt", "level": "secure", "requires_https": True})
        page_ref = Ref(label="Page", name=pname, id=page.id)

        if conn is None and _wants_secure(page):
            intent = Intent(action="connect_with_auth", source=page_ref, target=db_ref, auth=auth_ref, raw=f"secure handshake for {pname}")
            suggestions.append(Suggestion(
                code="missing_secure_path",
                page=pname,
                spoken=f"{pname} looks like it should be secure, but it has no path to {db_name}. Want me to draw a secure handshake?",
                intent=intent,
            ))
            continue
        if conn is None:
            intent = Intent(action="connect", source=page_ref, target=db_ref, raw=f"connect {pname} to {db_name}")
            suggestions.append(Suggestion(
                code="missing_db_line",
                page=pname,
                spoken=f"{pname} has no database line. I can connect it to {db_name}. Should I?",
                intent=intent,
            ))
            continue
        if conn and (conn.props.get("secure") or _wants_secure(page)) and not authed:
            intent = Intent(action="connect_with_auth", source=page_ref, target=db_ref, auth=auth_ref, raw=f"add secure auth to {pname}")
            suggestions.append(Suggestion(
                code="secure_without_auth",
                page=pname,
                spoken=f"{pname} has a connection, but no auth line. That is not a secure path. Want me to add SecureJWT?",
                intent=intent,
            ))
        page_includes = [r for r in graph.rels if r.src == page.id and r.type == "INCLUDES"]
        if not page_includes and includes:
            intent = _include(pname, *[_name(i) for i in includes[:2]])
            suggestions.append(Suggestion(
                code="missing_includes",
                page=pname,
                spoken=f"{pname} has no includes. Attach Header and Footer?",
                intent=intent,
            ))
    return suggestions


def advise(graph: InMemoryGraph, extra: str = "") -> list[Suggestion]:
    scenes = scene_suggestions(graph, extra)
    lines = line_suggestions(graph)
    # Scene offers first — they feel like a collaborator, not a linter.
    return scenes + lines


def accept_phrase(text: str) -> bool:
    lowered = text.strip().lower()
    needles = (
        "yes",
        "yeah",
        "yep",
        "ok",
        "okay",
        "do it",
        "do that",
        "fix it",
        "make it right",
        "make it secure",
        "draw it",
        "draw the handshake",
        "go ahead",
        "sure",
        "please do",
        "add those",
        "add them",
        "build that",
        "build it",
        "do the storefront",
        "do the fan site",
        "add the forum",
    )
    return any(n == lowered or n in lowered for n in needles)
