from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

CONFIG_PATH = Path(".chat_client_config.json")


@dataclass
class ClientConfig:
    mcp_url: str = "http://127.0.0.1:58473/mcp"
    mcp_project_root: str = ""
    model_index: int = 0
    max_steps: int = 20
    temperature: float = 0.0


def load_config() -> ClientConfig:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return ClientConfig(**{**asdict(ClientConfig()), **data})
        except Exception:
            return ClientConfig()
    return ClientConfig()


def save_config(config: ClientConfig) -> None:
    CONFIG_PATH.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
