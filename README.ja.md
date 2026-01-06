# agent-contracts

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**LangGraphエージェント構築のための、モジュラーでコントラクト駆動のノードアーキテクチャ**

[English](README.md) | 日本語

`agent-contracts`は、宣言的なコントラクトを使用してAIエージェントを構築するための構造化されたフレームワークです。ノードのI/O、依存関係、ルーティングルールを定義し、自動グラフ構築、型安全な状態管理、柔軟なLLMベースのルーティングを実現します。

---

## ✨ 特徴

- **📝 コントラクト駆動設計**: `NodeContract`を通じてノードのI/O、依存関係、トリガー条件を宣言
- **🔧 レジストリベースアーキテクチャ**: 手動配線なしで登録されたノードからLangGraphを自動構築
- **🧠 スマートスーパーバイザー**: ルールベース + LLMフォールバックによる柔軟なルーティング
- **💬 インタラクティブノード**: インタビューパターンを持つ会話型エージェント用の基底クラス
- **📊 型付き状態管理**: Pydanticベースの状態スライスとバリデーション
- **⚙️ YAML設定**: Pydanticバリデーション付きの外部設定

---

## 📦 インストール

```bash
pip install agent-contracts

# または git から
pip install git+https://github.com/your-org/agent-contracts.git
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

    async def execute(self, inputs: NodeInputs) -> NodeOutputs:
        request = inputs.get_slice("request")
        user_name = request.get("params", {}).get("name", "ユーザー")
        
        # LLMで挨拶を生成
        response = await self.llm.ainvoke(
            f"{user_name}さんへのフレンドリーな挨拶を生成してください"
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
from agent_contracts import get_node_registry, GraphBuilder
from langchain_openai import ChatOpenAI

# グローバルレジストリを取得
registry = get_node_registry()

# ノードを登録
registry.register(GreetingNode)

# LangGraphを構築
llm = ChatOpenAI(model="gpt-4")
builder = GraphBuilder(registry, default_llm=llm)
graph = builder.build_graph()

# グラフを実行
result = await graph.ainvoke({
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
2. **ルールベース評価**: トリガー条件のマッチング
3. **LLM判断**: 複雑なルーティングにはLLMを使用

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
from agent_contracts.config import load_config, get_config

# ファイルから読み込み
load_config("path/to/agent_config.yaml")

# 設定にアクセス
config = get_config()
print(config.supervisor.max_iterations)
```

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
| `GenericSupervisor` | スマートルーティングスーパーバイザー |
| `GraphBuilder` | LangGraph自動構築 |
| `BaseAgentState` | スライス付き基底状態クラス |

### 状態管理

```python
from agent_contracts import (
    BaseAgentState,
    BaseRequestSlice,
    BaseResponseSlice,
    get_slice,
    merge_slice_updates,
)
```

---

## 🤝 コントリビューション

コントリビューションを歓迎します！お気軽にPull Requestを送信してください。

---

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています - 詳細は[LICENSE](LICENSE)ファイルをご覧ください。

---

## 🔗 リンク

- [GitHubリポジトリ](https://github.com/your-org/agent-contracts)
- [LangGraphドキュメント](https://langchain-ai.github.io/langgraph/)
- [LangChainドキュメント](https://python.langchain.com/)
