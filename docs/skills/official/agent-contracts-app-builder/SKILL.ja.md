---
name: agent-contracts-app-builder
description: agent-contractsでプロダクション志向のAI Agentを実装する（state slices / contracts / validation / graph / runtime / CLI）。
metadata:
  short-description: agent-contractsでAgentを作る
---

# agent-contracts App Builder（利用者向け）

このSkillは、`agent-contracts` を“拡張する”のではなく、`agent-contracts` を使って実際のAI Agentを実装する時に使います。

## ゴール

- state slices と node contracts が明確な、動くエージェント
- CIで落とせる検証（`ContractValidator(strict=True)` / `agent-contracts validate --strict`）
- 可視化と差分レビュー（`visualize` / `diff`）

## 推奨ワークフロー

1. **動くベースから開始**
   - まず `examples/05_backend_runtime.py` を基準にする（バックエンド実装に寄せやすい）。
2. **state slices を設計**
   - コアは `request` / `response` / `_internal`。
   - ドメイン用スライス（例: `ticket`, `orders`, `workflow`）を追加し、`NodeRegistry.add_valid_slice(...)` で登録。
3. **contract-first でノード実装**
   - 各ノードは `NodeContract(...)` で `reads/writes/supervisor/trigger_conditions` を宣言。
   - `writes=["request"]` は避ける（非推奨）。
4. **registry + GraphBuilder で配線**
   - `NodeRegistry` に登録 → `build_graph_from_registry(...)` → entry point設定 → compile。
5. **Runtime を付ける**
   - API実装なら `AgentRuntime`。
   - 進捗や段階出力が必要なら `StreamingRuntime`（SSE向け）。
6. **変更に強くする**
   - `ContractValidator(strict=True)` をテスト/CIで実行。
   - バージョン間の破壊的変更レビューに `agent-contracts diff` を使う。
   - アーキテクチャ出力に `agent-contracts visualize` を使う。

## クイックチェック

- テスト: `pytest`
- カバレッジ: `pytest --cov=agent_contracts --cov-report=term-missing`
- コントラクト: `agent-contracts validate --strict --module <your.nodes.module>`
- 可視化: `agent-contracts visualize --module <your.nodes.module> --output ARCHITECTURE.md`

## よくあるパターン

### バックエンド request/response 型

- `RequestContext` + `AgentRuntime` をAPIハンドラから呼ぶ。
- `response.response_type` をAPIの “type” として扱い、payloadは `response.response_data` に寄せる。

### 逐次ワークフロー

- `workflow` のようなドメインスライス + `_internal` フラグでステップを進める（`examples/04_multi_step_workflow.py` 参照）。

### 対話（質問→回答）フロー

- `InteractiveNode` で ask/process/check を標準化（`docs/core_concepts.ja.md` 参照）。

## References（必要なときだけ）

- `docs/getting_started.ja.md`
- `docs/core_concepts.ja.md`
- `docs/best_practices.ja.md`
- `docs/cli.ja.md`
- `examples/`
