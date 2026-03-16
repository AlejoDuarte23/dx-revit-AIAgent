from __future__ import annotations

from agents import RunContextWrapper, function_tool

from app.aec import (
    DEFAULT_HIGHLIGHT_COLOR,
    build_highlight_payload,
    find_elements_by_element_name,
    get_model_context,
)
from app.state import save_viewer_html


def get_autodesk_file(wrapper: RunContextWrapper) -> object | None:
    context = getattr(wrapper, "context", None)
    return getattr(context, "autodesk_file", None)


def build_viewer_html(
    *,
    autodesk_file: object,
    highlight_elements: list[dict[str, str]] | None = None,
) -> str:
    from aps_viewer_sdk import APSViewer

    context = get_model_context(autodesk_file)
    viewer = APSViewer(
        urn=context.version_urn,
        token=context.token,
        views_selector=True,
    )
    if highlight_elements:
        viewer.highlight_elements(highlight_elements)
    return viewer.write()


@function_tool()
def display_model_tool(wrapper: RunContextWrapper) -> str:
    """Display the currently selected Autodesk model in the viewer panel."""
    autodesk_file = get_autodesk_file(wrapper)
    if not autodesk_file:
        return "Select an Autodesk model first."

    html = build_viewer_html(autodesk_file=autodesk_file)
    save_viewer_html(html)
    return "Model loaded in the viewer."


@function_tool()
def highlight_type_tool(
    wrapper: RunContextWrapper,
    type_name: str,
    family_name: str | None = None,
) -> str:
    """Highlight one Revit type in the viewer. Query instances by `Element Context` == Instance, optional `Family Name`, and `Element Name`."""
    autodesk_file = get_autodesk_file(wrapper)
    if not autodesk_file:
        return "Select an Autodesk model first."

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

    html = build_viewer_html(
        autodesk_file=autodesk_file,
        highlight_elements=highlight_elements,
    )
    save_viewer_html(html)

    if not highlight_elements:
        if family_name:
            return f'No elements matched family "{family_name}" and type "{type_name}".'
        return f'No elements matched "{type_name}".'

    count = len(highlight_elements)
    suffix = "" if count == 1 else "s"
    if family_name:
        return f'Highlighted {count} element{suffix} for family "{family_name}" and type "{type_name}".'
    return f'Highlighted {count} element{suffix} for "{type_name}".'
