"""Filesystem capability pack."""

from bedrock.tools import Tool, ToolCapability


class FsReadTool(Tool):
    name = "fs.read"
    capability = ToolCapability(
        name="fs.read",
        risk="low",
        permissions={"filesystem": "workspace"},
        input_schema={"path": "string"},
        output_schema={"content": "string", "path": "string"},
    )

    async def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        path = args.get("path", "")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return {"content": f.read(), "path": path}
        except Exception as exc:
            return {"content": "", "path": path, "error": str(exc)}


class FsWriteTool(Tool):
    name = "fs.write"
    capability = ToolCapability(
        name="fs.write",
        risk="medium",
        permissions={"filesystem": "workspace"},
        input_schema={"path": "string", "content": "string"},
        output_schema={"success": "boolean", "path": "string"},
    )

    async def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        path = args.get("path", "")
        content = args.get("content", "")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "path": path}
        except Exception as exc:
            return {"success": False, "path": path, "error": str(exc)}


class FsListTool(Tool):
    name = "fs.list"
    capability = ToolCapability(
        name="fs.list",
        risk="low",
        permissions={"filesystem": "workspace"},
        input_schema={"path": "string?"},
        output_schema={"entries": "array", "path": "string"},
    )

    async def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        import os
        path = args.get("path", ".")
        try:
            entries = os.listdir(path)
            return {"entries": entries, "path": path}
        except Exception as exc:
            return {"entries": [], "path": path, "error": str(exc)}


PACK = {
    "name": "filesystem",
    "tools": [FsReadTool(), FsWriteTool(), FsListTool()],
}
