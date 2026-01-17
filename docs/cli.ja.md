# CLI

CLIは、指定したモジュール/ファイルがノードを登録することを前提に動作します
（通常は `get_node_registry()` を使用）。

## Validate

```bash
agent-contracts validate --module myapp.nodes --strict
agent-contracts validate --file ./nodes.py --known-service db_service
```

- `--strict`: WARNINGをERRORに昇格（CI向け）
- `--known-service`: 複数指定可。`Contract.services`の検証に使用

終了コード: 成功は`0`、エラーありは`1`。

## Visualize

```bash
agent-contracts visualize --module myapp.nodes --output ARCHITECTURE.md
agent-contracts visualize --file ./nodes.py --output -
```

- `--output -` で標準出力に表示。

## Diff

```bash
agent-contracts diff --from-module myapp.v1.nodes --to-module myapp.v2.nodes
agent-contracts diff --from-file ./old_nodes.py --to-file ./new_nodes.py
```

終了コード: 破壊的変更がある場合は`2`、それ以外は`0`。
