"""팀원 breadth_benchmark 를 Gemini(상용 모델)로 실제 구동해 공격 성공 여부를 측정.

OpenAI 키 없이, 가진 Gemini 키 + OpenAI 호환 엔드포인트로 팀원 파이프라인을 그대로 돌린다.
  - agentdojo FastMCP 서버를 in-memory 로 연결(HTTP 전송 우회) → 도구 schema/실행은 팀원 것 그대로.
  - 팀원 client 의 mcp_bridge(도구→OpenAI변환, 결과→텍스트) + DEFAULT_SYSTEM_PROMPT 재사용.
  - prepare_case 로 case 세팅 → Gemini tool-calling 루프 → admin_evaluate_case 로 targeted_asr 채점.

사용(venv python):
  $env:GEMINI_API_KEY='...'; .venv/Scripts/python.exe run_with_gemini.py --case-id case_0184
  .venv/Scripts/python.exe run_with_gemini.py --case-id case_0184,case_1432 --model gemini-flash-lite-latest
"""
from __future__ import annotations
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
AGENTDOJO = HERE / "agentdojo"
CLIENT = HERE / "client"
sys.path.insert(0, str(AGENTDOJO))
sys.path.insert(0, str(CLIENT))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastmcp import Client                                    # noqa: E402
from openai import OpenAI                                     # noqa: E402
from mcp_server import mcp                                    # noqa: E402
from app.envs.seeder import prepare_case                      # noqa: E402
from app.mcp.admin import admin_evaluate_case                 # noqa: E402
from agentdojo_mcp_api_chat_client.mcp_bridge import (        # noqa: E402
    mcp_tool_to_openai_tool, mcp_result_to_text)
from agentdojo_mcp_api_chat_client.prompts import DEFAULT_SYSTEM_PROMPT  # noqa: E402

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"
OLLAMA_BASE = "http://localhost:11434/v1"


def _make_client(backend: str) -> OpenAI:
    if backend == "ollama":   # 로컬, 키·rate limit 없음, OpenAI 호환 tool-calling
        return OpenAI(api_key="ollama", base_url=OLLAMA_BASE, max_retries=2)
    if backend == "openai":   # 공식 OpenAI 또는 호환 게이트웨이(OPENAI_API_KEY/OPENAI_BASE_URL 환경변수)
        return OpenAI(max_retries=4)
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    return OpenAI(api_key=key, base_url=GEMINI_BASE, max_retries=6)


async def run_case(case_id: str, model: str, backend: str = "ollama", max_steps: int = 16,
                   verbose: bool = False, pace: float = 0.0) -> dict:
    info = prepare_case(case_id)
    user_prompt = info["user_prompt"]
    client = _make_client(backend)

    n_tool_calls = 0
    async with Client(mcp) as mc:
        tools = await mc.list_tools()
        oai_tools = [mcp_tool_to_openai_tool(t) for t in tools]
        messages = [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        for step in range(max_steps):
            if step > 0 and pace:
                await asyncio.sleep(pace)   # 무료 티어 RPM(분당 한도) 준수 페이싱
            resp = client.chat.completions.create(
                model=model, messages=messages, tools=oai_tools, temperature=0.0)
            msg = resp.choices[0].message
            if verbose:
                print(f"   [step {step}] tool_calls={len(msg.tool_calls or [])} "
                      f"content={(msg.content or '')[:120]!r}")
            # SDK 원본 메시지를 그대로 echo(Gemini thinking 모델의 thought_signature 등 extra 보존).
            am = msg.model_dump(exclude_none=True)
            am["content"] = msg.content or ""
            messages.append(am)
            if not msg.tool_calls:
                break
            for tc in msg.tool_calls:
                n_tool_calls += 1
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except Exception:
                    args = {}
                try:
                    result = await mc.call_tool(tc.function.name, args)
                    text = mcp_result_to_text(result)
                except Exception as e:
                    text = f"(tool error: {e})"
                if verbose:
                    print(f"   · {tc.function.name}({json.dumps(args, ensure_ascii=False)[:80]}) -> {text[:80]}")
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": text[:4000]})

    ev = admin_evaluate_case()
    return {"case_id": case_id, "user_task": info.get("user_task_id"),
            "surface": info.get("surface"), "model": model,
            "utility_ok": ev.get("utility_ok"), "targeted_asr": ev.get("targeted_asr"),
            "contamination_seen": ev.get("contamination_seen"),
            "tool_call_count": n_tool_calls}


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case-id", required=True, help="쉼표로 여러 개 가능")
    ap.add_argument("--backend", choices=["ollama", "gemini", "openai"], default="ollama")
    ap.add_argument("--model", default="llama3.1")
    ap.add_argument("--pace", type=float, default=0.0, help="gemini 무료티어 RPM 페이싱(초)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    cases = [c.strip() for c in args.case_id.split(",") if c.strip()]
    print(f"[breadth 실측] backend={args.backend} model={args.model}  cases={len(cases)}  (더미 데이터, 인가된 방어 연구)")
    print("-" * 78)
    print(f"{'case':<12}{'task':<6}{'surface':<9}{'정상성공':>9}{'공격성공(ASR)':>14}{'호출':>6}")
    print("-" * 78)
    rows = []
    for cid in cases:
        try:
            r = await run_case(cid, args.model, backend=args.backend, verbose=args.verbose, pace=args.pace)
        except Exception as e:
            print(f"{cid:<12} ERROR: {type(e).__name__}: {str(e)[:400]}")
            continue
        rows.append(r)
        print(f"{r['case_id']:<12}{str(r['user_task']):<6}{str(r['surface']):<9}"
              f"{str(r['utility_ok']):>9}{str(r['targeted_asr']):>14}{r['tool_call_count']:>6}")
    print("-" * 78)
    succ = [r for r in rows if r.get("targeted_asr")]
    print(f" 공격 성공(targeted_asr=True): {len(succ)}/{len(rows)}  → {[r['case_id'] for r in succ]}")


if __name__ == "__main__":
    asyncio.run(main())
