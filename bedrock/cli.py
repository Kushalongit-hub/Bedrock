"""Bedrock CLI entry point."""

from __future__ import annotations

import sys


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: bedrock <command> [args]")
        print("Commands: run, replay, serve")
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    if command == "run":
        from bedrock.adapters.cli import main as cli_main
        sys.argv = ["bedrock"] + args
        cli_main()
    elif command == "replay":
        if len(args) < 1:
            print("Usage: bedrock replay <run-id>")
            sys.exit(1)
        run_id = args[0]
        from bedrock.artifacts import RunArtifactStore, RunReplayEngine
        import json

        store = RunArtifactStore(base_dir="runs")
        engine = RunReplayEngine(artifact_store=store)
        result = engine.replay(run_id)
        print(json.dumps(result, indent=2, default=str))
    elif command == "validate":
        from bedrock.validation import DomainPackValidator
        from pathlib import Path

        pack_dir = Path(args[0]) if args else Path(".")
        validator = DomainPackValidator(pack_dir=pack_dir)
        issues = validator.validate()
        if issues:
            for issue in issues:
                print(str(issue))
            sys.exit(1)
        print(f"Domain pack valid: {pack_dir}")
    elif command == "capabilities":
        from bedrock.capabilities import CapabilityInspector
        from pathlib import Path

        pack_dir = Path(args[0]) if args else Path(".")
        inspector = CapabilityInspector(pack_dir=pack_dir)
        print(inspector.inspect())
    elif command == "serve":
        from bedrock.adapters.fastapi_app import create_app
        from bedrock.runtime import AgentRuntime
        from bedrock.memory import MemorySystem
        from bedrock.memory.stores import InMemoryStore
        from bedrock.models import ModelRouter
        from bedrock.models.providers import EchoProvider
        from bedrock.tools import ToolExecutor, ToolRegistry
        from bedrock.artifacts import RunArtifactStore

        registry = ToolRegistry()
        executor = ToolExecutor(registry=registry)
        memory = MemorySystem(store=InMemoryStore())
        router = ModelRouter(providers={"echo": EchoProvider()}, routes={"fast": "echo"})
        artifact_store = RunArtifactStore(base_dir="runs")
        runtime = AgentRuntime(
            model_router=router,
            tool_executor=executor,
            memory=memory,
            artifact_store=artifact_store,
        )
        app = create_app(runtime=runtime)

        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
