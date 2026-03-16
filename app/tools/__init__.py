from app.tools.tools import (
    clear_highlight_tool,
    get_element_group_id_tool,
    highlight_type_tool,
)


TOOL_DISPLAY_NAMES = {
    "clear_highlight_tool": "Clear highlight",
    "get_element_group_id_tool": "Get element group id",
    "highlight_type_tool": "Highlight type",
}


def get_tools():
    return [
        clear_highlight_tool,
        get_element_group_id_tool,
        highlight_type_tool,
    ]
