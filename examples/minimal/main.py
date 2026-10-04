"""Example: Minimal agent using Bedrock kernel."""

import asyncio

from bedrock.adapters.cli import run_cli


async def main() -> None:
    result = await run_cli("Hello, Bedrock!")
    final = result.artifacts.get("final")
    if final:
        print("Final:", final.get("content"))


if __name__ == "__main__":
    asyncio.run(main())
