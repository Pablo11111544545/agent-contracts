---
name: agent-contracts-tool-use-rag
description: services/依存注入/安全なLLMコンテキスト構築を使って、ツール実行やRAGノードを実装する。
metadata:
  short-description: ツール/RAGパターン
---

# agent-contracts Tool Use / RAG（利用者向け）

DB/検索/APIなど外部サービスを呼ぶノードや、RAG的な処理を実装する時に使います。

## 核となる考え方

- 依存は `NodeContract.services` に宣言（LLMが必要なら `requires_llm`）。
- 依存注入は以下のどちらかで統一:
  - ノード生成時に渡す（`node_cls(llm=..., my_service=...)`）
  - `build_graph_from_registry(...)` の `dependency_provider` を使う
- ルーティング用LLMコンテキストは小さく（サニタイズ + 必要時のみ `context_builder`）。

## ワークフロー

1. サービスは薄いラッパとして設計し、単体テストしやすくする。
2. `NodeContract.services=[...]` を宣言し、`execute()` 内で属性として利用。
3. CIで `ContractValidator(known_services=..., strict=True)` によりサービス名の取りこぼしを検知。
4. RAGの場合:
   - stateには小さな結果（id/短いsnippet）を置く
   - フルドキュメントや巨大データをstateに置かない
5. ルーティング精度:
   - 明確な分岐はルールで固定
   - LLMは小さな候補集合から選ぶ

## ガードレール

- LLMルーティング前のサニタイズを前提に設計（スーパーバイザーが実施）。
- stateに秘密情報を入れない（ログに出る前提で扱う）。

## References（必要なときだけ）

- `docs/core_concepts.ja.md`（context builder / サニタイズ）
- `docs/skills/official/agent-contracts-tool-use-rag/references/di_and_testing.ja.md`
