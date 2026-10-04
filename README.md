# Bedrock

A portable, model-agnostic agent kernel for building domain-specific AI systems without inheriting a generic assistant.

**Philosophy:** The framework provides mechanisms, not opinions about who the agent is. Identity belongs to the application. Knowledge belongs to the application. Behavior belongs to the application. Tools belong to the application. The kernel provides execution.

**Five rules:**
1. **No default assistant persona.**
2. **No forced autonomy.**
3. **No model-provider lock-in.**
4. **No hidden magic state.**
5. **Everything important is inspectable, replaceable, and testable.**

---

## What Bedrock Is

Bedrock is a **runtime substrate** for building specialized AI systems. You bring the domain, rules, tools, memory, knowledge, and behavior. Bedrock supplies the execution engine, contracts, observability, safety boundaries, context management, and extension points.

This distinction prevents the inevitable "generic AI slop" of frameworks that bake in an assistant persona and force you to fight the framework for every non-standard behavior.

**What Bedrock is not:**
- Not a prebuilt assistant
- Not a LangChain/CrewAI-style "wire together an LLM, a vector DB, and five tools" wrapper
- Not tied to OpenAI, Anthropic, or any single model provider
- Not opinionated about your product's personality, voice, or domain

---

## Architecture

```
┌──────────────────────────────────────────────┐
│                PRODUCT LAYER                 │
│                                              │
│  VakilAI / Sentinel / Coding Agent / Game AI │
│  Research Agent / Finance Agent / Anything   │
└───────────────────┬──────────────────────────┘
                    │
             Domain Pack
                    │
┌───────────────────▼──────────────────────────┐
│              AGENT KERNEL                    │
│                                              │
│  1. Runtime / Agent Loop                     │
│  2. Context Engine                           │
│  3. Tool Runtime                             │
│  4. Memory                                   │
│  5. Knowledge / Retrieval                    │
│  6. Policy + Permissions                     │
│  7. State / Workflow                         │
│  8. Model Gateway                            │
│  9. Events + Observability                   │
│ 10. Evaluation System                        │
└───────────────────┬──────────────────────────┘
                    │
          Environment Adapters
                    │
   ┌────────────────┼────────────────┐
   ▼                ▼                ▼
 CLI             Web/API          Embedded
 VS Code         Discord          Backend
 Desktop         Slack            Game
 Docker          Mobile           Edge
```

The **domain pack** is the important part. Instead of forking the entire framework every time, a project declares its identity, tools, skills, workflows, policies, and adapters in a standard structure. The kernel stays untouched.

---

## Domain Pack Structure

A domain pack is a directory with a standard layout:

```
my-agent/
├── agent.yaml
├── identity.md
├── policies/
│   ├── permissions.yaml
│   └── behavior.md
├── tools/
├── skills/
├── workflows/
├── knowledge/
├── memory/
├── evaluators/
└── adapters/
```

### `agent.yaml`

The manifest that defines the agent:

```yaml
name: my-agent
version: "0.1"
description: "My specialized agent."

identity:
  role: legal-research-engine
  objective: assist with Indian legal research
  style: evidence-first
  constraints:
    speculate: false
    citations_required: true
    unsupported_claims: reject

tools:
  - web.search
  - fs.read
  - fs.write

skills:
  - investigate

workflows:
  - research

policies:
  permissions:
    network: true
    filesystem: workspace

adapters:
  - cli
  - openai_api

mode: tool_loop
```

---

## Core Concepts

### Contracts

Everything in Bedrock is defined by explicit contracts (interfaces/ABCs). This is what makes the system replaceable and testable.

| Contract | Purpose |
|----------|---------|
| `Tool` | Something the system can execute |
| `ModelProvider` | Something that generates model responses |
| `MemoryStore` | Persists and retrieves memories |
| `Retriever` | Retrieves knowledge |
| `EnvironmentAdapter` | Connects the agent to an environment |
| `Evaluator` | Scores run quality |
| `WorkflowExecutor` | Executes declarative workflows |

### Tools

Tools are capabilities the agent can invoke. Each tool carries metadata:

```yaml
name: shell.execute
capability: system.shell
risk: high
permissions:
  filesystem: workspace
  network: false
execution:
  sandbox: required
  timeout: 30
input:
  command: string
```

Built-in capability packs:
- `packs/web` — `web.search`, `web.fetch`, `web.extract`
- `packs/filesystem` — `fs.read`, `fs.write`, `fs.list`
- `packs/coding` — `code.search`, `shell.execute`, `git.diff`

### Memory

Seven distinct memory classes:

| Class | Purpose |
|-------|---------|
| **Working** | Current task and scratchpad |
| **Session** | Current conversation/run |
| **Episodic** | Run history |
| **Semantic** | Facts learned over time |
| **Procedural** | Successful methods/workflows |
| **Artifact** | Code/docs/files created |
| **User** | User preferences |

All memories carry provenance: `source`, `confidence`, `created_at`, `expires_at`.

### Context Engine

Context is treated as a compiler, not a dump:

```
Raw State
   ↓
Context Selectors
   ↓
Relevance Ranking
   ↓
Budget Manager
   ↓
Context Compiler
   ↓
Model-specific representation
```

### Policy + Permissions

Every tool call goes through a policy engine:

```yaml
permissions:
  - capability: shell.execute
    allow: true
    require_approval: true
    max_risk: medium
```

### Events

Every meaningful action emits an event:

```
run.started
model.called
tool.requested
tool.authorized
tool.started
tool.completed
tool.failed
policy.denied
agent.completed
```

Events are recorded to `events.jsonl` for replay, debugging, and evaluation.

### Evaluators

Built-in evaluators:
- `task_completion` — Did the agent finish the task?
- `test_pass` — Did tests pass after a fix?
- `unauthorized_action` — Were any unauthorized actions attempted?
- `unnecessary_tool_call` — Were unnecessary tool calls made?
- `regression` — Did the fix introduce regressions?

---

## Getting Started

### Installation

```bash
pip install bedrock-kernel
```

Or install in development mode:

```bash
git clone https://github.com/Kushalongit-hub/Bedrock.git
cd Bedrock
pip install -e ".[dev]"
```

### Quick Start

Create a minimal agent:

```yaml
# agent.yaml
name: my-first-agent
version: "0.1"

identity:
  role: helpful-assistant
  objective: answer questions

tools: []
skills: []
workflows: []
policies: []
adapters:
  - cli
mode: reactive
```

Run it:

```bash
bedrock run "What is the capital of France?"
```

### Using the OpenAI-Compatible API

```bash
bedrock serve
```

Then POST to `http://localhost:8000/v1/chat/completions`:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"input": "Hello", "session_id": "test"}'
```

### Validate a Domain Pack

```bash
bedrock validate examples/coding-agent
```

### Inspect Capabilities

```bash
bedrock capabilities examples/coding-agent
```

### Replay a Run

```bash
# List runs
ls runs/

# Replay a specific run
bedrock replay <run-id>
```

---

## Examples

| Example | Description |
|---------|-------------|
| `examples/minimal` | Minimal reactive agent with no tools |
| `examples/research-agent` | Research agent using web and filesystem tools |
| `examples/coding-agent` | Planner-mode coding agent |
| `examples/coding-agent-pro` | Full reference coding agent with skills, workflows, policies |
| `examples/demo-broken-repo` | Deliberately broken repo for end-to-end testing |

### Running the Coding Agent Pro

```bash
cd examples/coding-agent-pro
python main.py /path/to/repo "Fix the failing tests"
```

This exercises the full architecture: tools, policies, context, workflows, events, memory, artifacts, and evaluation.

---

## CLI Reference

| Command | Description |
|---------|-------------|
| `bedrock run <input>` | Run an agent with the given input |
| `bedrock replay <run-id>` | Replay a previous run from artifacts |
| `bedrock validate <pack-dir>` | Validate a domain pack's `agent.yaml` |
| `bedrock capabilities <pack-dir>` | Print a pack's capabilities and risk level |
| `bedrock serve` | Start the OpenAI-compatible API server |

---

## Kernel Modules

| Module | Purpose |
|--------|---------|
| `bedrock.contracts` | Core data models: `Decision`, `ToolCall`, `AgentState`, `Message`, `FinalOutput`, `Plan` |
| `bedrock.runtime` | `AgentRuntime` — the perception-decision-action loop |
| `bedrock.tools` | `Tool` ABC, `ToolCapability`, `ToolRegistry`, `ToolExecutor` |
| `bedrock.models` | `ModelProvider`, `ModelRouter`, `TokenUsage` |
| `bedrock.models.providers` | `OpenAICompatibleProvider`, `AnthropicProvider`, `EchoProvider` |
| `bedrock.memory` | 7-class memory system: `Working`, `Session`, `Episodic`, `Semantic`, `Procedural`, `Artifact`, `User` |
| `bedrock.memory.stores` | `InMemoryStore` — in-memory implementation for development |
| `bedrock.context` | `ContextCompiler`, `ContextSelector`, `ContextBudget` |
| `bedrock.policy` | `PolicyEngine`, `PermissionRule`, `CapabilityManager` |
| `bedrock.events` | `EventBus`, `EventLogger` — full event taxonomy |
| `bedrock.workflows` | Declarative `WorkflowDefinition`, `SimpleWorkflowExecutor` |
| `bedrock.evaluation` | `Evaluator` ABC, `EvaluationRunner` |
| `bedrock.artifacts` | `RunArtifactStore`, `RunReplayEngine` — run persistence and replay |
| `bedrock.validation` | `DomainPackValidator` — validates `agent.yaml` |
| `bedrock.capabilities` | `CapabilityInspector` — prints pack capabilities |
| `bedrock.evaluators` | Built-in evaluators: task completion, test pass, unauthorized actions, regressions |
| `bedrock.adapters.cli` | CLI adapter |
| `bedrock.adapters.fastapi_app` | FastAPI OpenAI-compatible adapter |
| `bedrock.adapters.openai_api` | OpenAI API adapter wrapper |

---

## Execution Modes

Bedrock supports different execution semantics. Don't force agentic behavior where deterministic software is better.

| Mode | Description |
|------|-------------|
| `reactive` | Input → Answer |
| `tool_loop` | Input → Tool → Tool → Answer |
| `workflow` | Fixed deterministic stages |
| `planner` | Plan → Execute → Replan |
| `event_driven` | Events → Agent reactions |
| `supervisor` | Supervisor with sub-workers |

A legal RAG engine might barely need agentic behavior. A coding system may need heavy tool loops. A Sentinel-like system might rely primarily on deterministic rules and invoke AI only for ambiguous cases.

**Don't force agentic behavior where deterministic software is better.**

### Deterministic Nodes

Workflows support mixed execution:

| Node Type | Purpose |
|-----------|---------|
| `llm` | Language model call |
| `code` | Deterministic code |
| `rule` | Rule-based decision |
| `human` | Human approval gate |
| `tool` | Tool execution |
| `router` | Conditional routing |
| `validator` | Output validation |
| `retriever` | Knowledge retrieval |

---

## Workflows

Workflows are declarative YAML files that define multi-step agent behavior without touching the kernel:

```yaml
name: bug_fix
description: Diagnose and fix a failing test.

inputs:
  query: string
  repo_path: string

steps:
  - id: reproduce
    type: tool
    tool: test.run
    config:
      path: inputs.repo_path
    output: test_output

  - id: analyze
    type: model
    model: reasoning
    config:
      prompt: "Analyze this test failure:\n{test_output}"

  - id: search_code
    type: tool
    tool: code.search
    config:
      query: inputs.query
    output: search_results

  - id: patch
    type: tool
    tool: fs.write
    config:
      path: search_results.target_file
      content: hypothesize.patch
    output: patch_result

  - id: verify
    type: tool
    tool: test.run
    config:
      path: inputs.repo_path

  - id: validate
    type: evaluator
    evaluator: test_pass

  - id: summarize
    type: model
    model: fast
    config:
      prompt: "Summarize the fix."
```

---

## Model Providers

Bedrock is model-agnostic. Configure providers in your domain pack:

```yaml
models:
  fast:
    provider: openai
    model: gpt-x-mini

  reasoning:
    provider: anthropic
    model: claude-x

  local:
    provider: ollama
    model: qwen-x

routing:
  classification: fast
  reasoning: reasoning
  private_data: local
```

Application code asks for a model by alias:

```python
response = await models.invoke("reasoning", request)
```

Not:

```python
OpenAI(...)
```

---

## Run Artifacts

Every run produces a complete artifact package:

```
runs/
└── <run-id>/
    ├── manifest.json    # Run metadata, inputs, outputs, tool calls, model calls
    ├── events.jsonl     # Full event timeline
    └── artifacts/       # Named artifacts (files, outputs, patches)
        ├── patch.diff
        └── report.md
```

This enables:
- **Debugging** — inspect exactly what happened
- **Replay** — reconstruct the run from events
- **Evaluation** — score runs against criteria
- **Model comparison** — replay the same execution with different models
- **Audit trails** — compliance and safety reviews
- **Crash recovery** — resume from last recorded state

---

## Testing

Run the full test suite:

```bash
python -m pytest tests/ -v
```

Test modules:
- `tests/test_core.py` — Core contracts, memory, policy, events, artifact store, replay
- `tests/test_failures.py` — Failure modes: denied permissions, broken tools, bad models
- `tests/test_zero_kernel_change.py` — AST-enforced public API boundary for examples

---

## Roadmap

```
v0.1  Kernel Complete          ← YOU ARE HERE

v0.2  Runtime Reliability
      ├─ artifacts
      ├─ replay
      ├─ validation
      ├─ failure handling
      └─ coding reference app

v0.3  Generality Proof
      ├─ research/legal app
      ├─ deterministic decision app
      └─ cross-domain evaluations

v0.4  Persistence + Developer UX
      ├─ SQLite/Postgres stores
      ├─ vector stores
      ├─ CLI improvements
      ├─ run inspector
      └─ tracing UI

v0.5  Extension Ecosystem
      ├─ capability packs
      ├─ domain-pack packaging
      ├─ registry
      └─ SDK

v1.0  Stable contracts
```

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Run tests: `python -m pytest tests/ -v`
5. Submit a pull request

**Key principles:**
- No kernel changes should be required to build a new domain application
- All changes should be covered by tests
- Public API is everything importable from `bedrock.*` packages listed in `tests/test_zero_kernel_change.py`
- Internal modules (`bedrock.*` not in the public list) may change without notice

---

## License

MIT
