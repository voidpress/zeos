"""Validate `.faudge/software_architecture.json`.

Checks:
  1. Every edge `label` is from the standard vocabulary.
  2. Every edge `source` and `target` references a node `id` that exists.

Run it from either install location, with or without an explicit path:
    python .faudge/hooks/verify_architecture.py
    python .faudge/hooks/verify_architecture.py .faudge/software_architecture.json

With no argument the repo root is discovered by walking up from this script
and then from the working directory, so the same file works whether it lives
in `scripts/` or in `.faudge/hooks/`.

Exits non-zero when problems are found.

The allowed and retired label lists mirror `faudge.models.edge_vocabulary`
(also rendered into `.faudge/SOFTWARE_ARCHITECTURE_GUIDE.md`, Edge Labels
section). A unit test keeps this standalone copy in sync.
"""

import json
import sys
from pathlib import Path

# Mirrors faudge.models.edge_vocabulary — pinned by
# tests/unit/models/test_edge_vocabulary.py; regenerate when that module changes.
ALLOWED_EDGE_LABELS: frozenset[str] = frozenset(
    {
        "creates",
        "uses",
        "publishes to",
        "serves",
        "implements",
    }
)

# Labels from earlier vocabulary versions, mapped to the replacement to use.
RETIRED_EDGE_LABELS: dict[str, str] = {
    "delegates to": '`uses`',
    "extends": '`implements` for an abstract base; for a concrete base drop the edge, or `uses` if the subclass relies on the base as a collaborator',
    "spawns": '`uses`',
    "depends on": '`uses`',
    "produces": '`creates`',
    "returns": '`uses`',
    "accepts": '`uses`',
    "injects": '`uses`',
    "reads": '`uses`',
    "writes": '`publishes to` for event/queue-style writes, otherwise `uses`',
    "notifies": '`publishes to`',
    "registers": '`serves` for exposing an entrypoint (e.g. `app.include_router`); otherwise drop the edge — registration is implicit in the `publishes to` relationship it wires up, and a second edge between the same blocks confuses the layered layout',
    "registers as listener on": 'drop the edge — the listener relationship is already carried by the `publishes to` edge from the event source to the listener abstraction, plus an `implements` edge from each concrete listener',
    "subscribes to": '`publishes to` from the event source to the listener — the subscription is that same relationship seen from the other end, so a second edge back from the listener is redundant',
}


def verify(arch_path: Path) -> list[str]:
    """Return a list of problem descriptions (empty list = file is valid)."""
    try:
        data = json.loads(arch_path.read_text())
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    problems: list[str] = []
    node_ids: set[str] = set()
    for i, node in enumerate(nodes):
        node_id = node.get("id")
        if not node_id:
            problems.append(f"nodes[{i}]: missing 'id' field")
            continue
        if node_id in node_ids:
            problems.append(f"nodes[{i}]: duplicate id {node_id!r}")
        node_ids.add(node_id)

    for i, edge in enumerate(edges):
        source = edge.get("source")
        target = edge.get("target")
        label = edge.get("label")

        if label is None:
            problems.append(f"edges[{i}]: missing 'label' field")
        elif label in RETIRED_EDGE_LABELS:
            problems.append(
                f"edges[{i}]: label {label!r} is retired "
                f"(source={source!r}, target={target!r}). "
                f"Use instead: {RETIRED_EDGE_LABELS[label]}"
            )
        elif label not in ALLOWED_EDGE_LABELS:
            problems.append(
                f"edges[{i}]: unknown label {label!r} "
                f"(source={source!r}, target={target!r}). "
                f"Allowed: {sorted(ALLOWED_EDGE_LABELS)}"
            )

        if source is None:
            problems.append(f"edges[{i}]: missing 'source' field")
        elif source not in node_ids:
            problems.append(
                f"edges[{i}]: source {source!r} does not match any node id (label={label!r}, target={target!r})"
            )

        if target is None:
            problems.append(f"edges[{i}]: missing 'target' field")
        elif target not in node_ids:
            problems.append(
                f"edges[{i}]: target {target!r} does not match any node id (label={label!r}, source={source!r})"
            )

    return problems


def default_arch_file() -> Path:
    """Locate `.faudge/software_architecture.json` when no path is given.

    This script is shipped both as `scripts/verify_architecture.py` and, in
    every repo that installs the hook, as `.faudge/hooks/verify_architecture.py`
    — the two sit at different depths, so no fixed number of `.parent` hops is
    right for both. Walk up from the script and then from the working directory
    and take the first repo root that actually has the file.
    """
    script = Path(__file__).resolve()
    cwd = Path.cwd().resolve()
    for root in [*script.parents, cwd, *cwd.parents]:
        candidate = root / ".faudge" / "software_architecture.json"
        if candidate.is_file():
            return candidate
    return cwd / ".faudge" / "software_architecture.json"


def main() -> int:
    if len(sys.argv) > 2:
        print("Usage: verify_architecture.py [path/to/software_architecture.json]", file=sys.stderr)
        return 2

    arch_file = Path(sys.argv[1]) if len(sys.argv) == 2 else default_arch_file()

    if not arch_file.exists():
        print(f"ERROR: {arch_file} not found", file=sys.stderr)
        return 2

    problems = verify(arch_file)
    if not problems:
        print(f"OK: {arch_file} — no issues found")
        return 0

    print(f"FAIL: {arch_file} — {len(problems)} issue(s):", file=sys.stderr)
    for p in problems:
        print(f"  - {p}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
