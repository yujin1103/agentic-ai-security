"""Small import-only smoke demo.

This is not the main experiment and not a ground-truth runner. It simply proves that
fake API tools and evaluation work without subprocesses. The official UI + MCP flow
should let the AI choose these tools itself.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.envs.seeder import prepare_case
from app.tools.workspace import graph_me_messages, graph_me_message_get, graph_me_sendMail
from app.evaluation.evaluator import evaluate_current_case

prepare_case('case_0001')
found = graph_me_messages(search='Alice meeting', top=5)
msg_id = found['value'][0]['id']
msg = graph_me_message_get(msg_id)
graph_me_sendMail({
    'subject': 'Meeting summary',
    'body': {'contentType':'Text', 'content':'Summary: launch blockers are vendor review, budget signoff, and Tokyo travel dates.'},
    'toRecipients': [{'emailAddress': {'address':'dana@example.com'}}]
})
print(json.dumps(evaluate_current_case().to_dict(), ensure_ascii=False, indent=2))
