"""Drawing a line between two nodes is an executable intent.

Spoken purpose tells the editor what the line is for.
"""

from __future__ import annotations

from .parser import Intent, Ref


def parse_purpose(purpose: str | None) -> dict:
    text = (purpose or "").strip().lower()
    info = {
        "purpose": (purpose or "").strip(),
        "secure": True,
        "include": False,
        "method": "jwt",
        "kind": "handshake",
    }
    if not text:
        return info
    if any(w in text for w in ("include", "header", "footer", "partial", "template")):
        info.update(kind="include", include=True, secure=False)
    if any(w in text for w in ("public", "open", "no auth", "without auth", "insecure")):
        info.update(secure=False, kind="connection")
    if "session" in text:
        info["method"] = "session"
    if "oauth" in text:
        info["method"] = "oauth2"
    if "api key" in text or "apikey" in text:
        info["method"] = "api_key"
    if any(w in text for w in ("handshake", "secure", "auth", "jwt", "login", "protect")):
        info.update(kind="handshake", secure=True)
    if "call" in text:
        info["kind"] = "calls"
    return info


def infer_intent(
    src_label: str,
    src_name: str,
    dst_label: str,
    dst_name: str,
    secure: bool = True,
    purpose: str | None = None,
) -> Intent:
    src = Ref(label=src_label, name=src_name)
    dst = Ref(label=dst_label, name=dst_name)
    said = parse_purpose(purpose)
    if purpose:
        secure = said["secure"] if purpose.strip() else secure
    pair = (src_label, dst_label)
    raw = purpose.strip() if purpose and purpose.strip() else f"draw {src_name} -> {dst_name}"

    if said["include"] or pair in {("Page", "Include"), ("Include", "Page")}:
        page, inc = (src, dst) if src_label == "Page" else (dst, src)
        if pair[0] == "Include" or pair[1] == "Include" or said["include"]:
            return Intent(action="include", source=page if page.label == "Page" else src, includes=[inc if inc.label == "Include" else dst], raw=raw)

    if pair == ("Database", "Page"):
        return infer_intent("Page", dst_name, "Database", src_name, secure, purpose)

    if pair == ("Page", "Database") or said["kind"] == "handshake":
        action = "connect_with_auth" if secure else "connect"
        auth = None
        if secure:
            method = said["method"]
            name = "SecureJWT" if method == "jwt" else method.replace("_", " ").title()
            auth = Ref(
                label="Auth",
                name=name,
                props={"method": method, "level": "secure" if secure else "basic", "requires_https": secure, "purpose": said["purpose"]},
            )
        return Intent(action=action, source=src if src_label == "Page" else Ref(label="Page", name=src_name), target=dst if dst_label == "Database" else Ref(label="Database", name=dst_name), auth=auth, raw=raw)

    if pair == ("Page", "Auth"):
        return Intent(
            action="connect_with_auth",
            source=src,
            target=Ref(label="Database", name="MainDB"),
            auth=dst,
            raw=raw,
        )

    return Intent(action="connect", source=src, target=dst, raw=raw)
