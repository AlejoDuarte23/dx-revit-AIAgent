import viktor as vkt
from pathlib import Path

from app.agent import dx_agent_sync


class Parametrization(vkt.Parametrization):
    input = vkt.Text("# Dx - APS - ACC - VIKTOR Agent")
    chat = vkt.Chat("", method="call_llm")

class Controller(vkt.Controller):
    parametrization = Parametrization
    
    def call_llm(self, params, **kwargs) -> vkt.ChatResult | None:
        """Multi-turn conversation between the user and the agent."""

        conversation_history = params.chat.get_messages()
        response: str = ""
        if conversation_history:
            response = dx_agent_sync(chat_history=conversation_history)
        return vkt.ChatResult(conversation=params.chat, response=response)
    
    @vkt.WebView("Model Viewer", duration_guess=2)
    def show_cad_model(self, params, **kwargs):
        if not params.chat:
            entities = vkt.Storage().list(scope="entity")
            for entity in entities:
                if entity == "aps_view":
                    vkt.Storage().delete("aps_view", scope="entity")

        try:
            raw_html = vkt.Storage().get("aps_view", scope="entity").getvalue()
            # Ensure WebResult gets a string
            if isinstance(raw_html, (bytes, bytearray)):
                raw_html = raw_html.decode("utf-8", errors="replace")
            return vkt.WebResult(html=raw_html)

        except Exception:
            # fig = default_blank_scene()
            file_path = Path(__file__).parent / "views" / "BlankScene.html"
            # fig.write_html(str(file_path))
            return vkt.WebResult.from_path(file_path=file_path)