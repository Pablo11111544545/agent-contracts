---
name: agent-contracts-backend-runtime
description: AgentRuntime/StreamingRuntimeを使い、request/responseスライスを前提にバックエンド向けAI Agentを実装する。
metadata:
  short-description: バックエンド実装パターン
---

# agent-contracts Backend Runtime（利用者向け）

HTTP API / バッチ / SSEなど、バックエンドとしてAI Agentを実装する時に使います。

## 想定する形

- 入力: `RequestContext(session_id, action, params, message, image, resume_session)`
- 出力: `response.response_type` と `response.response_data`（必要なら `response.response_message`）
- state slices: `request`, `response`, `_internal` + ドメインスライス（例: `ticket`, `orders`, `workflow`）

## 推奨ワークフロー

1. `examples/05_backend_runtime.py` をベースに開始。
2. ドメインスライスを設計して登録: `NodeRegistry.add_valid_slice("your_slice")`。
3. 各ノードを `NodeContract` で宣言（`reads/writes` は最小に）。
4. `build_graph_from_registry(...)` でグラフ生成→compile。
5. `AgentRuntime` で request/response 実行を統一。
6. 段階的な出力が必要なら `StreamingRuntime` + `StreamEvent.to_sse()`。

## ガードレール

- 終了/分岐は `response.response_type` を中心に設計する。
- `request` への書き込みは避ける（非推奨）。
- 大きいデータは state に入れすぎない。LLMルーティング前にはサニタイズする（`GenericSupervisor`）。

## References（必要なときだけ）

- `docs/getting_started.ja.md`
- `docs/core_concepts.ja.md`
- `docs/cli.ja.md`
- `docs/skills/official/agent-contracts-backend-runtime/references/patterns.ja.md`
