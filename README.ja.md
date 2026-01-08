# agent-contracts

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MPL 2.0](https://img.shields.io/badge/License-MPL_2.0-brightgreen.svg)](https://opensource.org/licenses/MPL-2.0)
[![CI](https://github.com/yatarousan0227/agent-contracts/actions/workflows/ci.yml/badge.svg)](https://github.com/yatarousan0227/agent-contracts/actions/workflows/ci.yml)

**LangGraphエージェント構築のための、モジュラーでコントラクト駆動のノードアーキテクチャ**

[English](README.md) | 日本語

`agent-contracts`は、宣言的なコントラクトを使用してAIエージェントを構築するための構造化されたフレームワークです。ノードのI/O、依存関係、ルーティングルールを定義し、自動グラフ構築、型安全な状態管理、柔軟なLLMベースのルーティングを実現します。

![アーキテクチャ概要](images/overview.png)

---

## ✨ 特徴

- **📝 コントラクト駆動設計**: `NodeContract`を通じてノードのI/O、依存関係、トリガー条件を宣言
- **🔧 レジストリベースアーキテクチャ**: 手動配線なしで登録されたノードからLangGraphを自動構築
- **🧠 LLM駆動スーパーバイザー**: ルールヒントを参考にLLMがルーティングを決定
- **💬 インタラクティブノード**: インタビューパターンを持つ会話型エージェント用の基底クラス
- **📊 型付き状態管理**: Pydanticベースの状態スライスとバリデーション
- **🔒 StateAccessorパターン**: 型安全でイミュータブルな状態アクセス、IDE補完対応
- **🔄 Runtimeレイヤー**: フック、セッション管理、ストリーミングを備えた統合実行エンジン
- **⚙️ YAML設定**: Pydanticバリデーション付きの外部設定
- **🏗️ アーキテクチャ視覚化**: コントラクトから包括的なドキュメントを自動生成

---

## 📦 インストール

```bash
pip install agent-contracts

# または git から
pip install git+https://github.com/yatarousan0227/agent-contracts.git
```

### 必要要件

- Python 3.11+
- LangGraph >= 0.2.0
- LangChain Core >= 0.3.0
- Pydantic >= 2.0.0

---

## 🚀 クイックスタート

### 1. コントラクト付きノードの定義

```python
from agent_contracts import ModularNode, NodeContract, NodeInputs, NodeOutputs, TriggerCondition

class GreetingNode(ModularNode):
    CONTRACT = NodeContract(
        name="greeting",
        description="パーソナライズされた挨拶を生成",
        reads=["request"],
        writes=["response"],
        requires_llm=True,
        supervisor="main",
        trigger_conditions=[
            TriggerCondition(
                when={"request.action": "greet"},
                priority=10,
            )
        ],
    )

    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        request = inputs.get_slice("request")
        user_name = request.get("params", {}).get("name", "ユーザー")
        
        # LLMで挨拶を生成
        response = await self.llm.ainvoke(
            f"{user_name}さんへのフレンドリーな挨拶を生成してください",
            config=config,  # トレース用にconfigを渡す
        )
        
        return NodeOutputs(
            response={
                "response_type": "greeting",
                "response_data": {"message": response.content},
            }
        )
```

### 2. 登録とグラフ構築

```python
from agent_contracts import get_node_registry, build_graph_from_registry
from langchain_openai import ChatOpenAI

# グローバルレジストリを取得
registry = get_node_registry()

# ノードを登録
registry.register(GreetingNode)

# LangGraphを構築
llm = ChatOpenAI(model="gpt-4")
graph = build_graph_from_registry(
    registry=registry,
    llm=llm,
    supervisors=["main"],
)
compiled = graph.compile()

# グラフを実行
result = await compiled.ainvoke({
    "request": {
        "action": "greet",
        "params": {"name": "太郎"}
    },
})
```

---

## 🏗️ コアコンセプト

### NodeContract

`NodeContract`はこのライブラリの中心です。ノードに関するすべてを宣言します：

```python
NodeContract(
    # 識別情報
    name="my_node",                    # 一意のノード識別子
    description="このノードが行うこと", # 人間が読める説明
    
    # I/O定義（状態スライス単位）
    reads=["request", "context"],      # このノードが読み取る状態スライス
    writes=["response"],               # このノードが書き込む状態スライス
    
    # 依存関係
    requires_llm=True,                 # LLMが必要かどうか
    services=["db_service"],           # 必要なサービス名
    
    # ルーティング
    supervisor="main",                 # このノードを管理するスーパーバイザー
    trigger_conditions=[...],          # このノードをトリガーする条件
    is_terminal=False,                 # 実行後にENDするかどうか
)
```

### TriggerCondition

スーパーバイザーがノードを選択するタイミングを定義：

```python
TriggerCondition(
    priority=10,                           # 高いほど優先的に評価
    when={"request.action": "search"},     # ルールベースのマッチング
    when_not={"response.done": True},      # 否定マッチング
    llm_hint="商品検索に使用",             # LLMルーティングのヒント
)
```

### GenericSupervisor

スーパーバイザーはノード選択を統括します：

1. **即時ルール**: 終端状態のチェック
2. **明示的ルーティング**: 回答を質問元ノードに返す
3. **ルールヒント収集**: トリガー条件から候補を収集
4. **LLM判断**: ルールヒントを参考にLLMが最終決定
5. **フォールバック**: LLM不在時はルール候補を使用

```python
from agent_contracts import GenericSupervisor

supervisor = GenericSupervisor(
    supervisor_name="main",
    llm=llm,
    max_iterations=10,
)
```

### InteractiveNode

会話型エージェントには`InteractiveNode`を継承：

```python
from agent_contracts import InteractiveNode

class InterviewNode(InteractiveNode):
    CONTRACT = NodeContract(...)
    
    def prepare_context(self, inputs):
        """入力からコンテキストを抽出"""
        return {"interview_state": inputs.get_slice("interview")}
    
    def check_completion(self, context, inputs):
        """インタビュー完了をチェック"""
        return context["interview_state"].get("complete", False)
    
    async def process_answer(self, context, inputs):
        """ユーザーの回答を処理"""
        # 回答を処理
        return True
    
    async def generate_question(self, context, inputs):
        """次の質問を生成"""
        return NodeOutputs(response={"question": "..."})
```

---

## ⚙️ 設定

プロジェクトに`agent_config.yaml`を作成：

```yaml
supervisor:
  max_iterations: 10

response_types:
  terminal_states:
    - interview
    - proposals
    - error

interview:
  my_interviewer:
    max_turns: 10
    max_questions: 5
```

設定の読み込み：

```python
from agent_contracts.config import load_config, set_config, get_config

# ファイルから読み込みグローバルに設定
config = load_config("path/to/agent_config.yaml")
set_config(config)

# どこからでも設定にアクセス
config = get_config()
print(config.supervisor.max_iterations)
```

---

---
 
 ## 🔍 可観測性 (LangSmith)
 
 `agent-contracts`は[LangSmith](https://smith.langchain.com/)と完全に統合されており、トレースとデバッグが可能です。
 
 ### 1. 環境変数の設定
 
 ```bash
 export LANGCHAIN_TRACING_V2=true
 export LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
 export LANGCHAIN_API_KEY="<your-api-key>"
 export LANGCHAIN_PROJECT="my-agent-project"
 ```
 
 ### 2. 自動トレース
 
 グラフを実行するだけで、自動的にトレースがLangSmithに送信されます。フレームワークはデバッグに役立つ豊富なメタデータを追加します：
 
 - **Supervisors**: 反復回数、決定理由、候補ルールを表示
 - **Nodes**: 実行時間、入出力スライス、ノードタイプを表示
 
 ---
 
 ## 🏗️ アーキテクチャ視覚化

登録されたコントラクトから包括的なアーキテクチャドキュメントを生成：

```python
from agent_contracts import ContractVisualizer, get_node_registry

registry = get_node_registry()
# ... ノードを登録 ...
# ... グラフを構築 ...
# compiled_graph = graph.compile()

# グラフを渡すことでLangGraphのフローも可視化可能
visualizer = ContractVisualizer(registry, graph=compiled_graph)
doc = visualizer.generate_architecture_doc()

with open("ARCHITECTURE.md", "w") as f:
    f.write(doc)
```

### 生成されるセクション

| セクション | 説明 |
|-----------|------|
| **📦 State Slices** | 全スライスの読み書き関係 + ERダイアグラム |
| **🔗 LangGraph Node Flow** | コンパイルされたグラフのMermaid可視化 |
| **🎯 System Hierarchy** | Supervisor-Node構造のMermaidフローチャート |
| **🔀 Data Flow** | 共有スライスによるノード依存関係 |
| **⚡ Trigger Hierarchy** | 優先度順トリガー (🔴高 → 🟢低) |
| **📚 Nodes Reference** | 全ノード詳細テーブル |

### 個別セクション生成

セクションを個別に生成することも可能：

```python
# LangGraphフロー
print(visualizer.generate_langgraph_flow())

# 状態スライスドキュメント
print(visualizer.generate_state_slices_section())

# 階層ダイアグラム
print(visualizer.generate_hierarchy_diagram())

# データフロー
print(visualizer.generate_dataflow_diagram())

# トリガー階層
print(visualizer.generate_trigger_hierarchy())

# ノード参照テーブル
print(visualizer.generate_nodes_reference())
```

出力例は [ARCHITECTURE_SAMPLE.md](docs/ARCHITECTURE_SAMPLE.md) を参照。

---
 
 ## 📚 APIリファレンス

### 主要エクスポート

| エクスポート | 説明 |
|-------------|------|
| `ModularNode` | すべてのノードの基底クラス |
| `InteractiveNode` | 会話型ノードの基底クラス |
| `NodeContract` | ノードI/Oコントラクト定義 |
| `TriggerCondition` | ルーティング用トリガー条件 |
| `NodeInputs` / `NodeOutputs` | 型付きI/Oコンテナ |
| `NodeRegistry` | ノードの登録と探索 |
| `GenericSupervisor` | LLM駆動ルーティングスーパーバイザー |
| `GraphBuilder` | LangGraph自動構築 |
| `BaseAgentState` | スライス付き基底状態クラス |
| `ContractVisualizer` | アーキテクチャドキュメント生成 |

### Runtimeレイヤー

| エクスポート | 説明 |
|-------------|------|
| `AgentRuntime` | ライフサイクルフック付き統合実行エンジン |
| `StreamingRuntime` | SSE用ノード単位ストリーミング |
| `RequestContext` | 実行リクエストコンテナ |
| `ExecutionResult` | レスポンス付き実行結果 |
| `RuntimeHooks` | カスタマイズフック用Protocol |
| `SessionStore` | セッション永続化用Protocol |
| `InMemorySessionStore` | 開発/テスト用インメモリストア |

### StateAccessorパターン

型安全でイミュータブルな状態アクセス：

```python
from agent_contracts import (
    Internal,
    Request,
    Response,
    reset_response,
)

# 状態の読み取り
count = Internal.turn_count.get(state)

# 状態の書き込み（イミュータブル - 新しいstateを返す）
state = Internal.turn_count.set(state, 5)
state = reset_response(state)
```

### 状態操作ヘルパー

```python
from agent_contracts.runtime import (
    create_base_state,
    merge_session,
    reset_internal_flags,
    update_slice,
)

# 初期状態の作成
state = create_base_state(session_id="abc", action="answer")

# セッションデータのマージ
state = merge_session(state, session_data, ["interview", "shopping"])

# スライスの更新
state = update_slice(state, "interview", question_count=5)
```

---

## 🔄 Runtimeレイヤー

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

print(result.response_type)  # "interview", "proposals" など
print(result.response_data)  # レスポンスペイロード
```

### StreamingRuntime（SSE対応）

```python
from agent_contracts.runtime import StreamingRuntime

runtime = (
    StreamingRuntime()
    .add_node("search", search_node, "検索中...")
    .add_node("stylist", stylist_node, "おすすめ生成中...")
)

async for event in runtime.stream(request):
    yield event.to_sse()
```

### カスタムフック & セッションストア

アプリケーション固有のProtocol実装：

```python
from agent_contracts import RuntimeHooks, SessionStore

class PostgresSessionStore(SessionStore):
    async def load(self, session_id: str) -> dict | None:
        return await self.db.get_session(session_id)
    
    async def save(self, session_id: str, data: dict, ttl: int = 3600):
        await self.db.save_session(session_id, data, ttl)
    
    async def delete(self, session_id: str):
        await self.db.delete_session(session_id)

class MyHooks(RuntimeHooks):
    async def prepare_state(self, state, request):
        # 実行前の状態正規化
        return state
    
    async def after_execution(self, state, result):
        # セッション永続化、ログなど
        pass
```

---

## 📖 サンプル

| サンプル | 説明 |
|---------|------|
| [01_contract_validation.py](examples/01_contract_validation.py) | 静的コントラクト検証デモ |
| [02_routing_explain.py](examples/02_routing_explain.py) | 追跡可能なルーティング決定デモ |

実行方法:

```bash
python examples/01_contract_validation.py
python examples/02_routing_explain.py
```

---

## 📚 ドキュメント

| ドキュメント | 説明 |
|-------------|------|
| [はじめに](docs/getting_started.ja.md) | agent-contractsの始め方 |
| [コアコンセプト](docs/core_concepts.ja.md) | アーキテクチャの詳細 |
| [ベストプラクティス](docs/best_practices.ja.md) | 設計パターンとヒント |
| [トラブルシューティング](docs/troubleshooting.ja.md) | よくある問題と解決策 |


---

## 🤝 コントリビューション

コントリビューションを歓迎します！お気軽にPull Requestを送信してください。

---

## 📄 ライセンス

このプロジェクトはMozilla Public License 2.0 (MPL-2.0)の下で公開されています - 詳細は[LICENSE](LICENSE)ファイルをご覧ください。

> **なぜMPL 2.0？** コミュニティからの貢献を促進しつつ、統合のしやすさを維持するためにMPL 2.0を選択しました。`agent-contracts`のコアファイルへの改善は共有が必要ですが、独自のノードや拡張機能はあなたのものとして保持できます。

---

## 🔗 リンク

- [GitHubリポジトリ](https://github.com/yatarousan0227/agent-contracts)
- [LangGraphドキュメント](https://langchain-ai.github.io/langgraph/)
- [LangChainドキュメント](https://python.langchain.com/)
