from __future__ import annotations

"""Compatibility module for Python imports only.

These functions are intentionally not registered in mcp_server.py. The AI under
 test must not see case-selection or evaluation controls as MCP tools.
"""

from app.mcp.admin import (
    admin_current_task,
    admin_evaluate_case,
    admin_get_trace,
    admin_list_cases,
    admin_prepare_case,
)

__all__ = [
    "admin_list_cases",
    "admin_prepare_case",
    "admin_current_task",
    "admin_evaluate_case",
    "admin_get_trace",
]
