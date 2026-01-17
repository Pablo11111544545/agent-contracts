---
name: agent-contracts-contracts-ci
description: strict検証・可視化・差分レビューをCIに組み込み、契約駆動エージェントを安全に変更できるようにする。
metadata:
  short-description: CIでコントラクト運用
---

# agent-contracts Contracts in CI（利用者向け）

チーム開発/CI前提で、エージェントを安全に変更するための運用手順です。

## ゴール

- コントラクトのミスを早期に検知（`strict=True`）
- アーキテクチャを最新化（`visualize`）
- 破壊的変更をレビュー（`diff`）

## 推奨CIチェック

1. テスト: `pytest`
2. コントラクト検証（strict）: `agent-contracts validate --strict --module <your.nodes>`
3. 可視化（任意）: `agent-contracts visualize --module <your.nodes> --output ARCHITECTURE.md`
4. 破壊的変更のレビュー:
   - `agent-contracts diff` で2バージョン間を比較
   - 破壊的変更が意図的ならリリースノートに明記

## `diff` の現実的な使い方

次のどちらかを選びます:

- **バージョン別モジュール**: `myapp/agents/v1.py` と `myapp/agents/v2.py` を `--from-module/--to-module` の入力にする
- **タグ運用**: 2つのチェックアウト（CIジョブ）で `agent-contracts diff` を実行して結果を比較

## ガードレール

- stateはログに出る前提。秘密情報をスライスに入れない。
- 既存の意味を変えるより、新しいスライス/フィールド追加を優先。

## References（必要なときだけ）

- `docs/cli.ja.md`
- `docs/roadmap.md`
- `docs/skills/official/agent-contracts-contracts-ci/references/checklist.ja.md`
