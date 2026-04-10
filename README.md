![CD Pipeline](https://github.com/Ayato-AI-for-Auto/LogicHive/actions/workflows/cd.yml/badge.svg)
# 🛡️ LogicHive: Professional AI Logic Hub

LogicHiveは、開発者を「仕様の再構築」や「冗長な実装」といった反復的な作業から解放し、AIエージェント（Antigravity, Cursor, Gemini等）を通じて最高の実装を瞬時に再利用するための**プロフェッショナル向けプライベート・ロジック・ハブ**です。

> **哲学：AIによる人間の作業からの解放。巨人の肩の上に乗り、真に価値ある創造に集中せよ。**

---

## 🌟 主な特徴

### 1. 3層構造の厳格な品質ゲート (Quality Gate)
AIエージェントが生成したコードを、3つの指標（30/30/40）で自動審査。
- **AI Gate (30%)**: Gemini 1.5 Proによる多角的なロジック検証と改善案。
- **Static Analysis (30%)**: Ruff / Radon による構文確認とコードの複雑度計測。
- **Runtime Verification (40%)**: サンドボックス内でのテストコード実行。
合格した資産のみが `[VERIFIED]` として Vault に永続化されます。

### 2. 高セキュア・コード実行サンドボックス
`EphemeralPythonExecutor` を搭載し、安全なコード検証を実現。
- **Network Isolation**: `uv --offline` による物理的なネットワーク遮断。
- **Environment Isolation**: ホスト環境変数（APIキー等）の漏洩を完全に防止。
- **Auto Dependency**: 必要ライブラリを `uv run` で一時的に自動構成し実行。

### 3. マルチテナント対応 RAG Isolation
複数のプロジェクトが混在しても、知財が混ざることはありません。
- **Composite Indexing**: `(project, name)` ベースの複合キーによるFAISSインデックス管理。
- **Metadata Management**: プロジェクトごとに厳格に分離された SQLite / FAISS 検索空間。

### 4. ローカルファースト & ハイブリッド成長
SQLite (WAL) と FAISS CPU を採用し、外部DB不要で爆速検索。
- **GitHub Sync (Optional)**: プライベートリポジトリと自動同期し、アーカイブ保護を実現。

---

## 🚀 セットアップ

`uv` を基盤とした、1コマンドでのプロフェッショナルな環境構築に対応しています。

### 1. 依存関係のインストール
```powershell
uv pip install -e .
```

### 2. 環境設定 (.env)
`.env.example` を `.env` にコピーし、`GEMINI_API_KEY` を設定してください。

### 3. MCPの登録
AIエージェント（Desktop App等）から呼び出せるようにMCPサーバーを登録します。
```powershell
uv run src/mcp_server.py
```

---

## 🤖 AIエージェント × LogicHive の運用サイクル

1. **Discovery (探索)**: AIエージェントに「〜の処理が欲しい」と依頼。
2. **Retrieval (抽出)**: LogicHive MCPが過去の良質な資産を提案。
3. **Adaptation (適合)**: 提案されたコードを現在のプロジェクト向けに洗練。
4. **Professionalization (資産化)**: 完成したコードを `save_function` で登録。
5. **Stabilization (安定化)**: `tools/audit/stabilize_vault.py` が24時間体制でVault資産を監視。

---

## 🏗️ リポジトリ構造

```text
src/
  ├── core/        # 評価、実行、DB接続のコアロジック
  └── storage/     # SQLite, FAISS, History 管理
tests/
  ├── unit/        # 関数単位の単体テスト
  ├── integration/ # コンポーネント間の結合テスト
  └── system/      # ユーザーフロー全体の総合テスト
tools/
  ├── audit/       # 品質監視・監査ツール
  ├── db/          # DB操作・バックアップ
  └── migration/   # 旧データからの移行ツール
```

---

## 🤝 Community & Support

LogicHiveの開発、および「AIによる人間の作業からの解放」というビジョンを支援していただける方を募集しています。
ご支援いただいた方には、感謝として限定Discordコミュニティ「Ayato's Dev Collective」への招待をお送りしています。

[🛡️ OFUSEで支援してコミュニティに参加する](https://ofuse.me/21cfc1d2)

---

## 📄 ライセンス

LogicHiveは **PolyForm Shield License 1.0.0** の下で公開されています。
競合サービスの提供を除き、個人・商用問わず知財活用目的で自由にご利用いただけます。

詳細は [LICENSE](LICENSE) を参照してください。
