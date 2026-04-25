"""LangGraph supervisor pattern for internal-doc Q&A.

The supervisor inspects the question and routes to one of three experts:

    faq_expert       : handles handbook / faq buckets
    security_expert  : handles it-security bucket
    directory_expert : handles department-notes bucket (PII aware)

Each expert is a self-contained LangGraph node that retrieves from Milvus
with its own metadata filter and produces a draft answer. The supervisor
collects the draft and emits the final response.
"""

from __future__ import annotations

import os
from typing import Annotated, Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_nvidia_ai_endpoints import ChatNVIDIA, NVIDIAEmbeddings
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pymilvus import MilvusClient
from typing_extensions import TypedDict

MILVUS_URI = os.environ.get("MILVUS_URI", "http://milvus:19530")
COLLECTION = os.environ.get("MILVUS_COLLECTION", "internal_docs")
EMBED_MODEL = "nvidia/nv-embedqa-e5-v5"
TOP_K = 3

EXPERT_TO_FILTER: dict[str, str] = {
    "faq_expert": "category in ['faq', 'handbook'] && confidentiality != 'confidential'",
    "security_expert": "category == 'it-security' && confidentiality != 'confidential'",
    "directory_expert": "category == 'department-notes' && confidentiality != 'confidential'",
}


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    expert: str | None
    draft: str | None
    sources: list[dict[str, Any]] | None


def _llm() -> ChatNVIDIA:
    return ChatNVIDIA(
        model="nvidia/llama-3.3-nemotron-super-49b-v1",
        api_key=os.environ["NGC_API_KEY"],
        base_url="https://integrate.api.nvidia.com/v1",
        temperature=0.0,
        max_tokens=512,
    )


def supervisor_node(state: State) -> dict:
    last = state["messages"][-1]
    text = last.content if isinstance(last.content, str) else ""

    instruction = (
        "あなたは社内 Q&A の supervisor です。ユーザーの質問を読み、"
        "次のいずれか 1 つの専門エージェント名だけを答えてください。\n\n"
        "- faq_expert: 経費精算 / 休暇 / オンボーディング / 福利厚生 / オフィス利用\n"
        "- security_expert: パスワード / VPN / アカウント / インシデント / デバイス\n"
        "- directory_expert: 連絡先 / 担当者 / 部署 / 社員\n\n"
        "応答は専門エージェント名 1 語だけで、説明は不要です。"
    )
    response = _llm().invoke(
        [SystemMessage(content=instruction), HumanMessage(content=text)],
    )
    raw = response.content.strip().lower() if isinstance(response.content, str) else ""
    for name in EXPERT_TO_FILTER:
        if name in raw:
            return {"expert": name}
    return {"expert": "faq_expert"}


def _expert_run(state: State, expert_name: str) -> dict:
    last = state["messages"][-1]
    query = last.content if isinstance(last.content, str) else ""

    embedder = NVIDIAEmbeddings(
        model=EMBED_MODEL,
        api_key=os.environ["NGC_API_KEY"],
    )
    vec = embedder.embed_query(query)

    client = MilvusClient(uri=MILVUS_URI)
    results = client.search(
        collection_name=COLLECTION,
        data=[vec],
        limit=TOP_K,
        output_fields=["title", "category", "confidentiality", "has_pii", "source_path", "text"],
        filter=EXPERT_TO_FILTER[expert_name],
    )

    sources = []
    blocks = []
    for i, hit in enumerate(results[0], start=1):
        e = hit.get("entity", {}) or {}
        sources.append(
            {
                "title": e.get("title"),
                "source": e.get("source_path"),
                "has_pii": e.get("has_pii"),
            }
        )
        blocks.append(f"[{i}] {e.get('title')}（{e.get('source_path')}）\n{e.get('text', '')}")
    context = "\n\n".join(blocks) if blocks else "（参考情報なし）"

    system_text = (
        f"あなたは Example 株式会社の {expert_name} です。"
        "以下の参考情報のみに基づいて、日本語で 1〜2 文で簡潔に答えてください。"
        "回答末尾に [1] [2] の引用番号を付けてください。"
        "情報が不足している場合は『参考情報からは判断できません』と返してください。"
        f"\n\n# 参考情報\n{context}"
    )
    reply = _llm().invoke([SystemMessage(content=system_text), HumanMessage(content=query)])
    draft = reply.content if isinstance(reply.content, str) else str(reply.content)
    return {"draft": draft, "sources": sources}


def faq_expert_node(state: State) -> dict:
    return _expert_run(state, "faq_expert")


def security_expert_node(state: State) -> dict:
    return _expert_run(state, "security_expert")


def directory_expert_node(state: State) -> dict:
    return _expert_run(state, "directory_expert")


def finalize_node(state: State) -> dict:
    expert = state.get("expert", "faq_expert")
    draft = state.get("draft") or "（応答が生成されませんでした）"
    sources = state.get("sources") or []
    refs = "\n".join(f"[{i}] {s['title']}" for i, s in enumerate(sources, start=1))
    final = f"{draft}\n\n参考（{expert}）:\n{refs}" if refs else draft
    return {"messages": [AIMessage(content=final)]}


def _route(state: State) -> str:
    return state.get("expert") or "faq_expert"


def make_graph(_config: RunnableConfig):
    builder = StateGraph(State)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("faq_expert", faq_expert_node)
    builder.add_node("security_expert", security_expert_node)
    builder.add_node("directory_expert", directory_expert_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        _route,
        {
            "faq_expert": "faq_expert",
            "security_expert": "security_expert",
            "directory_expert": "directory_expert",
        },
    )
    builder.add_edge("faq_expert", "finalize")
    builder.add_edge("security_expert", "finalize")
    builder.add_edge("directory_expert", "finalize")
    builder.add_edge("finalize", END)
    return builder.compile()
