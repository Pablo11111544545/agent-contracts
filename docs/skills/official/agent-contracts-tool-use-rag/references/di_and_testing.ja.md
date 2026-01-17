# 依存注入とテストの注意点

## dependency_provider

サービスが多い場合、`dependency_provider(contract)` で `contract.services` に応じて注入します。

推奨:

- 必須サービスが無い場合はテスト/CIで早期に落とす。
- サービスはできるだけステートレス、もしくはスコープを明確にする。

## ツール実行ノードのテスト

- `node.execute(NodeInputs(...))` を呼び、スタブサービスで単体テストする。
- 外部呼び出しはサービス境界に閉じ込めてスタブ可能にする。

## 安全なstate

- state slices に秘密情報（APIキー/トークン）を入れない。
- 秘密情報は state ではなくサービスインスタンス側で保持する。
