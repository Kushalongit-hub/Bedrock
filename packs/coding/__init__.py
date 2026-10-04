"""Coding capability pack."""

from bedrock.tools import Tool, ToolCapability


class CodeSearchTool(Tool):
    name = "code.search"
    capability = ToolCapability(
        name="code.search",
        risk="low",
        input_schema={"query": "string", "path": "string?"},
        output_schema={"results": "array"},
    )

    async def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        return {"results": []}


class ShellExecuteTool(Tool):
    name = "shell.execute"
    capability = ToolCapability(
        name="shell.execute",
        risk="high",
        permissions={"filesystem": "workspace", "network": False},
        execution={"sandbox": "required", "timeout": 30},
        input_schema={"command": "string"},
        output_schema={"stdout": "string", "stderr": "string", "returncode": "integer"},
    )

    async def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        import subprocess
        command = args.get("command", "")
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except Exception as exc:
            return {"stdout": "", "stderr": str(exc), "returncode": -1}


class GitDiffTool(Tool):
    name = "git.diff"
    capability = ToolCapability(
        name="git.diff",
        risk="low",
        input_schema={"path": "string?"},
        output_schema={"diff": "string"},
    )

    async def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        import subprocess
        try:
            result = subprocess.run(["git", "diff"], capture_output=True, text=True)
            return {"diff": result.stdout}
        except Exception as exc:
            return {"diff": str(exc)}


PACK = {
    "name": "coding",
    "tools": [CodeSearchTool(), ShellExecuteTool(), GitDiffTool()],
}
