from __future__ import annotations


VIEWER_HTML_KEY = "aps_view"


def load_viewer_html() -> str | None:
    import viktor as vkt

    try:
        raw = vkt.Storage().get(VIEWER_HTML_KEY, scope="user").getvalue()
    except Exception:
        return None

    if isinstance(raw, (bytes, bytearray)):
        return raw.decode("utf-8", errors="replace")
    return str(raw) if raw else None


def save_viewer_html(html: str) -> None:
    import viktor as vkt

    vkt.Storage().set(
        VIEWER_HTML_KEY,
        data=vkt.File.from_data(html.encode("utf-8")),
        scope="user",
    )


def clear_viewer_html() -> None:
    import viktor as vkt

    try:
        vkt.Storage().delete(VIEWER_HTML_KEY, scope="user")
    except Exception:
        return
