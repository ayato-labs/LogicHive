# LogicHive Hub & Edge トラブルシューティング記録

このドキュメントは、LogicHive の Hub (Cloud Run) および Edge (ローカルMCPクライアント) の開発・運用フェーズにおいて発生した特有のトラップと、その解決策を記録したものです。

## 1. Supabase ベクトル検索で「常に0件」になる問題

### 現象
- `push` された関数データが Supabase の `logichive_functions` テーブルに正常に保存されている（API のステータスコードは 200）。
- しかし、直後に同じ内容で `search` を行っても、検索結果（RPC `match_functions` の戻り値）が常に空のリスト `[]` になる。

### 原因：Embedding次元数の不一致 (The Dimension Mismatch Trap)
Google の `gemini-embedding-001` モデルはデフォルトで **3072次元** のベクトルを出力します。API リクエスト時に `output_dimensionality=768` を指定することで 768次元に圧縮できます。
問題は、データベース側の定義がそれに追いついていない場合に起こります。

Python (Hub API) 側では 768次元でベクトルを生成して Supabase に送信できても、**Supabase側のテーブル定義、または検索用の SQL RPC 関数のパラメータ定義が 3072次元のまま（あるいは不一致な次元数）であると、PostgreSQL 側で暗黙の型エラーが発生し、検索結果がサイレントに 0件になります。**

### 解決策
1. **テーブル定義の修正**:
   `logichive_functions` テーブルの `embedding` カラムを `vector(768)` に明示的に設定する。
2. **RPC 定義の修正**:
   検索を実行する関数 `match_functions` の引数 `query_embedding` の型を `vector(768)` に指定する。

```sql
-- テーブル再構築例
CREATE TABLE logichive_functions (
    -- ...
    embedding vector(768),
    -- ...
);

-- RPC再構築例
CREATE OR REPLACE FUNCTION match_functions (
    query_embedding vector(768),
    match_threshold float,
    match_count int
)
-- ...
```
**教訓**: ベクトル検索エンジンを扱う際は、「生成モデルの出力次元」「テーブルカラムの次元」「検索関数の引数次元」の**3箇所すべてが完全に一致していること**を常に確認する必要があります。

---

## 2. 実用的な標準ライブラリが AST Security Gate に弾かれる問題

### 現象
- Hubのエンドポイントに安全なユーティリティ関数（例：`re.compile()` を使用する関数）を `push` すると、`403 Forbidden: Security Violation: Attribute call 'compile' is forbidden.` としてハジかれる。

### 原因：属性呼び出しの過剰ブロック
Hub に実装されている `ASTSecurityChecker` は、悪意のあるコード（例: `eval()`, `exec()`, `compile()`）を防ぐために用意されています。
当初、組込関数の `compile` を禁止するために、これを `FORBIDDEN_CALLS` というリストに入れていました。しかし、このリストに含まれるキーワードはメソッドアクセス（例：`module.function()` の `function` 部分）であってもブロックするように実装されていました。
そのため、`re.compile` のような完全に無害な関数呼び出しまで過剰にブロックしてしまっていました。

### 解決策
`compile` のような「組み込み関数としては危険だが、モジュールのメソッド名としてはありふれているもの」を `FORBIDDEN_CALLS` から外し、**直接呼び出しのみをブロックする `FORBIDDEN_BUILTINS` に移動**させました。

```python
# 修正前：属性呼び出しでも一律ブロックされるリスト
FORBIDDEN_CALLS = {
    "eval", "exec", "compile", "breakpoint", "__import__",
    "system", "popen", "spawn", "fork", "kill"
}

# 修正後：
FORBIDDEN_CALLS = {
    "eval", "exec", "breakpoint", "__import__",
    "system", "popen", "spawn", "fork", "kill"
}
FORBIDDEN_BUILTINS = {
    "open", "getattr", "setattr", "delattr", "hasattr", 
    "globals", "locals", "vars", "dir", "help", "input", "compile"
}
```
**教訓**: 静的コード解析によるセキュリティゲートを設ける場合、Pythonの「組み込み関数」と「オブジェクトのメソッド（属性）」を厳密に区別するロジックを組まないと、実用的な関数の登録を妨げるボトルネックになり得ます。
