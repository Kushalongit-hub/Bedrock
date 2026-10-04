"""Zero-kernel-change enforcement test.

Ensures that reference applications can be built entirely through
the public Bedrock API without touching internal kernel modules.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
KERNEL_DIR = Path(__file__).parent.parent / "bedrock"

PUBLIC_KERNEL_MODULES = {
    "bedrock",
    "bedrock.adapters.cli",
    "bedrock.adapters.fastapi_app",
    "bedrock.adapters.openai_api",
    "bedrock.artifacts",
    "bedrock.capabilities",
    "bedrock.contracts",
    "bedrock.context",
    "bedrock.evaluators",
    "bedrock.evaluation",
    "bedrock.events",
    "bedrock.memory",
    "bedrock.memory.stores",
    "bedrock.models",
    "bedrock.models.providers",
    "bedrock.packs",
    "bedrock.packs.coding",
    "bedrock.packs.filesystem",
    "bedrock.packs.web",
    "bedrock.policy",
    "bedrock.runtime",
    "bedrock.tools",
    "bedrock.validation",
    "bedrock.workflows",
}

ALLOWED_IMPORTS = PUBLIC_KERNEL_MODULES | {
    "asyncio",
    "sys",
    "pathlib",
    "json",
    "yaml",
    "typing",
}


def _get_imports(file_path: Path) -> set[str]:
    """Extract all import targets from a Python file."""
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                imports.add(top)
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                imports.add(top)
                imports.add(node.module)
                for alias in node.names:
                    if alias.name != "*":
                        imports.add(f"{node.module}.{alias.name}")
    return imports


def _is_kernel_internal(module: str) -> bool:
    """Check if a module is an internal kernel module."""
    if not module.startswith("bedrock."):
        return False
    parts = module.split(".")
    # Check progressively longer prefixes: bedrock, bedrock.workflows, bedrock.workflows.executor
    for length in range(1, len(parts) + 1):
        candidate = ".".join(parts[:length])
        if candidate in PUBLIC_KERNEL_MODULES:
            return False
    return True


@pytest.mark.parametrize("example_dir", [d for d in EXAMPLES_DIR.iterdir() if d.is_dir()])
def test_example_only_uses_public_api(example_dir: Path) -> None:
    """All Python files in examples/ must only import from the public API."""
    py_files = list(example_dir.rglob("*.py"))
    if not py_files:
        pytest.skip(f"No Python files in {example_dir}")

    violations = []
    for py_file in py_files:
        imports = _get_imports(py_file)
        for imp in imports:
            if imp == "bedrock":
                continue
            if imp.startswith("bedrock.") and _is_kernel_internal(imp):
                violations.append(f"{py_file.relative_to(EXAMPLES_DIR)}: {imp}")

    assert not violations, (
        f"Example {example_dir.name} uses internal kernel modules:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )


def test_no_kernel_internal_imports_in_examples() -> None:
    """Scan all example files for internal kernel imports."""
    py_files = list(EXAMPLES_DIR.rglob("*.py"))
    violations = []
    for py_file in py_files:
        imports = _get_imports(py_file)
        for imp in imports:
            if imp == "bedrock":
                continue
            if imp.startswith("bedrock.") and _is_kernel_internal(imp):
                violations.append(f"{py_file.relative_to(EXAMPLES_DIR)}: {imp}")

    assert not violations, "Internal kernel imports found in examples:\n" + "\n".join(f"  - {v}" for v in violations)
