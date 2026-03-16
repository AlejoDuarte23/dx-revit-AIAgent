from app.tools.query_tools.query_tools import (
    highlight_family_tool,
    highlight_type_tool,
)


QUERY_TOOL_DISPLAY_NAMES = {
    "highlight_type_tool": "Highlight type",
    "highlight_family_tool": "Highlight family",
}


def get_query_tools():
    return [
        highlight_type_tool,
        highlight_family_tool,
    ]
