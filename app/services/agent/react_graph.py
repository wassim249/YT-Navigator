"""ReAct Agent to process messages with tool calls."""

import copy
import os
from typing import Literal

from django.conf import settings
from langchain_core.messages import (
    SystemMessage,
    ToolMessage,
    trim_messages,
)
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableConfig
from langchain_groq import ChatGroq
from langgraph.graph import (
    END,
    StateGraph,
)
from langgraph.graph.state import CompiledStateGraph

from app.schemas import (
    AgentOutput,
    AgentState,
)
from app.services.agent.prompts import SYSTEM_PROMPT_TEMPLATE
from app.services.vector_database.tools import (
    SQLTools,
    VectorDatabaseTools,
)

tools = [
    VectorDatabaseTools.tool(),
    SQLTools.tool(),
]

model = ChatGroq(
    model_name=settings.POWERFUL_LLM,
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.0,
).bind_tools(tools)


tools_by_name = {tool.name: tool for tool in tools}


# Define our tool node
async def tool_node(state: AgentState) -> AgentState:
    """Process tool calls from the last message.

    Args:
        state: The current agent state containing messages and tool calls.

    Returns:
        Dict with updated messages containing tool responses.
    """
    outputs = []
    for tool_call in state.messages[-1].tool_calls:
        tool_result = await tools_by_name[tool_call["name"]].ainvoke(tool_call["args"])
        outputs.append(
            ToolMessage(
                content=tool_result,
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            )
        )
    return {"messages": outputs}


async def call_model(
    state: AgentState,
    config: RunnableConfig,
) -> AgentState:
    """Call the model with the system prompt and tool calls.

    Args:
        state: The current agent state containing messages and tool calls.
        config: The configuration for the runnable.

    Returns:
        Dict with updated messages containing the model's response.
    """
    output_parser = PydanticOutputParser(pydantic_object=AgentOutput)

    system_prompt = SystemMessage(
        SYSTEM_PROMPT_TEMPLATE.format(
            channel=await state.channel.pretty_str(),
            user=state.user,
            format_instructions=output_parser.get_format_instructions(),
        )
    )

    trimmed_messages = trim_messages(
        copy.deepcopy(state.messages),
        strategy="last",
        token_counter=model,
        max_tokens=2000,
        start_on="human",
        include_system=False,
        allow_partial=False,
    )

    response = await model.ainvoke([system_prompt] + trimmed_messages, config)
    return {"messages": [response]}


def should_continue(state: AgentState) -> Literal["end", "continue"]:
    """Determine if the agent should continue or end based on the last message.

    Args:
        state: The current agent state containing messages.

    Returns:
        Literal["end", "continue"]: "end" if there are no tool calls, "continue" otherwise.
    """
    messages = state.messages
    last_message = messages[-1]
    # If there is no function call, then we finish
    if not last_message.tool_calls:
        return "end"
    # Otherwise if there is, we continue
    else:
        return "continue"


def build_workflow() -> CompiledStateGraph:
    """Build the workflow for the agent.

    Returns:
        CompiledStateGraph: The compiled workflow for the agent.
    """
    workflow = StateGraph(AgentState)

    # Define the two nodes we will cycle between
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    workflow.set_entry_point("agent")

    # We now add a conditional edge
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            # If `tools`, then we call the tool node.
            "continue": "tools",
            # Otherwise we finish.
            "end": END,
        },
    )

    workflow.add_edge("tools", "agent")

    return workflow.compile()


react_agent = build_workflow()
