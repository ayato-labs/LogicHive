# 🛡️ LogicHive: Private AI Logic Hub

LogicHiveは、エンジニアが「一度書いた最高の実装」を資産として蓄積し、AIエージェント（Antigravity, Cursor, Gemini等）を通じて瞬時に呼び出し・再利用するためのプライベート・ロジック・ハブです。

## 🌟 主な特徴
- **プライベート運用**: SQLite (WALモード) と FAISS を使用した高速・セキュアなローカル環境。
- **堅牢な自動バックアップ**: GitHubのプライベートリポジトリと自動同期。万が一のPC故障時も `restore_backup.py` で一瞬で復元。
- **セーフ削除（アーカイブ）**: `delete_function` で削除したロジックは、GitHub上の `archives/` へ自動退避。資産を失うことはありません。
- **高精度AI再ランキング**: ベクトル検索に加え、Gemini LLMがクエリとの関連性を再評価（Re-ranking）することで、最適なロジックを確実に提案。
- **インテリジェント・品質ゲート**: Gemini APIによる解析と静的解析ツールを組み合わせた多角的な評価（Score 0-100）。
- **エージェント協調**: MCP（Model Context Protocol）を通じて、AIエージェントとシームレスにロジックを統合。

---

## 🚀 セットアップ

### 1. 依存関係のインストール
`uv` を使用して、プロジェクトの依存関係をインストール・同期します。

```powershell
uv pip install -e .
```

### 2. 環境設定 (.env)
`.env.example` を `.env` にコピーし、`GEMINI_API_KEY` と `GITHUB_TOKEN` を設定してください。
- `GEMINI_API_KEY`: 品質評価とRAG（ベクトル生成）に使用します。
- `GITHUB_TOKEN`: プライベートリポジトリへの自動バックアップに使用します。

### 3. MCPの登録（自動設定）
プロジェクト内の `scripts/register_mcp.bat` を実行してください。以下の設定が試行されます。

- **`mcp_config.json` の自動編集**: 各OSの標準的なMCP構成パスを検出し、`logic-hive` サーバーを登録します。
- **指示の自動注入**: `~/.gemini/GEMINI.md` 等へ「LogicHiveを活用する」というルールを追記します。

### 3. システムの起動

- **Streamlit UI (閲覧・検索)**:
  `run_ui.bat` をダブルクリックして、ブラウザからVaultの内容を視覚的に確認・検索できます。
- **MCPサーバー (AIエージェント用)**:
  エージェントが自動的に起動しますが、手動でテストする場合は `uv run src/mcp_server.py` を実行します。

### 4. データの復元 (Rehydrate)
PCの乗り換えやデータ紛失時は、GitHubから一瞬で復元できます：
```powershell
uv run scripts/restore_backup.py
```
これにより、最新のロジックとメタデータがローカルDBに同期され、埋め込みベクトルが再生成されます。

---

## 🏗️ ビルドとデプロイ

### ローカルでのEXE化
`uv run python ci_cd/build_exe.py` を実行することで、`dist/LogicHive-MCP.exe` が生成されます。ビルドには `LogicHive.spec` が使用されます。

### GitHub Actions (CI/CD)
GitHubへプッシュすると、自動的にビルドテストが実行されます。
- **自動リリース**: `v*` タグ（例: `v0.2.0`）をプッシュすると、自動的にGitHub Releaseが作成され、最新のビルド済み `.exe` が添付されます。
- **手動実行**: GitHub Actionsタブから `workflow_dispatch` を利用して手動でビルドを開始することも可能です。

---

## 🤖 AIエージェントとの連携・思想

1. **Request (探索)**: AIエージェントに「〜する処理が欲しい」とリクエスト。
2. **Retrieve (抽出)**: LogicHive MCPが過去の良質なロジック（38以上の初期登録済みロジックを含む）を提案。
3. **Adaptation (適合)**: エージェントが、提案されたコードを現在のプロジェクトに適合させる。
4. **Registration (資産化)**: 洗練されたコードを `save_function` で LogicHive に再登録。品質ゲートが自動で審査します。

---

## 📄 ライセンス

LogicHiveは **PolyForm Shield License 1.0.0** の下で公開されています。

- **個人利用・社内利用**: 完全に無料です。
- **改変・配布**: 自由に行えます。
- **🚫 禁止事項**: 本ソフトウェアと **競合する製品またはサービス（SaaS等）を提供すること** は禁止されています。

詳細は [LICENSE](LICENSE) を参照してください。
