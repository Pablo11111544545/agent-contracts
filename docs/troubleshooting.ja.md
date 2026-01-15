# トラブルシューティング

> よくある問題とその解決策

---

## バリデーションエラー

### "Unknown slice 'X' in node 'Y' reads/writes"

**原因**: スライス名がレジストリに登録されていない

**解決策**:

```python
# オプション1: スライスをレジストリに追加
registry.add_valid_slice("your_slice_name")

# オプション2: タイポを確認
# "shoping" → "shopping" かも？
```

**予防策**:
```python
# スライス名を定数として定義
SLICE_ORDERS = "orders"
SLICE_WORKFLOW = "workflow"

# コントラクトで定数を使用
reads=[SLICE_ORDERS]
```

---

### "Node requires LLM but not provided"

**原因**: コントラクトに`requires_llm=True`があるがLLMが注入されていない

**解決策**:
```python
# インスタンス化時にLLMを提供
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4")
node = MyNode(llm=llm)

# またはグラフ構築時
graph = build_graph_from_registry(
    registry=registry,
    llm=llm,  # 全ノードに渡される
)
```

---

### "Unknown service 'X' required by node 'Y'"

**原因**: `services`で宣言されたサービスが利用できない

**解決策**:
```python
# 必要なサービスをすべて提供
db_service = DatabaseService()
cache_service = CacheService()

node = MyNode(
    llm=llm,
    db_service=db_service,
    cache_service=cache_service,
)
```

**予防策**:
```python
# 既知のサービスでバリデーション
validator = ContractValidator(
    registry,
    known_services={"db_service", "cache_service"},
)
```

---

## ルーティングの問題

### "ノードが呼び出されない"

**考えられる原因と解決策**:

1.  **TriggerConditionがマッチしない**
    ```python
    # 確認: 'when'条件は正しい？
    when={"request.action": "serch"}  # タイポ！ "search" が正しい
    ```

2.  **優先度が低すぎる**
    ```python
    # 優先度が高い別のノードが先にマッチしている
    # decide_with_trace()でデバッグ
    decision = await supervisor.decide_with_trace(state)
    print(decision.reason.matched_rules)
    ```

3.  **スーパーバイザーに属していない**
    ```python
    # 確認: 正しいスーパーバイザーに登録されている？
    supervisor="main"  # build_graph_from_registryのsupervisors=と一致が必要
    ```

4.  **到達不能（トリガー条件がない）**
    ```python
    # トリガー条件を追加
    trigger_conditions=[
        TriggerCondition(priority=10, when={"request.action": "my_action"})
    ]
    ```

---

### "間違ったノードが選択される"

**トレーサブルルーティングでデバッグ**:
```python
decision = await supervisor.decide_with_trace(state)

print(f"選択: {decision.selected_node}")
print(f"タイプ: {decision.reason.decision_type}")
print(f"マッチしたルール:")
for rule in decision.reason.matched_rules:
    print(f"  P{rule.priority}: {rule.node} - {rule.condition}")
```

**一般的な修正方法**:
-   優先度の値を調整
-   `when`条件をより具体的に
-   `when_not`を追加して不要なマッチを除外

---

### "LLMルーティングが予測不能"

**解決策**:

1.  **llm_hintsを改善**
    ```python
    # 悪い例
    llm_hint="検索"

    # 良い例
    llm_hint="ユーザーが明示的に商品を検索したい時に使用。閲覧やレコメンドには使用しない。"
    ```

2.  **明確なアクションにはルールベースを使用**
    ```python
    # アクションが明示的ならLLMの代わりにルールを使用
    when={"request.action": "search"}  # 明確な意図
    ```

3.  **クリティカルパスの優先度を上げる**
    ```python
    priority=100  # LLMが決定する前に強制選択
    ```

---

## 実行の問題

### "無限ループ / Max iterations reached"

**原因**: ノードがENDに到達せずルーティングを繰り返す

**解決策**:

1.  **終了状態を確認**
    ```python
    # response typeがterminal_statesに含まれていることを確認
    terminal_response_types={"question", "results", "error"}

    # ノードの出力が一致するタイプであること
    return NodeOutputs(
        response={
            "response_type": "results",
            "response_data": {"items": [1, 2, 3]},
        }
    )
    ```

2.  **適切なノードにis_terminalを設定**
    ```python
    class ResultNode(ModularNode):
        CONTRACT = NodeContract(
            name="result",
            description="最終結果を返してフローを終了",
            reads=["request"],
            writes=["response"],
            supervisor="main",
            trigger_conditions=[TriggerCondition(priority=10)],
            is_terminal=True,  # このノードの後にENDを強制
        )
    ```

3.  **デバッグ中はmax_iterationsを増やす**
    ```python
    supervisor = GenericSupervisor(
        max_iterations=50,  # 問題を見つけるために増加
    )
    ```

---

### "ステート更新が永続化されない"

**原因**: ノード出力がコントラクトのwritesと一致しない

**解決策**:
```python
# コントラクトで宣言
writes=["orders"]

# executeで一致するスライスを返す
return NodeOutputs(
    orders={"cart": [...]},  # ✅ 正しい
    # Not: response={"cart": [...]}  # ❌ 間違ったスライス
)
```

---

### "NodeInputsに期待するデータがない"

**原因**: コントラクトのreadsに必要なスライスが含まれていない

**解決策**:
```python
# 'context'スライスからデータが必要な場合
CONTRACT = NodeContract(
    name="my_node",
    description="contextスライスが必要な例",
    reads=["request", "context"],  # 'context'を含める
    writes=["response"],
    supervisor="main",
)

async def execute(self, inputs, config=None):
    context = inputs.get_slice("context")  # これで利用可能
```

---

## 設定の問題

### "設定が読み込まれない"

**ファイルパスを確認**:
```python
from agent_contracts.config import load_config, set_config

# 絶対パス
config = load_config("/path/to/agent_config.yaml")

# または作業ディレクトリからの相対パス
config = load_config("./config/agent_config.yaml")

set_config(config)
```

**YAML構文を確認**:
```yaml
# 有効なYAML
supervisor:
  max_iterations: 10

response_types:
  terminal_states:
    - interview
    - results
```

---

### "終了状態が機能しない"

**設定を確認**:
```yaml
# agent_config.yaml内
response_types:
  terminal_states:
    - question    # response_typeと完全一致が必要
    - results
    - error
```

**response_typeのフォーマットを確認**:
```python
# 完全一致が必要
return NodeOutputs(
    response={
        "response_type": "question",  # 完全一致
        # "Question" や "QUESTION" ではない
    }
)
```

---

## テストの問題

### "非同期テストが失敗する"

**pytest-asyncioを使用**:
```python
import pytest

@pytest.mark.asyncio
async def test_node_execution():
    node = MyNode(llm=mock_llm)
    inputs = NodeInputs(request={"action": "test"})
    
    result = await node.execute(inputs)
    
    assert result.response is not None
```

**pytestを設定**:
```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "strict"
```

---

### "テスト間でレジストリ状態がリークする"

**fixtureでレジストリをリセット**:
```python
import pytest
from agent_contracts import reset_registry


@pytest.fixture(autouse=True)
def clean_registry():
    reset_registry()
    yield
    reset_registry()
```

---

## パフォーマンスの問題

### "LLM呼び出しが遅い"

**解決策**:

1. **ルーティングには軽量モデルを使用**
   ```python
   # スーパーバイザーにはGPT-3.5、ノードにはGPT-4
   routing_llm = ChatOpenAI(model="gpt-3.5-turbo")
   execution_llm = ChatOpenAI(model="gpt-4")
   
   supervisor = GenericSupervisor(llm=routing_llm)
   ```

2. **ルールベースルーティングに依存**
   ```python
   # アクションが明示的ならLLMは不要
   when={"request.action": "search"}
   ```

3. **シンプルなグラフからLLMを除去**
   ```python
   # 純粋なルールベース、LLMオーバーヘッドなし
   supervisor = GenericSupervisor(
       llm=None,  # ルールベースのみ
   )
   ```

---

## トークン消費の問題

### "Supervisorでのトークン使用量が予想外に多い"

**原因**: ステートスライス内の大きなデータ（特にbase64画像）がルーティング判断のためにLLMに送信されている

**症状**:
- ルーティング判断で数千トークンを消費
- Supervisorの応答が遅い
- APIコストが高い

**解決策**:

1. **データサニタイズが機能していることを確認（v0.3.3+）**
   ```python
   # GenericSupervisorは自動的にサニタイズ:
   # - 画像データ → "[IMAGE_DATA]"
   # - 長い文字列 → 先頭を保持してトリミング
   
   # デフォルトのmax_field_lengthは10000文字
   supervisor = GenericSupervisor(
       supervisor_name="main",
       llm=llm,
       max_field_length=10000,  # 必要に応じて調整
   )
   ```

2. **requestスライス内の画像データを確認**
   ```python
   # ステートにbase64画像を保存している場合:
   request = {
       "action": "analyze",
       "image": "image/png;base64,iVBORw0KG..."  # 自動的にサニタイズされる
   }
   ```

3. **context_builder実装を見直す**
   ```python
   def my_context_builder(state, candidates):
       # 大きなデータを含むスライスは含めない
       return {
           "slices": {"request", "response", "_internal"},  # 最小限のコンテキスト
           # 避ける: {"request", "response", "raw_data", "images"}
       }
   ```

4. **トークン使用量を監視**
   ```python
   # LLMに送信される内容を確認するためにデバッグログを有効化
   import logging
   logging.getLogger("agent_contracts").setLevel(logging.DEBUG)
   ```

**予防策**:
- 可能な場合、大きなデータ（画像、ファイル）はステートスライスの外に保存
- データを埋め込む代わりに参照/URLを使用
- 自動サニタイズを活用（v0.3.3+）
- `context_builder`で最小限のコンテキストを使用

---

## マイグレーション問題

### "TypeError: 'TriggerMatch' object is not subscriptable" (v0.4.0)

**原因**: `evaluate_triggers()`を直接使用しているコードがv0.3.xの`tuple`形式を前提としている

**症状**:
```python
# v0.3.x形式のコード
matches = registry.evaluate_triggers("main", state)
priority, node_name = matches[0]  # エラー！
```

**解決策**:
```python
# v0.4.0形式に更新
matches = registry.evaluate_triggers("main", state)
match = matches[0]
priority = match.priority
node_name = match.node_name
condition_index = match.condition_index  # 新機能！
```

**影響を受けるコード:**
- `evaluate_triggers()`を直接呼び出している
- `registry.evaluate_triggers()`の結果を処理している

**影響を受けないコード:**
- `GenericSupervisor`のみを使用
- `decide()`や`decide_with_trace()`のみを使用

---

## ヘルプを得る

困ったときは:

1. **サンプルを確認**: `examples/` ディレクトリ
2. **バリデーションを使用**: `ContractValidator.validate()`
3. **トレースを使用**: `decide_with_trace()`
4. **デバッグログを有効化**:
   ```python
   import logging
   logging.getLogger("agent_contracts").setLevel(logging.DEBUG)
   ```

---

## 関連ドキュメント

- 📚 [コアコンセプト](core_concepts.ja.md) - アーキテクチャの理解
- 🎯 [ベストプラクティス](best_practices.ja.md) - 設計パターン
