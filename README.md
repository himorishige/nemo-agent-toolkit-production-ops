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

```bash
git clone https://github.com/himorishige/nemo-agent-toolkit-production-ops.git
cd nemo-agent-toolkit-production-ops

# NAT のベースイメージは前作のものを流用（前作リポでビルド済みであれば不要）
docker build -t nat-nim-handson:1.6.0 docker/nat/  # 前作の Dockerfile を別途取得して配置

# Langfuse v3 self-hosted を起動（第 2 章 / 第 10 章）
cd poc/langfuse
cp .env.example .env  # ENCRYPTION_KEY などのシークレットを生成
docker compose up -d

# Milvus standalone を起動（第 6 章）+ 合成データ ingest
cd ../../ch06-rag-milvus
cp .env.example .env  # NGC_API_KEY を記入
docker compose up -d milvus
docker compose --profile ingest run --rm ingest

# RAG エージェント（第 7 章）を実行
cd ../poc/nat-rag-langgraph
cp .env.example .env
docker compose run --rm nat
```

## 章とディレクトリの対応

書籍の章ごとに、対応するサンプルディレクトリは次のとおりです。

| 章                | ディレクトリ                       | 内容                                                                   |
| ----------------- | ---------------------------------- | ---------------------------------------------------------------------- |
| 第 4 章 (PoC-2)   | `poc/nat-langfuse/`                | hello agent + Langfuse OTLP 直送（最小構成）                           |
| 第 4 章 (PoC-4)   | `poc/nat-langgraph/`               | 最小 LangGraph（classify + respond の 2 ノード）                       |
| 第 5 章           | `datasets/internal-docs/`          | 架空企業の社内文書 16 ファイル（PII / 機密度メタデータ付き、Apache 2.0）|
| 第 6 章           | `ch06-rag-milvus/`                 | Milvus + frontmatter 対応 ingest スクリプト + retrieval スモークテスト |
| 第 7 章           | `poc/nat-rag-langgraph/`           | classify → retrieve → answer の 3 ノード RAG エージェント               |
| 第 8 章           | `poc/nat-guardrails/`              | NeMo Guardrails self_check（Guardrails 主導の 1 ノード構成）           |
| 第 9 章           | `poc/nat-multilingual-safety/`     | Multilingual Safety Guard v3 を NIM 経由で組み込み                     |
| 第 10-11 章       | `poc/langfuse/`                    | Langfuse v3 self-hosted の compose（postgres + clickhouse + minio 等） |
| 第 12 章          | `poc/nat-prompts/`                 | Langfuse Prompts 経由で system prompt を取得（v1/v2 の A/B 比較）      |
| 付録              | `poc/screenshots/`                 | 本書スクショ撮影用の Python スクリプト（Playwright）                   |

第 13 章（コスト追跡・Datasets）と第 14 章（4 本柱統合）の compose / 評価スクリプトは、本リポジトリの順次更新で追加していきます。

## 共通構成

- `docker/nat/` — 全章共通の NAT 実行コンテナ（前作の `nat-nim-handson:1.6.0` イメージを再利用、または `python:3.12-slim` + `nvidia-nat[langchain,mcp,eval,opentelemetry]==1.6.0` でビルド）
- `poc/nat-guardrails/Dockerfile` — NeMo Guardrails 0.21.0 を追加した `nat-prod-ops-guardrails:0.21.0` 派生イメージ
- `poc/nat-prompts/Dockerfile` — langfuse Python SDK を追加した `nat-prod-ops-prompts:1.6.0` 派生イメージ
- `datasets/internal-docs/` — 16 ファイルの社内文書（公開可、Apache 2.0、すべて架空）

## バージョン

| コンポーネント   | バージョン                                       |
| ---------------- | ------------------------------------------------ |
| nvidia-nat       | 1.6.0                                            |
| Python           | 3.12（Docker イメージ側）                        |
| workflow LLM     | `nvidia/llama-3.3-nemotron-super-49b-v1`         |
| Guardrail LLM    | `nvidia/llama-3.1-nemotron-safety-guard-8b-v3`（Multilingual Safety Guard v3）|
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
