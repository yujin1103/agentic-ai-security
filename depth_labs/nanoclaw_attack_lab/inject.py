"""격리 주입기 — 세션 inbound.db 의 messages_in 에 메시지를 직접 삽입.

NanoClaw의 'Everything is a message' 설계상, 외부 채널 없이도 세션의 inbound.db에
행을 넣으면 컨테이너의 agent-runner가 폴링해 에이전트를 구동한다. 이것이
'완전 로컬 격리 주입' 벡터다. (스키마는 src/db/schema.ts INBOUND_SCHEMA 검증본)

선택적으로 --gate 를 주면 review_gate를 통과시켜(방어 ON) 차단/살균 후 삽입한다.

사용:
  # 방어 없음(공격): 페이로드를 그대로 주입
  python inject.py --db <inbound.db경로> --payload A1-direct

  # 방어 있음: 게이트 통과 후 주입
  python inject.py --db <inbound.db경로> --payload A1-direct --gate

  # (오프라인 테스트용) 빈 inbound.db 생성 + 스키마 + 주입
  python inject.py --db ./results/sandbox/inbound.db --payload A1-direct --bootstrap

  # (라이브 DB 직접 기록 — 비가역) --i-understand 필수, 자동 .bak 백업 생성
  python inject.py --db <라이브 inbound.db> --payload A1-direct --i-understand

스키마 검증 기준: nanoclaw src/db/schema.ts INBOUND_SCHEMA + src/db/session-db.ts
insertMessage (series_id=id, idx_messages_in_series 인덱스, content 는 flat 모양).
"""
from __future__ import annotations
import argparse
import json
import shutil
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import config
import payloads
import review_gate

# 검증된 INBOUND_SCHEMA (src/db/schema.ts) 의 messages_in 부분 — bootstrap 전용.
# schema.ts 와 동일하게 series_id 컬럼 + idx_messages_in_series 인덱스를 포함한다.
MESSAGES_IN_DDL = """
CREATE TABLE IF NOT EXISTS messages_in (
  id TEXT PRIMARY KEY, seq INTEGER UNIQUE, kind TEXT NOT NULL, timestamp TEXT NOT NULL,
  status TEXT DEFAULT 'pending', process_after TEXT, recurrence TEXT, series_id TEXT,
  tries INTEGER DEFAULT 0, trigger INTEGER NOT NULL DEFAULT 1, platform_id TEXT,
  channel_type TEXT, thread_id TEXT, content TEXT NOT NULL, source_session_id TEXT,
  on_wake INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_messages_in_series ON messages_in(series_id);
"""


def next_even_seq(con: sqlite3.Connection) -> int:
    row = con.execute("SELECT MAX(seq) FROM messages_in").fetchone()
    maxseq = row[0] or 0
    return ((maxseq // 2) + 1) * 2  # 호스트는 짝수 seq 사용


def inject(db_path: str, text: str, sender: str = "ExternalSender") -> dict:
    con = sqlite3.connect(db_path)
    try:
        seq = next_even_seq(con)
        msg_id = f"inject-{uuid.uuid4().hex[:12]}"
        # content 모양: 실제 채널이 기록하는 flat 형태(text/sender/senderId)를
        # 최상위에 둔다(session-db.ts insertMessage 가 받는 content 와 정합).
        # author 는 무해한 추가 필드로 유지만 한다.
        content = json.dumps({
            "text": text,
            "sender": sender,
            "senderId": "memory:attacker",
            "author": {"fullName": sender, "userName": sender.lower()},
        }, ensure_ascii=False)
        # session-db.ts insertMessage 는 series_id = id 로 INSERT 한다(스키마 인덱스 대상).
        con.execute(
            """INSERT INTO messages_in
               (id, seq, kind, timestamp, status, trigger, content, series_id, on_wake)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (msg_id, seq, "chat", datetime.now(timezone.utc).isoformat(),
             "pending", 1, content, msg_id, 0),
        )
        con.commit()
        return {"id": msg_id, "seq": seq}
    finally:
        con.close()


def main():
    ap = argparse.ArgumentParser(description="NanoClaw 격리 주입기")
    ap.add_argument("--db", required=True, help="세션 inbound.db 경로")
    ap.add_argument("--payload", default="A1-direct", help="payloads.py 의 id")
    ap.add_argument("--sender", default="ExternalSender")
    ap.add_argument("--gate", action="store_true", help="review_gate(방어) 통과 후 주입")
    ap.add_argument("--bootstrap", action="store_true",
                    help="inbound.db 없으면 스키마 생성(오프라인 테스트용)")
    ap.add_argument("--i-understand", action="store_true", dest="i_understand",
                    help="라이브(비-bootstrap) DB에 비가역 기록함을 명시 확인. "
                         "지정 시 INSERT 전에 <db>.bak.<ts> 백업을 만든다.")
    args = ap.parse_args()

    p = payloads.by_id(args.payload)
    text = p["text"]
    print(f"[payload] {p['id']} ({p['level']}) — {p['desc']}")

    if args.gate:
        v = review_gate.review(text)
        print(f"[gate] action={v.action} score={v.score} reasons={v.reasons}")
        if v.action == "block":
            print("[gate] 차단됨 → inbound.db 에 기록하지 않음. (방어 성공: 에이전트가 보지 못함)")
            return
        if v.action == "sanitize":
            text = v.sanitized_text
            print(f"[gate] 살균됨 → 기록할 텍스트: {text!r}")

    db = Path(args.db)
    if args.bootstrap:
        db.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(db))
        con.executescript(MESSAGES_IN_DDL)
        con.commit()
        con.close()
    if not db.exists():
        print(f"[오류] inbound.db 없음: {db}\n  → 라이브 세션 경로를 주거나 --bootstrap 사용.",
              file=sys.stderr)
        sys.exit(1)

    # 라이브 DB 안전장치: bootstrap 이 아닌 기존 DB에 비가역 기록할 때는
    # --i-understand 를 강제하고, INSERT 전에 타임스탬프 백업을 만든다.
    if not args.bootstrap:
        if not args.i_understand:
            print(f"[거부] '{db}' 는 라이브 inbound.db 로 보입니다. 여기에 직접 기록하면",
                  file=sys.stderr)
            print("       되돌릴 수 없습니다. 의도가 맞다면 --i-understand 를 붙이세요.",
                  file=sys.stderr)
            print("       (격리 테스트라면 --bootstrap 으로 빈 DB를 만드세요.)",
                  file=sys.stderr)
            sys.exit(2)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        bak = db.with_name(db.name + f".bak.{ts}")
        shutil.copy2(str(db), str(bak))
        print(f"[백업] INSERT 전 스냅샷 생성: {bak}")

    res = inject(str(db), text, args.sender)
    print(f"[주입 완료] id={res['id']} seq={res['seq']} → {db}")
    print("  컨테이너 agent-runner가 다음 폴링에서 이 메시지를 읽어 에이전트를 구동합니다.")


if __name__ == "__main__":
    main()
