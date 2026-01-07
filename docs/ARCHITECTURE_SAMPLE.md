# 🏗️ Agent Architecture

> Auto-generated from `NodeRegistry` contracts

---

## 🔗 LangGraph Node Flow

> Auto-generated from compiled LangGraph

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	greeter(greeter)
	helper(helper)
	analyzer(analyzer)
	planner(planner)
	executor(executor)
	reporter(reporter)
	main_supervisor(main_supervisor)
	task_supervisor(task_supervisor)
	__end__([<p>__end__</p>]):::last
	__start__ --> main_supervisor;
	analyzer --> main_supervisor;
	executor --> task_supervisor;
	greeter --> main_supervisor;
	helper --> task_supervisor;
	main_supervisor --> analyzer;
	main_supervisor --> greeter;
	main_supervisor --> helper;
	planner --> task_supervisor;
	task_supervisor --> executor;
	task_supervisor --> planner;
	task_supervisor --> reporter;
	reporter --> __end__;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc

```

---

## 📦 State Slices

State is organized into isolated **slices** for separation of concerns.

| Slice | Read By | Written By |
|:------|:--------|:-----------|
| `context` | `analyzer`, `helper`, `planner` | `greeter`, `analyzer` |
| `request` | `greeter`, `helper`, `planner` | - |
| `response` | - | `greeter`, `helper`, `executor`, `reporter` |
| `task` | `planner`, `executor`, `reporter` | `helper`, `planner`, `executor` |

---

## 🎯 System Hierarchy

```mermaid
flowchart TB
    subgraph main["🎯 Main"]
        direction LR
        greeter["🤖📦 greeter"]
        analyzer["🤖📦 analyzer"]
        helper["🤖📦 helper"]
    end
    subgraph task["🎯 Task"]
        direction LR
        planner["🤖📦 planner"]
        executor["📦 executor"]
        reporter["🤖🔚 reporter"]
    end

    classDef terminal fill:#e94560,stroke:#16213e,color:#fff
    class reporter terminal
```

---

## 🔀 Data Flow

> Key data paths through the system

```mermaid
flowchart TB
    subgraph slices["📦 State"]
        slice_context[("📁 context")]
        slice_request[("📥 request")]
        slice_response[("📤 response")]
        slice_task[("📁 task")]
    end

    subgraph sup_main["🎯 main"]
        direction LR
        greeter["🤖📦 greeter"]
        analyzer["🤖📦 analyzer"]
        helper["🤖📦 helper"]
    end
    subgraph sup_task["🎯 task"]
        direction LR
        planner["🤖📦 planner"]
        executor["📦 executor"]
        reporter["🤖🔚 reporter"]
    end

    %% Entry points
    slice_request --> greeter
    slice_request --> helper
    slice_request --> planner
    %% Response outputs
    greeter --> slice_response
    helper --> slice_response
    executor --> slice_response
    reporter --> slice_response
    %% Slice data flows
    greeter -.-> slice_context
    analyzer -.-> slice_context
    slice_context -.-> analyzer
    slice_context -.-> helper
    slice_context -.-> planner
    helper -.-> slice_task
    planner -.-> slice_task
    executor -.-> slice_task
    slice_task -.-> planner
    slice_task -.-> executor
    slice_task -.-> reporter

    classDef slice fill:#f5f5f5,stroke:#999
    classDef terminal fill:#e94560,stroke:#16213e,color:#fff
    class reporter terminal
```

<details>
<summary>📊 Detailed Node Dependencies</summary>

**main**

| Node | Depends On (via shared slices) |
|:-----|:-------------------------------|
| `analyzer` | `greeter` (context) |
| `helper` | `greeter` (context), `analyzer` (context) |

**task**

| Node | Depends On (via shared slices) |
|:-----|:-------------------------------|
| `planner` | `greeter` (context), `analyzer` (context), `helper` (task), `executor` (task) |
| `executor` | `helper` (task), `planner` (task) |
| `reporter` | `helper` (task), `planner` (task), `executor` (task) |

</details>

---

## ⚡ Trigger Hierarchy

> Nodes are evaluated by **priority** (highest first)

### 🎯 Main

| Priority | Node | Condition | Hint |
|:--------:|:-----|:----------|:-----|
| 🔴 **100** | `greeter` | `request.action=greet` | Handle greeting |
| 🟡 **50** | `analyzer` | `context.needs_analysis=true` | Run analysis |
| 🟢 **10** | `helper` | _(always)_ | General assistance |

<details>
<summary>📊 main Priority Chain</summary>

```mermaid
flowchart TD
    subgraph main["main"]
        direction TB
        greeter["🔴 P100: greeter"]
        analyzer["🟡 P50: analyzer"]
        greeter -->|"not matched"| analyzer
        helper["🟢 P10: helper"]
        analyzer -->|"not matched"| helper
    end
```

</details>

### 🎯 Task

| Priority | Node | Condition | Hint |
|:--------:|:-----|:----------|:-----|
| 🟡 **80** | `planner` | `task.needs_planning=true` | Create plan |
| 🟡 **50** | `executor` | `task.plan_ready=true` | Execute tasks |
| 🟢 **30** | `reporter` | `task.execution_done=true` | Generate report |

<details>
<summary>📊 task Priority Chain</summary>

```mermaid
flowchart TD
    subgraph task["task"]
        direction TB
        planner["🟡 P80: planner"]
        executor["🟡 P50: executor"]
        planner -->|"not matched"| executor
        reporter["🟢 P30: reporter"]
        executor -->|"not matched"| reporter
    end
```

</details>

---

## 📚 Nodes Reference

| Node | Supervisor | Reads | Writes | LLM | Terminal |
|:-----|:-----------|:------|:-------|:---:|:--------:|
| `analyzer` | main | `context` | `context` | ✅ |  |
| `executor` | task | `task` | `task`, `response` |  |  |
| `greeter` | main | `request` | `context`, `response` | ✅ |  |
| `helper` | main | `request`, `context` | `task`, `response` | ✅ |  |
| `planner` | task | `request`, `context`, `task` | `task` | ✅ |  |
| `reporter` | task | `task` | `response` | ✅ | 🔚 |

<details>
<summary>🔍 Legend</summary>

- ✅ = Requires LLM
- 🔚 = Terminal node (exits to END)
- Reads/Writes = State slices accessed

</details>

---

<sub>Generated by `agent-contracts` visualizer</sub>