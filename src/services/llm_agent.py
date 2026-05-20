import logging
from uuid import uuid4

from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Checkpointer

from src.config import settings
from src.services.prompt_config import SYSTEM_PROMPT

logger = logging.getLogger("job-finder")


async def create_llm_agent(checkpointer: Checkpointer):
    # client = MultiServerMCPClient(connections={})
    # tools = await client.get_tools()

    tools = []

    if settings.llm_provider == "lmstudio":
        tools = [
            {"type": "mcp", "server_label": "playwright"},
            {"type": "mcp", "server_label": "job_finder"},
        ]

    if settings.llm_provider == "anthropic":
        tools.append(
            {
                "type": "web_search_20260209",
                "name": "web_search",
                "allowed_callers": ["direct"],
            }
        )

    if settings.llm_provider == "openai":
        tools.append({"type": "web_search"})

    logger.info("Initializing LLM agent")
    return create_agent(
        model=settings.llm_client,
        tools=tools,
        name="Job Finder Agent",
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )


async def invoke_agent(query: str) -> bool:
    logger.info(f"Invoking agent with query: {query}")

    async with AsyncSqliteSaver.from_conn_string(
        settings.CHECKPOINTER_DATABASE_PATH
    ) as checkpointer:
        agent = await create_llm_agent(checkpointer)

        config = RunnableConfig(
            configurable={"thread_id": str(uuid4())}, recursion_limit=100
        )
        response = await agent.invoke([HumanMessage(content=query)], config=config)

    return response
