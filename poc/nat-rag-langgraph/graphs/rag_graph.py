"""3-node LangGraph for internal-doc Q&A.

classify -> retrieve -> answer.

The classify node tags the question with one of five buckets
(faq / handbook / it-security / department-notes / general).
The retrieve node queries Milvus with optional metadata filters derived
from the bucket. The answer node composes a Japanese reply with citations.
"""

from __future__ import annotations

import os
from typing import Annotated, Any

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
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

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "faq": ("faq", "経費", "申請", "休暇", "問い合わせ", "FAQ"),
    "handbook": ("オンボーディング", "入社", "ハンドブック", "オフィス", "福利厚生"),
    "it-security": ("セキュリティ", "アカウント", "パスワード", "VPN", "デバイス", "インシデント"),
    "department-notes": ("連絡先", "担当者", "部長", "電話", "顧客"),
}


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    bucket: str | None
    retrieved: list[dict[str, Any]] | None


def classify_node(state: State) -> dict:
    last = state["messages"][-1]
    text = last.content if isinstance(last.content, str) else ""
    for bucket, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return {"bucket": bucket}
    return {"bucket": "general"}


def _milvus_filter(bucket: str) -> str | None:
    """Map the classified bucket to a Milvus boolean expression."""
    if bucket in {"faq", "handbook", "it-security", "department-notes"}:
        # category 一致と confidential 除外を組み合わせる
        return f"category == '{bucket}' && confidentiality != 'confidential'"
    return "confidentiality != 'confidential'"


def retrieve_node(state: State) -> dict:
    last = state["messages"][-1]
    query = last.content if isinstance(last.content, str) else ""
    embedder = NVIDIAEmbeddings(
        model=EMBED_MODEL,
        api_key=os.environ["NGC_API_KEY"],
    )
    vec = embedder.embed_query(query)

    client = MilvusClient(uri=MILVUS_URI)
    bucket = state.get("bucket") or "general"
    expr = _milvus_filter(bucket)
    results = client.search(
        collection_name=COLLECTION,
        data=[vec],
        limit=TOP_K,
        output_fields=[
            "title",
            "category",
            "confidentiality",
            "has_pii",
            "source_path",
            "text",
        ],
        filter=expr,
    )

    retrieved: list[dict[str, Any]] = []
    for hit in results[0]:
        entity = hit.get("entity", {}) or {}
        retrieved.append(
            {
                "title": entity.get("title"),
                "category": entity.get("category"),
                "confidentiality": entity.get("confidentiality"),
                "has_pii": entity.get("has_pii"),
                "source": entity.get("source_path"),
                "text": entity.get("text", ""),
                "distance": float(hit.get("distance", 0.0)),
            }
        )
    return {"retrieved": retrieved}


def _format_context(docs: list[dict[str, Any]]) -> str:
    if not docs:
        return "（参考情報は見つかりませんでした）"
    blocks = []
    for i, d in enumerate(docs, start=1):
        head = f"[{i}] {d['title']}（{d['source']}）"
        blocks.append(f"{head}\n{d['text']}")
    return "\n\n".join(blocks)


def answer_node(state: State) -> dict:
    bucket = state.get("bucket", "general")
    docs = state.get("retrieved") or []
    context = _format_context(docs)

    system_text = (
        "あなたはアサヒシステムズ株式会社の社内文書 Q&A アシスタントです。"
        f"質問種別は {bucket} です。"
        "以下の参考情報のみに基づいて、日本語で 1〜3 文で簡潔に答えてください。"
        "回答末尾に [1] や [2] の引用番号を付け、『参考』として参考情報の見出しを列挙してください。"
        "情報が不足している場合は『参考情報からは判断できません』と答えてください。"
        "\n\n# 参考情報\n"
        f"{context}"
    )

    llm = ChatNVIDIA(
        model="nvidia/llama-3.3-nemotron-super-49b-v1",
        api_key=os.environ["NGC_API_KEY"],
        base_url="https://integrate.api.nvidia.com/v1",
        temperature=0.0,
        max_tokens=512,
    )
    history = [SystemMessage(content=system_text), *state["messages"]]
    reply = llm.invoke(history)
    if not isinstance(reply, AIMessage):
        reply = AIMessage(content=str(reply.content))
    return {"messages": [reply]}


def make_graph(_config: RunnableConfig):
    builder = StateGraph(State)
    builder.add_node("classify", classify_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("answer", answer_node)
    builder.add_edge(START, "classify")
    builder.add_edge("classify", "retrieve")
    builder.add_edge("retrieve", "answer")
    builder.add_edge("answer", END)
    return builder.compile()
