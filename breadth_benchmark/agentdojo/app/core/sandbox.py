from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAB_ROOT = PROJECT_ROOT / "lab_env"
OUTPUT_ROOT = PROJECT_ROOT / "outputs"

class SandboxError(ValueError):
    pass

def ensure_lab_dirs() -> None:
    for p in [LAB_ROOT, LAB_ROOT / "traces", OUTPUT_ROOT]:
        p.mkdir(parents=True, exist_ok=True)

def resolve_lab_path(*parts: str | Path, must_exist: bool = False) -> Path:
    ensure_lab_dirs()
    candidate = LAB_ROOT.joinpath(*[str(p) for p in parts]).resolve(strict=False)
    root = LAB_ROOT.resolve(strict=False)
    if candidate != root and root not in candidate.parents:
        raise SandboxError(f"Path escapes lab_env: {candidate}")
    if must_exist and not candidate.exists():
        raise FileNotFoundError(str(candidate))
    return candidate

def reset_lab_root() -> None:
    ensure_lab_dirs()
    for child in LAB_ROOT.iterdir():
        if child.is_dir():
            import shutil
            shutil.rmtree(child)
        else:
            child.unlink()
    ensure_lab_dirs()
