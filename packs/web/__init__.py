"""Web capability pack."""

from bedrock.tools import Tool, ToolCapability


class WebSearchTool(Tool):
    name = "web.search"
    capability = ToolCapability(
        name="web.search",
        risk="low",
        input_schema={"query": "string", "limit": "integer?"},
        output_schema={"results": "array", "query": "string"},
    )

    async def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        return {"results": [], "query": args.get("query", "")}


class WebFetchTool(Tool):
    name = "web.fetch"
    capability = ToolCapability(
        name="web.fetch",
        risk="medium",
        input_schema={"url": "string"},
        output_schema={"content": "string", "url": "string"},
    )

    async def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        return {"content": "", "url": args.get("url", "")}


class WebExtractTool(Tool):
    name = "web.extract"
    capability = ToolCapability(
        name="web.extract",
        risk="low",
        input_schema={"content": "string", "pattern": "string"},
        output_schema={"matches": "array"},
    )

    async def execute(self, ctx: Any, args: Dict[str, Any]) -> Any:
        return {"matches": []}


PACK = {
    "name": "web",
    "tools": [WebSearchTool(), WebFetchTool(), WebExtractTool()],
}
