from app.tools.query_tools import QUERY_TOOL_DISPLAY_NAMES, get_query_tools
from app.tools.tools import (
    clear_highlight_tool,
    get_element_group_id_tool,
)


TOOL_DISPLAY_NAMES = {
    "clear_highlight_tool": "Clear highlight",
    "get_element_group_id_tool": "Get element group id",
    **QUERY_TOOL_DISPLAY_NAMES,
}


def get_tools():
    return [
        clear_highlight_tool,
        get_element_group_id_tool,
        *get_query_tools(),
    ]
