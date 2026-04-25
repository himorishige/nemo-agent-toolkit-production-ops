# 社内ドキュメント題材データセット

Zenn Book **NeMo Agent Toolkit 実践運用編** の第 5 章以降で使う、合成された架空企業の社内ドキュメントです。

## ライセンスと注意

- 本データセットの内容はすべて **本書のために合成した架空のもの** です
- 登場する企業名「Example 株式会社」、社員氏名、顧客名、電話番号、メールアドレス、住所、ID 値などは、実在する企業・人物・連絡先と一致するものではありません
- 電話番号は `03-1XXX-XXXX` のような架空形式、メールは `@example.com` ドメインで統一しています
- 配布ライセンスは Apache License 2.0

## 設定（架空）

| 項目     | 値                                                                   |
| -------- | -------------------------------------------------------------------- |
| 企業名   | Example 株式会社                                             |
| 業種     | ソフトウェア / SaaS                                                  |
| 社員数   | 約 300 名                                                            |
| 部署構成 | 営業部 / 開発部 / 人事部 / 情シス部 / カスタマーサポート部 / 経営企画部 |
| ドメイン | `example.com`（架空）                                  |

## ディレクトリ構成

```
internal-docs/
├── handbook/             # 社員ハンドブック（公開〜社内向け、PII 少）
├── it-security/          # IT セキュリティポリシー（社内〜制限）
├── faq/                  # 全社 FAQ（公開〜社内向け）
├── product/              # 製品マニュアル抜粋（公開）
└── department-notes/     # 部署ナレッジ（制限〜機密、PII 多）
```

## メタデータスキーマ

各 Markdown の frontmatter に次のフィールドを持ちます。

| フィールド        | 値                                                                                       |
| ----------------- | ---------------------------------------------------------------------------------------- |
| `title`           | 文書タイトル                                                                             |
| `category`        | `handbook` / `it-security` / `faq` / `product` / `department-notes`                      |
| `department`      | `all` / `sales` / `engineering` / `hr` / `it` / `cs` / `management`                      |
| `confidentiality` | `public` / `internal` / `restricted` / `confidential`                                    |
| `has_pii`         | `true` / `false`                                                                         |
| `pii_types`       | 配列。`name` / `phone` / `email` / `address` / `employee_id` のいずれか（`has_pii: true` のとき） |
| `updated_at`      | 最終更新日（YYYY-MM-DD）                                                                 |

## 統計

合計 16 ファイル。`confidentiality` の分布:

- public: 5 ファイル
- internal: 5 ファイル
- restricted: 4 ファイル
- confidential: 2 ファイル

`has_pii: true` は 4 ファイル（すべて `department-notes/`）に含まれます。第 9 章で Guardrails の PII マスキングテストに使う題材です。
