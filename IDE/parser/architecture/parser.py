"""GraphLang intent parser.

Speech -> structured Intent -> Cypher templates.

This first implementation is deterministic (rules + light NLP), so the
approved sentences compile the same way every time. An LLM can later
emit the same Intent objects for freer speech.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any


def slug(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "unnamed"


def stable_id(label: str, name: str) -> str:
    prefix = {
        "Page": "page",
        "Database": "db",
        "Auth": "auth",
        "Include": "inc",
        "Function": "fn",
        "Service": "svc",
    }.get(label, label.lower())
    return f"{prefix}_{slug(name)}"


@dataclass
class Ref:
    label: str
    name: str
    id: str | None = None
    props: dict[str, Any] = field(default_factory=dict)

    def resolved_id(self) -> str:
        return self.id or stable_id(self.label, self.name)


@dataclass
class Intent:
    action: str
    source: Ref | None = None
    target: Ref | None = None
    auth: Ref | None = None
    includes: list[Ref] = field(default_factory=list)
    nodes: list[Ref] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    create_missing: bool = True
    raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data


@dataclass
class ConversationContext:
    last_database: str | None = None
    last_page: str | None = None
    last_auth: str | None = None
    last_node: tuple[str, str] | None = None
    pages: list[str] = field(default_factory=list)
    databases: list[str] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)
    auths: list[str] = field(default_factory=list)

    def remember_page(self, name: str) -> None:
        if name not in self.pages:
            self.pages.append(name)
        self.last_page = name
        self.last_node = ("Page", name)

    def remember_db(self, name: str) -> None:
        if name not in self.databases:
            self.databases.append(name)
        self.last_database = name
        self.last_node = ("Database", name)

    def remember_include(self, name: str) -> None:
        if name not in self.includes:
            self.includes.append(name)
        self.last_node = ("Include", name)

    def remember_auth(self, name: str) -> None:
        if name not in self.auths:
            self.auths.append(name)
        self.last_auth = name
        self.last_node = ("Auth", name)

    def remember_node(self, label: str, name: str) -> None:
        self.last_node = (label, name)
        if label == "Page":
            self.remember_page(name)
        elif label == "Database":
            self.remember_db(name)
        elif label == "Include":
            self.remember_include(name)
        elif label == "Auth":
            self.last_auth = name
            if name not in self.auths:
                self.auths.append(name)


NUMBER_WORDS = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "a couple": 2,
    "couple": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}

DEFAULT_PAGE_NAMES = ["Landing", "Dashboard", "Settings", "Profile", "Home"]
DEFAULT_INCLUDE_NAMES = ["Header", "Footer", "Sidebar", "Nav", "Scripts"]

PAGE_ALIASES = {
    "landing": "Landing",
    "landing page": "Landing",
    "home": "Home",
    "home page": "Home",
    "dashboard": "Dashboard",
    "settings": "Settings",
    "profile": "Profile",
}

AUTH_METHODS = {
    "jwt": "jwt",
    "json web token": "jwt",
    "session": "session",
    "session-based": "session",
    "oauth": "oauth2",
    "oauth2": "oauth2",
    "api key": "api_key",
    "api_key": "api_key",
}


class IntentParser:
    def __init__(self, context: ConversationContext | None = None):
        self.context = context or ConversationContext()

    def parse(self, text: str) -> list[Intent]:
        raw = text.strip()
        if not raw:
            return []

        # Split on sentence boundaries but keep related clauses together
        chunks = self._split_commands(raw)
        intents: list[Intent] = []
        for chunk in chunks:
            intents.extend(self._parse_chunk(chunk))
        return intents

    def parse_all(self, text: str) -> list[Intent]:
        return self.parse(text)

    def _split_commands(self, text: str) -> list[str]:
        parts = re.split(r"(?<=[.!?])\s+|(?<=;)\s+", text)
        return [p.strip() for p in parts if p.strip()]

    def _parse_chunk(self, text: str) -> list[Intent]:
        lowered = text.lower().strip()

        if self._is_query(lowered):
            return [self._parse_query(text, lowered)]

        if self._is_disconnect(lowered):
            return [self._parse_disconnect(text, lowered)]

        intents: list[Intent] = []

        create = self._parse_create(text, lowered)
        if create:
            intents.append(create)

        purpose = self._parse_purpose(text, lowered)
        if purpose:
            intents.append(purpose)

        connect = self._parse_connect(text, lowered)
        if connect and not (purpose and purpose.action.startswith("connect")):
            intents.append(connect)

        include = self._parse_include(text, lowered)
        if include:
            intents.append(include)

        if not intents:
            intents.append(
                Intent(
                    action="unknown",
                    raw=text,
                    create_missing=True,
                )
            )
        else:
            for intent in intents:
                intent.raw = text
        return intents

    def _is_query(self, lowered: str) -> bool:
        return bool(
            re.search(
                r"\b(show|list|what|which|who|inspect|impact|break|connected to)\b",
                lowered,
            )
            and not re.search(r"\b(connect|create|add|make|need|include)\b", lowered)
        )

    def _is_disconnect(self, lowered: str) -> bool:
        return bool(re.search(r"\b(remove|delete|disconnect|drop the connection)\b", lowered))

    def _parse_create(self, text: str, lowered: str) -> Intent | None:
        wants_create = bool(
            re.search(r"\b(i need|create|add|make me|set up|setup)\b", lowered)
        )
        if not wants_create:
            return None

        nodes: list[Ref] = []

        db_name = self._extract_named(text, r"(?:database|db) called ([A-Za-z0-9_ -]+)")
        if re.search(r"\b(a db|a database|database|db)\b", lowered):
            name = db_name or self.context.last_database or "MainDB"
            engine = "postgres" if "postgres" in lowered else "neo4j"
            if "sqlite" in lowered:
                engine = "sqlite"
            ref = Ref(label="Database", name=name, props={"engine": engine})
            nodes.append(ref)
            self.context.remember_db(name)

        page_count = self._extract_count(lowered, r"(\d+|a|an|one|two|three|four|five) pages?")
        named_pages = self._extract_page_names(text)
        named_explicit = bool(re.search(r"\b(?:page|node)\s+(?:called|named)\b", lowered))
        if (page_count or named_pages or re.search(r"\blanding page\b", lowered)) and not named_explicit:
            names = named_pages
            if not names:
                count = page_count or (1 if "landing page" in lowered else 0)
                if "landing" in lowered and count:
                    names = ["Landing"] + [
                        n for n in DEFAULT_PAGE_NAMES if n != "Landing"
                    ][: max(count - 1, 0)]
                else:
                    names = DEFAULT_PAGE_NAMES[:count]
            for name in names:
                path = "/" if name.lower() in {"landing", "home"} else f"/{slug(name)}"
                nodes.append(Ref(label="Page", name=name, props={"path": path}))
                self.context.remember_page(name)

        include_count = self._extract_count(
            lowered, r"(a couple(?: of)?|two|three|four|five|\d+) includes?"
        )
        named_includes = self._extract_include_names(text)
        if include_count or named_includes or re.search(r"\bincludes?\b", lowered) and wants_create:
            names = named_includes or DEFAULT_INCLUDE_NAMES[: (include_count or 2)]
            for name in names:
                nodes.append(Ref(label="Include", name=name))
                self.context.remember_include(name)

        if re.search(r"\bsecure(?: jwt)? auth\b|\bjwt auth\b|\bauth named\b", lowered):
            method = self._extract_auth_method(lowered) or "jwt"
            level = "secure" if "secure" in lowered else "basic"
            name = f"{level.title()}{method.upper() if method != 'jwt' else 'JWT'}"
            if method == "jwt" and level == "secure":
                name = "SecureJWT"
            nodes.append(
                Ref(
                    label="Auth",
                    name=name,
                    props={
                        "method": method,
                        "level": level,
                        "requires_https": level == "secure",
                    },
                )
            )
            self.context.remember_auth(name)

        generic = re.search(
            r"\b(?:add|create|make)\s+(?:a\s+)?(?:new\s+)?(?P<label>node|page|database|db|include|auth|function|service|module)?\s*(?:called|named)?\s+(?P<name>[A-Za-z][A-Za-z0-9_\- ]{0,40})?",
            text,
            flags=re.I,
        )
        if generic and generic.group("name"):
            raw_label = (generic.group("label") or "node").lower()
            label_map = {
                "node": "Resource",
                "page": "Page",
                "database": "Database",
                "db": "Database",
                "include": "Include",
                "auth": "Auth",
                "function": "Function",
                "service": "Service",
                "module": "Resource",
            }
            label = label_map.get(raw_label, "Resource")
            name = generic.group("name").strip(" .,")
            name = re.split(r"\b(?:for|to|that|which)\b", name, maxsplit=1)[0].strip().title().replace(" ", "")
            if name and not any(n.name.lower() == name.lower() for n in nodes):
                nodes.append(Ref(label=label, name=name, props={"purpose": None}))
                self.context.remember_node(label, name)

        if not nodes:
            return None

        return Intent(action="create_node", nodes=nodes, raw=text)

    def _parse_purpose(self, text: str, lowered: str) -> Intent | None:
        match = re.search(
            r"\b(?:it(?:'s| is)|that(?:'s| is)|this is|use it to|for)\b\s+(?P<why>.+)$",
            text.strip(),
            flags=re.I,
        )
        if not match:
            return None
        if re.search(r"\b(i need|create|add a db|three pages)\b", lowered):
            why = match.group("why").strip()
            if len(why.split()) < 2 and "for" in lowered and "auth" not in lowered:
                return None
        why = match.group("why").strip(" .")
        target = None
        if self.context.last_node:
            label, name = self.context.last_node
            target = Ref(label=label, name=name, props={"purpose": why})
        else:
            target = Ref(label="Resource", name="LastNode", props={"purpose": why})
        intent = Intent(action="set_purpose", target=target, raw=why, create_missing=True)
        # If they explained a handshake, also connect last page-like node to the db.
        if self.context.last_node and re.search(r"\b(auth|handshake|database|db|connect|talk)\b", why.lower()):
            label, name = self.context.last_node
            source = Ref(label=label if label != "Database" else "Page", name=name)
            db = Ref(label="Database", name=self.context.last_database or "MainDB")
            method = self._extract_auth_method(why.lower()) or "jwt"
            secure = "public" not in why.lower() and "no auth" not in why.lower()
            if label in {"Page", "Service", "Function", "Resource"}:
                intent = Intent(
                    action="connect_with_auth" if secure else "connect",
                    source=source if source.label == "Page" else Ref(label="Page", name=name),
                    target=db,
                    auth=Ref(label="Auth", name="SecureJWT", props={"method": method, "level": "secure", "purpose": why}) if secure else None,
                    raw=why,
                )
        return intent

    def _parse_connect(self, text: str, lowered: str) -> Intent | None:
        if not re.search(r"\b(connect|draw a line|handshake|link)\b", lowered):
            return None

        page = self._resolve_page(text, lowered)
        database = self._resolve_database(text, lowered)
        all_pages = bool(re.search(r"\ball pages\b", lowered))

        wants_auth = bool(re.search(r"\b(auth|secure|jwt|session|oauth)\b", lowered))
        method = self._extract_auth_method(lowered) or ("jwt" if wants_auth else None)
        level = "secure" if "secure" in lowered else ("basic" if wants_auth else None)

        auth = None
        if wants_auth:
            auth_name = self.context.last_auth
            if not auth_name:
                auth_name = "SecureJWT" if level == "secure" else "Auth"
            auth = Ref(
                label="Auth",
                name=auth_name,
                props={
                    "method": method or "jwt",
                    "level": level or "secure",
                    "requires_https": (level or "secure") == "secure",
                },
            )
            self.context.remember_auth(auth_name)

        source = None if all_pages else Ref(label="Page", name=page or self.context.last_page or "Landing")
        if source:
            self.context.remember_page(source.name)

        target = Ref(label="Database", name=database or self.context.last_database or "MainDB")
        self.context.remember_db(target.name)

        action = "connect_with_auth" if wants_auth else "connect"
        if all_pages:
            action = "connect_all_with_auth" if wants_auth else "connect_all"

        return Intent(
            action=action,
            source=source,
            target=target,
            auth=auth,
            roles=[],
            create_missing=True,
            raw=text,
        )

    def _parse_include(self, text: str, lowered: str) -> Intent | None:
        if not re.search(r"\binclude[s]?\b", lowered):
            return None
        # "I need ... includes" is creation, not an INCLUDES relationship
        if re.search(r"\b(i need|create|add)\b", lowered) and not re.search(
            r"\b(make|should also include|include header|include footer)\b", lowered
        ):
            return None

        include_names = self._extract_include_names(text) or list(self.context.includes[:2]) or ["Header", "Footer"]
        includes = [Ref(label="Include", name=name) for name in include_names]
        for name in include_names:
            self.context.remember_include(name)

        all_pages = bool(re.search(r"\b(all pages|every page)\b", lowered))
        page = None if all_pages else self._resolve_page(text, lowered)

        return Intent(
            action="include_all" if all_pages else "include",
            source=None if all_pages else Ref(label="Page", name=page or self.context.last_page or "Landing"),
            includes=includes,
            create_missing=True,
            raw=text,
        )

    def _parse_query(self, text: str, lowered: str) -> Intent:
        if re.search(r"\b(break|impact|delete header|delete footer)\b", lowered):
            name = self._extract_named(lowered, r"delete ([a-z0-9_ -]+)") or "Header"
            label = "Include" if name.lower() in {n.lower() for n in self.context.includes + DEFAULT_INCLUDE_NAMES} else "Page"
            return Intent(action="impact", target=Ref(label=label, name=name.title()), raw=text)

        if re.search(r"\bwhat auth\b|\bwhich auth\b", lowered):
            page = self._resolve_page(text, lowered) or self.context.last_page or "Landing"
            return Intent(action="query_auth", source=Ref(label="Page", name=page), raw=text)

        if re.search(r"\bno database connection\b|\bwithout a database\b", lowered):
            return Intent(action="lint", raw=text)

        db = self._resolve_database(text, lowered) or self.context.last_database or "MainDB"
        return Intent(
            action="query_neighbors",
            target=Ref(label="Database", name=db),
            raw=text,
        )

    def _parse_disconnect(self, text: str, lowered: str) -> Intent:
        page = self._resolve_page(text, lowered) or self.context.last_page or "Settings"
        db = self._resolve_database(text, lowered) or self.context.last_database or "MainDB"
        only_auth = bool(re.search(r"\bauth\b", lowered) and re.search(r"\bkeep\b", lowered))
        return Intent(
            action="disconnect_auth" if only_auth else "disconnect",
            source=Ref(label="Page", name=page),
            target=Ref(label="Database", name=db),
            raw=text,
        )

    def _extract_count(self, lowered: str, pattern: str) -> int | None:
        match = re.search(pattern, lowered)
        if not match:
            return None
        token = match.group(1) if match.lastindex else match.group(0)
        if token.isdigit():
            return int(token)
        if "couple" in token:
            return 2
        return NUMBER_WORDS.get(token)

    def _extract_named(self, text: str, pattern: str) -> str | None:
        match = re.search(pattern, text, flags=re.I)
        if not match:
            return None
        token = match.group(1).strip(" .,")
        if token.isupper() or any(c.isupper() for c in token[1:]):
            return token.replace(" ", "")
        return token.title().replace(" ", "")

    def _extract_page_names(self, text: str) -> list[str]:
        found: list[str] = []
        lowered = text.lower()
        for alias, name in PAGE_ALIASES.items():
            if re.search(rf"\b{re.escape(alias)}\b", lowered) and name not in found:
                found.append(name)
        parenthetical = re.search(r"pages?\s*\(([^)]+)\)", text, re.I)
        if parenthetical:
            for part in parenthetical.group(1).split(","):
                name = part.strip().title()
                if name and name not in found:
                    found.append(name)
        return found

    def _extract_include_names(self, text: str) -> list[str]:
        found: list[str] = []
        for name in DEFAULT_INCLUDE_NAMES:
            if re.search(rf"\b{name.lower()}\b", text.lower()):
                found.append(name)
        parenthetical = re.search(r"includes?\s*\(([^)]+)\)", text, re.I)
        if parenthetical:
            for part in parenthetical.group(1).split(","):
                name = part.strip().title()
                if name and name not in found:
                    found.append(name)
        return found

    def _extract_auth_method(self, lowered: str) -> str | None:
        for phrase, method in AUTH_METHODS.items():
            if phrase in lowered:
                return method
        return None

    def _resolve_page(self, text: str, lowered: str) -> str | None:
        names = self._extract_page_names(text)
        if names:
            return names[0]
        if "last" in lowered and self.context.last_page:
            return self.context.last_page
        return None

    def _resolve_database(self, text: str, lowered: str) -> str | None:
        called = self._extract_named(text, r"(?:database|db) called ([A-Za-z0-9_-]+)")
        if called:
            return called
        explicit = re.search(r"\b(maindb|[a-z0-9_]*db)\b", lowered.replace("-", ""))
        if explicit and explicit.group(1) not in {"db", "thedb"}:
            raw = explicit.group(1)
            return "MainDB" if raw == "maindb" else raw.replace("_", " ").title().replace(" ", "")
        if re.search(r"\b(the db|the database|\bdb\b|\bdatabase\b)\b", lowered):
            return self.context.last_database or (self.context.databases[0] if self.context.databases else "MainDB")
        return None


class CypherCompiler:
    def compile(self, intents: list[Intent]) -> list[dict[str, Any]]:
        statements = []
        for intent in intents:
            statements.extend(self.compile_one(intent))
        return statements

    def compile_one(self, intent: Intent) -> list[dict[str, Any]]:
        action = intent.action
        if action == "create_node":
            return [self._create_node(node) for node in intent.nodes]
        if action == "set_purpose":
            target = intent.target or Ref(label="Resource", name="LastNode")
            return [
                {
                    "action": "set_purpose",
                    "cypher": """
MERGE (n {id: $id})
ON CREATE SET n.name = $name, n.purpose = $purpose, n.created_at = datetime()
ON MATCH SET n.purpose = $purpose
RETURN n
""".strip(),
                    "params": {
                        "id": target.resolved_id(),
                        "name": target.name,
                        "purpose": (target.props or {}).get("purpose") or intent.raw,
                    },
                }
            ]
        if action == "connect":
            return [self._connect(intent, with_auth=False)]
        if action == "connect_with_auth":
            return [self._connect(intent, with_auth=True)]
        if action == "connect_all":
            return [self._connect_all(intent, with_auth=False)]
        if action == "connect_all_with_auth":
            return [self._connect_all(intent, with_auth=True)]
        if action == "include":
            return [self._include(intent, all_pages=False)]
        if action == "include_all":
            return [self._include(intent, all_pages=True)]
        if action == "query_neighbors":
            return [self._query_neighbors(intent)]
        if action == "query_auth":
            return [self._query_auth(intent)]
        if action == "impact":
            return [self._impact(intent)]
        if action == "lint":
            return [self._lint()]
        if action == "disconnect":
            return [self._disconnect(intent)]
        if action == "disconnect_auth":
            return [self._disconnect_auth(intent)]
        return [
            {
                "action": "unknown",
                "cypher": None,
                "params": {},
                "note": f"No template for: {intent.raw}",
            }
        ]

    def _create_node(self, node: Ref) -> dict[str, Any]:
        node_id = node.resolved_id()
        if node.label == "Page":
            return {
                "action": "create_node",
                "cypher": """
MERGE (p:Page {id: $id})
ON CREATE SET p.name = $name, p.path = $path, p.type = $type, p.created_at = datetime()
ON MATCH SET p.name = coalesce($name, p.name), p.path = coalesce($path, p.path)
RETURN p
""".strip(),
                "params": {
                    "id": node_id,
                    "name": node.name,
                    "path": node.props.get("path"),
                    "type": node.props.get("type"),
                },
            }
        if node.label == "Database":
            return {
                "action": "create_node",
                "cypher": """
MERGE (d:Database {id: $id})
ON CREATE SET d.name = $name, d.engine = $engine, d.host = $host, d.port = $port, d.created_at = datetime()
ON MATCH SET d.name = coalesce($name, d.name), d.engine = coalesce($engine, d.engine)
RETURN d
""".strip(),
                "params": {
                    "id": node_id,
                    "name": node.name,
                    "engine": node.props.get("engine", "neo4j"),
                    "host": node.props.get("host"),
                    "port": node.props.get("port"),
                },
            }
        if node.label == "Auth":
            return {
                "action": "create_node",
                "cypher": """
MERGE (a:Auth {id: $id})
ON CREATE SET a.name = $name, a.method = $method, a.level = $level,
  a.token_expiry = $token_expiry, a.requires_https = $requires_https, a.created_at = datetime()
ON MATCH SET a.method = coalesce($method, a.method), a.level = coalesce($level, a.level)
RETURN a
""".strip(),
                "params": {
                    "id": node_id,
                    "name": node.name,
                    "method": node.props.get("method", "jwt"),
                    "level": node.props.get("level", "secure"),
                    "token_expiry": node.props.get("token_expiry"),
                    "requires_https": node.props.get("requires_https", True),
                },
            }
        return {
            "action": "create_node",
            "cypher": """
MERGE (i:Include {id: $id})
ON CREATE SET i.name = $name, i.path = $path, i.created_at = datetime()
ON MATCH SET i.name = coalesce($name, i.name)
RETURN i
""".strip(),
            "params": {
                "id": node_id,
                "name": node.name,
                "path": node.props.get("path"),
            },
        }

    def _connect(self, intent: Intent, with_auth: bool) -> dict[str, Any]:
        page = intent.source or Ref(label="Page", name="Landing")
        db = intent.target or Ref(label="Database", name="MainDB")
        auth = intent.auth or Ref(
            label="Auth",
            name="SecureJWT",
            props={"method": "jwt", "level": "secure", "requires_https": True},
        )
        if with_auth:
            return {
                "action": "connect_with_auth",
                "cypher": """
MERGE (p:Page {id: $page_id})
ON CREATE SET p.name = $page_name, p.path = $page_path, p.created_at = datetime()
MERGE (d:Database {id: $db_id})
ON CREATE SET d.name = $db_name, d.engine = $engine, d.created_at = datetime()
MERGE (a:Auth {id: $auth_id})
ON CREATE SET a.name = $auth_name, a.method = $auth_method, a.level = $auth_level,
  a.requires_https = $requires_https, a.created_at = datetime()
MERGE (p)-[c:CONNECTS_TO]->(d)
ON CREATE SET c.secure = $secure, c.auth_method = $auth_method, c.created_at = datetime()
ON MATCH SET c.secure = $secure, c.auth_method = $auth_method
MERGE (p)-[ar:AUTHENTICATES_WITH]->(a)
ON CREATE SET ar.required = true, ar.roles = $roles, ar.created_at = datetime()
RETURN p, d, a, c, ar
""".strip(),
                "params": {
                    "page_id": page.resolved_id(),
                    "page_name": page.name,
                    "page_path": page.props.get("path") or ("/" if page.name.lower() in {"landing", "home"} else f"/{slug(page.name)}"),
                    "db_id": db.resolved_id(),
                    "db_name": db.name,
                    "engine": db.props.get("engine", "neo4j"),
                    "auth_id": auth.resolved_id(),
                    "auth_name": auth.name,
                    "auth_method": auth.props.get("method", "jwt"),
                    "auth_level": auth.props.get("level", "secure"),
                    "requires_https": auth.props.get("requires_https", True),
                    "secure": True,
                    "roles": intent.roles,
                },
            }
        return {
            "action": "connect",
            "cypher": """
MERGE (p:Page {id: $page_id})
ON CREATE SET p.name = $page_name, p.created_at = datetime()
MERGE (d:Database {id: $db_id})
ON CREATE SET d.name = $db_name, d.created_at = datetime()
MERGE (p)-[c:CONNECTS_TO]->(d)
ON CREATE SET c.secure = $secure, c.created_at = datetime()
RETURN p, c, d
""".strip(),
            "params": {
                "page_id": page.resolved_id(),
                "page_name": page.name,
                "db_id": db.resolved_id(),
                "db_name": db.name,
                "secure": False,
            },
        }

    def _connect_all(self, intent: Intent, with_auth: bool) -> dict[str, Any]:
        db = intent.target or Ref(label="Database", name="MainDB")
        auth = intent.auth
        if with_auth:
            return {
                "action": "connect_all_with_auth",
                "cypher": """
MATCH (p:Page)
MERGE (d:Database {id: $db_id})
ON CREATE SET d.name = $db_name, d.created_at = datetime()
MERGE (a:Auth {id: $auth_id})
ON CREATE SET a.name = $auth_name, a.method = $auth_method, a.level = $auth_level,
  a.requires_https = $requires_https, a.created_at = datetime()
MERGE (p)-[c:CONNECTS_TO]->(d)
ON CREATE SET c.secure = true, c.auth_method = $auth_method, c.created_at = datetime()
MERGE (p)-[ar:AUTHENTICATES_WITH]->(a)
ON CREATE SET ar.required = true, ar.created_at = datetime()
RETURN p, d, a
""".strip(),
                "params": {
                    "db_id": db.resolved_id(),
                    "db_name": db.name,
                    "auth_id": (auth or Ref(label="Auth", name="SecureJWT")).resolved_id(),
                    "auth_name": (auth.name if auth else "SecureJWT"),
                    "auth_method": (auth.props.get("method") if auth else "jwt"),
                    "auth_level": (auth.props.get("level") if auth else "secure"),
                    "requires_https": True,
                },
            }
        return {
            "action": "connect_all",
            "cypher": """
MATCH (p:Page)
MERGE (d:Database {id: $db_id})
ON CREATE SET d.name = $db_name, d.created_at = datetime()
MERGE (p)-[c:CONNECTS_TO]->(d)
ON CREATE SET c.created_at = datetime()
RETURN p, d
""".strip(),
            "params": {"db_id": db.resolved_id(), "db_name": db.name},
        }

    def _include(self, intent: Intent, all_pages: bool) -> dict[str, Any]:
        include_ids = [inc.resolved_id() for inc in intent.includes]
        include_names = [inc.name for inc in intent.includes]
        if all_pages:
            return {
                "action": "include_all",
                "cypher": """
UNWIND $includes AS inc
MERGE (i:Include {id: inc.id})
ON CREATE SET i.name = inc.name, i.created_at = datetime()
WITH i, inc
MATCH (p:Page)
MERGE (p)-[r:INCLUDES]->(i)
ON CREATE SET r.order = inc.order, r.created_at = datetime()
RETURN p, i, r
""".strip(),
                "params": {
                    "includes": [
                        {"id": i, "name": n, "order": idx}
                        for idx, (i, n) in enumerate(zip(include_ids, include_names))
                    ]
                },
            }
        page = intent.source or Ref(label="Page", name="Landing")
        return {
            "action": "include",
            "cypher": """
MERGE (p:Page {id: $page_id})
ON CREATE SET p.name = $page_name, p.created_at = datetime()
WITH p
UNWIND $includes AS inc
MERGE (i:Include {id: inc.id})
ON CREATE SET i.name = inc.name, i.created_at = datetime()
MERGE (p)-[r:INCLUDES]->(i)
ON CREATE SET r.order = inc.order, r.created_at = datetime()
RETURN p, i, r
""".strip(),
            "params": {
                "page_id": page.resolved_id(),
                "page_name": page.name,
                "includes": [
                    {"id": i, "name": n, "order": idx}
                    for idx, (i, n) in enumerate(zip(include_ids, include_names))
                ],
            },
        }

    def _query_neighbors(self, intent: Intent) -> dict[str, Any]:
        db = intent.target or Ref(label="Database", name="MainDB")
        return {
            "action": "query_neighbors",
            "cypher": """
MATCH (n)-[r:CONNECTS_TO]->(d:Database)
WHERE d.id = $db_id OR toLower(d.name) = toLower($db_name)
OPTIONAL MATCH (n)-[a:AUTHENTICATES_WITH]->(auth:Auth)
OPTIONAL MATCH (n)-[i:INCLUDES]->(inc:Include)
RETURN n, r, d, a, auth, i, inc
""".strip(),
            "params": {"db_id": db.resolved_id(), "db_name": db.name},
        }

    def _query_auth(self, intent: Intent) -> dict[str, Any]:
        page = intent.source or Ref(label="Page", name="Landing")
        return {
            "action": "query_auth",
            "cypher": """
MATCH (p:Page)
WHERE p.id = $page_id OR toLower(p.name) = toLower($page_name)
OPTIONAL MATCH (p)-[:AUTHENTICATES_WITH]->(a:Auth)
RETURN p.name AS page, collect(a {.*}) AS auth
""".strip(),
            "params": {"page_id": page.resolved_id(), "page_name": page.name},
        }

    def _impact(self, intent: Intent) -> dict[str, Any]:
        target = intent.target or Ref(label="Include", name="Header")
        return {
            "action": "impact",
            "cypher": """
MATCH (target)
WHERE target.id = $id OR toLower(target.name) = toLower($name)
OPTIONAL MATCH (src)-[r]->(target)
OPTIONAL MATCH (target)-[r2]->(dst)
RETURN target,
       collect(DISTINCT {from: src.name, rel: type(r)}) AS inbound,
       collect(DISTINCT {to: dst.name, rel: type(r2)}) AS outbound
""".strip(),
            "params": {"id": target.resolved_id(), "name": target.name},
        }

    def _lint(self) -> dict[str, Any]:
        return {
            "action": "lint",
            "cypher": """
MATCH (p:Page)
WHERE NOT (p)-[:CONNECTS_TO]->(:Database)
RETURN p.name AS page, p.id AS id
""".strip(),
            "params": {},
        }

    def _disconnect(self, intent: Intent) -> dict[str, Any]:
        page = intent.source or Ref(label="Page", name="Settings")
        db = intent.target or Ref(label="Database", name="MainDB")
        return {
            "action": "disconnect",
            "cypher": """
MATCH (src:Page)-[r:CONNECTS_TO]->(dst:Database)
WHERE (src.id = $src_id OR toLower(src.name) = toLower($src_name))
  AND (dst.id = $dst_id OR toLower(dst.name) = toLower($dst_name))
DELETE r
""".strip(),
            "params": {
                "src_id": page.resolved_id(),
                "src_name": page.name,
                "dst_id": db.resolved_id(),
                "dst_name": db.name,
            },
        }

    def _disconnect_auth(self, intent: Intent) -> dict[str, Any]:
        page = intent.source or Ref(label="Page", name="Landing")
        return {
            "action": "disconnect_auth",
            "cypher": """
MATCH (p:Page)-[r:AUTHENTICATES_WITH]->(:Auth)
WHERE p.id = $page_id OR toLower(p.name) = toLower($page_name)
DELETE r
""".strip(),
            "params": {"page_id": page.resolved_id(), "page_name": page.name},
        }


class GraphTalk:
    """High-level facade: say something, get intents + Cypher."""

    def __init__(self):
        self.parser = IntentParser()
        self.compiler = CypherCompiler()

    def say(self, text: str) -> dict[str, Any]:
        intents = self.parser.parse(text)
        compiled = self.compiler.compile(intents)
        return {
            "input": text,
            "intents": [intent.to_dict() for intent in intents],
            "statements": compiled,
        }


def dumps(result: dict[str, Any]) -> str:
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    talk = GraphTalk()
    samples = [
        "I need a db, three pages and a couple of includes.",
        "Connect the db to the landing page with a secure auth.",
        "Make all pages include Header and Footer.",
        "Connect all pages to MainDB with the same secure auth.",
        "Show me everything that connects to MainDB.",
        "What auth does the landing page use?",
        "What would break if I delete Header?",
        "Remove the connection between Settings and MainDB.",
    ]
    for sample in samples:
        print("=" * 72)
        print(dumps(talk.say(sample)))
        print()
