---
title: "ExampleFlow API リファレンス（抜粋）"
category: product
department: all
confidentiality: public
has_pii: false
updated_at: "2026-04-18"
---

# ExampleFlow API リファレンス（抜粋）

ExampleFlow の REST API のうち、よく使われるエンドポイントの抜粋です。完全版は開発者ポータルにあります。

## 認証

- 認証方式: Bearer トークン（個人 API キー、または OAuth 2.0）
- 個人 API キーは ExampleFlow の「設定 → API キー」から発行

## エンドポイント一覧

### `GET /api/v1/flows`

ユーザーがアクセスできるフロー一覧を返します。

- クエリ: `status` (active / archived), `limit` (default 50)
- レスポンス: `{"data": [{"id": "...", "name": "...", ...}]}`

### `POST /api/v1/flows/{flowId}/runs`

指定フローの新規実行を開始します。

- リクエスト body: `{"input": {...}}`
- レスポンス: `{"runId": "...", "status": "pending"}`

### `GET /api/v1/runs/{runId}`

実行ステータスを取得します。

- レスポンス: `{"runId": "...", "status": "running" | "succeeded" | "failed", "output": {...}}`

## レート制限

- Starter プラン: 60 リクエスト / 分
- Standard プラン: 600 リクエスト / 分
- Enterprise プラン: 個別設定

## サンプル

```bash
curl -X POST https://api.exampleflow.example.com/api/v1/flows/flow_123/runs \
  -H "Authorization: Bearer ${EXAMPLEFLOW_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"input": {"customer": "Acme Corp"}}'
```

## サポート

API 関連の質問は開発者向けフォーラムをご利用ください。
