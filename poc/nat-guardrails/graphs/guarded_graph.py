"""LangGraph that delegates the chat turn to NeMo Guardrails.

NAT calls a single LangGraph node which in turn calls
``LLMRails.generate_async()``. The Rails config defines the main LLM
plus self_check_input / self_check_output flows, so the rail evaluation
and the main response are produced in one Guardrails round trip.

This is the "let Guardrails own the LLM call" variant of the manual
middleware pattern. Chapter 9 swaps the rail LLM for the Multilingual
Safety Guard v3 NIM and keeps the same wiring.
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
    # rails が input/output いずれかでブロックすると content は空になる。
    # その場合に本書では明示的な refusal メッセージを返す。
    if not reply_text.strip():
        reply_text = "申し訳ありません。社内ポリシーにより、その内容には回答できません。"
    return {"messages": [AIMessage(content=reply_text)]}


def make_graph(_config: RunnableConfig):
    builder = StateGraph(State)
    builder.add_node("guarded_chat", guarded_chat_node)
    builder.add_edge(START, "guarded_chat")
    builder.add_edge("guarded_chat", END)
    return builder.compile()
