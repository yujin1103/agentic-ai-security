"""Tkinter launcher for the AgentDojo-style fake MCP lab.

This GUI is a human-only local control panel. It is not registered as an MCP
server tool and is never visible to the victim AI. It wraps the existing CLI
scripts so a Windows user can run the lab without typing PowerShell commands.
"""
from __future__ import annotations

import atexit
import json
import os
import queue
import subprocess
import signal
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENDPOINT = "http://127.0.0.1:58473/mcp"
MAX_VISIBLE_CASES = 20
FULL_CASE_LOAD_LIMIT = 3000



def _subprocess_env() -> dict[str, str]:
    """Force UTF-8 for child Python processes on Windows.

    Without this, scripts launched from pythonw.exe may write CP949/ANSI bytes
    while the GUI decodes as UTF-8, which produces mojibake in Korean output.
    """
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONLEGACYWINDOWSSTDIO"] = "0"
    return env


def _console_python_executable() -> str:
    """Prefer python.exe over pythonw.exe for CLI scripts with captured stdout."""
    exe = Path(sys.executable)
    if os.name == "nt" and exe.name.lower() == "pythonw.exe":
        candidate = exe.with_name("python.exe")
        if candidate.exists():
            return str(candidate)
    return sys.executable


def _project_python_executable() -> str:
    """Use the project venv Python after [환경 준비], fallback to current Python before it exists."""
    if os.name == "nt":
        venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return _console_python_executable()


def _startupinfo() -> Any:
    if os.name != "nt":
        return None
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return info


def _creationflags() -> int:
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return 0


class LabGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AgentDojo-style MCP Lab Launcher")
        self.geometry("1180x780")
        self.minsize(980, 650)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.cases: list[dict[str, Any]] = []
        self.visible_cases: list[dict[str, Any]] = []
        self.case_by_id: dict[str, dict[str, Any]] = {}
        self.server_proc: subprocess.Popen[str] | None = None
        self._closing = False
        self.python_exe = _project_python_executable()
        self.case_var = tk.StringVar()
        self.case_result_var = tk.StringVar(value="case 목록 미로드")
        self.status_var = tk.StringVar(value="준비됨")
        self.endpoint_var = tk.StringVar(value=DEFAULT_ENDPOINT)
        self.filter_surface_var = tk.StringVar(value="all")
        self.filter_text_var = tk.StringVar()

        self._build_ui()
        self.after(100, self._drain_log_queue)
        self.after(1000, self._poll_server)
        self._log(f"프로젝트 루트: {PROJECT_ROOT}")
        self._log(f"Python 실행 파일: {self.python_exe}")
        self._log("먼저 [환경 준비]를 누르거나, 이미 설치했다면 [case 목록 새로고침]을 누르세요.")

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        top = ttk.Frame(self, padding=8)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="MCP endpoint").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.endpoint_var).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(top, text="URL 복사", command=self.copy_endpoint).grid(row=0, column=2, padx=3)
        ttk.Label(top, textvariable=self.status_var).grid(row=0, column=3, sticky="e", padx=12)

        actions = ttk.LabelFrame(self, text="1. 환경 / 서버", padding=8)
        actions.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        for i in range(9):
            actions.columnconfigure(i, weight=1)
        ttk.Button(actions, text="환경 준비\nuv venv + install", command=self.setup_environment).grid(row=0, column=0, sticky="ew", padx=3)
        ttk.Button(actions, text="MCP 서버 시작", command=self.start_server).grid(row=0, column=1, sticky="ew", padx=3)
        ttk.Button(actions, text="MCP 서버 중지", command=self.stop_server).grid(row=0, column=2, sticky="ew", padx=3)
        ttk.Button(actions, text="전체 검증\nverify_all_cases", command=self.run_verify_all).grid(row=0, column=3, sticky="ew", padx=3)
        ttk.Button(actions, text="lab_env 정리", command=self.clean_lab_env).grid(row=0, column=4, sticky="ew", padx=3)
        ttk.Button(actions, text="로그 지우기", command=self.clear_log).grid(row=0, column=5, sticky="ew", padx=3)

        cases_frame = ttk.LabelFrame(self, text="2. Case 선택 / 준비", padding=8)
        cases_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 6))
        cases_frame.columnconfigure(4, weight=1)
        ttk.Button(cases_frame, text="case 목록 새로고침", command=self.load_cases).grid(row=0, column=0, sticky="ew", padx=3)
        ttk.Label(cases_frame, text="surface").grid(row=0, column=1, sticky="e", padx=(12, 3))
        surface_box = ttk.Combobox(
            cases_frame,
            textvariable=self.filter_surface_var,
            width=12,
            state="readonly",
            values=["all", "mail", "calendar", "drive", "web", "slack", "banking", "travel", "memory"],
        )
        surface_box.grid(row=0, column=2, sticky="ew", padx=3)
        surface_box.bind("<<ComboboxSelected>>", lambda _e: self._refresh_case_combo())
        ttk.Label(cases_frame, text="검색").grid(row=0, column=3, sticky="e", padx=(12, 3))
        search_entry = ttk.Entry(cases_frame, textvariable=self.filter_text_var)
        search_entry.grid(row=0, column=4, sticky="ew", padx=3)
        search_entry.bind("<KeyRelease>", lambda _e: self._refresh_case_combo())
        ttk.Label(cases_frame, textvariable=self.case_result_var).grid(row=0, column=5, columnspan=3, sticky="w", padx=6)
        self.case_combo = ttk.Combobox(cases_frame, textvariable=self.case_var, state="readonly")
        self.case_combo.grid(row=1, column=0, columnspan=5, sticky="ew", padx=3, pady=(8, 0))
        self.case_combo.bind("<<ComboboxSelected>>", lambda _e: self.show_selected_case_info())
        ttk.Button(cases_frame, text="선택 case 준비", command=self.prepare_selected_case).grid(row=1, column=5, sticky="ew", padx=3, pady=(8, 0))
        ttk.Button(cases_frame, text="single-vector 확인", command=self.check_selected_case).grid(row=1, column=6, sticky="ew", padx=3, pady=(8, 0))
        ttk.Button(cases_frame, text="UI용 문장 보기/복사", command=self.show_and_copy_task).grid(row=1, column=7, sticky="ew", padx=3, pady=(8, 0))

        main = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 6))

        left = ttk.Frame(main, padding=0)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        main.add(left, weight=1)
        ttk.Label(left, text="선택 case 정보 / 복사용 user task").grid(row=0, column=0, sticky="w")
        self.case_info = scrolledtext.ScrolledText(left, height=12, wrap=tk.WORD)
        self.case_info.grid(row=1, column=0, sticky="nsew")

        right = ttk.Frame(main, padding=0)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        main.add(right, weight=1)
        ttk.Label(right, text="실행 로그").grid(row=0, column=0, sticky="w")
        self.log_box = scrolledtext.ScrolledText(right, height=12, wrap=tk.WORD)
        self.log_box.grid(row=1, column=0, sticky="nsew")

        bottom = ttk.LabelFrame(self, text="3. 실험 후 평가 / Trace", padding=8)
        bottom.grid(row=4, column=0, sticky="ew", padx=8, pady=(0, 8))
        for i in range(7):
            bottom.columnconfigure(i, weight=1)
        ttk.Button(bottom, text="평가 실행", command=self.evaluate_case).grid(row=0, column=0, sticky="ew", padx=3)
        ttk.Button(bottom, text="Trace 보기", command=self.show_trace).grid(row=0, column=1, sticky="ew", padx=3)
        ttk.Button(bottom, text="lab_env 폴더 열기", command=lambda: self.open_path(PROJECT_ROOT / "lab_env")).grid(row=0, column=2, sticky="ew", padx=3)
        ttk.Button(bottom, text="프로젝트 폴더 열기", command=lambda: self.open_path(PROJECT_ROOT)).grid(row=0, column=3, sticky="ew", padx=3)
        ttk.Button(bottom, text="종료", command=self.on_close).grid(row=0, column=4, sticky="ew", padx=3)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        atexit.register(self._cleanup_server_quiet)
        self._install_signal_handlers()

    # ------------------------------------------------------------------ shutdown helpers
    def _install_signal_handlers(self) -> None:
        """Best-effort cleanup for normal termination signals.

        X button and Alt+F4 are handled by WM_DELETE_WINDOW. These signal
        handlers cover console closes / task termination paths where Python gets
        a signal. Hard power-off or kill -9 style termination cannot be handled
        by any application, but Windows will usually terminate child processes
        during system shutdown.
        """
        def handler(_signum: int, _frame: Any) -> None:
            self._cleanup_server_quiet()
            try:
                self.destroy()
            except Exception:
                pass

        for sig_name in ("SIGINT", "SIGTERM", "SIGBREAK"):
            sig = getattr(signal, sig_name, None)
            if sig is None:
                continue
            try:
                signal.signal(sig, handler)
            except Exception:
                pass

    def _terminate_process_tree(self, proc: subprocess.Popen[str], *, log: bool = True) -> None:
        if proc.poll() is not None:
            return
        if log:
            self._log("MCP 서버 중지 요청")
        try:
            proc.terminate()
            proc.wait(timeout=5)
            return
        except subprocess.TimeoutExpired:
            if log:
                self._log("정상 종료 지연: 프로세스 트리 강제 종료")
        except Exception as exc:
            if log:
                self._log(f"MCP 서버 종료 중 오류: {exc}")

        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    startupinfo=_startupinfo(),
                )
                proc.wait(timeout=5)
                return
            except Exception as exc:
                if log:
                    self._log(f"taskkill 실패: {exc}")
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception as exc:
            if log:
                self._log(f"강제 종료 실패: {exc}")

    def _cleanup_server_quiet(self) -> None:
        proc = getattr(self, "server_proc", None)
        if proc and proc.poll() is None:
            self._terminate_process_tree(proc, log=False)

    # ------------------------------------------------------------------ process helpers
    def _log(self, text: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {text}\n")

    def _drain_log_queue(self) -> None:
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_box.insert(tk.END, msg)
                self.log_box.see(tk.END)
        except queue.Empty:
            pass
        self.after(100, self._drain_log_queue)

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _run_async(self, title: str, cmd: list[str], on_done: Any | None = None) -> None:
        self._log(f"▶ {title}")
        self._log("$ " + " ".join(cmd))
        self._set_status(f"실행 중: {title}")

        def worker() -> None:
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=PROJECT_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=_subprocess_env(),
                    startupinfo=_startupinfo(),
                )
                output_parts: list[str] = []
                assert proc.stdout is not None
                for line in proc.stdout:
                    output_parts.append(line)
                    self.log_queue.put(line)
                rc = proc.wait()
                output = "".join(output_parts)
                self.log_queue.put(f"\n[{title}] 종료 코드: {rc}\n")
                self.after(0, lambda: self._set_status("준비됨" if rc == 0 else f"실패: {title}"))
                if on_done is not None:
                    self.after(0, lambda: on_done(rc, output))
            except FileNotFoundError as exc:
                self.log_queue.put(f"실행 파일을 찾을 수 없음: {exc}\n")
                self.after(0, lambda: self._set_status(f"실패: {title}"))
            except Exception as exc:  # noqa: BLE001 - GUI should show any failure
                self.log_queue.put(f"오류: {exc}\n")
                self.after(0, lambda: self._set_status(f"실패: {title}"))

        threading.Thread(target=worker, daemon=True).start()

    def _python_cmd(self, script: str, *args: str) -> list[str]:
        return [_project_python_executable(), script, *args]

    def _uv_cmd(self, *args: str) -> list[str]:
        return ["uv", *args]

    # ------------------------------------------------------------------ actions
    def setup_environment(self) -> None:
        cmd = self._uv_cmd("venv")

        def after_venv(rc: int, _out: str) -> None:
            if rc != 0:
                messagebox.showerror("환경 준비 실패", "uv venv 실행에 실패했습니다. 로그를 확인하세요.")
                return
            self._run_async("requirements 설치", self._uv_cmd("pip", "install", "-r", "requirements.txt"))

        self._run_async("uv venv", cmd, after_venv)

    def load_cases(self) -> None:
        """Load all cases without streaming the huge JSON into the Tk log widget.

        The old implementation used _run_async(), which echoes every stdout line
        into the GUI log. With --all-variants --json that means thousands of
        lines of JSON are inserted into ScrolledText, causing the window to look
        frozen. This loader captures stdout silently in a worker thread, parses it
        there, then sends only the final case list back to Tk.
        """
        if self.cases:
            self._refresh_case_combo()
            self._log(f"case {len(self.cases)}개는 이미 메모리에 로드됨: 현재 필터만 다시 적용했습니다.")
            self._set_status("준비됨")
            return

        cmd = self._python_cmd("scripts/list_cases.py", "--all-variants", "--limit", str(FULL_CASE_LOAD_LIMIT), "--json")
        self._log("▶ case 목록 로드")
        self._log("$ " + " ".join(cmd) + "  # 출력은 로그창에 표시하지 않음")
        self._set_status("case 목록 로드 중")
        self.case_result_var.set("case 목록 로드 중...")

        def add_search_blobs(cases: list[dict[str, Any]]) -> None:
            fields = (
                "case_id",
                "suite",
                "surface",
                "user_task_id",
                "user_task",
                "injection_surface",
                "injection_task_id",
                "attack_goal_summary",
                "canonical_attack_goal",
                "attack_family_id",
                "attack_family_display",
                "variant_summary",
            )
            for case in cases:
                blob = " ".join(str(case.get(field, "")) for field in fields).lower()
                case["_search_blob"] = blob
                cid = str(case.get("case_id", "")).lower()
                if cid.startswith("case_"):
                    suffix = cid.removeprefix("case_")
                    case["_case_digits"] = suffix
                    case["_search_blob"] += f" {suffix} {suffix.lstrip('0') or '0'}"

        def worker() -> None:
            start = time.perf_counter()
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=PROJECT_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=_subprocess_env(),
                    startupinfo=_startupinfo(),
                    check=False,
                )
                elapsed = time.perf_counter() - start
                if proc.returncode != 0:
                    err = (proc.stderr or proc.stdout or "").strip()
                    if len(err) > 4000:
                        err = err[:4000] + "\n...<truncated>"
                    self.after(0, lambda: self._finish_case_load_error(proc.returncode, elapsed, err))
                    return
                data = json.loads(proc.stdout)
                cases = data.get("cases", [])
                if not isinstance(cases, list):
                    raise ValueError("list_cases.py JSON에 cases 배열이 없습니다.")
                add_search_blobs(cases)
                self.after(0, lambda: self._finish_case_load_success(cases, elapsed))
            except Exception as exc:  # noqa: BLE001 - report GUI loader failure
                elapsed = time.perf_counter() - start
                self.after(0, lambda: self._finish_case_load_exception(elapsed, exc))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_case_load_success(self, cases: list[dict[str, Any]], elapsed: float) -> None:
        self.cases = cases
        self.case_by_id = {str(case.get("case_id", "")).lower(): case for case in self.cases}
        self._refresh_case_combo()
        self._set_status("준비됨")
        self._log(f"case {len(self.cases)}개 로드 완료 ({elapsed:.2f}초): 전체 variant는 메모리에 보관하고 화면에는 최대 {MAX_VISIBLE_CASES}개만 표시합니다.")

    def _finish_case_load_error(self, rc: int, elapsed: float, err: str) -> None:
        self._set_status("case 목록 로드 실패")
        self.case_result_var.set("case 목록 로드 실패")
        self._log(f"case 목록 로드 실패: 종료 코드 {rc}, {elapsed:.2f}초")
        if err:
            self._log(err)

    def _finish_case_load_exception(self, elapsed: float, exc: Exception) -> None:
        self._set_status("case 목록 로드 실패")
        self.case_result_var.set("case 목록 로드 실패")
        self._log(f"case 목록 로드 중 오류 ({elapsed:.2f}초): {exc}")

    def _build_case_search_blobs(self) -> None:
        """Precompute lowercase search text once so filtering all variants stays fast."""
        fields = (
            "case_id",
            "suite",
            "surface",
            "user_task_id",
            "user_task",
            "injection_surface",
            "injection_task_id",
            "attack_goal_summary",
            "canonical_attack_goal",
            "attack_family_id",
            "attack_family_display",
            "variant_summary",
        )
        for case in self.cases:
            blob = " ".join(str(case.get(field, "")) for field in fields).lower()
            case["_search_blob"] = blob
            cid = str(case.get("case_id", "")).lower()
            if cid.startswith("case_"):
                suffix = cid.removeprefix("case_")
                case["_case_digits"] = suffix
                case["_search_blob"] += f" {suffix} {suffix.lstrip('0') or '0'}"

    def _query_case_id_candidates(self, query: str) -> list[str]:
        q = query.strip().lower()
        if not q:
            return []
        candidates: list[str] = []
        if q.startswith("case_"):
            candidates.append(q)
            suffix = q.removeprefix("case_")
            if suffix.isdigit():
                candidates.append(f"case_{suffix.zfill(4)}")
        elif q.isdigit():
            candidates.append(f"case_{q.zfill(4)}")
            candidates.append(f"case_{int(q):04d}")
        # preserve order while removing duplicates
        return list(dict.fromkeys(candidates))

    def _case_matches_query(self, case: dict[str, Any], query: str) -> bool:
        if not query:
            return True
        q = query.lower()
        cid = str(case.get("case_id", "")).lower()
        if cid in self._query_case_id_candidates(q):
            return True
        return all(part in str(case.get("_search_blob", "")) for part in q.split())

    def _case_sort_key(self, case: dict[str, Any], query: str) -> tuple[int, str]:
        """Exact numeric/case_id hits first, then representative variants, then id order."""
        cid = str(case.get("case_id", "")).lower()
        candidates = self._query_case_id_candidates(query)
        exact_rank = 0 if cid in candidates else 1
        variant_rank = 0 if str(case.get("attack_family_id", "")) == "delayed_trigger" and str(case.get("injection_task_id", "")) == "I01" else 1
        if query.strip():
            return (exact_rank, cid)
        return (variant_rank, cid)

    def _refresh_case_combo(self) -> None:
        surface = self.filter_surface_var.get()
        needle = self.filter_text_var.get().strip().lower()
        matched: list[dict[str, Any]] = []
        for case in self.cases:
            if surface != "all" and case.get("surface") != surface:
                continue
            if not self._case_matches_query(case, needle):
                continue
            matched.append(case)
        matched.sort(key=lambda case: self._case_sort_key(case, needle))
        self.visible_cases = matched[:MAX_VISIBLE_CASES]
        values = [self._case_label(case) for case in self.visible_cases]
        self.case_combo["values"] = values
        total = len(matched)
        if total:
            self.case_result_var.set(f"검색 결과 {total}개 중 {len(values)}개 표시")
        else:
            self.case_result_var.set("검색 결과 없음")
        if values:
            if self.case_var.get() not in values:
                self.case_var.set(values[0])
            self.show_selected_case_info()
        else:
            self.case_var.set("")
            self.case_info.delete("1.0", tk.END)

    def _case_label(self, case: dict[str, Any]) -> str:
        return f"{case.get('case_id')} | {case.get('surface')} | {case.get('suite')} | {case.get('user_task_id')} | {case.get('injection_task_id')} | {case.get('attack_family_display')}"

    def _selected_case(self) -> dict[str, Any] | None:
        label = self.case_var.get()
        if not label:
            return None
        case_id = label.split("|")[0].strip().lower()
        case = self.case_by_id.get(case_id)
        if case is not None:
            return case
        for case in self.visible_cases:
            if str(case.get("case_id", "")).lower() == case_id:
                return case
        return None

    def show_selected_case_info(self) -> None:
        case = self._selected_case()
        self.case_info.delete("1.0", tk.END)
        if not case:
            return
        lines = [
            f"case_id: {case.get('case_id')}",
            f"suite: {case.get('suite')}",
            f"surface: {case.get('surface')}",
            f"task_id: {case.get('user_task_id')}",
            f"오염 위치: {case.get('injection_surface')}",
            f"공격 목표 요약: {case.get('attack_goal_summary')}",
            f"표현 방식: {case.get('attack_family_display')}",
            "",
            "[공식 UI에 복사할 사용자 요청]",
            str(case.get("user_task", "")),
        ]
        self.case_info.insert(tk.END, "\n".join(lines))

    def prepare_selected_case(self) -> None:
        case = self._selected_case()
        if not case:
            messagebox.showwarning("case 없음", "먼저 case 목록을 불러오고 case를 선택하세요.")
            return
        self._run_async("case 준비", self._python_cmd("scripts/prepare_case.py", "--case-id", str(case["case_id"])))

    def check_selected_case(self) -> None:
        case = self._selected_case()
        if not case:
            messagebox.showwarning("case 없음", "먼저 case를 선택하세요.")
            return
        self._run_async("single-vector 확인", self._python_cmd("scripts/check_single_vector.py", "--case-id", str(case["case_id"])))

    def show_and_copy_task(self) -> None:
        def on_done(rc: int, output: str) -> None:
            if rc == 0:
                # Prefer the selected case user_task when available. show_task output is also logged.
                case = self._selected_case()
                task = str(case.get("user_task", "")) if case else ""
                if task:
                    self.clipboard_clear()
                    self.clipboard_append(task)
                    self._log("공식 UI용 사용자 요청을 클립보드에 복사했습니다.")
                    self.case_info.delete("1.0", tk.END)
                    self.case_info.insert(tk.END, "[복사 완료]\n" + task)

        self._run_async("사용자 요청 보기", self._python_cmd("scripts/show_task.py"), on_done)

    def start_server(self) -> None:
        if self.server_proc and self.server_proc.poll() is None:
            messagebox.showinfo("서버 실행 중", "MCP 서버가 이미 실행 중입니다.")
            return
        cmd = self._python_cmd("mcp_server.py")
        self._log("▶ MCP 서버 시작")
        self._log("$ " + " ".join(cmd))
        try:
            self.server_proc = subprocess.Popen(
                cmd,
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=_subprocess_env(),
                startupinfo=_startupinfo(),
                creationflags=_creationflags(),
            )
        except FileNotFoundError as exc:
            self._log(f"MCP 서버 시작 실패: {exc}")
            messagebox.showerror("서버 시작 실패", "Python 실행 파일을 찾을 수 없습니다. [환경 준비] 로그를 확인하세요.")
            return

        def reader() -> None:
            assert self.server_proc is not None
            assert self.server_proc.stdout is not None
            for line in self.server_proc.stdout:
                self.log_queue.put(line)
            rc = self.server_proc.wait()
            self.log_queue.put(f"\n[MCP 서버] 종료 코드: {rc}\n")

        threading.Thread(target=reader, daemon=True).start()
        self._set_status("MCP 서버 실행 중")
        self._log(f"MCP endpoint: {self.endpoint_var.get()}")

    def stop_server(self) -> None:
        if not self.server_proc or self.server_proc.poll() is not None:
            self._log("MCP 서버가 실행 중이 아닙니다.")
            self._set_status("준비됨")
            return
        self._terminate_process_tree(self.server_proc, log=True)
        self._set_status("준비됨")

    def _poll_server(self) -> None:
        if self.server_proc and self.server_proc.poll() is None:
            self.status_var.set("MCP 서버 실행 중")
        elif self.status_var.get() == "MCP 서버 실행 중":
            self.status_var.set("준비됨")
        self.after(1000, self._poll_server)

    def evaluate_case(self) -> None:
        self._run_async("평가 실행", self._python_cmd("scripts/evaluate_case.py"))

    def show_trace(self) -> None:
        self._run_async("Trace 보기", self._python_cmd("scripts/show_trace.py", "--limit", "100"))

    def run_verify_all(self) -> None:
        if not messagebox.askyesno("전체 검증", "전체 case 검증은 시간이 걸릴 수 있습니다. 실행할까요?"):
            return
        self._run_async("전체 검증", self._python_cmd("scripts/verify_all_cases.py"))

    def clean_lab_env(self) -> None:
        paths = [
            PROJECT_ROOT / "lab_env" / "current_case.json",
            PROJECT_ROOT / "lab_env" / "state.json",
        ]
        trace_dir = PROJECT_ROOT / "lab_env" / "traces"
        removed = 0
        for path in paths:
            if path.exists():
                path.unlink()
                removed += 1
        if trace_dir.exists():
            for item in trace_dir.glob("*.jsonl"):
                item.unlink()
                removed += 1
        trace_dir.mkdir(parents=True, exist_ok=True)
        (PROJECT_ROOT / "lab_env").mkdir(exist_ok=True)
        self._log(f"lab_env 상태 파일 {removed}개 삭제")

    def copy_endpoint(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.endpoint_var.get())
        self._log("MCP endpoint를 클립보드에 복사했습니다.")

    def open_path(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True) if path.suffix == "" else None
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def clear_log(self) -> None:
        self.log_box.delete("1.0", tk.END)

    def on_close(self) -> None:
        if self._closing:
            return
        self._closing = True
        if self.server_proc and self.server_proc.poll() is None:
            if not messagebox.askyesno("종료", "MCP 서버가 실행 중입니다. 서버를 중지하고 GUI를 닫을까요?"):
                self._closing = False
                return
            self.stop_server()
        self.destroy()


def main() -> None:
    os.chdir(PROJECT_ROOT)
    app = LabGui()
    app.mainloop()


if __name__ == "__main__":
    main()
