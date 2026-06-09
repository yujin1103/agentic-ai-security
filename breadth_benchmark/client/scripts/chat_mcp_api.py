from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import signal
import sys
from pathlib import Path

from openai import OpenAI

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from agentdojo_mcp_api_chat_client.case_context import load_current_case
from agentdojo_mcp_api_chat_client.chat_loop import ChatSettings, OpenAIMCPChat
from agentdojo_mcp_api_chat_client.config import ClientConfig, load_config, save_config
from agentdojo_mcp_api_chat_client.env_loader import load_dotenv, env_default, ENV_PATH
from agentdojo_mcp_api_chat_client.logging_io import RunLogger, new_run_dir
from agentdojo_mcp_api_chat_client.mcp_bridge import MCPBridge, validate_openai_tool_contracts
from agentdojo_mcp_api_chat_client.models import API_MODELS, preferred_available_model, resolve_model
from agentdojo_mcp_api_chat_client.prompts import DEFAULT_SYSTEM_PROMPT
from agentdojo_mcp_api_chat_client.target_scripts import run_target_script
from agentdojo_mcp_api_chat_client.terminal_ui import (
    console,
    prompt_input,
    show_banner,
    show_case,
    show_error,
    show_info,
    show_models,
    show_warn,
    show_status,
    show_tools_detailed,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="OpenAI API chat client that uses an external MCP server.")
    p.add_argument("--mcp-url", default="", help="External MCP endpoint, e.g. http://127.0.0.1:58473/mcp")
    p.add_argument("--mcp-project-root", default="", help="Path to the separate MCP lab project root containing lab_env/current_case.json")
    p.add_argument("--model-index", type=int, default=None, help="Index into the API model array")
    p.add_argument("--list-models", action="store_true")
    p.add_argument("--max-steps", type=int, default=None)
    p.add_argument("--temperature", type=float, default=None)
    p.add_argument("--no-save-config", action="store_true")
    p.add_argument("--once", action="store_true", help="Run the prepared case only, then exit instead of opening follow-up chat")
    return p.parse_args()


def ask_with_default(label: str, default: str, *, secret: bool = False) -> str:
    shown = f" [{default}]" if default and not secret else ""
    prompt = f"{label}{shown}: "
    if secret:
        value = getpass.getpass(prompt).strip()
    else:
        value = console.input(f"[bold cyan]{prompt}[/bold cyan]").strip()
    return value or default


def ensure_api_key() -> None:
    if os.environ.get("OPENAI_API_KEY"):
        show_info("OPENAI_API_KEY loaded from environment/.env")
        return
    key = ask_with_default("OPENAI_API_KEY", "", secret=True).strip()
    if key:
        os.environ["OPENAI_API_KEY"] = key
    else:
        show_error("OPENAI_API_KEY is required. Put it in .env or enter it here.")
        raise SystemExit(2)



def validate_model_access_or_fallback(model: str) -> str:
    """Check /v1/models and fall back to the first available configured model."""
    try:
        ids = [m.id for m in OpenAI().models.list().data]
    except Exception as exc:
        show_warn(f"Could not verify model access; continuing with {model}. Reason: {exc}")
        return model
    chosen, replaced = preferred_available_model(ids, model)
    if replaced:
        show_warn(f"Selected model {model} is not available for this API key. Falling back to {chosen}.")
    return chosen

def print_help() -> None:
    show_info("Commands: /exit, /quit, /help, /eval, /trace, /task, /tools, /toolcheck, /status")
    show_info("Any other input is sent as a follow-up user message using the same conversation and MCP tools.")


async def main_async() -> int:
    args = parse_args()
    if args.list_models:
        show_models(API_MODELS)
        return 0

    show_banner()
    loaded_env = load_dotenv()
    if loaded_env:
        show_info(f"Loaded .env: {ENV_PATH}")
    cfg = load_config()

    # .env values are prompt defaults. CLI arguments still override them below.
    cfg.mcp_url = env_default("MCP_ENDPOINT", env_default("MCP_URL", cfg.mcp_url))
    cfg.mcp_project_root = env_default("MCP_PROJECT_ROOT", cfg.mcp_project_root)
    if env_default("MODEL_INDEX", ""):
        try:
            cfg.model_index = int(env_default("MODEL_INDEX"))
        except ValueError:
            show_warn("Ignoring invalid MODEL_INDEX in .env")
    if env_default("MAX_STEPS", ""):
        try:
            cfg.max_steps = int(env_default("MAX_STEPS"))
        except ValueError:
            show_warn("Ignoring invalid MAX_STEPS in .env")
    if env_default("TEMPERATURE", ""):
        try:
            cfg.temperature = float(env_default("TEMPERATURE"))
        except ValueError:
            show_warn("Ignoring invalid TEMPERATURE in .env")
    if args.mcp_url:
        cfg.mcp_url = args.mcp_url
    if args.mcp_project_root:
        cfg.mcp_project_root = args.mcp_project_root
    if args.model_index is not None:
        cfg.model_index = args.model_index
    if args.max_steps is not None:
        cfg.max_steps = args.max_steps
    if args.temperature is not None:
        cfg.temperature = args.temperature

    cfg.mcp_url = ask_with_default("MCP endpoint", cfg.mcp_url)
    cfg.mcp_project_root = ask_with_default("MCP lab project root", cfg.mcp_project_root)
    show_models(API_MODELS)
    model_text = ask_with_default("Model index", str(cfg.model_index))
    try:
        cfg.model_index = int(model_text)
    except ValueError:
        show_error("Model index must be an integer")
        return 2

    try:
        model = resolve_model(cfg.model_index)
    except ValueError as exc:
        show_error(str(exc))
        return 2

    ensure_api_key()
    model = validate_model_access_or_fallback(model)

    if not args.no_save_config:
        save_config(cfg)

    try:
        current_case = load_current_case(cfg.mcp_project_root)
    except Exception as exc:
        show_error(str(exc))
        show_warn("Prepare a case in the MCP project first, then run this client again.")
        return 2

    run_dir = new_run_dir()
    logger = RunLogger(run_dir)
    logger.event("start", {
        "mcp_url": cfg.mcp_url,
        "mcp_project_root": str(current_case.project_root),
        "case_id": current_case.case_id,
        "model": model,
    })

    show_case(current_case.case_id, current_case.suite, current_case.user_task_id, current_case.user_prompt, cfg.mcp_url, model)
    show_info(f"Run log: {run_dir}")

    try:
        async with MCPBridge(cfg.mcp_url) as mcp:
            openai_tools, raw_tools = await mcp.list_openai_tools()
            logger.event("tools_list", {"count": len(openai_tools), "tools": raw_tools})
            show_info(f"Loaded MCP tools: {len(openai_tools)}")

            chat = OpenAIMCPChat(
                mcp=mcp,
                openai_tools=openai_tools,
                settings=ChatSettings(model=model, max_steps=cfg.max_steps, temperature=cfg.temperature),
                system_prompt=DEFAULT_SYSTEM_PROMPT,
                logger=logger,
                mcp_project_root=current_case.project_root,
            )
            await chat.add_user_and_run(current_case.user_prompt)

            if args.once:
                return 0

            print_help()
            while True:
                try:
                    text = prompt_input().strip()
                except (EOFError, KeyboardInterrupt):
                    show_info("Exiting chat client.")
                    return 0
                if not text:
                    continue
                low = text.lower()
                if low in {"/exit", "/quit"}:
                    show_info("Exiting chat client.")
                    return 0
                if low == "/help":
                    print_help()
                    continue
                if low == "/eval":
                    code, out = run_target_script(current_case.project_root, "evaluate_case.py")
                    console.print(out)
                    show_info(f"evaluate_case.py exit code: {code}")
                    continue
                if low == "/trace":
                    code, out = run_target_script(current_case.project_root, "show_trace.py", "--limit", "100")
                    console.print(out)
                    show_info(f"show_trace.py exit code: {code}")
                    continue
                if low == "/task":
                    code, out = run_target_script(current_case.project_root, "show_task.py")
                    console.print(out)
                    show_info(f"show_task.py exit code: {code}")
                    continue
                if low == "/tools":
                    show_tools_detailed(raw_tools, openai_tools)
                    continue
                if low == "/toolcheck":
                    failures = validate_openai_tool_contracts(openai_tools)
                    if failures:
                        show_error(f"Tool contract failures: {len(failures)}")
                        console.print(json.dumps(failures, ensure_ascii=False, indent=2))
                    else:
                        show_info(f"Tool contract check passed for {len(openai_tools)} tools.")
                    continue
                if low == "/status":
                    show_status(
                        cfg.mcp_url,
                        str(current_case.project_root),
                        current_case.case_id,
                        str(run_dir),
                        str(current_case.project_root / "lab_env" / "traces" / "tool_calls.jsonl"),
                    )
                    continue

                await chat.add_user_and_run(text)
    except KeyboardInterrupt:
        show_info("Interrupted. MCP client session closed.")
        return 130
    except Exception as exc:
        show_error(f"Fatal error: {type(exc).__name__}: {exc}")
        return 1
    finally:
        logger.event("end", {})


def main() -> None:
    if hasattr(signal, "SIGBREAK"):
        try:
            signal.signal(signal.SIGBREAK, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
        except Exception:
            pass
    raise SystemExit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
