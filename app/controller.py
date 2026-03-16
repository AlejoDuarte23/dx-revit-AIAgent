from __future__ import annotations

import textwrap

import viktor as vkt

from app.agent import viewer_agent_sync_stream
from app.aec import get_model_context
from app.state import clear_viewer_state, load_viewer_state


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
            clear_viewer_state()
            return None

        messages = params.chat.get_messages()
        chat_history = [
            {"role": message["role"], "content": message["content"]}
            for message in messages
        ]
        text_stream = viewer_agent_sync_stream(
            chat_history=chat_history,
            autodesk_file=params.autodesk_file,
            show_tool_progress=True,
        )
        return vkt.ChatResult(conversation=params.chat, response=text_stream)

    @vkt.WebView("Viewer", duration_guess=30)
    def show_cad_model(self, params, **kwargs) -> vkt.WebResult:
        from aps_viewer_sdk import APSViewer
        if not params.chat:
            clear_viewer_state()

        context = get_model_context(params.autodesk_file)
        viewer = APSViewer(
            urn=context.version_urn,
            token=context.token,
            views_selector=True,
        )

        viewer_state = load_viewer_state()
        if (
            viewer_state.version_urn == context.version_urn
            and viewer_state.highlight_elements
        ):
            viewer.highlight_elements(viewer_state.highlight_elements)

        return vkt.WebResult(html=viewer.write())
