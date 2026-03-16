from __future__ import annotations

from agents import RunContextWrapper, function_tool

from app.aec import get_model_context
from app.state import clear_viewer_state


def require_autodesk_file(wrapper: RunContextWrapper) -> object:
    import viktor as vkt

    context = getattr(wrapper, "context", None)
    autodesk_file = getattr(context, "autodesk_file", None)
    if not autodesk_file:
        raise vkt.UserError("Select an Autodesk model first.")
    return autodesk_file


@function_tool()
def get_element_group_id_tool(wrapper: RunContextWrapper) -> str:
    """Return the AEC Data Model element group id for the selected Autodesk model."""
    autodesk_file = require_autodesk_file(wrapper)
    context = get_model_context(autodesk_file)
    return f"Element group id: {context.element_group_id}"


@function_tool()
def clear_highlight_tool(wrapper: RunContextWrapper) -> str:
    """Clear the highlighted elements from the viewer state."""
    require_autodesk_file(wrapper)
    clear_viewer_state()
    return "Cleared highlighted elements."
