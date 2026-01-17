# コントラクト運用チェックリスト（CI）

## マージ前

- `pytest`
- `agent-contracts validate --strict --module ...`
- ルーティングを変更した場合:
  - `decide_with_trace()` の挙動を固定するテストを追加/更新
  - `terminal_response_types` の整合性を確認
- スライスを変更した場合:
  - 新規スライスは `NodeRegistry.add_valid_slice(...)` を追加
  - `request` への書き込みは避ける

## リリース時

- `agent-contracts visualize` で `ARCHITECTURE.md` 相当を更新
- `agent-contracts diff` で前バージョンとの差分を確認し、破壊的変更を要約
