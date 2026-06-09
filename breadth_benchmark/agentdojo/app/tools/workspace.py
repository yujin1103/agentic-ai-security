from __future__ import annotations

import base64, email, re
from email.message import EmailMessage
from typing import Any

from app.tools.common import _contains, _trace, commit, load_state


def _mail_fields(message: dict[str, Any]) -> dict[str, str]:
    sender = message.get("from", {}).get("emailAddress", {})
    sender_address = sender.get("address", "")
    sender_name = sender.get("name", "")
    subject = message.get("subject", "")
    body = message.get("body", {}).get("content", "")
    return {
        "from": f"{sender_name} {sender_address}",
        "subject": subject,
        "body": body,
        "all": f"{sender_name} {sender_address} {subject} {body}",
    }


def _tokens(text: str) -> list[str]:
    return [t.casefold() for t in re.findall(r"[A-Za-z0-9_.@-]+", text or "") if t.strip()]


def _field_contains(text: str, query: str) -> bool:
    q_tokens = _tokens(query)
    if not q_tokens:
        return True
    hay = (text or "").casefold()
    return all(tok in hay for tok in q_tokens)


def _extract_operator_values(q: str, op: str) -> tuple[list[str], str]:
    """Extract simple Gmail-style operator values and return values + remaining query.

    Supported examples:
    - from:alice
    - subject:(meeting notes)
    - subject:"meeting notes"
    - to:dana@example.com

    Date/window operators such as newer_than:30d are intentionally stripped and
    ignored because this local fake mailbox is tiny and date ordering is not the
    purpose of the benchmark.
    """
    values: list[str] = []
    remaining = q or ""
    pattern = re.compile(rf"\b{re.escape(op)}:(\([^)]*\)|\"[^\"]*\"|'[^']*'|\S+)", re.IGNORECASE)
    while True:
        m = pattern.search(remaining)
        if not m:
            break
        raw = m.group(1).strip()
        if raw.startswith("(") and raw.endswith(")"):
            raw = raw[1:-1]
        if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
            raw = raw[1:-1]
        values.append(raw.strip())
        remaining = remaining[:m.start()] + " " + remaining[m.end():]
    return values, remaining


def _strip_ignored_gmail_ops(q: str) -> str:
    ignored = [
        "newer_than", "older_than", "after", "before", "newer", "older",
        "in", "is", "label", "category", "has", "filename",
    ]
    out = q or ""
    for op in ignored:
        out = re.sub(rf"\b{op}:(\([^)]*\)|\"[^\"]*\"|'[^']*'|\S+)", " ", out, flags=re.IGNORECASE)
    # Common boolean syntax is unnecessary for this local fake mailbox. Treat it
    # as whitespace so fallback keyword matching remains useful.
    out = re.sub(r"\b(AND|OR)\b", " ", out, flags=re.IGNORECASE)
    out = out.replace("(", " ").replace(")", " ")
    return " ".join(out.split())


def _mail_matches_query(message: dict[str, Any], query: str) -> bool:
    """Match common Gmail/Microsoft Graph search forms against fake mail.

    This keeps the official UI flow working while also supporting realistic LLM
    queries such as `from:alice subject:(meeting notes) newer_than:30d`.
    """
    q = (query or "").strip()
    if not q:
        return True
    fields = _mail_fields(message)

    from_values, rest = _extract_operator_values(q, "from")
    subject_values, rest = _extract_operator_values(rest, "subject")
    to_values, rest = _extract_operator_values(rest, "to")

    for value in from_values:
        if not _field_contains(fields["from"], value):
            return False
    for value in subject_values:
        if not _field_contains(fields["subject"], value):
            return False
    if to_values:
        recipients = " ".join(
            r.get("emailAddress", {}).get("address", "")
            for r in message.get("toRecipients", [])
        )
        for value in to_values:
            if not _field_contains(recipients, value):
                return False

    rest = _strip_ignored_gmail_ops(rest)
    if not rest:
        return True
    return _field_contains(fields["all"], rest)


def graph_me_messages(search: str = "", top: int = 10) -> dict[str, Any]:
    """Search the current user's fake Microsoft Graph mailbox.

    Parameters:
    - search: Keyword query over subject, sender, and body. Common mail search
      forms like `from:alice` and `subject:(meeting notes)` are supported.
    - top: Maximum number of message summaries to return.
    """
    state = load_state()
    rows = []
    for m in state["mail"]["messages"]:
        if _mail_matches_query(m, search):
            rows.append({k: m[k] for k in ["id", "subject", "from", "receivedDateTime"] if k in m})
    return _trace("graph_me_messages", {"search": search, "top": top}, {"value": rows[:top]})


def graph_me_message_get(message_id: str) -> dict[str, Any]:
    """Read a fake Microsoft Graph mail message by id.

    Parameters:
    - message_id: Message id returned by graph_me_messages, such as msg_alice_meeting.
    """
    state = load_state()
    for m in state["mail"]["messages"]:
        if m["id"] == message_id:
            return _trace("graph_me_message_get", {"message_id": message_id}, m)
    return _trace("graph_me_message_get", {"message_id": message_id}, {"error":"notFound"}, blocked=False)


def graph_me_sendMail(message: dict[str, Any], saveToSentItems: bool = True) -> dict[str, Any]:
    """Send a fake Microsoft Graph-style email.

    Parameters:
    - message: Object with subject, toRecipients, and body.content.
      Example: {"subject":"Summary","toRecipients":[{"emailAddress":{"address":"dana@example.com"}}],"body":{"contentType":"Text","content":"..."}}.
    - saveToSentItems: Keep a sent copy in the fake sent-mail state; usually true.
    """
    state = load_state()
    item = {"message": message, "saveToSentItems": bool(saveToSentItems), "transport":"fake_graph_sendMail"}
    state["mail"]["sent"].append(item)
    commit(state)
    return _trace("graph_me_sendMail", {"message": message, "saveToSentItems": saveToSentItems}, {"status":202})


def gmail_users_messages_list(userId: str = "me", q: str = "", maxResults: int = 10, pageToken: str | None = None) -> dict[str, Any]:
    """List fake Gmail messages for the current user.

    Parameters:
    - userId: Use `me` for the current fake user.
    - q: Search query over subject, sender, and body. Prefer simple terms such
      as `Alice meeting notes`, `meeting`, `Q2 budget`, or `Latest security
      email action items`. Common Gmail-style operators are also accepted:
      `from:alice`, `subject:(meeting notes)`, and date/window operators such as
      `newer_than:30d` are tolerated. Date/window operators are ignored in this
      local fake mailbox.
    - maxResults: Maximum number of message ids to return.
    - pageToken: Accepted for API-shape compatibility; pagination is not needed
      for this local fake dataset.
    """
    state = load_state()
    msgs = []
    for m in state["mail"]["messages"]:
        if _mail_matches_query(m, q):
            msgs.append({"id": m["id"], "threadId": "thread_" + m["id"]})
    return _trace("gmail_users_messages_list", {"userId":userId, "q":q, "maxResults":maxResults, "pageToken":pageToken}, {"messages": msgs[:maxResults], "resultSizeEstimate": len(msgs)})


def gmail_users_messages_get(userId: str, id: str, format: str = "full") -> dict[str, Any]:
    """Get/read a fake Gmail message by id.

    Parameters:
    - userId: Use `me` for the current fake mailbox.
    - id: Message id returned by gmail_users_messages_list, such as msg_alice_meeting.
    - format: Use `full` when the message body is needed.
    """
    state = load_state()
    for m in state["mail"]["messages"]:
        if m["id"] == id:
            payload = {"headers":[{"name":"Subject", "value":m["subject"]}, {"name":"From", "value":m["from"]["emailAddress"]["address"]}], "body":{"data":m["body"]["content"]}}
            out = {"id": id, "threadId":"thread_"+id, "labelIds":["INBOX"], "payload": payload, "snippet":m["body"]["content"][:120]}
            return _trace("gmail_users_messages_get", {"userId":userId, "id":id, "format":format}, out)
    return _trace("gmail_users_messages_get", {"userId":userId, "id":id, "format":format}, {"error":"notFound"})


def gmail_users_messages_send(userId: str = "me", raw: str = "", message: dict[str, Any] | None = None) -> dict[str, Any]:
    """Send a fake Gmail message.

    Parameters:
    - userId: Use `me` for the current fake mailbox.
    - raw: Optional RFC822/base64 message; usually omit when using the message object.
    - message: Object with to, subject, and body fields. Example: {"to":"dana@example.com","subject":"Summary","body":"..."}.
    """
    state = load_state()
    parsed = message or {}
    if raw and not message:
        try:
            decoded = base64.urlsafe_b64decode(raw + "===").decode("utf-8", errors="replace")
            msg = email.message_from_string(decoded)
            parsed = {"subject": msg.get("Subject", ""), "raw_decoded": decoded, "toRecipients":[{"emailAddress":{"address":msg.get("To", "")}}], "body":{"contentType":"Text", "content": decoded}}
        except Exception:
            parsed = {"raw": raw, "body":{"contentType":"Text", "content": raw}}
    state["mail"]["sent"].append({"message": parsed, "saveToSentItems": True, "transport":"fake_gmail_send"})
    msg_id = f"sent_{len(state['mail']['sent'])}"
    commit(state)
    return _trace("gmail_users_messages_send", {"userId":userId, "raw": raw[:60], "message":message}, {"id":msg_id, "labelIds":["SENT"]})


def _event_in_range(event: dict[str, Any], timeMin: str | None, timeMax: str | None) -> bool:
    start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date") or ""
    if timeMin and start and start < timeMin:
        return False
    if timeMax and start and start >= timeMax:
        return False
    return True


def calendar_events_list(calendarId: str = "primary", timeMin: str | None = None, timeMax: str | None = None, q: str = "", maxResults: int = 10) -> dict[str, Any]:
    """List fake Google Calendar events.

    Parameters:
    - calendarId: Use `primary` for the fake primary calendar.
    - timeMin: Optional inclusive lower bound ISO datetime/date. Use when the task gives a date, e.g. 2026-06-10T00:00:00+09:00.
    - timeMax: Optional exclusive upper bound ISO datetime/date, e.g. the next day for a one-day search.
    - q: Concrete event keyword from the task such as `Seoul trip planning` or `Compliance renewal deadline`.
    - maxResults: Maximum number of events to return.
    """
    state = load_state()
    events = []
    for e in state["calendar"]["events"]:
        hay = f"{e.get('summary','')} {e.get('description','')}"
        if _contains(hay, q) and _event_in_range(e, timeMin, timeMax):
            events.append(e)
    return _trace("calendar_events_list", {"calendarId":calendarId, "timeMin":timeMin, "timeMax":timeMax, "q":q, "maxResults":maxResults}, {"items":events[:maxResults]})


def calendar_events_insert(calendarId: str = "primary", body: dict[str, Any] | None = None, sendUpdates: str = "none") -> dict[str, Any]:
    """Create a fake calendar event.

    Parameters:
    - calendarId: Use `primary`.
    - body: Event object with summary, start, end, and optional description/location.
      Use start.dateTime/end.dateTime for timed events.
    - sendUpdates: Notification behavior; use `none` unless the task explicitly asks otherwise.
    """
    state = load_state()
    event = dict(body or {})
    event.setdefault("id", f"evt_created_{len(state['calendar']['events'])+1}")
    state["calendar"]["events"].append(event)
    commit(state)
    return _trace("calendar_events_insert", {"calendarId":calendarId, "body":body, "sendUpdates":sendUpdates}, {"status":"confirmed", **event})



def _drive_query_terms(q: str) -> list[str]:
    """Extract useful terms from common Drive query syntax.

    Supported examples:
    - risk_controls_overview.md
    - name = 'risk_controls_overview.md'
    - name contains 'risk_controls'
    - fullText contains 'vendor access'
    - trashed = false (ignored)
    """
    raw = (q or "").strip()
    if not raw:
        return []
    terms: list[str] = []
    # Pull quoted values from common Drive operators.
    for pattern in [
        r"\bname\s*=\s*(['\"])(.*?)\1",
        r"\bname\s+contains\s+(['\"])(.*?)\1",
        r"\bfullText\s+contains\s+(['\"])(.*?)\1",
    ]:
        for m in re.finditer(pattern, raw, flags=re.IGNORECASE):
            if m.group(2).strip():
                terms.append(m.group(2).strip())
    cleaned = re.sub(r"\btrashed\s*=\s*(true|false)", " ", raw, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bmimeType\s*=\s*(['\"])(.*?)\1", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(name|fullText)\s*(=|contains)\s*", " ", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("'", " ").replace('"', " ").replace("(", " ").replace(")", " ")
    cleaned = re.sub(r"\b(AND|OR)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = " ".join(cleaned.split())
    if cleaned:
        terms.append(cleaned)
    # Unique while preserving order.
    out: list[str] = []
    for t in terms:
        if t and t not in out:
            out.append(t)
    return out

def drive_files_list(q: str = "", pageSize: int = 10, fields: str = "files(id,name,mimeType,modifiedTime)") -> dict[str, Any]:
    """List fake Drive files.

    Parameters:
    - q: Concrete file name or search phrase. Simple terms like
      `risk_controls_overview.md`, `project_launch.md`, `q2_budget.md` work.
      Common Drive query forms such as `name = 'risk_controls_overview.md'`,
      `name contains 'risk_controls'`, `fullText contains 'vendor access'`, and
      `trashed = false` are supported or safely tolerated.
    - pageSize: Maximum number of file summaries to return.
    - fields: Accepted for Google Drive API-shape compatibility.
    """
    state = load_state()
    terms = _drive_query_terms(q)
    files = []
    for f in state["drive"]["files"]:
        if f.get("trashed"):
            continue
        hay = f"{f.get('id','')} {f.get('name','')} {f.get('content','')}"
        if not terms or any(_contains(hay, term) for term in terms):
            files.append({k:v for k,v in f.items() if k != "content"})
    return _trace("drive_files_list", {"q":q, "pageSize":pageSize, "fields":fields}, {"files":files[:pageSize]})


def drive_files_get(fileId: str, fields: str = "*") -> dict[str, Any]:
    """Get fake Drive file metadata by id.

    Parameters:
    - fileId: File id returned by drive_files_list, such as file_risk_controls.
    - fields: Metadata fields requested; `*` is accepted for compatibility.
    """
    state = load_state()
    for f in state["drive"]["files"]:
        if f["id"] == fileId:
            return _trace("drive_files_get", {"fileId":fileId, "fields":fields}, {k:v for k,v in f.items() if k != "content"})
    return _trace("drive_files_get", {"fileId":fileId, "fields":fields}, {"error":"notFound"})


def drive_files_export(fileId: str, mimeType: str = "text/plain") -> dict[str, Any]:
    """Export/read fake Drive file content.

    Parameters:
    - fileId: File id returned by drive_files_list.
    - mimeType: Use `text/plain` for the local text content used in these tasks.
    """
    state = load_state()
    for f in state["drive"]["files"]:
        if f["id"] == fileId and not f.get("trashed"):
            return _trace("drive_files_export", {"fileId":fileId, "mimeType":mimeType}, {"mimeType": mimeType, "data": f.get("content", "")})
    return _trace("drive_files_export", {"fileId":fileId, "mimeType":mimeType}, {"error":"notFound"})


def drive_files_create(body: dict[str, Any], media_body: str = "", fields: str = "id,name") -> dict[str, Any]:
    """Create a fake Drive file.

    Parameters:
    - body: File metadata object. Include at least name and optional mimeType/id.
    - media_body: Text content to store in the new fake Drive file.
    - fields: Return fields; accepted for Google Drive API-shape compatibility.
    """
    state = load_state()
    file = {"id": body.get("id") or f"file_created_{len(state['drive']['files'])+1}", "name": body.get("name", "untitled"), "mimeType": body.get("mimeType", "text/plain"), "modifiedTime":"2026-06-05T00:00:00Z", "trashed":False, "content": media_body}
    state["drive"]["files"].append(file)
    commit(state)
    return _trace("drive_files_create", {"body":body, "media_body":media_body[:200], "fields":fields}, {k:v for k,v in file.items() if k != "content"})


def drive_files_delete(fileId: str) -> dict[str, Any]:
    """Trash/delete a fake Drive file by id.

    Parameters:
    - fileId: File id to trash, such as file_strategy.
    """
    state = load_state()
    for f in state["drive"]["files"]:
        if f["id"] == fileId:
            f["trashed"] = True
            commit(state)
            return _trace("drive_files_delete", {"fileId":fileId}, {"status":204, "fileId":fileId})
    return _trace("drive_files_delete", {"fileId":fileId}, {"error":"notFound"})


def slack_conversations_history(channel: str, limit: int = 100, cursor: str | None = None) -> dict[str, Any]:
    """Read recent fake Slack messages from a channel.

    Parameters:
    - channel: Channel name from the user task, e.g. C-project, C-security, or C-travel.
    - limit: Maximum number of recent messages to return.
    - cursor: Optional pagination cursor; usually omitted in these local tasks.
    """
    state = load_state()
    messages = state["slack"]["channels"].get(channel, [])[-limit:]
    return _trace("slack_conversations_history", {"channel":channel, "limit":limit, "cursor":cursor}, {"ok":True, "messages":messages})


def slack_chat_postMessage(channel: str, text: str, blocks: list[dict[str, Any]] | None = None, thread_ts: str | None = None) -> dict[str, Any]:
    """Post a fake Slack message.

    Parameters:
    - channel: Target channel, e.g. C-project, C-security, C-travel, or C-general.
    - text: Message body to post.
    - blocks: Optional Slack blocks; plain text is enough for these tasks.
    - thread_ts: Optional thread timestamp.
    """
    state = load_state()
    msg = {"ts": f"posted_{sum(len(v) for v in state['slack']['channels'].values())+1}", "user":"U-agent", "text":text, "blocks":blocks, "thread_ts":thread_ts}
    state["slack"]["channels"].setdefault(channel, []).append(msg)
    commit(state)
    return _trace("slack_chat_postMessage", {"channel":channel, "text":text, "blocks":blocks, "thread_ts":thread_ts}, {"ok":True, "channel":channel, "ts":msg["ts"], "message":msg})
