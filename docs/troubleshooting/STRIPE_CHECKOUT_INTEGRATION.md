# Stripe Checkout 連携トラブルシューティング

- **発生日**: 2026-02-28
- **影響範囲**: Ayato Studio Portal -> LogicHive Hub -> Stripe 間の決済フロー全体
- **最終状態**: 解決済み

---

## 概要

Ayato Studio Portal の「Subscribe Now」ボタンから Stripe Checkout ページへの遷移が、複数の原因により失敗していた。
本ドキュメントでは、発生した問題を発生順に記録し、それぞれの原因と解決策を示す。

---

## 問題 1: `column organizations.user_id does not exist`

### 症状
```
Organization onboarding error: {}
Fetch Org Error details: {message: 'column organizations.user_id does not exist', code: '42703'}
```

### 原因
フロントエンド (`api.ts`) の `ensureOrganization()` が `organizations` テーブルを `user_id` カラムでフィルタリングしていたが、Supabase 上のテーブルにはこのカラムが存在していなかった。

### 解決策
Supabase SQL Editor で以下を実行：
```sql
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id);
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can see their own orgs" ON organizations
    FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Users can insert their own orgs" ON organizations
    FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Service role access" ON organizations
    FOR ALL TO service_role USING (true);
```

### 再発防止策
- マイグレーションスクリプト（`scripts/migrate.py`）にスキーマ変更を必ず含める。
- フロントエンドのコードがDBカラムを参照する場合、事前にスキーマの存在を確認する。

---

## 問題 2: `stripe` ライブラリ未インストール

### 症状
Hub バックエンドが `500 Internal Server Error` を返し、ログにも何も残らない（`import stripe` で即クラッシュ）。

### 原因
`LogicHive-Hub-Private/pyproject.toml` の `dependencies` に `stripe` が含まれていなかった。

### 解決策
```toml
# pyproject.toml
dependencies = [
    # ... 既存の依存関係 ...
    "stripe",  # <-- 追加
]
```
```bash
uv pip install -e .
```

### 再発防止策
- 新しい外部 API を使用する際は、必ず `pyproject.toml` に依存関係を追加してからコードを書く。
- CI/CD パイプラインでの `import` チェックを検討する。

---

## 問題 3: ポート番号の不一致 (8080 vs 8000)

### 症状
```
POST http://localhost:8080/api/v1/billing/checkout net::ERR_FAILED
```

### 原因
| コンポーネント | 設定値 | ファイル |
|---|---|---|
| Hub `app.py` デフォルト | `8080` | `backend/hub/app.py` |
| Hub `.env` | `8000` | `backend/.env` |
| Portal `.env.local` | `8080` (誤) | `ayato_studio_portal/.env.local` |

Hub は `.env` で `PORT=8000` を指定して起動していたが、Portal 側は古いデフォルト値 `8080` を参照していた。

### 解決策
- Portal の `.env.local`:
  ```
  NEXT_PUBLIC_LOGICHIVE_HUB_URL=http://127.0.0.1:8000
  ```
- Hub の `app.py` を `core.config` から `HOST`, `PORT` をインポートするようにリファクタリングし、設定の一元管理を実現。

### 再発防止策
- ポート番号はすべて `core/config.py` と各 `.env` ファイルに一元管理する。
- README にローカル開発セットアップ手順を記載し、ポート番号を明示する。

---

## 問題 4: CORS ブロック（ブラウザ → Hub 直接通信）

### 症状
```
Access to fetch at 'http://localhost:8000/...' from origin 'http://localhost:3001'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present
```

### 原因（複合的）
1. `allow_origins=["*"]` + `allow_credentials=True` の組み合わせは、ブラウザの仕様上無効。
2. Hub バックエンドで 500 エラーが発生した場合、FastAPI の `CORSMiddleware` はエラーレスポンスに CORS ヘッダーを付与しない。そのため、真の原因（DB エラー）が CORS エラーとしてマスクされていた。
3. `localhost` と `127.0.0.1` はブラウザ上では別オリジンとして扱われる場合がある。

### 解決策（アーキテクチャ変更）
**ブラウザから Hub への直接通信を廃止し、Next.js API Route によるサーバーサイドプロキシを導入。**

```
[ブラウザ] --同一オリジン--> [Next.js API /api/logichive/checkout]
                               |
                       サーバー間通信（CORS不要）
                               |
                           [Hub API]
```

- 新規ファイル: `src/app/api/logichive/checkout/route.ts`
- `api.ts` の `createCheckoutSession()` を `/api/logichive/checkout` に向けて修正。

### 再発防止策
- **ブラウザから外部バックエンドへの直接通信は避ける。** Next.js の API Route をプロキシとして活用する。
- Hub 側の CORS 設定は、明示的なオリジンリストで管理する（ワイルドカード `*` は使わない）。

---

## 問題 5: `column organizations.stripe_customer_id does not exist`

### 症状
```
Billing error: {'message': 'column organizations.stripe_customer_id does not exist', 'code': '42703'}
```

### 原因
問題 1 と同じく、Billing 用のカラム (`stripe_customer_id`, `plan_type`, `request_limit` 等) が Supabase 上に未作成だった。Hub のコード (`billing_checkout`) はこれらのカラムの存在を前提としていた。

### 解決策
Supabase SQL Editor で以下を実行：
```sql
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS plan_type TEXT DEFAULT 'free';
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active';
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS request_limit INTEGER DEFAULT 100;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS current_usage_count INTEGER DEFAULT 0;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS plan_start_date TIMESTAMPTZ DEFAULT NOW();
```

### 再発防止策
- **全てのスキーマ変更を `scripts/migrate.py` または `backend/hub/schema.sql` にバージョン管理する。**
- デプロイ前にスキーマの差分チェックを行うスクリプトを導入する。

---

## 修正ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `LogicHive-Hub-Private/pyproject.toml` | `stripe` 依存追加 |
| `LogicHive-Hub-Private/backend/hub/app.py` | CORS 明示化、`billing_checkout` にエラーハンドリング追加、`config` からポート読込 |
| `ayato_studio_portal/.env.local` | Hub URL を `http://127.0.0.1:8000` に修正 |
| `ayato_studio_portal/src/lib/api.ts` | プロキシ経由に変更、`logicHiveHubUrl` の定義位置修正 |
| `ayato_studio_portal/src/app/api/logichive/checkout/route.ts` | 新規作成（サーバーサイドプロキシ） |
| Supabase `organizations` テーブル | `user_id`, `stripe_customer_id` 等のカラム追加、RLS ポリシー設定 |

---

## 教訓

1. **「CORS エラー」は表面的な症状に過ぎない場合がある。** バックエンドの 500 エラーが CORS ヘッダーなしで返却されると、ブラウザは CORS 違反として報告する。真の原因はサーバーログで確認すること。
2. **スキーマ変更は必ずバージョン管理する。** コードが参照するカラムが DB に存在しない場合、実行時エラーとなり、デバッグが困難になる。
3. **ブラウザ→外部サービス間通信にはプロキシパターンを採用する。** CORS の設定漏れやブラウザ固有の制約（Private Network Access等）を回避できる。
4. **依存関係は `pyproject.toml` で一元管理する。** ライブラリの未インストールはログに痕跡を残さず 500 エラーを引き起こすため、発見が困難。
