# CLI

CLIは、指定したモジュール/ファイルがノードを登録することを前提に動作します
（通常は `get_node_registry()` を使用）。

モジュールが `register_all_nodes(registry=None)` を定義しているものの、import 時に登録を行わない場合は、CLI が import 後に自動で呼び出します。

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
- アプリ側で compiled LangGraph を用意している場合は `--graph-module` 経由で渡すのがおすすめです（アプリ固有の entrypoint/state を反映できます）:

```bash
agent-contracts visualize --module myapp.nodes --graph-module myapp.graph --graph-func get_graph --output -
```

- それ以外の場合、可能ならレジストリから best-effort で LangGraph をコンパイルして `LangGraph Node Flow` セクションも生成します。

## Diff

```bash
agent-contracts diff --from-module myapp.v1.nodes --to-module myapp.v2.nodes
agent-contracts diff --from-file ./old_nodes.py --to-file ./new_nodes.py
```

終了コード: 破壊的変更がある場合は`2`、それ以外は`0`。
