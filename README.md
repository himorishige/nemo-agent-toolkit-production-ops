# NeMo Agent Toolkit 実践運用編 サンプルコード

Zenn Book **NeMo Agent Toolkit 実践運用編 — Guardrails × Langfuse で本番投入する**（仮タイトル、`nemo-agent-toolkit-production-ops` slug 予定）のサンプルコード配布リポジトリです。

前作 [NIM + Docker ではじめる NeMo Agent Toolkit ハンズオン](https://zenn.dev/himorishige/books/nemo-agent-toolkit-nim-handson) の続編で、NAT を **production grade に昇華する 4 本柱**（Orchestration / Guardrails / Observability / Eval Dataset）を社内ドキュメント Q&A 題材で扱います。

各章の完成コードを `chNN-{topic}/` に置き、章ごとに `docker compose up` で動作確認できる構成です。

## Prerequisites

- Docker（Colima 推奨 / Docker Desktop / native Docker Engine）
- NGC API key（[build.nvidia.com](https://build.nvidia.com) で取得、Developer 無料枠あり）
- Python は不要（Docker コンテナ内で完結）
- 推奨リソース: Colima 6CPUs / 12GB / 40GB disk（前作 4CPUs / 8GB から増量）

## クイックスタート

各章の README を参照してください。Sprint 1 着手後に章ディレクトリを順次追加します。

## 章別ディレクトリ（予定）

| 章   | ディレクトリ                  | 内容                                                                        |
| ---- | ----------------------------- | --------------------------------------------------------------------------- |
| 04   | `ch04-langgraph/`             | LangGraph を NAT function として組み込む最小実装                            |
| 05   | `ch05-corpus/`                | 社内ドキュメント題材データセット（PII 含むサンプル、Apache 2.0 互換）      |
| 06   | `ch06-rag-milvus/`            | Milvus + nv-embedqa-e5-v5 で社内文書 RAG（前作 ch09 をベースに拡張）       |
| 07   | `ch07-langgraph-rag/`         | LangGraph state graph + RAG 統合エージェント                                |
| 08   | `ch08-guardrails-basics/`     | NeMo Guardrails 入門 — Colang 1.0 と input/output rails 最小構成           |
| 09   | `ch09-llama-guard/`           | Multilingual Safety Guard / Llama Guard 4 を NIM で動かしてレールに統合   |
| 10   | `ch10-langfuse-selfhosted/`   | Langfuse v3 self-hosted（Postgres + ClickHouse + Redis + MinIO）           |
| 11   | `ch11-nat-langfuse-otlp/`     | NAT → Langfuse OTLP 接続 + Agent Graph 可視化                              |
| 12   | `ch12-prompt-management/`     | Langfuse Prompt 登録 / version 管理 + A/B テスト                            |
| 13   | `ch13-cost-and-datasets/`     | コスト・トークン追跡 + Langfuse Datasets で RAG 評価                        |
| 14   | `ch14-final/`                 | 4 本柱統合 — production 想定アプリ                                          |
| 付録A | `appendixA-phoenix-migration/` | Phoenix → Langfuse 移行ガイド                                                |
| 付録B | `appendixB-langfuse-cloud/`   | Langfuse Cloud と self-hosted の使い分け                                    |

## 共通構成（予定）

- `docker/nat/` — 全章共通の NAT 実行コンテナ（前作と同じ `python:3.12-slim` ベース、`nvidia-nat[langchain,mcp,eval,opentelemetry]==1.6.0`）
- `docker/langfuse/` — Langfuse v3.22+ self-hosted compose の共通設定
- `datasets/internal-docs/` — Ch 5 以降で使う社内ドキュメント題材（PII 含む合成データ、Apache 2.0）
- `ch13-cost-and-datasets/dataset/` — 評価用データセット

## バージョン

| コンポーネント   | バージョン                                       |
| ---------------- | ------------------------------------------------ |
| nvidia-nat       | 1.6.0                                            |
| Python           | 3.12（Docker イメージ側）                        |
| workflow LLM     | `nvidia/llama-3.3-nemotron-super-49b-v1`         |
| Guardrail LLM    | 日本語強化モデル選定中（Sprint 0 追加調査後確定）|
| Embedding        | `nvidia/nv-embedqa-e5-v5`                        |
| NeMo Guardrails  | v0.21.0（Colang 1.0）                            |
| Langfuse         | v3.22+（self-hosted、`/api/public/otel` 必須）   |
| Milvus           | `milvusdb/milvus:v2.5.4`                         |

## Python コードの lint / format

```bash
uvx ruff check .
uvx ruff format .
uvx ruff format --check .
```

## License

Apache License 2.0。詳細は [LICENSE](./LICENSE) を参照してください。

`datasets/internal-docs/` 配下のサンプルデータは本書のために合成した PII 含む架空データで、Apache 2.0 で配布します。
