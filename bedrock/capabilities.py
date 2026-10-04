"""Capability inspection."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List


class CapabilityInspector:
    """Inspects what a domain pack can access and its risk level."""

    def __init__(self, pack_dir: Path) -> None:
        self.pack_dir = pack_dir

    def inspect(self) -> str:
        import yaml

        agent_yaml = self.pack_dir / "agent.yaml"
        if not agent_yaml.exists():
            return "No agent.yaml found"

        try:
            data = yaml.safe_load(agent_yaml.read_text(encoding="utf-8"))
        except Exception as exc:
            return f"Invalid YAML: {exc}"

        lines = []
        lines.append(f"Pack: {data.get('name', 'unknown')}")
        lines.append(f"Version: {data.get('version', 'unknown')}")
        lines.append(f"Mode: {data.get('mode', 'unspecified')}")
        lines.append("")

        tools = data.get("tools", [])
        lines.append(f"Tools ({len(tools)}):")
        for tool in tools:
            lines.append(f"  - {tool}")
        lines.append("")

        skills = data.get("skills", [])
        lines.append(f"Skills ({len(skills)}):")
        for skill in skills:
            lines.append(f"  - {skill}")
        lines.append("")

        workflows = data.get("workflows", [])
        lines.append(f"Workflows ({len(workflows)}):")
        for wf in workflows:
            lines.append(f"  - {wf}")
        lines.append("")

        adapters = data.get("adapters", [])
        lines.append(f"Adapters ({len(adapters)}):")
        for adapter in adapters:
            lines.append(f"  - {adapter}")
        lines.append("")

        policies = data.get("policies", {})
        if isinstance(policies, dict):
            perms = policies.get("permissions", {})
        else:
            perms = {}
        if perms:
            lines.append("Permissions:")
            for perm, value in perms.items():
                lines.append(f"  {perm}: {value}")
            lines.append("")

        risk_level = self._compute_risk_level(tools, perms)
        lines.append(f"Overall risk level: {risk_level}")

        return "\n".join(lines)

    def _compute_risk_level(self, tools: List[str], permissions: Dict[str, Any]) -> str:
        high_risk_tools = {"shell.execute", "fs.write", "git.push", "network.http"}
        has_high_risk = any(t in high_risk_tools for t in tools)
        has_network = permissions.get("network") is True

        if has_high_risk or has_network:
            return "high"
        if any("write" in t or "delete" in t for t in tools):
            return "medium"
        return "low"
