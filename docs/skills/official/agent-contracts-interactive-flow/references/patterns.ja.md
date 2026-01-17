# 対話フローのパターン

## response_type 設計

よくある `response.response_type`:

- `question`: クライアントがユーザーに質問を提示
- `done`: フロー完了
- `error`: ユーザーに見せる失敗

“完了”扱いにする型は `terminal_response_types` と整合させます。

## explicit routing（任意）

回答を“質問元ノード”に戻したい場合:

- 質問元をドメインスライスに保存（例: `interview.last_question.node_id`）
- `GenericSupervisor` に `explicit_routing_handler` を渡して、そのノード名を返す

各ノードに戻り先ロジックを散らさずに済みます。
