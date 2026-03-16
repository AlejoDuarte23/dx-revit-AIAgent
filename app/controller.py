from __future__ import annotations

import textwrap

import viktor as vkt

from app.agent import viewer_agent_sync_stream
from app.state import clear_viewer_html, load_viewer_html


def blank_view_html(message: str) -> str:
    safe_message = (
        message.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return f"""
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <title>APS Viewer</title>
        <style>
          body {{
            margin: 0;
            min-height: 100vh;
            display: grid;
            place-items: center;
            background: #f7f3ea;
            color: #22303c;
            font-family: Georgia, serif;
          }}
          main {{
            max-width: 36rem;
            padding: 2rem;
            text-align: center;
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid #d8d0c0;
            border-radius: 1rem;
          }}
        </style>
      </head>
      <body>
        <main>{safe_message}</main>
      </body>
    </html>
    """


class Parametrization(vkt.Parametrization):
    intro = vkt.Text(
        textwrap.dedent(
            """
            ## Revit Type Query

            Select one Autodesk model, then use chat.

            Examples:
            - `show the model`
            - `highlight Basic Wall`
            - `highlight CL_W1`
            """
        )
    )

    autodesk_file = vkt.AutodeskFileField("Autodesk model", oauth2_integration="aps-integration-viktor")

    chat = vkt.Chat("Ask the agent", method="call_llm")


class Controller(vkt.Controller):
    parametrization = Parametrization(width=35)

    def call_llm(self, params, **kwargs) -> vkt.ChatResult | None:
        if not params.chat:
            return None

        autodesk_file = getattr(params, "autodesk_file", None)
        if not autodesk_file:
            clear_viewer_html()
            return vkt.ChatResult(
                conversation=params.chat,
                response="Select an Autodesk model first.",
            )

        messages = params.chat.get_messages()
        chat_history = [
            {"role": message["role"], "content": message["content"]}
            for message in messages
        ]
        text_stream = viewer_agent_sync_stream(
            chat_history=chat_history,
            autodesk_file=autodesk_file,
            show_tool_progress=True,
        )
        return vkt.ChatResult(conversation=params.chat, response=text_stream)

    @vkt.WebView("Viewer")
    def show_cad_model(self, params, **kwargs) -> vkt.WebResult:
        autodesk_file = getattr(params, "model", None)
        if not params.chat or not autodesk_file:
            clear_viewer_html()
            return vkt.WebResult(html=blank_view_html("Select an Autodesk model, then ask the agent to show or highlight it."))

        html = load_viewer_html()
        if html:
            return vkt.WebResult(html=html)

        return vkt.WebResult(html=blank_view_html("Ask the agent to show the model."))
