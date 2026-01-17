---
name: agent-contracts-contributor
description: agent-contracts OSS本体を変更するための手順とガードレール（テスト/ドキュメント/CLI/strict検証）。
metadata:
  short-description: agent-contractsに貢献する
---

# agent-contracts コントリビューター向け Skill（テンプレ）

このSkillは、`agent-contracts` を“利用する”のではなく、`agent-contracts` 本体を実装/変更する時に使います。

## プロジェクトの狙い（意識すること）

- LangGraph向けの契約駆動ノード設計と高いDX
- CIで落とせる検証（`strict`）とツール（`validate/visualize/diff`）
- 表面積は小さく、既存パターンに揃える

## ローカルセットアップ

推奨（venv）:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
```

テスト/カバレッジ:

```bash
pytest
pytest --cov=agent_contracts --cov-report=term-missing
```

## PRのチェックリスト（毎回）

- 変更は小さく集中（無関係リファクタを混ぜない）
- 新しい挙動にはテストを追加/更新
- Public API/挙動が変わったらドキュメントも更新:
  - `README.md` / `README.ja.md`
  - `docs/*`（core concepts / getting started / CLI）
- 推奨フローが変わるならexamplesも更新（`examples/*`）

## よくある作業

### Contract検証を追加/変更する

- 実装: `src/agent_contracts/validator.py`
- テスト: `tests/test_validator.py`
- warning/errorの粒度を決める
- `strict=True` での挙動が意図通りか確認する

### CLIを追加/変更する

- 実装: `src/agent_contracts/cli.py`
- エントリポイント: `pyproject.toml`（`[project.scripts]`）
- テスト: `tests/test_cli.py`
- 終了コードは安定させる:
  - `validate`: 成功`0`、エラーあり`1`
  - `diff`: 成功`0`、破壊的変更あり`2`

### contract diffを追加/変更する

- 実装: `src/agent_contracts/contract_diff.py`
- 出力は読みやすく安定に（`ContractDiffReport.to_text()`）
- テスト: `tests/test_contract_diff.py`

### examplesを追加/更新する

- 実行可能なスクリプトは `examples/` に置く
- 可能ならネットワーク不要で動く例にする（導入障壁を下げる）

## ガードレール

- 既存の中核パターンを優先（`NodeRegistry` / `GraphBuilder` / `GenericSupervisor` / `AgentRuntime`）
- 最小のAPIで出す（早期の過剰一般化は避ける）
- 仕様が曖昧なら「テストで意図を固定」する

## Doneの定義

- `pytest` が通る
- カバレッジが大きく悪化していない（例外は理由を明記）
- docs/examplesが現状の挙動と一致している
