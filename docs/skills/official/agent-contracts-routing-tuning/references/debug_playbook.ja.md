# ルーティングデバッグ手順

## 1) terminal-state の確認

- `response.response_type` がterminalなら、スーパーバイザーは `done` で抜ける想定。
- terminal types の設定（framework config / supervisor設定）を確認。

## 2) ルールマッチの確認

- `decide_with_trace()` で以下を確認:
  - `decision.selected_node`
  - `decision.reason.decision_type`
  - `decision.reason.matched_rules`（priority と condition）

期待ノードが候補に出ない場合:
- スライス名/パス（`request.action`, `_internal.step` など）の誤り
- `when_not` の条件
- priority の大小関係

## 3) LLMが絡む場合

- 候補（candidates）に意図したノードが入っているか確認。
- `llm_hint` は短く、識別しやすい文にする。
- 不安定ならルールを強める/候補を減らす。

## 4) コンテキスト問題

- `context_builder` を使う場合、`slices` と任意で `summary` を返すこと。
- 文字列/画像など大きいデータは避ける（サニタイズで切られる）。 
