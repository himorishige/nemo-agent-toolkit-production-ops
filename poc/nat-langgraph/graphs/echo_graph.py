"""Minimal LangGraph state graph wrapped as NAT function.

Two-node graph: classify -> respond.
The classify node tags the question type (date / general),
the respond node produces a Japanese reply using Nemotron Super 49B via NIM.
"""

from __future__ import annotations

import os
from typing import Annotated

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    question_type: str | None


def _llm() -> ChatNVIDIA:
    return ChatNVIDIA(
        model="nvidia/llama-3.3-nemotron-super-49b-v1",
        api_key=os.environ["NGC_API_KEY"],
        base_url="https://integrate.api.nvidia.com/v1",
        temperature=0.0,
        max_tokens=512,
    )


def classify_node(state: State) -> dict:
    last = state["messages"][-1]
    text = last.content.lower() if isinstance(last.content, str) else ""
    if any(k in text for k in ["date", "today", "日付", "今日"]):
        return {"question_type": "date"}
    return {"question_type": "general"}


def respond_node(state: State) -> dict:
    qtype = state.get("question_type", "general")
    system_text = (
        "あなたは社内文書 Q&A の補助をする日本語アシスタントです。"
        f"今回の質問種別は {qtype} です。質問種別を意識して 1〜2 文で簡潔に答えてください。"
    )
    history = [SystemMessage(content=system_text), *state["messages"]]
    reply = _llm().invoke(history)
    if not isinstance(reply, AIMessage):
        reply = AIMessage(content=str(reply.content))
    return {"messages": [reply]}


def make_graph(_config: RunnableConfig):
    builder = StateGraph(State)
    builder.add_node("classify", classify_node)
    builder.add_node("respond", respond_node)
    builder.add_edge(START, "classify")
    builder.add_edge("classify", "respond")
    builder.add_edge("respond", END)
    return builder.compile()
