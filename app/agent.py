from __future__ import annotations

import asyncio
import queue
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from agents import Agent, Runner, set_tracing_disabled
from openai.types.responses import ResponseTextDeltaEvent

from app.tools import TOOL_DISPLAY_NAMES, get_tools
from dotenv import load_dotenv

load_dotenv()

@dataclass
class AgentContext:
    autodesk_file: Any | None = None


event_loop: asyncio.AbstractEventLoop | None = None
event_loop_thread: threading.Thread | None = None

set_tracing_disabled(True)


def ensure_loop() -> asyncio.AbstractEventLoop:
    global event_loop, event_loop_thread
    if event_loop and event_loop.is_running():
        return event_loop

    event_loop = asyncio.new_event_loop()
    event_loop_thread = threading.Thread(
        target=event_loop.run_forever,
        name="revit-agent-loop",
        daemon=True,
    )
    event_loop_thread.start()
    return event_loop


def extract_call_id(raw: Any) -> str | None:
    if isinstance(raw, dict):
        candidate = raw.get("call_id") or raw.get("id") or raw.get("tool_call_id")
        return str(candidate) if candidate else None

    for attr in ("call_id", "id", "tool_call_id"):
        value = getattr(raw, attr, None)
        if value:
            return str(value)
    return None


def extract_tool_name(raw: Any) -> str:
    if isinstance(raw, dict):
        if raw.get("name"):
            return str(raw["name"])
        fn = raw.get("function")
        if isinstance(fn, dict) and fn.get("name"):
            return str(fn["name"])
        if raw.get("tool_name"):
            return str(raw["tool_name"])

    for attr in ("name", "tool_name", "function_name"):
        value = getattr(raw, attr, None)
        if value:
            return str(value)

    fn = getattr(raw, "function", None)
    if fn is not None and getattr(fn, "name", None):
        return str(fn.name)

    return "tool"


def viewer_agent_sync_stream(
    chat_history: list[dict[str, Any]],
    *,
    autodesk_file: Any | None,
    show_tool_progress: bool = True,
) -> Iterator[str]:
    q: queue.Queue[object] = queue.Queue()
    sentinel = object()
    loop = ensure_loop()

    async def produce_stream_events() -> None:
        call_id_to_name: dict[str, str] = {}
        try:
            agent = Agent[AgentContext](
                name="RevitTypeAssistant",
                instructions=(
                    "You are a simple Autodesk Revit viewer assistant. "
                    "Use the tools for actions instead of pretending the action already happened. "
                    "The selected Autodesk model is already rendered in the viewer by default. "
                    "Do not call a tool just to show or load the model. "
                    "If the user wants to clear or reset the current highlights, call `clear_highlight_tool`. "
                    "If the user asks for the AEC Data Model element group id of the selected model, call `get_element_group_id_tool`. "
                    "If the user wants to highlight, find, or isolate one Revit type, call `highlight_type_tool`. "
                    "If the user wants to highlight all instances of a family (without filtering by type), call `highlight_family_tool`. "
                    "Treat the AEC Data Model property `Element Name` as the proxy for type name. "
                    "When the user gives both a family and a type, pass both. "
                    "Only support one type at a time. If the user asks for multiple types, ask them to pick one. "
                    "If no Autodesk model is selected, say so plainly."
                ),
                model="gpt-5-mini",
                tools=get_tools(),
            )

            result = Runner.run_streamed(
                agent,
                input=chat_history,
                context=AgentContext(autodesk_file=autodesk_file),
                max_turns=10,
            )

            async for event in result.stream_events():
                if event.type == "raw_response_event" and isinstance(
                    event.data, ResponseTextDeltaEvent
                ):
                    if event.data.delta:
                        q.put(event.data.delta)
                    continue

                if not show_tool_progress:
                    continue

                if event.type == "run_item_stream_event":
                    item = event.item
                    raw = getattr(item, "raw_item", None)

                    if event.name == "tool_called":
                        call_id = extract_call_id(raw)
                        tool_name = extract_tool_name(raw)
                        if call_id:
                            call_id_to_name[call_id] = tool_name
                        display_name = TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
                        q.put(f"\n\n[Running {display_name}]\n")
                        continue

                    if event.name == "tool_output":
                        call_id = extract_call_id(raw)
                        tool_name = call_id_to_name.get(call_id or "", "tool")
                        display_name = TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
                        q.put(f"\n[Done {display_name}]\n\n")
                        continue
        except Exception as exc:
            q.put(f"\n\n{type(exc).__name__}: {exc}\n")
        finally:
            q.put(sentinel)

    asyncio.run_coroutine_threadsafe(produce_stream_events(), loop)

    def generate_stream() -> Iterator[str]:
        while True:
            item = q.get()
            if item is sentinel:
                break
            yield item  # type: ignore[misc]

    return generate_stream()
