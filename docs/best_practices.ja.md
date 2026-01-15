# ベストプラクティス

> 堅牢なエージェント構築のための設計パターンとヒント

---

## スライス設計

### ✅ データフローを設計する

ノードは複数のスライスを読み取り、別のスライスに書き込むことで**データを変換・充実**させます。

```python
class ContextEnricherNode(ModularNode):
    CONTRACT = NodeContract(
        name="context_enricher",
        description="requestとuser_profileからcontextを生成",
        reads=["request", "user_profile"],   # 入力を組み合わせて
        writes=["context"],                   # 充実したコンテキストを生成
        supervisor="main",
    )

class SearchNode(ModularNode):
    CONTRACT = NodeContract(
        name="search",
        description="requestとcontextを使って検索する",
        reads=["request", "context"],        # コンテキストを活用して
        writes=["search_results"],           # 検索結果を生成
        supervisor="main",
    )

class ResponseBuilderNode(ModularNode):
    CONTRACT = NodeContract(
        name="response_builder",
        description="search_resultsとcontextから最終レスポンスを構築",
        reads=["search_results", "context"], # 結果とコンテキストから
        writes=["response"],                 # 最終レスポンスを構築
        supervisor="main",
    )
```

### ✅ スライスをパイプラインとして考える

```
request ─┬─→ [Enricher] ─→ context ─────┐
         │                              │
user_profile ─────────────────────────→ [Search] ─→ search_results
                                        │
                                        └→ [Builder] ─→ response
```

### ✅ 意味のある名前を使用

```python
# Good: 明確な目的
"workflow"       # ワークフローの進行状態
"search_results" # 検索結果
"user_profile"   # ユーザー情報

# Avoid: 曖昧な名前
"data"           # 何のデータ？
"temp"           # 何が一時的？
```

### ⚠️ 巨大なスライスを避ける

```python
# Avoid: すべてを1つのスライスに
"state": {
    "user": {...},
    "orders": {...},
    "analytics": {...},
}

# Better: ドメイン別に分割
"user_profile": {...}
"orders": {...}
"analytics": {...}
```

---

## 状態管理

### ✅ StateAccessorパターンを使用

```python
from agent_contracts import Internal, Request, Response

# 良い: 型安全、IDEオートコンプリート
count = Internal.turn_count.get(state)
state = Internal.turn_count.set(state, count + 1)

# 避ける: 直接辞書アクセス
count = state["_internal"]["turn_count"]  # KeyErrorリスク
state["_internal"]["turn_count"] = count + 1  # 状態をミューテート！
```

### ✅ 常に新しい状態を返す

```python
# 良い: イミュータブル操作
state = Internal.turn_count.set(state, 5)
state = reset_response(state)

# 悪い: インプレースでミューテート
state["_internal"]["turn_count"] = 5  # これはやらない！
```

### ✅ ヘルパー関数を使用

```python
from agent_contracts import increment_turn, reset_response
from agent_contracts.runtime import update_slice, merge_session

# Good: 明確な意図
state = increment_turn(state)
state = reset_response(state)
state = update_slice(state, "workflow", question_count=5)

# 避ける: 手動操作
state["_internal"]["turn_count"] += 1
state["_internal"]["is_first_turn"] = False
```

---

## Runtimeレイヤー

### ✅ 本番ではAgentRuntimeを使用

```python
from agent_contracts import AgentRuntime, RequestContext

# 良い: 統合ライフサイクル管理
runtime = AgentRuntime(graph=graph, session_store=store, hooks=hooks)
result = await runtime.execute(request)

# 避ける: 手動オーケストレーション
state = create_state()
state = restore_session()
state = normalize_state()
final = await graph.ainvoke(state)
# など... エラーが起きやすい！
```

### ✅ カスタムフックを実装

```python
class MyHooks(RuntimeHooks):
    async def prepare_state(self, state, request):
        # リソースの読み込み、状態の正規化
        return state
    
    async def after_execution(self, state, result):
        # レスポンスタイプに基づいてセッションを永続化
        if result.response_type in ("question", "results"):
            await self.session_store.save(...)
```

### ✅ SSEにはStreamingRuntimeを使用

```python
from agent_contracts.runtime import StreamingRuntime

runtime = (
    StreamingRuntime()
    .add_node("step1", node1, "処理中...")
    .add_node("step2", node2, "完了処理中...")
)

async for event in runtime.stream(request):
    yield event.to_sse()  # SSEフォーマット
```

---

## ノードの粒度

### ✅ 単一目的のノード

```python
# 良い例: 単一責任
class SearchNode(ModularNode):
    """商品検索を処理"""
    
class FilterNode(ModularNode):
    """結果にフィルタを適用"""
    
class RecommendNode(ModularNode):
    """レコメンデーションを生成"""
```

### ❌ 神ノードを避ける

```python
# 悪い例: やりすぎ
class EverythingNode(ModularNode):
    """検索、フィルタ、レコメンド、チェックアウト、分析を処理..."""
    
    async def execute(self, inputs, config=None):
        action = inputs.get_slice("request").get("action")
        if action == "search":
            # 100行の検索ロジック
        elif action == "filter":
            # 100行のフィルタロジック
        elif action == "recommend":
            # 100行のレコメンドロジック
        # ... さらに続く
```

### ✅ 適切なサイズの目安

| ノードサイズ | 症状 | 対処 |
|-------------|------|------|
| 小さすぎ | ノードが多い、複雑なルーティング | 関連タスクを統合 |
| 大きすぎ | 長いexecute()、多数のif/else | アクションタイプで分割 |
| 適切 | 20-100行、明確な目的 | 👍 |

---

## トリガー優先度

### ✅ 一貫した優先度バンドを使用

```python
# 優先度スキーム
PRIORITY_CRITICAL = 100  # エラー、オーバーライド
PRIORITY_PRIMARY = 50    # メインビジネスロジック
PRIORITY_SECONDARY = 30  # 代替パス
PRIORITY_FALLBACK = 10   # キャッチオールハンドラ

# 例
TriggerCondition(priority=PRIORITY_CRITICAL, when={"request.action": "emergency"})
TriggerCondition(priority=PRIORITY_PRIMARY, when={"request.action": "search"})
TriggerCondition(priority=PRIORITY_FALLBACK, llm_hint="一般的なアシスタンス")
```

### ✅ 柔軟な優先度の使用（v0.4.0+）

v0.4.0以降は、どの条件がマッチしたかを正確に追跡できるため、柔軟な優先度設計が可能です：

```python
# オプション1: 明確な順序付けのために優先度を分ける
class SearchNode(ModularNode):
    CONTRACT = NodeContract(
        name="search",
        description="複数条件を持つ検索ハンドラ",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=51,  # 画像検索を優先
                when={"request.action": "search", "request.has_image": True},
            ),
            TriggerCondition(
                priority=50,  # 通常の検索
                when={"request.action": "search"},
            ),
        ],
    )

# オプション2: 複数ノードが同じ優先度で競合する場合（v0.4.0+）
class ImageSearchNode(ModularNode):
    CONTRACT = NodeContract(
        name="image_search",
        description="画像ベースの検索ハンドラ",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=50,  # 同じ優先度、LLMに判断を任せる
                when={"request.action": "search", "request.has_image": True},
                llm_hint="画像ベースの検索に使用。ユーザーが画像をアップロードした場合に最適。",
            ),
        ],
    )

class TextSearchNode(ModularNode):
    CONTRACT = NodeContract(
        name="text_search",
        description="テキストベースの検索ハンドラ",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=50,  # 同じ優先度
                when={"request.action": "search"},
                llm_hint="テキストベースの検索に使用。商品名やキーワードでの検索に最適。",
            ),
        ],
    )
```

**v0.4.0のメリット:**
- 同じ優先度でも条件を正確に追跡
- LLMが実際にマッチした条件の正確な情報を受け取る
- 複数の条件が等しく有効な場合に柔軟な設計パターンが可能

**同じ優先度が有効なユースケース:**
- 複数の異なるノードが同じアクションを異なる方法で処理できる場合
- どちらのアプローチも有効で、LLMにコンテキストベースで選ばせたい場合
- A/Bテストシナリオ

**v0.3.x以前をご使用の場合:**
v0.3.x以前では、同じ優先度の複数条件を使用すると、条件説明が不正確になる可能性があります。これらのバージョンでは、明確な順序付けのために異なる優先度を使用してください。

### ✅ 優先度の決定をドキュメント化

```python
class SearchNode(ModularNode):
    CONTRACT = NodeContract(
        name="search",
        description="優先度設計を明示した検索ハンドラ",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=50,  # 主要ハンドラ、エラーハンドラ(100)より下
                when={"request.action": "search"},
            )
        ],
    )
```

---

## Supervisorの設定

### ✅ フィールド長制限をカスタマイズ

```python
from agent_contracts import GenericSupervisor

# 良い例: データサイズに基づいて調整
supervisor = GenericSupervisor(
    supervisor_name="main",
    llm=llm,
    max_field_length=10000,  # 長いコンテンツの場合は増加（デフォルト: 10000）
)

# 非常に大きなステートフィールドを持つアプリケーション向け
supervisor = GenericSupervisor(
    supervisor_name="main",
    llm=llm,
    max_field_length=20000,  # 詳細なコンテキスト用に高い制限
)
```

### ✅ データサニタイズを理解する

SupervisorはLLMに送信する前にステートデータを自動的にサニタイズします：

```python
# 自動的に処理:
# - Base64画像データ → "[IMAGE_DATA]" に置換
# - 長い文字列 → 先頭部分を保持してトリミング
# - 例: "長いテキスト..." → "長いテキスト...[TRUNCATED:5000_chars]"
```

**メリット**:
- 画像データによるトークン浪費を防止
- 長いフィールドの先頭を保持することでコンテキストを維持
- `max_field_length`パラメータでカスタマイズ可能

---

## LLMヒント

### ✅ 具体的でアクション可能に

```python
# 良い例: 明確なガイダンス
llm_hint="ユーザーが名前またはカテゴリで商品を検索したい時に使用"

# 悪い例: 曖昧
llm_hint="検索を処理"
```

### ✅ 使用しない場合のコンテキストを含める

```python
# 良い例: 明確な境界
llm_hint="商品検索に使用。カート表示やチェックアウトには使用しない。"

# 悪い例: ポジティブのみ
llm_hint="商品を検索"
```

### ✅ 一貫した言語を使用

```python
# 良い例: 一貫したパターン
llm_hint="ユーザーが商品を検索したい時に使用"
llm_hint="ユーザーがカートを見たい時に使用"
llm_hint="ユーザーがチェックアウトしたい時に使用"

# 悪い例: 不一致
llm_hint="検索するやつ"
llm_hint="カートを見るための"
llm_hint="チェックアウトを処理します"
```

---

## ノードのテスト

### ✅ 個別ノードをユニットテスト

```python
import pytest
from agent_contracts import NodeInputs


class TestSearchNode:
    @pytest.fixture
    def node(self):
        return SearchNode(llm=mock_llm)
    
    @pytest.mark.asyncio
    async def test_search_returns_results(self, node):
        inputs = NodeInputs(
            request={"action": "search", "params": {"query": "laptop"}}
        )
        
        outputs = await node.execute(inputs)
        
        assert outputs.response["response_type"] == "search_results"
        assert len(outputs.response["results"]) > 0
```

### ✅ エッジケースをテスト

```python
@pytest.mark.asyncio
async def test_empty_query_returns_error(self, node):
    inputs = NodeInputs(
        request={"action": "search", "params": {"query": ""}}
    )
    
    outputs = await node.execute(inputs)
    
    assert outputs.response["response_type"] == "error"
```

### ✅ 外部サービスをモック

```python
from unittest.mock import AsyncMock


@pytest.fixture
def node_with_mock_service():
    mock_db = AsyncMock()
    mock_db.search.return_value = [{"id": 1, "name": "Test"}]
    return SearchNode(llm=None, db_service=mock_db)
```

---

## バリデーション

### ✅ 早期にバリデーション

```python
# main.pyまたはアプリ起動時
from agent_contracts import ContractValidator, get_node_registry

registry = get_node_registry()

# 全ノードを登録
registry.register(NodeA)
registry.register(NodeB)

# グラフ構築前にバリデーション
validator = ContractValidator(registry)
result = validator.validate()

if result.has_errors:
    print("❌ コントラクト検証失敗:")
    print(result)
    exit(1)

# 安全に構築可能
graph = build_graph_from_registry(registry, llm)
```

### ✅ 共有ライターをチェック

```python
# データフローを理解
shared = validator.get_shared_writers()
for slice_name, writers in shared.items():
    if len(writers) > 1:
        print(f"⚠️  {slice_name} の書き込み元: {', '.join(writers)}")
```

### ✅ 既知のサービスを提供

```python
# 利用可能なサービスを明示的に指定
validator = ContractValidator(
    registry,
    known_services={"db_service", "search_api", "cache"},
)
```

---

## 共通パターン

### パターン: エラーハンドラ

```python
class ErrorHandlerNode(ModularNode):
    CONTRACT = NodeContract(
        name="error_handler",
        description="エラー状態を処理してエラーレスポンスを返す",
        reads=["_internal"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=100,  # 最高優先度
                when={"_internal.error": True},
            )
        ],
        is_terminal=True,  # 処理後にフローを終了
    )
```

### パターン: フォールバックハンドラ

```python
class FallbackNode(ModularNode):
    CONTRACT = NodeContract(
        name="fallback",
        description="未処理リクエスト用のフォールバックハンドラ",
        reads=["request"],
        writes=["response"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=1,  # 最低優先度
                # 'when'条件なし = 常にマッチ
                llm_hint="未処理リクエストのフォールバックとして使用",
            )
        ],
    )
```

### パターン: マルチステージワークフロー

```python
# Stage 1: 基本情報
class BasicInfoNode(InteractiveNode):
    CONTRACT = NodeContract(
        name="basic_info",
        description="ワークフローの基本情報を収集",
        reads=["request", "workflow"],
        writes=["response", "workflow"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=50,
                when={"workflow.stage": "basic"},
            )
        ],
    )

# Stage 2: 詳細情報
class DetailsNode(InteractiveNode):
    CONTRACT = NodeContract(
        name="details",
        description="ワークフローの詳細情報を収集",
        reads=["request", "workflow"],
        writes=["response", "workflow"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                priority=50,
                when={"workflow.stage": "details"},
            )
        ],
    )
```

---

## アンチパターン

### ❌ 循環依存

```python
# 悪い例: NodeAがXを読み、Yを書く
#         NodeBがYを読み、Xを書く
# 無限ループの原因に！

# 解決策: コーディネーターノードを使用するか、データフローを再設計
```

### ❌ LLMルーティングの過剰使用

```python
# 悪い例: すべての決定がLLMへ
# 遅い、高コスト、予測不能

# 良い例: 明確なアクションはルールベース、曖昧さはLLM
TriggerCondition(
    priority=100,
    when={"request.action": "search"},  # 明確な意図 = ルールベース
)
TriggerCondition(
    priority=10,
    llm_hint="意図が不明確な場合に使用",  # 曖昧 = LLM
)
```

### ❌ 警告を無視する

```python
# 警告には理由がある！
if result.has_warnings:
    for warning in result.warnings:
        print(f"⚠️  {warning}")
    # 本番前に修正を検討
```

---

## 次のステップ

- 🐛 [トラブルシューティング](troubleshooting.ja.md) - よくある問題
- 📚 [コアコンセプト](core_concepts.ja.md) - 詳細
