# LogicHive ポートフォリオ公開計画 ── 辛口評価と改善リスト

> LogicHiveプロジェクトの凍結後、3週間の開発成果を「ポートフォリオ（技術力の証明）」として
> GitHubパブリックリポジトリに公開し、サンクコストから最低限のリターンを回収するための計画。

---

## 辛口評価：このまま公開したら「逆効果」になる

### 結論：**現状のまま公開するのは自殺行為。ポートフォリオとしてマイナス評価になる。**

提案自体は正しい。凍結プロジェクトをポートフォリオに転用するのは、サンクコスト回収戦略としてありだ。
ただし、**今のコードベースをそのまま公開したら、あなたの技術力を「証明」するどころか、「この人はセキュリティ意識がない」「コードの整理ができない」と面接官に思わせる逆効果になる。**

以下、具体的な問題点を列挙する。

---

## 致命的問題（公開前に必ず修正）

### CRITICAL-1: APIキーがソースコードにハードコードされている

`setup_gcp_secrets.ps1` の5行目に**Gemini APIキーが平文でハードコード**されている。

```powershell
# setup_gcp_secrets.ps1 (Line 5)
$GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
```

**これをパブリックリポジトリにPushした瞬間、Googleのボットが検知してAPIキーを即座に無効化する**（最悪の場合、不正利用される）。
さらに、**gitの履歴にも残る**ため、ファイルを削除しただけでは不十分。git historyのrewriteか、新規リポジトリでの再構築が必要。

**対応**: このファイルの完全削除、またはAPIキーをプレースホルダーに置換した上で、**リポジトリを新規作成（git historyをリセット）**する。

### CRITICAL-2: `.env` ファイルが Hub-Private に存在する

`backend/.env`（466バイト）が実ファイルとしてディスク上に存在している。
`.gitignore` に `.env` が記載されているため、**Gitの追跡対象には入っていない可能性が高い**が、確認が必要。
もしGitの追跡に入っていた場合、Supabase接続情報やStripe APIキーが全世界に公開される。

**対応**: `git log --all --full-history -- backend/.env` でGit履歴を確認。万が一追跡されていたら、即座にキーをローテーション（再発行）し、リポジトリを新規作成。

### CRITICAL-3: メンテスクリプトに個人情報が含まれている

`backend/scripts/maintenance/get_org_key.py` に実在のメールアドレスが平文で含まれている。

```python
.eq("name", "cwtbrluuee@gmail.com's Org")
```

これはプレースホルダーに置換するか、スクリプト自体をポートフォリオから除外する。

---

## 重要問題（ポートフォリオの品質に直結）

### IMPORTANT-1: Edge リポジトリにデバッグ残骸が大量にある

以下のファイルがリポジトリのルートに散乱しており、「コードの整理ができない人」という印象を与える。

| ファイル | 問題 |
|:--|:--|
| `lint.json` | リントのデバッグ出力がルートに放置 |
| `lint_errors.txt` / `lint_errors_v2.txt` | リントエラーのログがそのまま残っている |
| `e402.json` | 意味不明なJSONファイル |
| `LogicHive.spec` | PyInstallerのSpec（不要） |

**対応**: すべて削除するか、`.gitignore` に追加して追跡から外す。

### IMPORTANT-2: ドキュメントが「戦略ドキュメント」のまま

`docs/` 配下の `saas_strategy.md`, `VALUE_PROPOSITION.md` は**「ビジネス戦略の社内文書」であり、技術ポートフォリオ向けではない。**
ポートフォリオとして公開するなら、これらは「技術設計書」として再構成するか、明示的に「このプロジェクトのビジネス戦略検討の記録」として位置付けるべき。

特に今日の会話で何度も書き換えた結果、saas_strategy.md内にLLM排除とLLM搭載が混在する**矛盾した記述**が残っている可能性がある。

**対応**:
- `architecture_overview.md` と `hub_design.md` を技術ポートフォリオの中心に据える（技術設計の証明）
- `saas_strategy.md` / `VALUE_PROPOSITION.md` は整合性を確認の上、「ビジネス検討ドキュメント」として残すか、非公開にする
- `blog/why_indie_devs_should_avoid_b2b_in_ai_era.md` をREADMEから参照し、「なぜこのプロジェクトを凍結したか」のストーリーとして活用する（これは非常に強力なアピールになる）

### IMPORTANT-3: Hub-PrivateとEdgeを**モノレポ**として統合すべき

現在、LogicHive-Edge（公開済み）とLogicHive-Hub-Private（非公開）は別リポジトリ。
ポートフォリオとして公開するなら、**1つのリポジトリに統合した方が、全体のアーキテクチャを俯瞰でき、技術力のアピールになる。**

```
LogicHive/
├── README.md          ← ポートフォリオ用の魅力的なREADME
├── docs/              ← 技術設計書 + ブログ記事
├── edge/              ← MCP Client (旧 LogicHive-Edge)
├── hub/               ← SaaS Backend (旧 LogicHive-Hub-Private)
└── .github/workflows/ ← CI/CD設定
```

---

## 改善計画（公開までのチェックリスト）

### Phase 1: セキュリティ浄化（最優先・30分）
- [ ] `setup_gcp_secrets.ps1` からAPIキーを削除、またはプレースホルダーに置換
- [ ] `backend/.env` がgit履歴に含まれていないことを確認
- [ ] `get_org_key.py` の個人メールアドレスをプレースホルダーに置換
- [ ] `.env.example` を作成（必要な環境変数のリストだけを記載）
- [ ] **新規リポジトリを作成し、クリーンなgit historyで再構築**（古いcommit履歴にAPIキーが含まれている可能性を完全に排除）

### Phase 2: コードのクリーンアップ（1時間）
- [ ] Edgeリポジトリのデバッグ残骸（`lint.json`, `lint_errors*.txt`, `e402.json`, `LogicHive.spec`）を削除
- [ ] `__pycache__/`, `.ruff_cache/`, `.pytest_cache/` が `.gitignore` に含まれていることを確認
- [ ] `egg-info/` ディレクトリを削除
- [ ] テストファイル（`setup_field_test.py`, `trigger_search_test.py`）を `tests/` ディレクトリに移動
- [ ] ruffでコード全体をlint & format（`ruff check --fix . && ruff format .`）

### Phase 3: ポートフォリオ用READMEの作成（1時間）
- [ ] プロジェクトの概要（何を作ったか、なぜ凍結したか）
- [ ] アーキテクチャ図（Mermaid）
- [ ] 技術スタック一覧（FastAPI, Supabase, Cloud Run, Stripe, MCP, AST Security）
- [ ] 「学んだこと」セクション（ブログ記事へのリンク）
- [ ] スクリーンショットまたはデモGIF（Streamlit ExplorerのUI等）
- [ ] 「This project is archived」バッジを明示

### Phase 4: ドキュメント整合性チェック（30分）
- [ ] `saas_strategy.md` と `VALUE_PROPOSITION.md` の内容が矛盾していないか確認
- [ ] `hub_design.md` がMVP版（LLM排除版）と一致しているか確認
- [ ] `architecture_overview.md` が最新のDual-Repoのままなら、モノレポ構成に合わせて更新

### Phase 5: GitHub公開（15分）
- [ ] 新規パブリックリポジトリ `LogicHive` を作成
- [ ] MITまたはApache 2.0ライセンスを付与
- [ ] READMEのトップに「Archived Project」バッジを表示
- [ ] GitHubのリポジトリ設定で「Archived」フラグを有効化
- [ ] ポータルサイト（ayato_studio_portal）のポートフォリオページにリンクを追加

---

## ポートフォリオとしての「売り」になるポイント

辛口評価した上で言うと、**上記の問題をクリアすれば、このプロジェクトは「非常に強力なポートフォリオ」になりうる。**

| 技術力の証明 | 具体的なアピール |
|:--|:--|
| **バックエンド設計** | FastAPI + Supabase (pgvector) + Cloud Runの本格的なSaaSアーキテクチャ |
| **セキュリティ** | ASTベースの静的コード解析によるZero-Trust防御（`security.py`） |
| **課金システム** | Stripe Webhookを使ったサブスクリプション管理の実装 |
| **MCP（最先端）** | Model Context Protocolの実装は2025年時点で極めてレア。これだけで面接官の目を引く |
| **テナント管理** | 組織ベースのマルチテナント設計（クォータ管理含む） |
| **意思決定力** | 「なぜこのプロジェクトを凍結したか」のブログ記事が、技術力だけでなく**ビジネス判断力**をもアピールする |

特に最後の「凍結の理由をブログ記事で公開している」というのは、**ほとんどのエンジニアがやらないこと**であり、「この人は技術だけでなく、プロダクトの市場性まで考えられる人材だ」という印象を与える。

---

## まとめ

> **「ポートフォリオに追加する」という判断自体は正しい。**
> **ただし、APIキーの漏洩とデバッグ残骸の放置をそのままPushしたら、「セキュリティ意識が低い」と烙印を押される逆効果になる。**
> **Phase 1（セキュリティ浄化）とPhase 2（クリーンアップ）を完了してから公開せよ。**
