from __future__ import annotations

"""MCP server for local productivity API tools.

The server exposes only application-like tools. Setup, reporting, and log
inspection are handled by separate command-line scripts.

Run modes:
- default HTTP: python mcp_server.py
- stdio only:   python mcp_server.py --transport stdio

By default the server binds only to 127.0.0.1 on port 58473.
The MCP endpoint is http://127.0.0.1:58473/mcp. Pair that local endpoint with
Cloudflare Tunnel when an HTTPS remote MCP URL is needed.
"""

import argparse

from fastmcp import FastMCP

from app.tools.banking import plaid_accounts_get, plaid_transactions_get, plaid_transfer_create
from app.tools.travel import (
    amadeus_flight_offers_search,
    amadeus_hotel_offers_search,
    booking_reservations_create,
    car_rental_offers_search,
)
from app.tools.web_memory import http_get, memory_create, memory_search
from app.tools.workspace import (
    calendar_events_insert,
    calendar_events_list,
    drive_files_create,
    drive_files_delete,
    drive_files_export,
    drive_files_get,
    drive_files_list,
    gmail_users_messages_get,
    gmail_users_messages_list,
    gmail_users_messages_send,
    graph_me_message_get,
    graph_me_messages,
    graph_me_sendMail,
    slack_chat_postMessage,
    slack_conversations_history,
)

mcp = FastMCP("productivity-api-suite")

# Model-facing fake APIs. These names are intentionally close to common REST/SDK
# method names, while all effects remain in the local project state.
for fn in [
    graph_me_messages,
    graph_me_message_get,
    graph_me_sendMail,
    gmail_users_messages_list,
    gmail_users_messages_get,
    gmail_users_messages_send,
    calendar_events_list,
    calendar_events_insert,
    drive_files_list,
    drive_files_get,
    drive_files_export,
    drive_files_create,
    drive_files_delete,
    slack_conversations_history,
    slack_chat_postMessage,
    plaid_accounts_get,
    plaid_transactions_get,
    plaid_transfer_create,
    amadeus_flight_offers_search,
    amadeus_hotel_offers_search,
    car_rental_offers_search,
    booking_reservations_create,
    http_get,
    memory_search,
    memory_create,
]:
    mcp.tool()(fn)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the MCP server.")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="http",
        help="http by default for official UI/Cloudflare; use stdio only for local MCP clients that require it.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host; default keeps server local.")
    parser.add_argument("--port", type=int, default=58473, help="HTTP port used by --transport http.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run()
