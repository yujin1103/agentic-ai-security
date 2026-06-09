from __future__ import annotations

from typing import Any

from app.tools.common import _contains, _trace, commit, load_state


def http_get(url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """Fetch an exact indexed URL from the fake web state.

    Parameters:
    - url: Exact URL explicitly present in the user task, such as https://security.example.test/risk-review.
    - headers: Optional request headers; usually omitted.
    """
    state = load_state()
    if url not in state["web"]["pages"]:
        return _trace("http_get", {"url":url, "headers":headers}, {"status_code":403, "text":"Blocked: URL is not available in the page index. No external network request was made."}, blocked=True)
    return _trace("http_get", {"url":url, "headers":headers}, {"status_code":200, "url":url, "text":state["web"]["pages"][url]})


def memory_search(query: str, top_k: int = 5) -> dict[str, Any]:
    """Search saved memory notes.

    Parameters:
    - query: Concrete phrase from the user task, e.g. Risk report rule, Bob Tokyo preference, or Bob's London hotel preference.
    - top_k: Maximum number of matching memories to return.
    """
    state = load_state()
    scored = []
    terms = [t for t in query.casefold().split() if t]
    for doc in state["memory"]["docs"] + state["memory"].get("saved", []):
        text = doc.get("text", "")
        score = sum(1 for t in terms if t in text.casefold())
        if score or not terms:
            scored.append((score, doc))
    scored.sort(key=lambda x: x[0], reverse=True)
    return _trace("memory_search", {"query":query, "top_k":top_k}, {"matches":[{"score":s, **d} for s,d in scored[:top_k]]})


def memory_create(memory: dict[str, Any]) -> dict[str, Any]:
    """Create/save a fake memory note.

    Parameters:
    - memory: Object with text and optional metadata/id fields.
    """
    state = load_state()
    item = {"id": memory.get("id") or f"mem_saved_{len(state['memory'].get('saved', []))+1}", "text": memory.get("text", str(memory)), "metadata": memory.get("metadata", {})}
    state["memory"].setdefault("saved", []).append(item)
    commit(state)
    return _trace("memory_create", {"memory":memory}, item)
