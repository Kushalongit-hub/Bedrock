"""Domain pack validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional


class ValidationError:
    def __init__(self, path: str, message: str, severity: str = "error") -> None:
        self.path = path
        self.message = message
        self.severity = severity

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.path}: {self.message}"


class DomainPackValidator:
    """Validates a domain pack YAML configuration."""

    REQUIRED_FIELDS = ["name", "version", "identity"]
    VALID_MODES = {"reactive", "tool_loop", "workflow", "planner", "event_driven", "supervisor"}

    def __init__(self, pack_dir: Path) -> None:
        self.pack_dir = pack_dir
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []

    def validate(self) -> List[ValidationError]:
        self.errors = []
        self.warnings = []
        agent_yaml = self.pack_dir / "agent.yaml"
        if not agent_yaml.exists():
            self.errors.append(ValidationError("agent.yaml", "Missing agent.yaml"))
            return self.errors

        import yaml
        try:
            data = yaml.safe_load(agent_yaml.read_text(encoding="utf-8"))
        except Exception as exc:
            self.errors.append(ValidationError("agent.yaml", f"Invalid YAML: {exc}"))
            return self.errors

        if not isinstance(data, dict):
            self.errors.append(ValidationError("agent.yaml", "Root must be a mapping"))
            return self.errors

        self._check_required_fields(data)
        self._check_identity(data.get("identity", {}))
        self._check_mode(data.get("mode"))
        self._check_tools(data.get("tools", []))
        self._check_skills(data.get("skills", []))
        self._check_workflows(data.get("workflows", []))
        self._check_policies(data.get("policies", {}))
        self._check_adapters(data.get("adapters", []))

        return self.errors + self.warnings

    def _check_required_fields(self, data: Dict[str, Any]) -> None:
        for field in self.REQUIRED_FIELDS:
            if field not in data:
                self.errors.append(ValidationError("agent.yaml", f"Missing required field: {field}"))

    def _check_identity(self, identity: Dict[str, Any]) -> None:
        if not identity.get("role"):
            self.warnings.append(ValidationError("identity", "Missing role", severity="warning"))
        if not identity.get("objective"):
            self.warnings.append(ValidationError("identity", "Missing objective", severity="warning"))

    def _check_mode(self, mode: Optional[str]) -> None:
        if mode is None:
            self.warnings.append(ValidationError("mode", "No execution mode specified", severity="warning"))
        elif mode not in self.VALID_MODES:
            self.errors.append(ValidationError("mode", f"Invalid mode: {mode}. Valid: {self.VALID_MODES}"))

    def _check_tools(self, tools: List[str]) -> None:
        for tool in tools:
            if "." not in tool:
                self.warnings.append(ValidationError(f"tools.{tool}", "Tool name should be namespaced (pack.tool)", severity="warning"))

    def _check_skills(self, skills: List[str]) -> None:
        for skill in skills:
            skill_dir = self.pack_dir / "skills" / skill
            if not skill_dir.exists():
                self.errors.append(ValidationError(f"skills.{skill}", f"Skill directory not found: {skill_dir}"))

    def _check_workflows(self, workflows: List[str]) -> None:
        for wf in workflows:
            wf_dir = self.pack_dir / "workflows" / wf
            if not wf_dir.exists():
                self.errors.append(ValidationError(f"workflows.{wf}", f"Workflow directory not found: {wf_dir}"))

    def _check_policies(self, policies: Any) -> None:
        if isinstance(policies, list):
            return
        if not isinstance(policies, dict):
            self.errors.append(ValidationError("policies", "policies must be a mapping or list"))
            return
        perms = policies.get("permissions", {})
        if isinstance(perms, dict):
            for perm, value in perms.items():
                if value not in (True, False, "workspace", "required", "optional"):
                    self.warnings.append(ValidationError(f"policies.permissions.{perm}", f"Unusual permission value: {value}", severity="warning"))

    def _check_adapters(self, adapters: List[str]) -> None:
        valid_adapters = {"cli", "openai_api", "fastapi", "discord", "slack", "vscode", "web", "desktop", "worker"}
        for adapter in adapters:
            if adapter not in valid_adapters:
                self.warnings.append(ValidationError(f"adapters.{adapter}", f"Unknown adapter: {adapter}", severity="warning"))
