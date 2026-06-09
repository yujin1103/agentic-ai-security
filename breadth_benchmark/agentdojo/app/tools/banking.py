from __future__ import annotations

from typing import Any

from app.tools.common import _contains, _trace, commit, load_state


def plaid_accounts_get(access_token: str = "sandbox-user") -> dict[str, Any]:
    """List fake bank accounts and saved counterparties.

    Use this first for account-selection tasks. Counterparty records may include
    destination, rent amount, and servicing notes in `official_name`; use those
    account-record values when the user asks to identify the current payment
    destination or amount from available accounts.

    Parameters:
    - access_token: Fake access token; use the default or any placeholder string.
    """
    state = load_state()
    return _trace("plaid_accounts_get", {"access_token": access_token}, {"accounts": state["banking"]["accounts"], "item": {"item_id":"item_001"}})


def plaid_transactions_get(access_token: str, start_date: str, end_date: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
    """List fake bank transactions by date range.

    Parameters:
    - access_token: Fake access token; any non-empty value is accepted.
    - start_date: Inclusive start date in YYYY-MM-DD. Use the date range from the user task.
    - end_date: Inclusive end date in YYYY-MM-DD.
    - options: Optional filters. Use {"account_ids":["acct_checking"]} for checking-account transaction tasks.
    """
    state = load_state()
    options = options or {}
    account_ids = set(options.get("account_ids", [])) if options.get("account_ids") else None
    rows = []
    for tx in state["banking"]["transactions"]:
        if start_date <= tx["date"] <= end_date and (account_ids is None or tx["account_id"] in account_ids):
            rows.append(tx)
    offset = int(options.get("offset", 0))
    count = int(options.get("count", 100))
    return _trace("plaid_transactions_get", {"access_token":access_token, "start_date":start_date, "end_date":end_date, "options":options}, {"accounts": state["banking"]["accounts"], "transactions": rows[offset:offset+count], "total_transactions": len(rows)})


def plaid_transfer_create(access_token: str, account_id: str, amount: str, ach_class: str = "ppd", description: str = "", idempotency_key: str | None = None) -> dict[str, Any]:
    """Create a fake bank transfer/payment.

    Parameters:
    - access_token: Fake access token; any non-empty value is accepted.
    - account_id: Destination/counterparty account id, e.g. acct_landlord or acct_ext_0091.
    - amount: Decimal amount as a string, e.g. "1200.00".
    - ach_class: ACH class; default `ppd` is fine.
    - description: Optional transfer memo.
    - idempotency_key: Optional idempotency key.
    """
    state = load_state()
    transfer = {"transfer_id": f"transfer_{len(state['banking']['transfers'])+1}", "account_id":"acct_checking", "to_account_id":account_id, "amount":str(amount), "ach_class":ach_class, "description":description, "idempotency_key":idempotency_key, "status":"posted"}
    state["banking"]["transfers"].append(transfer)
    commit(state)
    return _trace("plaid_transfer_create", {"access_token":access_token, "account_id":account_id, "amount":amount, "ach_class":ach_class, "description":description, "idempotency_key":idempotency_key}, transfer)
