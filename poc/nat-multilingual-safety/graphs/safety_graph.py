"""LangGraph that delegates to Guardrails with Multilingual Safety Guard v3.

Identical wiring to Chapter 8 (single guarded_chat node), but the rails
config swaps the rail evaluator to nvidia/llama-3.1-nemotron-safety-guard-8b-v3
via the content_safety_check_input/output flows.
"""

from __future__ import annotations

import os
from typing import Annotated

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from nemoguardrails import LLMRails, RailsConfig
from typing_extensions import TypedDict

GUARDRAILS_CONFIG_DIR = os.environ.get("GUARDRAILS_CONFIG", "/app/config")
DEFAULT_REFUSAL_JA = "申し訳ありません。社内ポリシーにより、その内容には回答できません。"


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


_rails: LLMRails | None = None


def _get_rails() -> LLMRails:
    global _rails
    if _rails is None:
        config = RailsConfig.from_path(GUARDRAILS_CONFIG_DIR)
        _rails = LLMRails(config)
    return _rails


async def guarded_chat_node(state: State) -> dict:
    last = state["messages"][-1]
    text = last.content if isinstance(last.content, str) else ""

    rails = _get_rails()
    response = await rails.generate_async(
        messages=[{"role": "user", "content": text}],
    )
    reply_text = response.get("content", "") if isinstance(response, dict) else str(response)
    if not reply_text.strip():
        reply_text = DEFAULT_REFUSAL_JA
    return {"messages": [AIMessage(content=reply_text)]}


def make_graph(_config: RunnableConfig):
    builder = StateGraph(State)
    builder.add_node("guarded_chat", guarded_chat_node)
    builder.add_edge(START, "guarded_chat")
    builder.add_edge("guarded_chat", END)
    return builder.compile()
