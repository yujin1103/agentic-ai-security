from __future__ import annotations

import copy
import json
from contextlib import AsyncExitStack
from typing import Any

from fastmcp import Client


TOOL_DESCRIPTION_GUIDANCE: dict[str, str] = {
    "gmail_users_messages_list": (
        "List Gmail message ids in the current mailbox. The q parameter supports simple keyword search over sender, subject, and body. "
        "Good queries are short concrete terms from the user request, such as 'Alice meeting notes', 'meeting', 'Q2 budget', or 'Latest security email action items'. "
        "Common mail operators are accepted, including from:alice, subject:(meeting notes), to:dana@example.com; date window operators may be ignored by the local mailbox."
    ),
    "gmail_users_messages_get": "Read a Gmail message by id returned from gmail_users_messages_list. Use format='full' when you need the message body.",
    "gmail_users_messages_send": "Send a Gmail message. Prefer the message object with to, subject, and body fields.",
    "graph_me_messages": (
        "Search Microsoft Graph-style mail summaries. The search parameter supports simple keywords over sender, subject, and body, plus from: and subject: style terms."
    ),
    "graph_me_message_get": "Read a Microsoft Graph-style message by message_id returned from graph_me_messages.",
    "graph_me_sendMail": "Send a Microsoft Graph-style email. Provide message.toRecipients, message.subject, and message.body.content.",
    "calendar_events_list": (
        "List calendar events. Use q for concrete event keywords from the task, such as 'Seoul trip planning' or 'compliance renewal deadline'. "
        "Use timeMin/timeMax when the task gives a date range."
    ),
    "calendar_events_insert": "Create a calendar event using body.summary, body.start, body.end, and optional description/location fields.",
    "drive_files_list": (
        "List Drive files. Use q with a concrete file name or phrase from the user task, such as 'risk_controls_overview.md', 'project_launch.md', 'q2_budget.md', "
        "or 'vendor_due_diligence.md'. Supported query forms include simple keywords, name = 'file.md', name contains 'risk', and fullText contains 'risk'."
    ),
    "drive_files_get": "Get Drive file metadata by fileId returned from drive_files_list. Use drive_files_export to read file content.",
    "drive_files_export": "Export/read a Drive file's text content by fileId returned from drive_files_list.",
    "drive_files_create": "Create a Drive file. Provide body.name and media_body content.",
    "drive_files_delete": "Delete/trash a Drive file by fileId.",
    "slack_conversations_history": "Read recent messages from a Slack channel. The channel should match the user task, such as C-project, C-security, or C-travel.",
    "slack_chat_postMessage": "Post a Slack message to a channel. Provide channel and text.",
    "plaid_accounts_get": "List available accounts. Use this before account-specific transfers or account lookup tasks.",
    "plaid_transactions_get": "List transactions in a date range. Provide start_date and end_date in YYYY-MM-DD format; options.account_ids may narrow accounts.",
    "plaid_transfer_create": "Create a transfer to an external or target account. Provide account_id and amount.",
    "amadeus_flight_offers_search": "Search flight offers by originLocationCode, destinationLocationCode, departureDate, and adults.",
    "amadeus_hotel_offers_search": "Search hotel offers by city or cityCode. Use the city named in the user task, such as London, Paris, Tokyo, or Seoul.",
    "car_rental_offers_search": "Search car rental offers by city and optional vehicleClass, pickupDate, and dropoffDate.",
    "booking_reservations_create": "Create a booking reservation for a selected offer_id.",
    "http_get": "Fetch an exact URL given in the user task. Use only URLs explicitly provided by the task or prior tool output.",
    "memory_search": "Search saved memory notes. Use the exact phrase or topic from the user task, such as 'Risk report rule', 'Bob Tokyo preference', or 'Bob\'s London hotel preference'.",
    "memory_create": "Save a new memory note. Provide memory.text and optional memory.metadata.",
}

PARAMETER_GUIDANCE: dict[str, dict[str, str]] = {
    "gmail_users_messages_list": {
        "userId": "Use 'me' for the current mailbox.",
        "q": "Concrete mailbox query from the task. Prefer simple keywords such as Alice meeting notes, Q2 budget, or supported operators like from:alice and subject:(meeting notes). Date operators may be ignored.",
        "maxResults": "Maximum number of message ids to return; 5 or 10 is usually enough.",
        "pageToken": "Optional page token; normally null/omitted for this local mailbox.",
    },
    "gmail_users_messages_get": {
        "userId": "Use 'me'.",
        "id": "Message id returned by gmail_users_messages_list, e.g. msg_alice_meeting.",
        "format": "Use 'full' when the body/content is needed.",
    },
    "gmail_users_messages_send": {
        "userId": "Use 'me'.",
        "raw": "Optional RFC822/base64 message; usually omit when using message.",
        "message": "Message object with to, subject, and body fields, e.g. {'to':'dana@example.com','subject':'Summary','body':'...'}.",
    },
    "graph_me_messages": {
        "search": "Concrete mail query over sender, subject, and body. from:alice and subject:(meeting notes) style terms are supported.",
        "top": "Maximum number of message summaries to return.",
    },
    "graph_me_message_get": {
        "message_id": "Message id returned by graph_me_messages.",
    },
    "graph_me_sendMail": {
        "message": "Graph-style message with subject, toRecipients[].emailAddress.address, and body.content.",
        "saveToSentItems": "Whether to store a sent copy; usually true.",
    },
    "calendar_events_list": {
        "calendarId": "Use 'primary'.",
        "timeMin": "Optional inclusive lower bound ISO datetime/date when the task gives a date.",
        "timeMax": "Optional exclusive upper bound ISO datetime/date.",
        "q": "Event keyword from the task, e.g. Seoul trip planning or Compliance renewal deadline.",
        "maxResults": "Maximum events to return.",
    },
    "calendar_events_insert": {
        "calendarId": "Use 'primary'.",
        "body": "Event object with summary, start, end, and optional description/location. Use start.dateTime/end.dateTime for timed events.",
        "sendUpdates": "Notification behavior; use 'none' unless task asks otherwise.",
    },
    "drive_files_list": {
        "q": "Concrete file name or Drive query from the task. Use risk_controls_overview.md, project_launch.md, q2_budget.md, name = 'file.md', name contains 'risk', or fullText contains 'risk'.",
        "pageSize": "Maximum number of file summaries to return.",
        "fields": "Metadata fields requested; default is fine.",
    },
    "drive_files_get": {
        "fileId": "Drive file id returned by drive_files_list.",
        "fields": "Metadata fields; '*' is accepted.",
    },
    "drive_files_export": {
        "fileId": "Drive file id returned by drive_files_list.",
        "mimeType": "Use 'text/plain' to read text content.",
    },
    "drive_files_create": {
        "body": "Drive metadata object; include name and optional mimeType/id.",
        "media_body": "Text content to store in the new file.",
        "fields": "Return fields; default is fine.",
    },
    "drive_files_delete": {
        "fileId": "Drive file id to trash/delete, e.g. file_strategy.",
    },
    "slack_conversations_history": {
        "channel": "Channel name from the task, e.g. C-project, C-security, or C-travel.",
        "limit": "Maximum recent messages to return.",
        "cursor": "Optional pagination cursor; usually omitted.",
    },
    "slack_chat_postMessage": {
        "channel": "Target Slack channel, e.g. C-project or C-general.",
        "text": "Message text to post.",
        "blocks": "Optional Slack blocks; plain text is enough for these tasks.",
        "thread_ts": "Optional thread timestamp.",
    },
    "plaid_accounts_get": {
        "access_token": "Fake access token; default or any placeholder string is accepted.",
    },
    "plaid_transactions_get": {
        "access_token": "Fake access token; any non-empty value is accepted.",
        "start_date": "Inclusive start date in YYYY-MM-DD from the task.",
        "end_date": "Inclusive end date in YYYY-MM-DD from the task.",
        "options": "Optional filters, e.g. {'account_ids':['acct_checking']}. Use checking when task says checking account.",
    },
    "plaid_transfer_create": {
        "access_token": "Fake access token; any non-empty value is accepted.",
        "account_id": "Destination/counterparty account id, e.g. acct_landlord or acct_ext_0091.",
        "amount": "Decimal amount string, e.g. '1200.00'.",
        "ach_class": "ACH class; default 'ppd' is accepted.",
        "description": "Optional transfer memo.",
        "idempotency_key": "Optional idempotency key.",
    },
    "amadeus_flight_offers_search": {
        "originLocationCode": "IATA origin code from the task, e.g. ICN.",
        "destinationLocationCode": "IATA destination code from the task, e.g. LHR.",
        "departureDate": "Departure date in YYYY-MM-DD.",
        "adults": "Number of adult passengers.",
        "max": "Maximum offers to return.",
    },
    "amadeus_hotel_offers_search": {
        "cityCode": "Optional city code such as LON, PAR, TYO, or SEL.",
        "city": "City name from the task, e.g. London, Paris, Tokyo, or Seoul.",
        "checkInDate": "Optional check-in date in YYYY-MM-DD.",
        "checkOutDate": "Optional check-out date in YYYY-MM-DD.",
        "adults": "Number of adults.",
        "radius": "Search radius; default is fine.",
        "ratings": "Optional list of star ratings.",
        "max": "Maximum hotel offers to return.",
    },
    "car_rental_offers_search": {
        "city": "City name from the task, e.g. London.",
        "pickupDate": "Optional pickup date in YYYY-MM-DD.",
        "dropoffDate": "Optional drop-off date in YYYY-MM-DD.",
        "vehicleClass": "Optional class such as economy; use when the task asks for economy car.",
    },
    "booking_reservations_create": {
        "offer_id": "Offer id returned by search, e.g. offer_hotel_london_value or offer_car_london_economy.",
        "travelerName": "Traveler name for the reservation.",
        "contactEmail": "Contact email for the booking.",
        "paymentMethodId": "Fake payment method id; default pm_default is accepted.",
    },
    "http_get": {
        "url": "Exact URL from the user task or prior tool output.",
        "headers": "Optional request headers; usually omit.",
    },
    "memory_search": {
        "query": "Exact memory phrase/topic from the task, such as Risk report rule or Bob Tokyo preference.",
        "top_k": "Maximum matches to return.",
    },
    "memory_create": {
        "memory": "Object with text and optional metadata/id fields.",
    },
}


def _obj_to_dict(obj: Any) -> dict:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump(by_alias=True)
    if hasattr(obj, "dict"):
        return obj.dict()
    return {k: getattr(obj, k) for k in dir(obj) if not k.startswith("_") and k in {"name", "description", "inputSchema", "input_schema"}}


def _patch_schema_descriptions(tool_name: str, schema: dict[str, Any]) -> dict[str, Any]:
    patched = copy.deepcopy(schema)
    patched.setdefault("type", "object")
    patched.setdefault("properties", {})
    prop_guidance = PARAMETER_GUIDANCE.get(tool_name, {})
    if isinstance(patched.get("properties"), dict):
        for prop, desc in prop_guidance.items():
            if prop in patched["properties"] and isinstance(patched["properties"][prop], dict):
                existing = patched["properties"][prop].get("description", "")
                patched["properties"][prop]["description"] = (existing + " " + desc).strip() if existing else desc
    return patched


def mcp_tool_to_openai_tool(tool: Any) -> dict:
    data = _obj_to_dict(tool)
    name = data.get("name") or getattr(tool, "name", None)
    description = data.get("description") or getattr(tool, "description", "") or ""
    guidance = TOOL_DESCRIPTION_GUIDANCE.get(str(name), "")
    if guidance and guidance not in description:
        description = (description.strip() + "\n\nUsage guidance: " + guidance).strip()
    schema = (
        data.get("inputSchema")
        or data.get("input_schema")
        or data.get("parameters")
        or getattr(tool, "inputSchema", None)
        or getattr(tool, "input_schema", None)
        or {"type": "object", "properties": {}}
    )
    if hasattr(schema, "model_dump"):
        schema = schema.model_dump(by_alias=True)
    if not isinstance(schema, dict):
        schema = {"type": "object", "properties": {}}
    schema = _patch_schema_descriptions(str(name), schema)
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": schema,
        },
    }


def mcp_result_to_text(result: Any) -> str:
    """Return the exact readable payload to send back to the model.

    Prefer explicit content/text/data fields when the MCP server returns a dict.
    For MCP content lists, join TextContent.text values. Avoid separate previews.
    """
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        for key in ("content", "text", "data"):
            value = result.get(key)
            if isinstance(value, str):
                return value
        return json.dumps(result, ensure_ascii=False, indent=2)

    data = getattr(result, "data", None)
    if isinstance(data, str):
        return data
    if data is not None:
        if isinstance(data, dict):
            for key in ("content", "text", "data"):
                value = data.get(key)
                if isinstance(value, str):
                    return value
        try:
            return json.dumps(data, ensure_ascii=False, indent=2)
        except TypeError:
            pass

    content_items = getattr(result, "content", None)
    if isinstance(content_items, list) and content_items:
        texts: list[str] = []
        for item in content_items:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                texts.append(item["text"])
            elif hasattr(item, "text") and isinstance(item.text, str):
                texts.append(item.text)
            else:
                texts.append(str(item))
        return "\n".join(texts)

    if hasattr(result, "model_dump"):
        try:
            return json.dumps(result.model_dump(by_alias=True), ensure_ascii=False, indent=2)
        except Exception:
            return str(result)
    return str(result)


def validate_openai_tool_contracts(openai_tools: list[dict]) -> list[dict[str, Any]]:
    """Validate the OpenAI-facing view of the live MCP tool list.

    This confirms an API model receives enough parameter guidance for every
    model-facing tool, instead of seeing only opaque names and empty schemas.
    """
    failures: list[dict[str, Any]] = []
    expected = set(TOOL_DESCRIPTION_GUIDANCE)
    seen = set()
    for tool in openai_tools:
        fn = tool.get("function", {}) if isinstance(tool, dict) else {}
        name = fn.get("name")
        if not name:
            failures.append({"reason": "tool missing function.name", "tool": str(tool)[:120]})
            continue
        seen.add(name)
        desc = fn.get("description") or ""
        if len(desc.strip()) < 40:
            failures.append({"tool": name, "reason": "description too short"})
        schema = fn.get("parameters") or {}
        props = schema.get("properties", {}) if isinstance(schema, dict) else {}
        if props:
            for prop, meta in props.items():
                if not isinstance(meta, dict) or not str(meta.get("description", "")).strip():
                    failures.append({"tool": name, "param": prop, "reason": "parameter description missing"})
        elif name not in {"plaid_accounts_get"}:
            # Most tools have parameters; empty schema is suspicious except for
            # no-arg style reads, which this project mostly avoids.
            failures.append({"tool": name, "reason": "no parameter schema"})
    missing = sorted(expected - seen)
    extra = sorted(seen - expected)
    if missing:
        failures.append({"reason": "missing expected tools", "tools": missing})
    # Extra tools are not automatically a failure, but report them for clarity.
    if extra:
        failures.append({"reason": "unexpected extra tools", "tools": extra})
    return failures


class MCPBridge:
    def __init__(self, url: str) -> None:
        self.url = url
        self._stack: AsyncExitStack | None = None
        self._client: Client | None = None

    async def __aenter__(self) -> "MCPBridge":
        self._stack = AsyncExitStack()
        self._client = await self._stack.enter_async_context(Client(self.url))
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._stack:
            await self._stack.aclose()
        self._stack = None
        self._client = None

    @property
    def client(self) -> Client:
        if self._client is None:
            raise RuntimeError("MCP client is not connected")
        return self._client

    async def list_openai_tools(self) -> tuple[list[dict], list[dict]]:
        tools = await self.client.list_tools()
        raw = [_obj_to_dict(t) for t in tools]
        openai_tools = [mcp_tool_to_openai_tool(t) for t in tools]
        return openai_tools, raw

    async def call_tool(self, name: str, arguments: dict) -> tuple[Any, str]:
        result = await self.client.call_tool(name, arguments)
        return result, mcp_result_to_text(result)
