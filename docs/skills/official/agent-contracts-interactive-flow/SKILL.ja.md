---
name: agent-contracts-interactive-flow
description: InteractiveNode/explicit routing/workflowスライスを使って、質問→回答の対話型フローを実装する。
metadata:
  short-description: 対話（質問→回答）フロー
---

# agent-contracts Interactive Flow（利用者向け）

質問を出して回答を受け取り、複数ターンで進むエージェントを作る時に使います。

## 推奨ビルディングブロック

- `InteractiveNode`（ask/process/checkの標準ライフサイクル）
- 進捗を持つドメインスライス（例: `workflow`, `interview`）
- 回答を“質問元ノードに戻す”必要がある場合は `explicit_routing_handler`

## ワークフロー

1. ドメインスライス（`workflow`/`interview`）を決め、必要最小のフィールドを設計。
2. `InteractiveNode` を実装:
   - `prepare_context()` でドメインスライスを読み取る
   - `process_answer()` で `request` から更新
   - `check_completion()` で完了判定
   - `generate_question()` で `response` を返す（例: `response_type="question"`）
3. ルーティングを設計:
   - “続き”はルールトリガー（priority 50-100）で安定化
   - “終了”は terminal response types で `done`
4. ループ/停滞は `decide_with_trace()` で原因を確認。

## ガードレール

- 会話履歴はルーティングに必要なときだけ。必要なら `context_builder` の summary で渡す。
- ドメインスライスに大きいpayloadを入れない（コスト/トークン）。

## References（必要なときだけ）

- `docs/core_concepts.ja.md`（InteractiveNode / explicit routing）
- `docs/skills/official/agent-contracts-interactive-flow/references/patterns.ja.md`
