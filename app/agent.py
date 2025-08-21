from agents import Agent, Runner
from app.tools.tools import (
    get_hub_tool,
    get_exchanges_tool,
    get_exchange_file_file_urn_tool,
    display_exchange_model,
    query_elements_by_metadata_name,
    display_dashboard
)
from dotenv import load_dotenv
import asyncio
import threading

load_dotenv()

# Persistent background event loop to avoid creating/closing loops per request.
_loop = None
_loop_thread = None


def _ensure_loop():
    global _loop, _loop_thread
    if _loop and _loop.is_running():
        return
    _loop = asyncio.new_event_loop()
    _loop_thread = threading.Thread(target=_loop.run_forever, name="dx-agent-loop", daemon=True)
    _loop_thread.start()


def _run_async(coro):
    _ensure_loop()
    fut = asyncio.run_coroutine_threadsafe(coro, _loop)
    return fut.result()


async def dx_agent(chat_history: list[dict[str, str]]):
    agent = Agent(
        name="Assistant",
        instructions=(
            "Help user to navigate ther Data Exchanges with the Autodesk Platform services "
            "Tool you have at your disposal"
        ),
        tools=[
            get_hub_tool,
            get_exchanges_tool,
            get_exchange_file_file_urn_tool,
            display_exchange_model,
            query_elements_by_metadata_name,
            display_dashboard
        ],
    )

    result = await Runner.run(agent, input=chat_history)
    return result.final_output


def dx_agent_sync(chat_history: list[dict[str, str]]):
    """Synchronous wrapper to run dx_agent on a persistent event loop."""
    return _run_async(dx_agent(chat_history))