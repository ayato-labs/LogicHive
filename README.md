# 🛡️ LogicHive: Private AI Logic Hub

LogicHiveは、エンジニアが「一度書いた最高の実装」を資産として蓄積し、AIエージェント（Antigravity, Cursor, Gemini等）を通じて瞬時に呼び出し・再利用するためのプライベート・ロジック・ハブです。

## 🌟 主な特徴
- **プライベート運用**: SQLite (WALモード) を使用した高速・セキュアなローカル環境。
- **インテリジェント検索**: ベクトル検索とLLMによるリランキングを組み合わせた高度なセマンティック検索。
- **エージェント協調**: MCP（Model Context Protocol）を通じて、AIエージェントと対話的にロジックを統合。

---

## 🚀 セットアップ

### 1. 依存関係のインストール
`uv` を使用して、プロジェクトの依存関係をインストールします。

```powershell
uv pip install -e .
```

### 2. MCPの登録（自動設定）
プロジェクトルートにある `register_mcp.bat` を実行してください。以下の設定が自動で行われます。

- **`mcp_config.json` の自動編集**: 以下の各エージェントの構成ファイルに `logic-hive` サーバーを登録します。
    - Antigravity: `~/.gemini/antigravity/mcp_config.json`
    - Cursor: `%APPDATA%/Cursor/User/globalStorage/heavy.cursor.cursor/mcp_config.json`
    - Cloud Code: `%APPDATA%/Code/User/globalStorage/googlecloudtools.cloudcode/mcp_config.json`
- **指示の自動注入**: `~/.gemini/GEMINI.md` 等へ「LogicHiveを活用する」というルールを追記します。

### 3. システムの起動
以下のいずれかの方法で LogicHive Hub（APIサーバー）を起動できます。

- **バッチファイルで起動**: プロジェクトルートの `run.bat` をダブルクリックします。
- **Pythonで起動**: プロジェクトルートで `uv run run.py` を実行します。

起動後、コンソールに表示される「MCP CONFIG HINT」の内容を各エージェントの `mcp_config.json` に設定することで、AIエージェントから LogicHive の機能を利用可能になります。

> [!TIP]
> ファイルパスは環境によって異なります。手動で設定したい場合やパスを確認したい場合は、`python src/app.py` を実行すると、その環境に最適な JSON 設定例がコンソールに表示されます。

---

## 🤖 AIエージェントとの連携

### 🌌 Antigravity
Antigravityは、`~/.gemini/GEMINI.md` に記載されたルールに従って動作します。
`register_mcp.bat` を実行すると、自動的に以下のルールが追加されます：
- `- function-storeっていうMCPを活用してください。`

エージェントが「〜する機能はない？」と尋ねられた際、自動的に LogicHive を検索するようになります。

### ♊ Gemini CLI / Cloud Code
`mcp_config.json` を通じてツールとして認識されます。
エージェントに対して直接「LogicHiveで〜を検索して」と指示を出すことが可能です。

---

## 🔄 開発ワークフロー（思想）

1. **Request (探索)**: 
   CursorやAntigravityに「〜する処理が欲しい」とリクエスト。
2. **Retrieve (抽出)**: 
   LogicHive MCPが `search_functions` ツールを使用して、過去の良質なロジックを提案。
3. **Adaptation (適合)**: 
   エージェントが、提案されたコードを現在のプロジェクトの型や変数名に適合させる。
   > **Note**: LogicHive側での自動加工は行いません。常に最新で強力な「エージェント側のLLM」に微調整を任せるのが設計思想です。
4. **Registration (資産化)**: 
   うまく動作した洗練されたコードを `save_function` で LogicHive に再登録。

---

## 🛠️ MCP ツール一覧
- `search_functions(query)`: 自然言語でロジックを検索。
- `get_function(name)`: 特定の関数のソースコードを全文取得。
- `save_function(name, code, description, tags)`: 新しいロジックを永久保存。

## 📖 詳細な思想
詳細は [docs/LogicHiveの設計思想.md](docs/LogicHiveの設計思想.md) を参照してください。
