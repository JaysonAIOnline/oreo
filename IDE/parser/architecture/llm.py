"""LLM fallback that must emit the same Intent JSON as the rule parser.

Rules stay first. The model is only asked when speech is unknown, or when
you force llm_first=True.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any, Callable

from .parser import ConversationContext, Intent, IntentParser, Ref


INTENT_SCHEMA = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["action"],
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "create_node",
                    "connect",
                    "connect_with_auth",
                    "connect_all",
                    "connect_all_with_auth",
                    "include",
                    "include_all",
                    "query_neighbors",
                    "query_auth",
                    "impact",
                    "lint",
                    "disconnect",
                    "disconnect_auth",
                    "set_purpose",
                ],
            },
            "source": {"type": ["object", "null"]},
            "target": {"type": ["object", "null"]},
            "auth": {"type": ["object", "null"]},
            "includes": {"type": "array"},
            "nodes": {"type": "array"},
            "roles": {"type": "array"},
            "create_missing": {"type": "boolean"},
        },
    },
}


SYSTEM_PROMPT = """You are the GraphLang compiler. Humans, drawings, and tools
all speak through you. Return ONLY a JSON array of intent objects. No markdown.

GraphLang is AI-native. Intents are the language. Cypher/GQL/HTML are projections.

Allowed actions:
create_node, connect, connect_with_auth, connect_all, connect_all_with_auth,
include, include_all, query_neighbors, query_auth, impact, lint,
disconnect, disconnect_auth, set_purpose

Node ref: {"label":"Page|Database|Auth|Include|Function|Service|Resource","name":"...","props":{}}

Meaning:
- "add a page called Checkout" -> create_node Page Checkout
- "it's for secure auth to the db" -> set_purpose on context.last_node AND connect_with_auth if they want a handshake
- Drawing a line + spoken purpose -> connect / connect_with_auth / include, with raw=purpose
- props.purpose holds why the node or line exists
- "the db" is context.last_database or MainDB
- secure auth = Auth method=jwt, level=secure, requires_https=true, name=SecureJWT
- Never invent Cypher. Never drop AI structure to make a human shortcut.
"""


def _ref_from_dict(data: dict[str, Any] | None) -> Ref | None:
    if not data:
        return None
    return Ref(
        label=data.get("label") or "Resource",
        name=data.get("name") or "Unnamed",
        id=data.get("id"),
        props=data.get("props") or {},
    )


def intents_from_json(payload: Any, raw: str) -> list[Intent]:
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        raise ValueError("LLM output must be a JSON array")
    intents: list[Intent] = []
    for item in payload:
        intents.append(
            Intent(
                action=item.get("action") or "unknown",
                source=_ref_from_dict(item.get("source")),
                target=_ref_from_dict(item.get("target")),
                auth=_ref_from_dict(item.get("auth")),
                includes=[_ref_from_dict(x) for x in item.get("includes") or [] if x],
                nodes=[_ref_from_dict(x) for x in item.get("nodes") or [] if x],
                roles=item.get("roles") or [],
                create_missing=item.get("create_missing", True),
                raw=raw,
            )
        )
    return intents


class LLMClient:
    def complete_json(self, prompt: str) -> Any:
        raise NotImplementedError


class OpenAICompatClient(LLMClient):
    """Works with OpenAI-compatible chat APIs, including xAI if configured."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ):
        self.api_key = api_key or os.environ.get("XAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        self.base_url = (base_url or os.environ.get("GRAPHLang_LLM_BASE") or os.environ.get("OPENAI_BASE_URL") or "https://api.x.ai/v1").rstrip("/")
        self.model = model or os.environ.get("GRAPHLang_LLM_MODEL") or os.environ.get("XAI_MODEL") or "grok-4"
        if not self.api_key:
            raise RuntimeError("No API key. Set XAI_API_KEY or OPENAI_API_KEY.")

    def complete_json(self, prompt: str) -> Any:
        body = json.dumps(
            {
                "model": self.model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        content = content.strip()
        content = re.sub(r"^```(?:json)?", "", content)
        content = re.sub(r"```$", "", content).strip()
        return json.loads(content)


class ParaphraseLexicon(LLMClient):
    """Offline stand-in for freer speech when no API key is present."""

    PHRASES = [
        (
            r"handshake (?:the )?(?P<page>.+?) (?:to|with) (?:the )?(?:db|database)(?: with (?P<auth>secure auth|jwt|session))?",
            "connect",
        ),
        (
            r"(?:wire|hook|plug) (?:the )?(?P<page>.+?) (?:into|to) (?:the )?(?:db|database)",
            "connect",
        ),
        (
            r"who talks to (?:the )?(?:db|database|maindb)",
            "query",
        ),
        (
            r"pages missing a database",
            "lint",
        ),
    ]

    def complete_json(self, prompt: str) -> Any:
        # prompt contains the user sentence after "Speech:"
        match = re.search(r"Speech:\s*(.+)", prompt, re.S)
        speech = (match.group(1) if match else prompt).strip().splitlines()[0].strip()
        lowered = speech.lower()

        if "missing" in lowered and "database" in lowered:
            return [{"action": "lint"}]
        if "who talks" in lowered or "who is connected" in lowered:
            return [{"action": "query_neighbors", "target": {"label": "Database", "name": "MainDB"}}]

        for pattern, _kind in self.PHRASES:
            found = re.search(pattern, lowered)
            if not found:
                continue
            page = (found.groupdict().get("page") or "landing").replace("page", "").strip().title() or "Landing"
            auth_bit = found.groupdict().get("auth") if found.groupdict() else None
            if auth_bit or "secure" in lowered or "jwt" in lowered:
                return [
                    {
                        "action": "connect_with_auth",
                        "source": {"label": "Page", "name": page},
                        "target": {"label": "Database", "name": "MainDB"},
                        "auth": {
                            "label": "Auth",
                            "name": "SecureJWT",
                            "props": {"method": "jwt", "level": "secure", "requires_https": True},
                        },
                    }
                ]
            return [
                {
                    "action": "connect",
                    "source": {"label": "Page", "name": page},
                    "target": {"label": "Database", "name": "MainDB"},
                }
            ]
        raise ValueError(f"offline lexicon does not know: {speech}")


def default_llm_client() -> LLMClient:
    if os.environ.get("XAI_API_KEY") or os.environ.get("OPENAI_API_KEY"):
        return OpenAICompatClient()
    return ParaphraseLexicon()


class HybridParser:
    def __init__(
        self,
        context: ConversationContext | None = None,
        llm: LLMClient | None = None,
        llm_first: bool = False,
    ):
        self.rules = IntentParser(context=context)
        self.llm = llm if llm is not None else default_llm_client()
        # A real model, when present, is the compiler. Rules are the offline stand-in.
        self.llm_first = llm_first or isinstance(self.llm, OpenAICompatClient)

    @property
    def context(self) -> ConversationContext:
        return self.rules.context

    def parse(self, text: str) -> list[Intent]:
        if self.llm_first:
            try:
                return self._llm_parse(text)
            except Exception:
                return self.rules.parse(text)

        intents = self.rules.parse(text)
        if intents and all(intent.action != "unknown" for intent in intents):
            return intents
        try:
            return self._llm_parse(text)
        except Exception:
            return intents

    def _llm_parse(self, text: str) -> list[Intent]:
        prompt = (
            "Context:\n"
            + json.dumps(
                {
                    "last_database": self.context.last_database,
                    "last_page": self.context.last_page,
                    "last_auth": self.context.last_auth,
                    "pages": self.context.pages,
                    "databases": self.context.databases,
                }
            )
            + f"\n\nSpeech:\n{text}\n"
        )
        payload = self.llm.complete_json(prompt)
        return intents_from_json(payload, text)
