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

event_loop: asyncio.AbstractEventLoop | None = None
event_loop_thread: threading.Thread | None = None


def ensure_loop() -> asyncio.AbstractEventLoop:
    global event_loop, event_loop_thread
    if event_loop and event_loop.is_running():
        return event_loop
    event_loop = asyncio.new_event_loop()
    event_loop_thread = threading.Thread(
        target=event_loop.run_forever, name="dx-agent-loop", daemon=True
    )
    event_loop_thread.start()
    return event_loop


def run_async(coro):
    loop = ensure_loop()
    fut = asyncio.run_coroutine_threadsafe(coro, loop)
    return fut.result()


async def dx_agent(chat_history: list[dict[str, str]]):
    agent = Agent(
        name="Assistant",
        instructions=(
            "Help user to navigate ther Data Exchanges with the Autodesk Platform services "
            "Use the tools you have at your disposal"
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
    """Synchronous wrapper using the background event loop.
    If a loop already exists (previous call), it's reused; otherwise a new one is created.
    the entry is sync but the even loop can make concurrent api call to Autodesk! 
    """
    return run_async(dx_agent(chat_history))