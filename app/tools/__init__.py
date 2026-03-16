from app.tools.tools import display_model_tool, highlight_type_tool


TOOL_DISPLAY_NAMES = {
    "display_model_tool": "Display model",
    "highlight_type_tool": "Highlight type",
}


def get_tools():
    return [
        display_model_tool,
        highlight_type_tool,
    ]
