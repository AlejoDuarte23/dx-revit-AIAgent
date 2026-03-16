from __future__ import annotations

import json
from dataclasses import dataclass


VIEWER_STATE_KEY = "aps_view_state"


@dataclass(frozen=True)
class ViewerState:
    version_urn: str | None = None
    highlight_elements: list[dict[str, str]] | None = None


def load_viewer_state() -> ViewerState:
    import viktor as vkt

    try:
        raw = vkt.Storage().get(VIEWER_STATE_KEY, scope="entity").getvalue()
    except Exception:
        return ViewerState()

    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", errors="replace")

    try:
        data = json.loads(str(raw))
    except Exception:
        return ViewerState()

    highlight_elements = data.get("highlight_elements")
    if not isinstance(highlight_elements, list):
        highlight_elements = []

    return ViewerState(
        version_urn=data.get("version_urn"),
        highlight_elements=[
            element
            for element in highlight_elements
            if isinstance(element, dict)
        ],
    )


def save_highlight_state(version_urn: str, highlight_elements: list[dict[str, str]]) -> None:
    import viktor as vkt

    payload = {
        "version_urn": version_urn,
        "highlight_elements": highlight_elements,
    }
    vkt.Storage().set(
        VIEWER_STATE_KEY,
        data=vkt.File.from_data(json.dumps(payload).encode("utf-8")),
        scope="entity",
    )


def clear_viewer_state() -> None:
    import viktor as vkt

    try:
        vkt.Storage().delete(VIEWER_STATE_KEY, scope="entity")
    except Exception:
        return
