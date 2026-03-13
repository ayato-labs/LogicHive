---
title: "AIが毎回同じコードを生成し直すのが不満すぎたので、エージェント用の関数リポジトリを作ってみた"
emoji: "🧠"
type: "tech"
topics: ["MCP", "AI", "Supabase", "pgvector", "Python"]
published: false
---

## はじめに: 同じコード、何回書かせるんだ問題

Cursor や Claude Desktop などの AI エディタを日常的に使っていると、ある違和感に気づく。

**「この sort の比較関数、先週も書かせたよな...？」**

AI は賢い。だが、記憶力がない。
セッションが切り替わるたびに、昨日完璧に生成してくれたユーティリティ関数の存在を忘れ、ゼロから似たようなコードを組み立て直す。しかも、毎回微妙にクオリティが違う。

npm や PyPI に上げるほどでもない。Gist に放り込んでも、AI が自発的にそれを探しに行ってくれるわけでもない。
**「AI エージェントが自分で貯めて、自分で引き出せる関数の貯金箱」が欲しい。**

この不満から生まれたのが、[**LogicHive**](https://github.com/Ayato-AI-for-Auto/LogicHive) だ。

---

## LogicHive とは何か

LogicHive は、**AI エージェントが生成したコードを蓄積・検索・再利用するための MCP (Model Context Protocol) サーバー**だ。

ユーザー（人間）が直接操作する UI は存在しない。
AI エディタに対して「LogicHive から entropy の計算関数を探して」と指示するだけで、エージェントが自律的にベクトル検索を実行し、最適な関数を見つけてプロジェクトに注入してくれる。

```
ユーザー: 「エントロピー計算の関数、LogicHive にある？」
  ↓
AI Agent (MCP): LogicHive Hub にクエリ送信
  ↓
Hub (GCP): Supabase でセマンティック検索 → 類似度 0.82 の関数を発見
  ↓
AI Agent: 「ありました。calculate_shannon_entropy です。プロジェクトに追加しますか？」
```

### なぜ npm / PyPI / Gist ではダメなのか

| 観点 | npm / PyPI | GitHub Gist | LogicHive |
| :--- | :--- | :--- | :--- |
| AI からの直接検索 | 不可（人間が手動で探す） | 不可 | MCP 経由で自然言語検索 |
| 粒度 | パッケージ単位（重い） | ファイル単位（雑多） | **関数単位**（最適化） |
| 品質管理 | 手動レビュー / CI | なし | LLM による自動品質評価 |
| 重複排除 | なし | なし | **セマンティック重複検知** |

核心は「**関数単位**」で管理している点だ。
40 行の便利関数を共有するためだけに、`pyproject.toml` を書いて PyPI に公開する人はいない。LogicHive はその隙間を埋める。

---

## アーキテクチャ: Edge-Cloud Hybrid

LogicHive は「Edge（ローカル）」と「Hub（クラウド）」の 2 層で構成されている。

```
┌───────────────────────────┐     ┌──────────────────────────────┐
│  Edge (ユーザーの PC)      │     │  Hub (GCP Cloud Run)         │
│                           │     │                              │
│  Cursor / Claude Desktop  │     │  FastAPI (Stateless)         │
│       ↕ MCP Protocol      │────→│   ├─ Security Gate (AST)     │
│  LogicHive Edge Client    │     │   ├─ Embedding (768d)        │
│                           │     │   └─ Consolidation (LLM)     │
└───────────────────────────┘     │         ↕                    │
                                  │  Supabase (pgvector)         │
                                  └──────────────────────────────┘
```

### なぜ 2 層に分けたのか

1. **API キーを預からない**
   ユーザーの Gemini API Key を Hub に送信することは一切ない。キーはローカル環境（Edge）でのみ保持される。これにより、運営側（つまり自分）に API キーの管理責任が発生しないようにした。

2. **知的財産の秘匿**
   「どんなプロンプトで品質を評価するか」「どうやって重複を判定するか」というロジックは、競合に知られたくない部分だ。これを GCP の裏側に配置することで、リバースエンジニアリングを防いでいる。

3. **コスト最小化**
   Hub はステートレスな推論エンジンに徹し、永続化は Supabase の Free Tier に完全に委譲している。アクセスがなければ Cloud Run のインスタンスはゼロになり、維持費はほぼ $0 だ。

---

## 技術スタック詳細

### ベクトル検索: pgvector + gemini-embedding-001

関数の検索には、Google の `gemini-embedding-001` モデルで生成した **768 次元のベクトル**を使用している。

```python
# Hub 側での Embedding 生成
from google import genai

client = genai.Client(api_key=api_key)
result = client.models.embed_content(
    model="gemini-embedding-001",
    contents=text,
    config=types.EmbedContentConfig(output_dimensionality=768)
)
embedding = result.embeddings[0].values  # 768-dim vector
```

Supabase (PostgreSQL) に `pgvector` 拡張を入れ、`vector(768)` 型のカラムでコサイン類似度検索を行う。

```sql
-- match_functions RPC
SELECT name, code, description,
       1 - (embedding <=> query_embedding) AS similarity
FROM logichive_functions
WHERE 1 - (embedding <=> query_embedding) > match_threshold
ORDER BY embedding <=> query_embedding
LIMIT match_count;
```

### 開発中にハマった罠: Embedding Dimension の不一致

`gemini-embedding-001` はデフォルトで **3072 次元**のベクトルを返す。
しかし Supabase Free Tier のストレージを考慮して、MRL (Matryoshka Representation Learning) を活用し **768 次元に圧縮**した。

ここで地獄を見た。

**保存時に `output_dimensionality=768` を指定していたが、検索時の SQL 関数 (`match_functions`) が古い次元数のまま残っていた。** 結果、データは入るのに検索結果が常にゼロ件という、原因特定が極めて困難なバグに半日悩まされた。

教訓: **ベクトルDBの次元数は、保存側・検索側・SQL関数の 3 箇所すべてで厳密に一致させること。** 1 箇所でもズレるとサイレントに失敗する。

### セキュリティ: AST ベースの静的解析

ユーザーから送られてくるコードを無条件に保存するわけにはいかない。
Hub は受信したコードを Python の `ast` モジュールでパースし、危険なインポートや関数呼び出しを検出する。

```python
FORBIDDEN_IMPORTS = {"os", "sys", "subprocess", "shutil", "pickle", ...}
FORBIDDEN_CALLS = {"eval", "exec", "system", "popen", ...}
```

ここでも罠があった。`re.compile()` のような完全に安全な標準ライブラリの呼び出しが、`compile` というキーワードだけでブロックされてしまった。**属性呼び出し (`re.compile`) と直接呼び出し (`compile()`) を区別するロジック**を追加して解決した。

---

## 使い方

### 1. インストール

```bash
git clone https://github.com/Ayato-AI-for-Auto/LogicHive.git
cd LogicHive
uv run logic-hive-setup
```

### 2. MCP 設定

```json
{
  "mcpServers": {
    "logic-hive": {
      "command": "uv",
      "args": ["--directory", "/path/to/LogicHive", "run", "mcp-server"]
    }
  }
}
```

### 3. AI に指示するだけ

```
「LogicHive から、テキストの絵文字を除去する関数を探して」
「今作ったこのユーティリティ関数を LogicHive に保存して」
```

---

## 現状と正直な課題

**現在 MVP フェーズであり、実ユーザーはまだいない。** これは正直に書いておく。

### 今できること
- 関数の Push（登録）と Semantic Search（自然言語検索）
- AST ベースのセキュリティチェック
- 768 次元ベクトルによるコサイン類似度検索

### まだできないこと
- Edge クライアントと Hub の完全な E2E 統合（現在は Hub の API を直接叩く形）
- LLM による本格的な品質評価・リランキング（スタブ状態）
- チーム / 組織単位での Private リポジトリ機能

### ライセンスに関する重要事項
MVP フェーズでは、登録されたコードは **MIT ライセンス**が自動適用され、全世界に公開される。企業秘密や個人情報を含むコードは絶対に登録しないでほしい。

---

## 今後のロードマップ

1. **Edge-Hub 完全統合**: MCP ツール呼び出しから Hub への Push/Search をシームレスに。
2. **Intelligence-Driven Compression**: 意味的に同じ関数を LLM が自動マージし、DB の純度を極限まで高める。
3. **Team / Enterprise**: 社内チーム専用の Private リポジトリを提供する SaaS モデルへの移行。

---

## おわりに

LogicHive は、「AI が毎回同じコードを書き直す無駄」という素朴な不満から生まれた。

技術的にはまだ粗削りだが、**「AI エージェントが自分で知識を蓄え、自分で再利用する」**という方向性自体は、間違っていないと信じている。

興味がある方は、ぜひリポジトリを覗いてみてほしい。Issue や PR も歓迎だ。

**GitHub**: [https://github.com/Ayato-AI-for-Auto/LogicHive](https://github.com/Ayato-AI-for-Auto/LogicHive)

---

*この記事は LogicHive の開発者（個人開発）が執筆しています。*
