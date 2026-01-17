---
name: agent-contracts-routing-tuning
description: TriggerConditionの優先度・LLMヒント・context_builder・トレース情報でルーティングを設計/デバッグする。
metadata:
  short-description: ルーティング設計とデバッグ
---

# agent-contracts Routing Tuning（利用者向け）

ルール一致とLLM選択のバランス調整、ルーティングが思った通り動かない時の切り分けに使います。

## ルーティングモデル（最適化対象）

1. `TriggerCondition` によるルール評価（`when` / `when_not`, priority）
2. 候補選定（上位 + タイブレーク）
3. 候補内の最終選択（必要ならLLM、`llm_hint`）
4. フォールバック/終了条件（`response.response_type`）

## チューニング手順

1. まずLLMなしで決定的に動く状態にする。
2. priorityでビジネスルールを表現（100+=最優先、50-99=主処理、1-49=フォールバック）。
3. ルールで絞り切れない曖昧さだけ `llm_hint` を足す。
4. `context_builder` は必要なときだけ。デフォルトの最小スライスを優先。
5. `decide_with_trace()` で matched rules を見て原因を特定。

## ガードレール

- 制約/安全性はルール優先、意図の曖昧さはLLMで解く。
- 候補セットは小さく、説明可能に保つ。
- `response.response_type` の終了値もルーティング設計に含める。

## References（必要なときだけ）

- `docs/core_concepts.ja.md`（トレーサブルルーティング / context builder）
- `examples/02_routing_explain.py`
- `docs/skills/official/agent-contracts-routing-tuning/references/debug_playbook.ja.md`
