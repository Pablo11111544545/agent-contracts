# CLI

CLIは、指定したモジュール/ファイルがノードを登録することを前提に動作します
（通常は `get_node_registry()` を使用）。

モジュールが `register_all_nodes(registry=None)` を定義しているものの、import 時に登録を行わない場合は、CLI が import 後に自動で呼び出します。

`AGENT_CONTRACTS_DEBUG=1` を設定すると、デバッグログを stderr に出力します（モジュール/グラフのロード、コンパイル、Mermaid 生成など）。

## Validate

```bash
agent-contracts validate --module myapp.nodes --strict
agent-contracts validate --file ./nodes.py --known-service db_service
```

- `--module`（複数指定可）: import する Python モジュールパス（例: `myapp.nodes`）。CLI は import（既に import 済みなら reload）し、ノード登録が行われることを期待します。
- `--file`（複数指定可）: 実行する Python ファイルパス（`runpy.run_path`）で、ノード登録が行われることを期待します。
- `--strict`: WARNINGをERRORに昇格（CI向け）
- `--known-service`（複数指定可）: 利用可能な service 名を宣言し、`NodeContract.services` を検証します。

終了コード: 成功は`0`、エラーありは`1`。

## Visualize

```bash
agent-contracts visualize --module myapp.nodes --output ARCHITECTURE.md
agent-contracts visualize --file ./nodes.py --output -
```

- `--module` / `--file`: `validate` と同じ読み込み挙動（複数指定可）。
- `--output`（デフォルト: `ARCHITECTURE.md`）: 出力先パス。`-` で標準出力に表示。
- アプリ側で compiled LangGraph を用意している場合は `--graph-module` 経由で渡すのがおすすめです（アプリ固有の entrypoint/state を反映できます）:

```bash
agent-contracts visualize --module myapp.nodes --graph-module myapp.graph --graph-func get_graph --output -
```

- `--graph-module`: compiled graph を返す関数を含むモジュールパス（例: `myapp.graph`）。
- `--graph-func`（デフォルト: `get_graph`）: compiled graph（または `.compile()` 可能な graph）を返す関数名。
- それ以外の場合、可能ならレジストリから best-effort で LangGraph をコンパイルして `LangGraph Node Flow` セクションも生成します（アプリの実グラフと差異が出ることがあります）。

## Diff

```bash
agent-contracts diff --from-module myapp.v1.nodes --to-module myapp.v2.nodes
agent-contracts diff --from-file ./old_nodes.py --to-file ./new_nodes.py
```

- `--from-module/--to-module`（複数指定可）: “before/after” のソースモジュール。
- `--from-file/--to-file`（複数指定可）: “before/after” のソースファイル。

終了コード: 破壊的変更がある場合は`2`、それ以外は`0`。
