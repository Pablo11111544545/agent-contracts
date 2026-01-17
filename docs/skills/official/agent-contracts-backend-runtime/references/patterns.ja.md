# バックエンド実装パターン

## 最小スライス構成

- `request`, `response`, `_internal` は常に維持。
- `context` を巨大化させるより、`ticket`/`orders` のようにドメインで分割。

## 推奨レスポンス設計

- `response.response_type`: クライアント/スーパーバイザーの分岐に使う安定した文字列
- `response.response_data`: JSON化できるpayload
- `response.response_message`: 任意のユーザー向けテキスト

## セッション

- 継続性が必要なら `AgentRuntime` + `SessionStore` と `RequestContext.resume_session=True` を使う。
- 復元するスライスは `slices_to_restore` で明示（デフォルトは `_internal`）。

## ストリーミング（SSE）

- ノード単位の安定したイベントが欲しいなら `StreamingRuntime.stream(...)`。
- LangGraphのストリーミングに寄せるなら `StreamingRuntime.stream_with_graph(...)`。
- SSEのpayloadは小さく。毎回フルstateを流さない。

## ノード設計

- `reads`/`writes` は最小・明示。
- ビジネスデータは `_internal` ではなくドメインスライスへ。
