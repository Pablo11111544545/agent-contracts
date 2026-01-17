# コアコンセプト

> agent-contractsアーキテクチャの詳細

---

## 概要

`agent-contracts`はシンプルな原則に基づいています：**ノードが何をするかを宣言し、どう接続するかは宣言しない**

```
┌─────────────────────────────────────────────────────────────┐
│                        Registry                              │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐               │
│  │ NodeA     │  │ NodeB     │  │ NodeC     │  ...          │
│  │ CONTRACT  │  │ CONTRACT  │  │ CONTRACT  │               │
│  └───────────┘  └───────────┘  └───────────┘               │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     GraphBuilder                             │
│  • コントラクトを分析                                         │
│  • スーパーバイザーを作成                                     │
│  • LangGraphを自動配線                                       │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      LangGraph                               │
│  START → Supervisor ⟷ Nodes → END                           │
└─────────────────────────────────────────────────────────────┘
```

---

## NodeContract

`NodeContract`はライブラリの中心です。ノードに関するすべてを宣言します：

```python
NodeContract(
    # === 識別 ===
    name="my_node",                    # 一意の識別子
    description="このノードの役割", # 人間が読める説明
    
    # === I/O定義 ===
    reads=["request", "context"],      # 読み取るステートスライス
    writes=["response"],               # 書き込むステートスライス
    
    # === 依存関係 ===
    requires_llm=True,                 # LLMが必要か
    services=["db_service"],           # 必要な外部サービス
    
    # === ルーティング ===
    supervisor="main",                 # 管理するスーパーバイザー
    trigger_conditions=[...],          # ノードを起動する条件
    is_terminal=False,                 # 実行後にフローを終了するか
)
```

### なぜコントラクトか？

| コントラクトなし | コントラクトあり |
|-----------------|-----------------|
| 手動でグラフを配線 | 自動グラフ構築 |
| 依存関係が隠れている | 明示的なI/O宣言 |
| ランタイムエラー | 静的検証 |
| ドキュメント化が困難 | 自動生成ドキュメント |

---

## ステートスライス

`agent-contracts`のステートは独立した**スライス**に整理されます：

```python
state = {
    "request": {           # ユーザーからの入力
        "action": "search",
        "params": {"query": "laptop"}
    },
    "response": {          # ユーザーへの出力
        "response_type": "results",
        "data": [...]
    },
    "context": {           # 共有コンテキスト
        "user_preferences": {...}
    },
    "_internal": {         # フレームワーク内部
        "decision": "search_node",
        "iteration": 1
    }
}
```

### 設計原則

1. **関心の分離**: 各スライスは単一の目的を持つ
2. **明示的アクセス**: ノードは読み書きするスライスを宣言
3. **検証**: 不明なスライス名や、コントラクト外I/Oは警告/エラーで検知できる

**コントラクト外I/Oの扱い（実行時）**:
- **デフォルト**: 警告して継続（コントラクト外writeはデフォルトで破棄）
- **strict**: 例外（`ContractViolationError`）で停止
- **コントラクト外read**: デフォルトでは `{}` を返す（strictでは例外）
- **コントラクト外write**: デフォルトでは破棄（strictでは例外）

YAML設定例:
```yaml
io:
  strict: true                  # 例外で停止
  warn: true                    # 警告ログ
  drop_undeclared_writes: true  # コントラクト外writeを破棄
```

### 組み込みスライス

| スライス | 目的 |
|----------|------|
| `request` | ユーザー入力（読み取り専用推奨） |
| `response` | ユーザー出力 |
| `_internal` | フレームワークのルーティング/イテレーション |

カスタムスライスを定義可能：

```python
registry.add_valid_slice("orders")
registry.add_valid_slice("workflow")
```

---

## TriggerCondition

トリガー条件はノードが選択されるタイミングを制御します：

```python
TriggerCondition(
    priority=10,                           # 高い = 先に評価
    when={"request.action": "search"},     # マッチ条件
    when_not={"response.done": True},      # 否定マッチ
    llm_hint="商品検索に使用",               # LLMルーティングヒント
)
```

### 優先度レベル

| 範囲 | 用途 | 例 |
|------|------|----|
| 🔴 100+ | クリティカル/即時 | エラーハンドラ |
| 🟡 50-99 | 主要ハンドラ | メインビジネスロジック |
| 🟢 1-49 | フォールバック | デフォルトハンドラ |
| ⚪ 0 | 常にマッチ | キャッチオール |

### 条件マッチング

```python
# 正確な値マッチ
when={"request.action": "search"}

# ブール値チェック
when={"context.authenticated": True}

# ネストパス
when={"request.params.category": "electronics"}

# 複数条件 (AND)
when={"request.action": "buy", "context.cart_ready": True}
```

---

## GenericSupervisor

スーパーバイザーは多段階アプローチでノード選択を調整します。

### LLM用データサニタイズ（v0.3.3+）

Supervisorはルーティング判断のためにLLMに送信する前に、ステートデータを自動的にサニタイズします：

**自動処理**:
- **画像データ**: Base64エンコード画像（`image/`または`image`パターンで検出）は`"[IMAGE_DATA]"`に置換
- **長い文字列**: `max_field_length`（デフォルト: 10000文字）を超える文字列は、先頭部分を保持してトリミング
  - フォーマット: `data[:max_field_length] + "...[TRUNCATED:N_chars]"`
  - 例: 15000文字の文字列は: `"最初の10000文字...[TRUNCATED:5000_chars]"`になる

**メリット**:
- **トークン効率**: base64画像データによる大量のトークン消費を防止
- **コンテキスト保持**: 長いフィールドの先頭を維持することで、より良いルーティング判断を実現
- **カスタマイズ可能**: `max_field_length`パラメータで調整可能

**設定**:
```python
from agent_contracts import GenericSupervisor

supervisor = GenericSupervisor(
    supervisor_name="main",
    llm=llm,
    max_field_length=10000,  # デフォルト: 10000文字
)
```

### 決定フロー

```
┌─────────────────────────────────────────────────────────────┐
│                    決定フロー                                │
├─────────────────────────────────────────────────────────────┤
│  1. 終了状態チェック                                         │
│     └─ response_type が terminal_states に含まれる → done    │
│                                                              │
│  2. 明示的ルーティング                                       │
│     └─ action="answer" → 質問の送信元にルーティング          │
│                                                              │
│  3. ルールベース評価                                         │
│     └─ 全TriggerConditionを評価、候補を収集                  │
│                                                              │
│  4. LLM決定（利用可能な場合）                                │
│     └─ LLMがllm_hintsを使用して候補から選択                  │
│                                                              │
│  5. フォールバック                                           │
│     └─ 最高優先度のルールマッチを使用                        │
└─────────────────────────────────────────────────────────────┘
```

### LLMあり vs なし

| モード | 動作 |
|--------|------|
| **LLMあり** | LLMがルールヒントを使用して最終決定 |
| **LLMなし** | 純粋なルールベース、最高優先度マッチを使用 |

---

## InteractiveNode

会話型エージェントには`InteractiveNode`を使用：

```python
from agent_contracts import InteractiveNode, NodeContract, NodeOutputs, TriggerCondition


class QuestionerNode(InteractiveNode):
    CONTRACT = NodeContract(
        name="questioner",
        description="質問を行い、回答を処理する",
        reads=["request", "workflow"],
        writes=["response", "workflow", "_internal"],
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(priority=10, llm_hint="次の質問を行うときに使用"),
        ],
    )
    
    def prepare_context(self, inputs):
        """Extract context from inputs."""
        return inputs.get_slice("workflow")
    
    def check_completion(self, context, inputs):
        """インタビュー完了をチェック"""
        return len(context.get("answers", [])) >= 5
    
    async def process_answer(self, context, inputs, config=None):
        """ユーザーの回答を処理"""
        answer = inputs.get_slice("request").get("answer")
        # 回答を保存...
        return True
    
    async def generate_question(self, context, inputs, config=None):
        """次の質問を生成"""
        # LLMで質問を生成...
        return NodeOutputs(
            response={
                "response_type": "question",
                "response_data": {"question": "どの色が好きですか？"},
            }
        )
```

### ライフサイクル

```
┌─────────────────────────────────────────────────────────────┐
│                  InteractiveNode フロー                      │
├─────────────────────────────────────────────────────────────┤
│  1. prepare_context()     → 必要なデータを抽出               │
│  2. check_completion()    → 既に完了？                       │
│       └─ Yes → create_completion_output()                    │
│       └─ No ↓                                               │
│  3. process_answer()      → ユーザーの応答を処理             │
│  4. check_completion()    → 今完了？                         │
│       └─ Yes → create_completion_output()                    │
│       └─ No → generate_question()                           │
└─────────────────────────────────────────────────────────────┘
```

---

## ContractValidator

実行前にコントラクトを検証：

```python
from agent_contracts import ContractValidator

validator = ContractValidator(
    registry,
    known_services={"db_service", "cache_service"},
)
result = validator.validate()

if result.has_errors:
    print(result)  # エラーを表示
    exit(1)
```

### Strictモード（CI向け）

```python
validator = ContractValidator(
    registry,
    known_services={"db_service", "cache_service"},
    strict=True,  # WARNINGもERRORとして扱う
)
result = validator.validate()
```

**Strictモード**は、WARNING（不明なサービス、到達不能ノード、`request`への書き込み等）を
ERRORに昇格し、CIで早期に検知できます。

### 検証レベル

| レベル | 例 |
|--------|-----|
| **ERROR** | reads/writesの不明なスライス |
| **WARNING** | 不明なサービス、到達不能ノード |
| **INFO** | 共有ライター（複数ノードが同じスライスに書き込み） |


---

## トレーサブルルーティング

デバッグには`decide_with_trace()`を使用：

```python
decision = await supervisor.decide_with_trace(state)

print(f"選択: {decision.selected_node}")
print(f"タイプ: {decision.reason.decision_type}")

for rule in decision.reason.matched_rules:
    print(f"  {rule.node} (P{rule.priority}): {rule.condition}")
```

### 決定タイプ

| タイプ | 意味 |
|--------|------|
| `terminal_state` | レスポンスタイプが終了をトリガー |
| `explicit_routing` | 回答が質問の送信元にルーティング |
| `rule_match` | TriggerConditionがマッチ |
| `llm_decision` | LLMが選択 |
| `fallback` | マッチなし、デフォルトを使用 |

### TriggerMatch構造（v0.4.0+）

v0.4.0から、`evaluate_triggers()`は`TriggerMatch`オブジェクトを返します：

```python
from agent_contracts import TriggerMatch

# evaluate_triggers() の返り値
matches: list[TriggerMatch] = registry.evaluate_triggers("supervisor_name", state)

for match in matches:
    print(f"ノード: {match.node_name}")
    print(f"優先度: {match.priority}")
    print(f"条件インデックス: {match.condition_index}")  # 実際にマッチした条件
```

**メリット:**
- 同じ優先度の複数条件がある場合でも、実際にマッチした条件を正確に特定
- LLMルーティングでより正確な説明を提供
- デバッグとトレーサビリティの向上

**マイグレーション (v0.3.x → v0.4.0):**

```python
# v0.3.x - tuple形式
matches: list[tuple[int, str]] = registry.evaluate_triggers("main", state)
for priority, node_name in matches:
    print(f"{node_name}: P{priority}")

# v0.4.0 - TriggerMatch形式
matches: list[TriggerMatch] = registry.evaluate_triggers("main", state)
for match in matches:
    print(f"{match.node_name}: P{match.priority}")
```

**注意:** `GenericSupervisor`や`decide()`/`decide_with_trace()`を使用している場合は、変更不要です。


## Supervisorのコンテキスト構築

`GenericSupervisor`はLLMベースのルーティング判断のためのコンテキストを自動的に構築します。

### デフォルトのコンテキスト構築（v0.2.3+）

デフォルトでは、Supervisorは**最小限のコンテキスト**をLLMに提供します：

1. **基本スライスのみ**: 常に`request`、`response`、`_internal`を含む
2. **根拠**:
   - 候補スライスはトリガー条件で既に評価済み
   - それらをLLMに渡すのは冗長でトークンを浪費
   - 明確な分離：トリガー = ルールベースフィルタリング、LLM = 最終選択
3. **メリット**:
   - 大幅なトークン削減
   - パフォーマンス向上（シリアライズと送信データが少ない）
   - LLM理解のため`response`経由で会話コンテキストを維持

### カスタムコンテキストビルダー（v0.3.0+）

追加のコンテキストが必要な複雑なシナリオでは、カスタム`context_builder`関数を提供できます：

```python
from agent_contracts import GenericSupervisor

def my_context_builder(state: dict, candidates: list[str]) -> dict:
    """ルーティング判断用のカスタムコンテキストを構築"""
    return {
        "slices": {"request", "response", "_internal", "conversation"},
        "summary": {
            "total_turns": len(state.get("conversation", {}).get("messages", [])),
            "readiness_score": calculate_readiness(state),
        }
    }

supervisor = GenericSupervisor(
    supervisor_name="orders",
    llm=llm,
    context_builder=my_context_builder,
)
```

### サマリーフォーマット（v0.3.1+）

`context_builder`の戻り値の`summary`フィールドは`dict`と`str`の両フォーマットをサポート：

```python
# 文字列フォーマット - プロンプトに直接含まれる（整形テキストに最適）
def context_builder(state, candidates):
    return {
        "slices": {"request", "response", "conversation"},
        "summary": f"最近の会話:\n{format_messages(state)}"
    }

# 辞書フォーマット - 含まれる前にJSON化（構造を保持）
def context_builder(state, candidates):
    return {
        "slices": {"request", "response", "conversation"},
        "summary": {
            "turn_count": 5,
            "topics": ["orders", "preferences"]
        }
    }
```

### レジストリベースグラフでの使用（v0.3.1+）

`build_graph_from_registry()`を`llm_provider`と共に使用する場合、`supervisor_factory`を使用してカスタムスーパーバイザーを注入：

```python
from agent_contracts import build_graph_from_registry, GenericSupervisor

def my_context_builder(state, candidates):
    return {
        "slices": {"request", "response", "conversation"},
        "summary": f"会話履歴:\n{format_history(state)}"
    }

def supervisor_factory(name: str, llm):
    return GenericSupervisor(
        supervisor_name=name,
        llm=llm,
        context_builder=my_context_builder,  # カスタムコンテキストが保持される！
    )

graph = build_graph_from_registry(
    llm_provider=get_llm,
    supervisor_factory=supervisor_factory,  # カスタムスーパーバイザーを注入
    supervisors=["orders", "notifications"],
)
```

### コンテキストビルダープロトコル

```python
from typing import Protocol

class ContextBuilder(Protocol):
    def __call__(self, state: dict, candidates: list[str]) -> dict:
        """
        LLMルーティング判断用のコンテキストを構築
        
        Args:
            state: 現在のエージェント状態
            candidates: 候補ノード名のリスト
            
        Returns:
            以下を含む辞書:
            - slices (set[str]): 含めるスライス名のセット
            - summary (dict | str | None): オプションの追加コンテキスト
              - str: プロンプトに直接含まれる（整形テキスト）
              - dict: 含まれる前にJSON化
        """
        ...
```

### ユースケース

| シナリオ | カスタムコンテキスト |
|----------|---------------------|
| **ECサイト** | 購入認識ルーティングのために`cart`、`inventory`を含める |
| **カスタマーサポート** | コンテキスト認識レスポンスのために`ticket_history`、`sentiment`を含める |
| **教育** | 適応型指導のために`learning_progress`、`pace`を含める |
| **会話** | ターン数と履歴を含む`conversation`を含める |

### 例: 会話認識ルーティング

```python
def conversation_context_builder(state: dict, candidates: list[str]) -> dict:
    """より良いルーティングのために会話履歴を含める"""
    messages = state.get("conversation", {}).get("messages", [])
    
    # LLM可読性向上のため文字列としてフォーマット
    formatted = "\n".join([
        f"{m['role']}: {m['content']}"
        for m in messages[-5:]  # 最後の5メッセージ
    ])
    
    return {
        "slices": {"request", "response", "_internal", "conversation"},
        "summary": f"最近の会話 ({len(messages)} ターン):\n{formatted}"
    }
```

### メリット

- **柔軟性**: アプリケーションドメインごとにコンテキストをカスタマイズ
- **後方互換性**: 提供されない場合は最小コンテキストをデフォルトで使用
- **型安全**: プロトコルが正しい実装を保証
- **効率的**: LLMに送信されるコンテキストを正確に制御
- **フォーマットサポート**: 整形テキスト用の文字列、構造化データ用の辞書

### 移行ノート

- **v0.2.x → v0.3.0**: 移行不要、完全に後方互換性あり
- **v0.3.0 → v0.3.1**: `build_graph_from_registry()`を`llm_provider`と共に使用する場合、`context_builder`を保持するために`supervisor_factory`を使用

---

## StateAccessorパターン

型安全でイミュータブルな状態フィールドアクセス：

```python
from agent_contracts import Internal, Request, Response, reset_response

# 状態の読み取り
count = Internal.turn_count.get(state)
action = Request.action.get(state)

# 状態の書き込み（イミュータブル - 新しいstateを返す）
state = Internal.turn_count.set(state, 5)
state = reset_response(state)
```

### 利用可能なアクセサー

| クラス | フィールド |
|-------|----------|
| `Internal` | `turn_count`, `is_first_turn`, `active_mode`, `next_node`, `error` |
| `Request` | `session_id`, `action`, `params`, `message`, `image` |
| `Response` | `response_type`, `response_data`, `response_message` |

### 便利関数

```python
from agent_contracts import increment_turn, set_error, clear_error

state = increment_turn(state)  # turn_count++, is_first_turn=False
state = set_error(state, "エラーが発生しました")
state = clear_error(state)
```

---

## Runtimeレイヤー

本番アプリケーションでは、統合実行のためにRuntimeレイヤーを使用：

### AgentRuntime

```python
from agent_contracts import AgentRuntime, RequestContext, InMemorySessionStore

runtime = AgentRuntime(
    graph=compiled_graph,
    session_store=InMemorySessionStore(),
)

result = await runtime.execute(RequestContext(
    session_id="abc123",
    action="answer",
    message="カジュアルが好き",
    resume_session=True,
))
```

### 実行ライフサイクル

```
┌─────────────────────────────────────────────────────────────┐
│                  AgentRuntime ライフサイクル                 │
├─────────────────────────────────────────────────────────────┤
│  1. 初期状態を作成                                           │
│  2. セッションを復元（resume_session=True の場合）            │
│  3. hooks.prepare_state() → 実行前カスタマイズ               │
│  4. graph.ainvoke() → LangGraphを実行                        │
│  5. ExecutionResultを構築                                    │
│  6. hooks.after_execution() → 永続化、クリーンアップ         │
└─────────────────────────────────────────────────────────────┘
```

### カスタムフック

```python
from agent_contracts import RuntimeHooks

class MyHooks(RuntimeHooks):
    async def prepare_state(self, state, request):
        # 状態の正規化、リソースの読み込み
        return state
    
    async def after_execution(self, state, result):
        # セッション保存、ログなど
        await self.session_store.save(...)
```

### StreamingRuntime（SSE対応）

```python
from agent_contracts.runtime import StreamingRuntime, StreamEventType

runtime = (
    StreamingRuntime()
    .add_node("search", search_node, "検索中...")
    .add_node("stylist", stylist_node, "生成中...")
)

async for event in runtime.stream(request):
    if event.type == StreamEventType.NODE_END:
        print(f"ノード {event.node_name} 完了")
    yield event.to_sse()
```

---

## 次のステップ

- 🎯 [ベストプラクティス](best_practices.ja.md) - 設計パターン
- 🐛 [トラブルシューティング](troubleshooting.ja.md) - よくある問題
