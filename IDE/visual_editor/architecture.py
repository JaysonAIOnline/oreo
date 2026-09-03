"""
OREO Visual Editor - Architecture editor bridge.

The OREO Architecture subsystem ships its own self-contained web editor
(talk + draw canvas + model view + voice) in parser/architecture/visual.py.

This module is the bridge into the existing visual_editor/ module namespace.
"""

from __future__ import annotations

from typing import Any

from parser.architecture.visual import (
    EDITOR_PATH,
    VOICE_INTRO,
    apply_draw,
    render_editor,
    serve,
)

__all__ = [
    "EDITOR_PATH",
    "VOICE_INTRO",
    "apply_draw",
    "render_editor",
    "serve",
]


def architecture_editor_url(host: str = "127.0.0.1", port: int = 8765) -> str:
    return f"http://{host}:{port}/editor"
