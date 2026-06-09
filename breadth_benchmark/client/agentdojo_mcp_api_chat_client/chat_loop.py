from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from pathlib import Path

from .logging_io import RunLogger, mirror_tool_trace
from .mcp_bridge import MCPBridge
from .terminal_ui import show_assistant, show_error, show_info, show_tool_call, show_tool_result, show_user, show_warn


@dataclass
class ChatSettings:
    model: str
    max_steps: int = 20
    temperature: float = 0.0


def _tool_calls_to_message(tool_calls: list[Any]) -> list[dict[str, Any]]:
    payload = []
    for tc in tool_calls:
        payload.append({
            "id": tc.id,
            "type": "function",
            "function": {
                "name": tc.function.name,
                "arguments": tc.function.arguments or "{}",
            },
        })
    return payload


class OpenAIMCPChat:
    def __init__(
        self,
        *,
        mcp: MCPBridge,
        openai_tools: list[dict[str, Any]],
        settings: ChatSettings,
        system_prompt: str,
        logger: RunLogger,
        mcp_project_root: Path | None = None,
    ) -> None:
        self.mcp = mcp
        self.openai_tools = openai_tools
        self.settings = settings
        self.client = AsyncOpenAI()
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
        ]
        self.logger = logger
        self.mcp_project_root = mcp_project_root

    async def add_user_and_run(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})
        self.logger.transcript("User", text)
        self.logger.event("user", {"text": text})
        show_user(text)
        await self.run_until_idle()

    async def run_until_idle(self) -> None:
        for step in range(self.settings.max_steps):
            kwargs = {
                "model": self.settings.model,
                "messages": self.messages,
                "tools": self.openai_tools,
                "tool_choice": "auto",
            }
            # Some model families may reject temperature=0.0; keep it configurable and omit only if None.
            if self.settings.temperature is not None:
                kwargs["temperature"] = self.settings.temperature

            try:
                response = await self.client.chat.completions.create(**kwargs)
            except Exception as exc:
                show_error(f"OpenAI API error: {exc}")
                self.logger.event("openai_error", {"error": str(exc)})
                return

            msg = response.choices[0].message
            content = msg.content or ""
            tool_calls = list(msg.tool_calls or [])

            if content.strip():
                show_assistant(content)
                self.logger.transcript("Assistant", content)
                self.logger.event("assistant", {"text": content})

            assistant_message: dict[str, Any] = {"role": "assistant", "content": content or None}
            if tool_calls:
                assistant_message["tool_calls"] = _tool_calls_to_message(tool_calls)
            self.messages.append(assistant_message)

            if not tool_calls:
                return

            for tc in tool_calls:
                name = tc.function.name
                arg_text = tc.function.arguments or "{}"
                try:
                    args = json.loads(arg_text)
                except json.JSONDecodeError:
                    args = {}
                    show_warn(f"Tool arguments were not valid JSON for {name}; using empty args")

                show_tool_call(name, args)
                self.logger.event("tool_call", {"name": name, "args": args})

                try:
                    raw_result, output_text = await self.mcp.call_tool(name, args)
                except Exception as exc:
                    output_text = f"Tool execution failed: {type(exc).__name__}: {exc}"
                    show_error(output_text)
                    self.logger.event("tool_error", {"name": name, "args": args, "error": str(exc)})
                    if self.mcp_project_root is not None:
                        mirror_tool_trace(self.mcp_project_root, name, args, output_text, blocked=True)
                else:
                    show_tool_result(name, output_text)
                    self.logger.event("tool_result", {"name": name, "output": output_text})
                    if self.mcp_project_root is not None:
                        mirror_tool_trace(self.mcp_project_root, name, args, output_text, blocked=False)

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": output_text,
                })

        show_warn(f"Stopped after max_steps={self.settings.max_steps}. The model may not be finished.")
        self.logger.event("max_steps", {"max_steps": self.settings.max_steps})
