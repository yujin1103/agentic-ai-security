from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from agentdojo_mcp_api_chat_client.mcp_bridge import MCPBridge, validate_openai_tool_contracts
from agentdojo_mcp_api_chat_client.terminal_ui import console, show_tools_detailed


async def run(url: str, json_out: bool) -> int:
    async with MCPBridge(url) as mcp:
        openai_tools, raw_tools = await mcp.list_openai_tools()
        failures = validate_openai_tool_contracts(openai_tools)
        result = {
            "mcp_url": url,
            "tool_count": len(openai_tools),
            "failure_count": len(failures),
            "failures": failures,
        }
        if json_out:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            console.print(f"Loaded MCP tools: {len(openai_tools)}")
            show_tools_detailed(raw_tools, openai_tools)
            if failures:
                console.print("[bold red]Tool contract failures[/bold red]")
                console.print(json.dumps(failures, ensure_ascii=False, indent=2))
            else:
                console.print("[green]All tool descriptions and parameter schemas look usable.[/green]")
        return 1 if failures else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit live MCP tool descriptions and parameter schemas as seen by the API chat client.")
    parser.add_argument("--mcp-url", default="http://127.0.0.1:58473/mcp")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.mcp_url, args.json)))


if __name__ == "__main__":
    main()
