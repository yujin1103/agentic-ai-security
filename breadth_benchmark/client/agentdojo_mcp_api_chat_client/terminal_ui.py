from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

console = Console()


def show_banner() -> None:
    console.print(Panel.fit("[bold cyan]MCP API Chat Client[/bold cyan]\nOpenAI API ↔ external MCP server", border_style="cyan"))


def show_models(models: list[str]) -> None:
    table = Table(title="Models")
    table.add_column("Index", justify="right")
    table.add_column("Model")
    for i, m in enumerate(models):
        table.add_row(str(i), m)
    console.print(table)


def show_case(case_id: str, suite: str, task_id: str, prompt: str, mcp_url: str, model: str) -> None:
    body = f"case_id: {case_id}\nsuite: {suite}\ntask_id: {task_id}\nmodel: {model}\nmcp: {mcp_url}\n\n[bold]Initial user task[/bold]\n{prompt}"
    console.print(Panel(body, title="Loaded Current Case", border_style="green"))


def show_user(text: str) -> None:
    console.print(Panel(text, title="User", border_style="blue"))


def show_assistant(text: str) -> None:
    console.print(Panel(text or "[no text]", title="Assistant", border_style="green"))


def show_tool_call(name: str, args: dict[str, Any]) -> None:
    pretty = json.dumps(args, ensure_ascii=False, indent=2)
    console.print(Panel(Syntax(pretty, "json", theme="ansi_dark"), title=f"Tool call: {name}", border_style="yellow"))


def show_tool_result(name: str, output: str, max_chars: int = 4000) -> None:
    text = output if len(output) <= max_chars else output[:max_chars] + f"\n... [truncated {len(output)-max_chars} chars]"
    console.print(Panel(text, title=f"Tool result: {name}", border_style="magenta"))


def show_info(text: str) -> None:
    console.print(f"[cyan]{text}[/cyan]")


def show_warn(text: str) -> None:
    console.print(f"[yellow]{text}[/yellow]")


def show_error(text: str) -> None:
    console.print(f"[bold red]{text}[/bold red]")


def prompt_input() -> str:
    return console.input("\n[bold blue]You[/bold blue] > ")


def _schema_summary(schema: dict[str, Any]) -> str:
    if not isinstance(schema, dict):
        return ""
    props = schema.get("properties", {}) or {}
    required = set(schema.get("required", []) or [])
    if not isinstance(props, dict) or not props:
        return "(no parameters)"
    lines = []
    for name, meta in props.items():
        meta = meta if isinstance(meta, dict) else {}
        typ = meta.get("type", "any")
        desc = meta.get("description", "")
        req = "required" if name in required else "optional"
        line = f"- {name} ({typ}, {req})"
        if desc:
            line += f": {desc}"
        lines.append(line)
    return "\n".join(lines)


def show_tools_detailed(raw_tools: list[dict[str, Any]], openai_tools: list[dict[str, Any]] | None = None) -> None:
    by_name: dict[str, dict[str, Any]] = {}
    for t in openai_tools or []:
        fn = t.get("function", {}) if isinstance(t, dict) else {}
        if fn.get("name"):
            by_name[fn["name"]] = fn
    for raw in raw_tools:
        name = raw.get("name", "")
        fn = by_name.get(name, {})
        description = fn.get("description") or raw.get("description", "") or ""
        schema = fn.get("parameters") or raw.get("inputSchema") or raw.get("input_schema") or {}
        body = f"[bold]{name}[/bold]\n\n{description}\n\n[bold]Parameters[/bold]\n{_schema_summary(schema)}"
        console.print(Panel(body, title=f"Tool: {name}", border_style="cyan"))


def show_status(mcp_url: str, mcp_project_root: str, case_id: str, run_dir: str, trace_path: str) -> None:
    body = (
        f"MCP endpoint: {mcp_url}\n"
        f"MCP project root: {mcp_project_root}\n"
        f"Current case: {case_id}\n"
        f"Client run log: {run_dir}\n"
        f"MCP trace mirror: {trace_path}\n"
    )
    console.print(Panel(body, title="Status", border_style="cyan"))
