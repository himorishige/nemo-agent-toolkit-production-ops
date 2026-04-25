"""Ingest the synthetic internal-docs corpus into Milvus standalone.

Reads frontmatter-annotated Markdown files from /app/datasets/internal-docs,
embeds chunks with NIM nv-embedqa-e5-v5, and writes them to a Milvus
collection together with metadata for category / department / confidentiality.

Run:
    docker compose up -d milvus etcd minio
    docker compose --profile ingest run --rm ingest
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import yaml
from langchain_core.documents import Document
from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pymilvus import DataType, MilvusClient

DOCS_DIR = Path("/app/datasets/internal-docs")
MILVUS_URI = os.environ.get("MILVUS_URI", "http://milvus:19530")
COLLECTION = "internal_docs"
EMBED_MODEL = "nvidia/nv-embedqa-e5-v5"
EMBED_DIM = 1024
CHUNK_SIZE = 500
CHUNK_OVERLAP = 80


def parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter from the body of a markdown file."""
    if not raw.startswith("---\n"):
        return {}, raw
    end = raw.find("\n---\n", 4)
    if end == -1:
        return {}, raw
    meta = yaml.safe_load(raw[4:end]) or {}
    body = raw[end + 5 :]
    return meta, body


def load_documents() -> list[Document]:
    """Walk the corpus directory and return LangChain Documents with metadata."""
    md_files = sorted(p for p in DOCS_DIR.rglob("*.md") if p.name != "README.md")
    print(f"Loading {len(md_files)} markdown files from {DOCS_DIR}")

    documents: list[Document] = []
    for md in md_files:
        text = md.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        documents.append(
            Document(
                page_content=body.strip(),
                metadata={
                    "source_path": str(md.relative_to(DOCS_DIR)),
                    "title": meta.get("title", md.stem),
                    "category": meta.get("category", "unknown"),
                    "department": meta.get("department", "all"),
                    "confidentiality": meta.get("confidentiality", "internal"),
                    "has_pii": bool(meta.get("has_pii", False)),
                    "pii_types": ",".join(meta.get("pii_types", []) or []),
                    "updated_at": meta.get("updated_at", ""),
                },
            )
        )
    return documents


def split_documents(documents: list[Document]) -> list[Document]:
    """Chunk while preserving frontmatter metadata."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    return chunks


def embed_chunks(chunks: list[Document]) -> list[list[float]]:
    api_key = os.environ.get("NGC_API_KEY")
    if not api_key:
        sys.exit("NGC_API_KEY is not set")

    embedder = NVIDIAEmbeddings(model=EMBED_MODEL, api_key=api_key)
    texts = [chunk.page_content for chunk in chunks]
    vectors = embedder.embed_documents(texts)
    print(f"Embedded {len(vectors)} chunks with {EMBED_MODEL}")
    return vectors


def write_to_milvus(chunks: list[Document], vectors: list[list[float]]) -> None:
    client = MilvusClient(uri=MILVUS_URI)

    if client.has_collection(COLLECTION):
        client.drop_collection(COLLECTION)

    schema = client.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field("id", DataType.INT64, is_primary=True)
    schema.add_field("vector", DataType.FLOAT_VECTOR, dim=EMBED_DIM)
    schema.add_field("text", DataType.VARCHAR, max_length=4096)
    schema.add_field("source_path", DataType.VARCHAR, max_length=256)
    schema.add_field("title", DataType.VARCHAR, max_length=256)
    schema.add_field("category", DataType.VARCHAR, max_length=64)
    schema.add_field("department", DataType.VARCHAR, max_length=64)
    schema.add_field("confidentiality", DataType.VARCHAR, max_length=32)
    schema.add_field("has_pii", DataType.BOOL)
    schema.add_field("pii_types", DataType.VARCHAR, max_length=256)
    schema.add_field("updated_at", DataType.VARCHAR, max_length=32)

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="vector",
        index_type="AUTOINDEX",
        metric_type="L2",
    )

    client.create_collection(
        collection_name=COLLECTION,
        schema=schema,
        index_params=index_params,
    )

    payload = [
        {
            "id": i,
            "vector": vec,
            "text": chunk.page_content[:4000],
            "source_path": chunk.metadata["source_path"],
            "title": chunk.metadata["title"],
            "category": chunk.metadata["category"],
            "department": chunk.metadata["department"],
            "confidentiality": chunk.metadata["confidentiality"],
            "has_pii": chunk.metadata["has_pii"],
            "pii_types": chunk.metadata["pii_types"],
            "updated_at": chunk.metadata["updated_at"],
        }
        for i, (vec, chunk) in enumerate(zip(vectors, chunks, strict=True))
    ]

    result = client.insert(collection_name=COLLECTION, data=payload)
    inserted = result.get("insert_count", len(payload))
    print(f"Inserted {inserted} records into '{COLLECTION}' at {MILVUS_URI}")

    by_cat: dict[str, int] = {}
    by_conf: dict[str, int] = {}
    for c in chunks:
        by_cat[c.metadata["category"]] = by_cat.get(c.metadata["category"], 0) + 1
        by_conf[c.metadata["confidentiality"]] = by_conf.get(c.metadata["confidentiality"], 0) + 1
    print(f"chunks by category: {by_cat}")
    print(f"chunks by confidentiality: {by_conf}")


def main() -> None:
    docs = load_documents()
    chunks = split_documents(docs)
    vectors = embed_chunks(chunks)
    write_to_milvus(chunks, vectors)
    print("Done.")


if __name__ == "__main__":
    main()
