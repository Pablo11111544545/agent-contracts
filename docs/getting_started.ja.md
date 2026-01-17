# はじめに

> 10分で最初のエージェントを構築

---

## 前提条件

- Python 3.11+
- LangGraphの基本的な理解

---

## インストール

```bash
# PyPIから
pip install agent-contracts

# またはGitHubから
pip install git+https://github.com/yatarousan0227/agent-contracts.git
```

---

## 最初のノード

挨拶リクエストを処理するシンプルなノードを作成：

```python
# my_agent.py
from agent_contracts import (
    ModularNode,
    NodeContract,
    NodeInputs,
    NodeOutputs,
    TriggerCondition,
)


class GreetingNode(ModularNode):
    """シンプルな挨拶ノード"""
    
    CONTRACT = NodeContract(
        name="greeting",
        description="パーソナライズされた挨拶を生成",
        reads=["request"],           # 'request'スライスから読み取り
        writes=["response"],         # 'response'スライスに書き込み
        supervisor="main",           # 'main'スーパーバイザーに所属
        is_terminal=True,            # このノードの後にフローを終了
        trigger_conditions=[
            TriggerCondition(
                priority=10,
                when={"request.action": "greet"},
                llm_hint="ユーザーが挨拶を求めている時に使用",
            )
        ],
    )
    
    async def execute(self, inputs: NodeInputs, config=None) -> NodeOutputs:
        # requestスライスからデータを取得
        request = inputs.get_slice("request")
        name = request.get("params", {}).get("name", "World")
        
        # レスポンスを返す
        return NodeOutputs(
            response={
                "response_type": "greeting",
                "response_message": f"こんにちは、{name}さん！",
            }
        )
```

---

## 最初のグラフ

ノードを登録してLangGraphを構築：

```python
from agent_contracts import BaseAgentState, get_node_registry, build_graph_from_registry
from langchain_openai import ChatOpenAI


# グローバルレジストリを取得
registry = get_node_registry()

# ノードを登録
registry.register(GreetingNode)

# グラフを構築（シンプルなルーティングならLLMはオプション）
llm = ChatOpenAI(model="gpt-4")
graph = build_graph_from_registry(
    registry=registry,
    llm=llm,
    supervisors=["main"],
    state_class=BaseAgentState,
)

# エントリーポイント設定してコンパイル
graph.set_entry_point("main_supervisor")
compiled = graph.compile()
```

---

## エージェントの実行

```python
import asyncio


async def main():
    result = await compiled.ainvoke({
        "request": {
            "action": "greet",
            "params": {"name": "太郎"},
        },
    })
    
    print(result["response"])
    # 出力: {'response_type': 'greeting', 'response_message': 'こんにちは、太郎さん！'}


if __name__ == "__main__":
    asyncio.run(main())
```

---

## バリデーションの追加

実行前にコントラクトを検証：

```python
from agent_contracts import ContractValidator

validator = ContractValidator(registry)
result = validator.validate()

if result.has_errors:
    print(result)
    exit(1)

print("✅ コントラクト検証完了！")
```

---

## 次のステップ

- 📚 [コアコンセプト](core_concepts.ja.md) - アーキテクチャを理解する
- 🧰 [CLI](cli.ja.md) - コントラクトの検証・可視化・差分
- 🎯 [ベストプラクティス](best_practices.ja.md) - 設計パターンとヒント
- 🐛 [トラブルシューティング](troubleshooting.ja.md) - よくある問題と解決策
- 📦 Examples - `examples/05_backend_runtime.py` のバックエンド実行例
