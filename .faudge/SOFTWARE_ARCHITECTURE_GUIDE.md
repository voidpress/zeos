# Software Architecture JSON Guide

This document describes the purpose, structure, and conventions of `software_architecture.json` so that any future Claude session can understand and update it accurately.

---

## Purpose

`software_architecture.json` is a machine-readable graph of The Faudge codebase. It is used to generate architecture diagrams, navigate component relationships, and give Claude an accurate mental model of the system when asked to reason about or modify it.

It represents the **current state of the code** — it must be kept in sync with actual source files. Do not add speculative or aspirational components.

---

## Two-Layer Architecture Data Model

Architecture information is split into two layers to avoid merge conflicts and keep the JSON file small:

### Layer 1: `software_architecture.json` — Topology only

Contains `nodes` (components) and `edges` (relationships). Nodes store only topology fields; no description or method call data lives here.

### Layer 2: Source file docblocks — Detail

Each class or module referenced by a node carries an `Architecture:` block in its docstring. `ArchitectureService` reads and parses these at request time to populate `description` and `methods_called` in the API response.

---

## Top-Level JSON Structure

```json
{
  "nodes": [ ... ],
  "edges": [ ... ]
}
```

- **nodes** — every meaningful stateful component: classes and router modules
- **edges** — directed relationships between nodes

---

## Node Schema

Each node contains only topology fields:

```json
{
  "id": "py:faudge.web.services.git_client.GitClient",
  "label": "GitClient",
  "file": "src/faudge/web/services/git_client.py",
  "type": "class",
  "application": "Web Backend"
}
```

### Field definitions

| Field | Type | Description |
|---|---|---|
| `id` | string | Language-tagged identifier (see Node `id` scheme below). |
| `label` | string | Short human-readable name — the class name or a concise module name. |
| `file` | string | Source file path relative to the repo root (e.g. `src/faudge/web/services/git_client.py`). |
| `type` | string | Either `"class"` or `"module"`. Use `"class"` when the node represents a single dominant class. Use `"module"` for router files (which have no class but still coordinate stateful dependencies). |
| `application` | string | The deployed application/process this component runs in; the diagram draws one container per application. Optional at the schema level (older files may omit it) but **expected** for this repo. See Application Conventions below — assign by runtime process, **not** by file path. |

`description` and `methods_called` are **not** stored in the JSON. They are sourced from source file docblocks at request time.

---

## Node `id` scheme

Every node `id` is prefixed with a language tag: `<lang>:<symbol>`. This lets `ArchitectureService` dispatch to the correct language parser automatically.

| Type | Format | Example |
|---|---|---|
| Python class | `py:<dotted_path>` | `py:faudge.web.services.git_client.GitClient` |
| Python module | `py:<dotted_path>` | `py:faudge.web.app` |
| TypeScript/JS class | `ts:<repo_relative_path>#<ClassName>` | `ts:src/web/foo.ts#FooService` |
| TypeScript/JS module | `ts:<repo_relative_path>` | `ts:src/web/foo.ts` |
| Go struct | `go:<package_path>#<StructName>` | `go:internal/worker#Worker` |
| Go package | `go:<package_path>` | `go:internal/worker` |
| C++ class/struct | `cpp:<repo_relative_path>#<ClassName>` | `cpp:src/engine/renderer.hpp#Renderer` |
| C++ translation unit | `cpp:<repo_relative_path>` | `cpp:src/engine/renderer.cpp` |
| C translation unit | `c:<repo_relative_path>` | `c:src/io/buffer.c` |
| Java class/interface/enum/record | `java:<fully_qualified_name>` | `java:org.openpnp.machine.reference.ReferenceMachine` |

Notes:
- `ts:` covers both `.ts` and `.js` files — do **not** use `js:`.
- For `java:` ids the symbol is the fully-qualified type name. The `JavaDocblockParser` locates the type by the node's `label` (the simple class name), so `label` must be the bare type name (e.g. `ReferenceMachine`), not the dotted path.
- Edge `source` and `target` fields use the same prefixed id format.

---

## Source File Docblock Format

Every class or module referenced by a node must carry an `Architecture:` block in its doc comment. The block format is the same across all languages — only the surrounding comment syntax differs.

### Python

**For class nodes** — add the block to the class docstring:

```python
class DesignPlanService:
    """Orchestrates design plan session lifecycle, PTY bridges, and file access.

    Architecture:
        Calls: DesignPlanSessionStore.create_session, ContainerRuntime.run, PtyBridge.start, ProjectSettingsService.get_settings
    """
```

**For module nodes** — add the block to the module-level docstring (the first triple-quoted string in the file):

```python
"""FastAPI router exposing endpoints for forge task CRUD at /api/tasks.

Architecture:
    Calls: TaskService.list_tasks, TaskService.get_task, TaskService.upload_attachment
"""
```

### TypeScript / JavaScript

JSDoc `/** ... */` block immediately above the class or export declaration. The first JSDoc block in the file (before any non-comment code) is the module docblock.

```typescript
/**
 * Manages HTTP requests to the backend API.
 *
 * Architecture:
 *   Calls: HttpClient.get, Cache.set
 */
export class FooService { /* ... */ }
```

### Go

Contiguous `//` comment block immediately above the `type X struct` or `package` declaration — no blank line between the comment and the declaration (Go doc comment convention).

```go
// Worker processes jobs from the queue.
//
// Architecture:
//   Calls: Queue.Dequeue, Logger.Info
type Worker struct { /* ... */ }
```

### C++

Doxygen-style `/** ... */` or `/*! ... */` block immediately above the `class` or `struct` declaration. For translation-unit nodes, use the first Doxygen block at the top of the file.

```cpp
/**
 * Renders frames to the display buffer.
 *
 * Architecture:
 *   Calls: Logger.info, Buffer.flush
 */
class Renderer { /* ... */ };
```

### Java

Javadoc `/** ... */` block immediately above the `class`/`interface`/`enum`/`record` declaration. Only annotation lines (`@Foo`) may sit between the Javadoc and the declaration. For module nodes, use the first Javadoc block at the top of the file (a leading `package` statement and `import`s are skipped).

```java
/**
 * Coordinates the machine's heads, feeders, and drivers during a job.
 *
 * Architecture:
 *   Calls: ReferenceHead.moveTo, ReferenceNozzle.pick, ReferencePnpJobProcessor.next
 */
public class ReferenceMachine implements Machine { /* ... */ }
```

### C

Doxygen-style `/** ... */` or `/*! ... */` block at the very top of the `.c` or `.h` file (before any `#include` or other code). C nodes are always translation-unit (`module`) nodes.

```c
/**
 * Buffer management translation unit.
 *
 * Architecture:
 *   Calls: log_info, malloc_safe
 */

#include <stdio.h>
```

For C, `Calls:` entries may be bare function names (no class prefix). They are stored as `MethodCall(object="", method="fn_name")`.

### Docblock field definitions

| Field | Required | Description |
|---|---|---|
| Description (text before `Architecture:`) | **Required** | One or more sentences describing what this component does and its role in the system. Becomes the `description` field in the API response. |
| `Calls:` | When applicable | Comma-separated list of `ClassName.method_name` pairs (or bare function names for C) for meaningful cross-component calls made by this component. Omit for pure-data-access stores, abstract base classes, and components that only call OS/subprocess APIs. |

**Do NOT add these fields to the docblock:**
- `Layer:` / `Band:` — the architecture view positions blocks itself; a layer named in a docblock is a second source of truth that nothing reads.
- `Called by:` — caller relationships are already captured by edges in `software_architecture.json` and are derivable from the graph. Only `Calls:` (outbound) is stored here.

**`Calls:` format:** each entry is `ReceiverClass.method_name`. Use the class name (not the instance variable name). Only include calls that meaningfully illustrate the component's role — omit logger calls, asyncio primitives, string/list methods, and standard library calls.

### Parsing rules (for `ArchitectureService`)

- `ArchitectureService` dispatches to the correct parser based on the `id` language tag prefix.
- The text before `\nArchitecture:` in the extracted doc comment becomes the `description` field.
- Each `Calls:` entry is parsed into a `MethodCall(object, method)` with `line=0`.
- If no `Architecture:` block is present, `description` and `methods_called` are empty.

---

## Adding a New Language

To support a new language (e.g. Rust):

1. **Add a parser class** in `src/faudge/web/services/docblocks/` (e.g. `rust.py`):
   - Subclass `DocblockParser` from `base.py`.
   - Implement `language_tag` (e.g. `"rs"`), `file_extensions` (e.g. `(".rs",)`), and `parse()`.
   - Extract the doc comment using language-native patterns (e.g. `/// ...` or `/** ... */`), then call `_parse_arch_block(text)` from `base.py`.

2. **Register the parser** in `registry.py`:
   - Instantiate the new class and add it to the `_PARSERS` tuple.

3. **Document the doc-comment convention** in this guide under "Source File Docblock Format" — show a minimal example with `Architecture:` and `Calls:`.

4. **Use the new language tag** in `software_architecture.json` node ids for the new-language components.

No changes to `ArchitectureService` or the registry dispatch logic are needed — the registry handles it automatically.

---


## Application Conventions

`application` names the deployed application/process a component runs in. The architecture viewer draws one container per distinct `application` value and routes edges that cross an application boundary through a shared lane below the containers.

**Assign by runtime process, not by file path.** Group each node by which process actually loads and executes its code at runtime — check `docker/docker-compose.yml`, service entrypoints, and Dockerfiles — not by which directory the file lives in.

The four current values for this repo:

| `application` | Members |
|---|---|
| `Orchestrator` | `application.py`, everything under `core/`, and **all `ForgeApi*Service` / `BaseForgeApiClient` classes** |
| `Web Backend` | the rest of `web/**` — the FastAPI app, routers, services, stores, docblock parsers, `PtyBridge` |
| `Worker` | `worker/entrypoint.py`, `integrations/claude/runner.py` |
| `MCP Server` | `mcp/forge_tasks_mcp/**` |

**Canonical gotcha:** the `ForgeApi*Service` and `BaseForgeApiClient` classes live under `src/faudge/web/services/` on disk, but they are HTTP clients constructed by `Application` and run inside the **orchestrator** process — so their `application` is `Orchestrator`, not `Web Backend`. Path-based guessing gets this wrong; always verify against the construction/execution site.

### The process boundary — quota and attachment, not state and compute

The split between the two long-lived Faudge processes is not "state here, compute
there". It is:

> The web backend owns state, the browser-facing API, and interactive agent
> sessions a user is attached to. The orchestrator owns autonomous agent work that
> spends Claude subscription quota, and is therefore the process that can be
> paused, throttled and restarted without the UI noticing.

`WorkflowOrchestrator` gating every tick on the pause switch, subscription
utilization and active rate limits is the observable form of this: those gates
exist because that work spends quota, and nothing in the web backend needs them.

Two consequences for placing a new node's `application`:

- Interactive sessions a user is attached to — design plan sessions and
  the `PtyBridge` terminal behind them — belong to `Web Backend` even though they
  spawn containers and run agents. They must start while processing is paused, so
  they cannot live behind the orchestrator's gates.
- Anything that consumes subscription quota on its own schedule belongs to
  `Orchestrator`, including work whose files sit under `web/` — see the
  `ForgeApi*` gotcha above.

If a codebase is a single deployable process, or the deployment topology is unclear, use one shared value for every node — a coarse single-application grouping is safer than a wrong multi-way split.

---

## Edge Schema

Each edge is a directed relationship from one node to another:

```json
{
  "source": "py:faudge.web.routers.tasks",
  "target": "py:faudge.web.services.task_service.TaskService",
  "label": "uses"
}
```

### Field definitions

| Field | Type | Description |
|---|---|---|
| `source` | string | The `id` of the calling/owning component. |
| `target` | string | The `id` of the called/owned component. |
| `label` | string | The relationship type (see Edge Labels below). |

### Edge Labels

<!-- The two tables below are generated from src/faudge/models/edge_vocabulary.py.
     Edit that module and re-render; tests/unit/models/test_edge_vocabulary.py enforces sync. -->

Use these standard labels consistently. This vocabulary matches the diagram
renderer's legend exactly — an edge with a label outside this table will not
be drawn.

| Label | Meaning |
|---|---|
| `creates` | Source instantiates target (typically in constructor or factory). Hidden by default in the diagram; viewers enable it via the legend. |
| `uses` | Source calls methods on or reads data from target (dependency injection, import, store/file reads). The default label when nothing more specific fits an invocation. |
| `publishes to` | Source emits events or writes data out to target (queue, event bus, store). |
| `serves` | Source exposes target to external callers as an entrypoint (e.g. the app serving a router's endpoints). |
| `implements` | Source is a concrete subclass/implementation of an abstract base class target. **Required** for ABC grouping — the diagram renderer uses this label to detect ABCs and render them with the abstract group visual (the edge itself is absorbed into that visual, not drawn as an arrow). Use this for all ABC/interface relationships, including Python `ABC` subclasses. |

### Legacy labels — do not use

Earlier versions of this guide defined additional labels. They are retired;
when updating a diagram that still contains one, relabel it:

| Legacy label | Use instead |
|---|---|
| `delegates to` | `uses` |
| `extends` | `implements` for an abstract base; for a concrete base drop the edge, or `uses` if the subclass relies on the base as a collaborator |
| `spawns` | `uses` |
| `depends on` | `uses` |
| `produces` | `creates` |
| `returns` | `uses` |
| `accepts` | `uses` |
| `injects` | `uses` |
| `reads` | `uses` |
| `writes` | `publishes to` for event/queue-style writes, otherwise `uses` |
| `notifies` | `publishes to` |
| `registers` | `serves` for exposing an entrypoint (e.g. `app.include_router`); otherwise drop the edge — registration is implicit in the `publishes to` relationship it wires up, and a second edge between the same blocks confuses the layered layout |
| `registers as listener on` | drop the edge — the listener relationship is already carried by the `publishes to` edge from the event source to the listener abstraction, plus an `implements` edge from each concrete listener |
| `subscribes to` | `publishes to` from the event source to the listener — the subscription is that same relationship seen from the other end, so a second edge back from the listener is redundant |

---

## What to Include

**Include:**
- Every class that holds state or has meaningful behaviour (business logic, data access, orchestration)
- Router modules — even though they are collections of functions, they wire together stateful dependencies and represent a distinct layer boundary
- The FastAPI app module
- Worker/entrypoint modules
- Model classes that are passed across layer boundaries

**Exclude:**
- Modules that are just a collection of stateless helper functions (no instance state, no class, just `def` at module level) — these do not appear as nodes in the diagram
- Modules that only contain Pydantic models, dataclasses, or enums with no business logic — e.g. `models/forge_task.py`, `web/models.py`
- Pure config dicts or constants files with no behaviour
- Third-party library classes (FastAPI, SQLite, asyncio, etc.) — only include our own code
- Test files
- Migration or one-off scripts

The key question is: **does this component hold state or coordinate stateful dependencies?** If no, leave it out.

---

## How to Update

### When you add or delete a class or module

1. **Add/remove the node** in `software_architecture.json` with the correct `id`, `label`, `file`, `type`, and `application`.
2. **Add/remove edges** to reflect new or removed dependencies.
3. **Add/remove the `Architecture:` docblock** in the source file (or remove when the class is deleted).

### When a class's purpose or dependencies change

1. **Update the docblock** in the source file — change the description text or `Calls:` line.
2. **Update edges** in `software_architecture.json` if dependencies changed.
3. No JSON node fields need to change unless `file`, `type`, or `application` changed.

### General rules

- Keep `id` values in the `<lang>:<symbol>` format — see the Node `id` scheme section above.
- Update `file` paths if files were moved or renamed.
- Edge `source` and `target` fields must use the same prefixed `id` format as nodes.
- Edge `label` values come from the standard vocabulary above; do not invent new labels unless none fit.

---

## Current Component Inventory (as of May 2026)

### Orchestrator · Entry
- `py:faudge.application.Application` — bootstraps and wires all components, creates per-project CodingAgent instances, manages shutdown

### Orchestrator · Orchestration
- `py:faudge.core.workflow_orchestrator.WorkflowOrchestrator` — drives the main processing loop, delegates to processors
- Worker entrypoint module

### Orchestrator · Processors and Agents
- `py:faudge.core.coding_agent.CodingAgent` — abstract base class defining agent interface for code execution
- `py:faudge.core.claude_code_agent.ClaudeCodeAgent` — Docker-based CodingAgent managing container lifecycle, repo checkout, workspace preparation, execution, and result handling
- `py:faudge.core.initial_task_processor.InitialTaskProcessor` — orchestrates initial task execution via agents
- `py:faudge.core.review_task_processor.ReviewTaskProcessor` — orchestrates review processing via agents

### Web Backend · Web Tier and Services
- `py:faudge.web.app` — FastAPI application factory
- `py:faudge.web.dependencies` — FastAPI dependency factories; owns the process-wide singletons (`FaudgeTaskEmitter`, `ReviewEventEmitter`, `DesignPlanService`) and wires the `FaudgeTaskEmitter` as a listener onto each per-request `TaskService`
- Routers: `tasks`, `reviews`, `diff`, `architecture` (also serves node positions), `design_plans`, `ideas`, `system` (usage, system settings and first-run setup), `logs`, `transcripts`, `files`, `projects` (also serves git history), `events`, `armory`, `project_skills`
- `py:faudge.web.services.architecture_service.ArchitectureService`
- `py:faudge.web.services.design_plan_service.DesignPlanService`
- `py:faudge.web.services.task_service.TaskService` — owns a `_listeners: list[TaskListener]` and calls `on_task_changed()` on them after every mutation
- `py:faudge.web.services.project_settings_service.ProjectSettingsService`
- `py:faudge.web.services.system_service.SystemService`

### Web Backend · Data Access
- `py:faudge.web.services.task_store.TaskStore`
- `py:faudge.web.services.idea_store.IdeaStore`
- `py:faudge.web.services.project_store.ProjectStore`
- `py:faudge.web.services.system_settings_store.SystemSettingsStore`
- `py:faudge.web.services.usage_store.UsageStore`
- `py:faudge.web.services.design_plan_session_store.DesignPlanSessionStore`
- `py:faudge.web.services.task_service.TaskListener` — abstract base class (observer interface) for task change notifications
- `py:faudge.web.services.faudge_task_emitter.FaudgeTaskEmitter` — concrete `TaskListener`; holds asyncio.Queue subscribers and broadcasts SSE bump events; singleton stored on `app.state`

### Integrations and Runners
- `py:faudge.integrations.claude.runner.ClaudeSubprocessRunner` — runs Claude CLI subprocess
- `py:mcp.forge_tasks_mcp.forge_tasks_client.ForgeTasksClient` — HTTP client bridging MCP tool calls to the web API

### Web Backend · Utilities
- `py:faudge.web.services.pty_bridge.PtyBridge`
- `py:mcp.forge_tasks_mcp.server` — MCP server module
- Logging utilities

### Web Backend · Utilities — Docblock Parsers
- `py:faudge.web.services.docblocks.docblock_parser.DocblockParser` — abstract base class for all language parsers
- `py:faudge.web.services.docblocks.python_docblock_parser.PythonDocblockParser`
- `py:faudge.web.services.docblocks.typescript_docblock_parser.TypescriptDocblockParser`
- `py:faudge.web.services.docblocks.go_docblock_parser.GoDocblockParser`
- `py:faudge.web.services.docblocks.c_docblock_parser.CDocblockParser`
- `py:faudge.web.services.docblocks.cpp_docblock_parser.CppDocblockParser`
- `py:faudge.web.services.docblocks.java_docblock_parser.JavaDocblockParser`

---

## Conventions Summary

- `id` = `<lang>:<symbol>` — language-tagged identifier (see Node `id` scheme)
- `file` = repo-relative path starting with `src/` or `mcp/`
- `application` = deployed process the node runs in — assign by runtime process, not file path (see Application Conventions)
- `type` = `"class"` or `"module"` only
- Descriptions live in source doc comments, not in the JSON
- Method call data lives in `Calls:` docblock lines, not in the JSON
- Edge `source` and `target` use the same `<lang>:<symbol>` format as node ids
- Edge `label` values come from the standard vocabulary above; do not invent new labels unless none fit
