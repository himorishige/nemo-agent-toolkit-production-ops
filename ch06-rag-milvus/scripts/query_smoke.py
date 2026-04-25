"""Smoke-test retrieval against the internal_docs Milvus collection.

Runs three illustrative queries:

1. plain question that should hit the FAQ chunks (PII-free)
2. question that needs department-notes (PII present)
3. question filtered by confidentiality so confidential rows are excluded

Run:
    docker compose --profile query run --rm query
"""

from __future__ import annotations

import json
import os
import sys

from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from pymilvus import MilvusClient

MILVUS_URI = os.environ.get("MILVUS_URI", "http://milvus:19530")
COLLECTION = "internal_docs"
EMBED_MODEL = "nvidia/nv-embedqa-e5-v5"
TOP_K = 3

QUERIES = [
    {
        "label": "FAQ にヒットする想定",
        "text": "経費精算の月次締切日はいつですか？",
        "filter": "",
    },
    {
        "label": "department-notes（PII あり）にヒットする想定",
        "text": "情シス部の担当者の連絡先を教えてください",
        "filter": "",
    },
    {
        "label": "confidential を除外して検索",
        "text": "今期の経営戦略について",
        "filter": "confidentiality != 'confidential'",
    },
]


def main() -> None:
    api_key = os.environ.get("NGC_API_KEY")
    if not api_key:
        sys.exit("NGC_API_KEY is not set")

    embedder = NVIDIAEmbeddings(model=EMBED_MODEL, api_key=api_key)
    client = MilvusClient(uri=MILVUS_URI)

    output_fields = [
        "title",
        "category",
        "department",
        "confidentiality",
        "has_pii",
        "source_path",
    ]

    for q in QUERIES:
        print("=" * 70)
        print(f"Q: {q['text']}  | label={q['label']}")
        if q["filter"]:
            print(f"   filter: {q['filter']}")
        vec = embedder.embed_query(q["text"])
        results = client.search(
            collection_name=COLLECTION,
            data=[vec],
            limit=TOP_K,
            output_fields=output_fields,
            filter=q["filter"] or None,
        )
        for rank, hit in enumerate(results[0], start=1):
            entity = hit.get("entity", {})
            line = {
                "rank": rank,
                "distance": round(float(hit.get("distance", 0.0)), 4),
                "title": entity.get("title"),
                "category": entity.get("category"),
                "department": entity.get("department"),
                "confidentiality": entity.get("confidentiality"),
                "has_pii": entity.get("has_pii"),
                "source": entity.get("source_path"),
            }
            print(json.dumps(line, ensure_ascii=False))


if __name__ == "__main__":
    main()
