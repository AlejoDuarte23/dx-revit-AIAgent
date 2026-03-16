from __future__ import annotations

from agents import RunContextWrapper, function_tool

from app.aec import (
    DEFAULT_HIGHLIGHT_COLOR,
    build_highlight_payload,
    find_elements_by_element_name,
    get_model_context,
)
from app.state import clear_viewer_state, save_highlight_state


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


@function_tool()
def highlight_type_tool(
    wrapper: RunContextWrapper,
    type_name: str,
    family_name: str | None = None,
) -> str:
    """Highlight one Revit type in the viewer. Query instances by `Element Context` == Instance, optional `Family Name`, and `Element Name`."""
    autodesk_file = require_autodesk_file(wrapper)
    context = get_model_context(autodesk_file)
    elements = find_elements_by_element_name(
        context,
        type_name=type_name,
        family_name=family_name,
    )
    highlight_elements = build_highlight_payload(
        elements,
        color=DEFAULT_HIGHLIGHT_COLOR,
    )
    save_highlight_state(context.version_urn, highlight_elements)

    if not highlight_elements:
        if family_name:
            return f'No elements matched family "{family_name}" and type "{type_name}".'
        return f'No elements matched "{type_name}".'

    count = len(highlight_elements)
    suffix = "" if count == 1 else "s"
    if family_name:
        return f'Highlighted {count} element{suffix} for family "{family_name}" and type "{type_name}".'
    return f'Highlighted {count} element{suffix} for "{type_name}".'
