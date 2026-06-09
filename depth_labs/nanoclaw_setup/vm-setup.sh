#!/usr/bin/env bash
# =============================================================================
#  NanoClaw 격리 보안랩 — 게스트 VM(Ubuntu) 원샷 셋업 스크립트
#  대상: VMware(또는 VirtualBox/Hyper-V) 위의 Ubuntu 22.04/24.04 LTS 게스트
#  목적: Docker + Node + Ollama + NanoClaw + 공격 툴킷을 한 번에 구성
#
#  실행(게스트 VM 터미널에서, sudo 권한 사용자로):
#      chmod +x vm-setup.sh && ./vm-setup.sh
#
#  [안전] 이 VM은 인가된 격리 보안 연구 전용. 실제 자격증명/계정 연결 금지.
#         공격 전 스냅샷을 찍고, 네트워크는 NAT 또는 host-only 권장.
# =============================================================================
set -euo pipefail

OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:7b-instruct}"   # CPU용. 더 빠르게: llama3.2:3b
NANOCLAW_DIR="${HOME}/nanoclaw"
LAB_DIR="${HOME}/nanoclaw_attack_lab"

say() { printf "\n\033[1;36m=== %s ===\033[0m\n" "$1"; }

# ---------------------------------------------------------------------------
say "0/6  사전 점검"
. /etc/os-release; echo "OS: ${PRETTY_NAME:-?}"
echo "CPU: $(nproc) cores / RAM: $(free -m | awk '/Mem:/{print $2}') MB"
if ! sudo -n true 2>/dev/null; then echo "(sudo 비밀번호를 한 번 물어볼 수 있습니다)"; fi

# ---------------------------------------------------------------------------
say "1/6  기본 패키지 + Docker Engine"
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl git python3 python3-pip jq
# Docker Engine (공식 convenience 스크립트)
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sudo sh
fi
sudo usermod -aG docker "$USER" || true
sudo systemctl enable --now docker || sudo service docker start || true
echo "docker: $(sudo docker --version)"

# ---------------------------------------------------------------------------
say "2/6  Node 20 + pnpm"
if ! command -v node >/dev/null 2>&1 || [ "$(node -v | cut -dv -f2 | cut -d. -f1)" -lt 20 ]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
sudo corepack enable || sudo npm i -g pnpm
echo "node: $(node -v) / pnpm: $(pnpm -v 2>/dev/null || echo MISSING)"

# ---------------------------------------------------------------------------
say "3/6  Ollama 설치 + 모델 pull (CPU)"
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi
# 컨테이너에서 host.docker.internal 로 닿도록 0.0.0.0 바인드
sudo mkdir -p /etc/systemd/system/ollama.service.d
printf '[Service]\nEnvironment="OLLAMA_HOST=0.0.0.0:11434"\n' | \
  sudo tee /etc/systemd/system/ollama.service.d/override.conf >/dev/null
sudo systemctl daemon-reload 2>/dev/null || true
sudo systemctl restart ollama 2>/dev/null || (nohup ollama serve >/tmp/ollama.log 2>&1 &)
sleep 3
echo "모델 pull: ${OLLAMA_MODEL} (수 GB, 시간 걸림)"
ollama pull "${OLLAMA_MODEL}"
echo "설치된 모델:"; ollama list

# ---------------------------------------------------------------------------
say "4/6  NanoClaw 클론 + 호스트 빌드"
if [ ! -d "${NANOCLAW_DIR}" ]; then
  git clone https://github.com/nanocoai/nanoclaw.git "${NANOCLAW_DIR}"
fi
cd "${NANOCLAW_DIR}"
pnpm install --frozen-lockfile
pnpm run build || echo "(build 경고는 무시 가능 — dev 모드로 구동)"

# ---------------------------------------------------------------------------
say "5/6  공격 툴킷 확보"
if [ ! -d "${LAB_DIR}" ]; then
  echo "공격 툴킷(nanoclaw_attack_lab)을 이 VM으로 복사하세요:"
  echo "  - VMware 공유 폴더(/mnt/hgfs/...) 또는 scp 로 ${LAB_DIR} 에 두면 됩니다."
  echo "  - python3 만 있으면 모델/컨테이너 없이도 run_demo.py(오프라인)는 즉시 동작."
else
  echo "툴킷 발견: ${LAB_DIR}"
fi

# ---------------------------------------------------------------------------
say "6/6  완료 — 다음 단계(대화식)"
cat <<'NEXT'

[A] NanoClaw 첫 기동 (새 터미널에서, docker 그룹 적용 위해 재로그인 또는 `newgrp docker`):
      cd ~/nanoclaw
      bash nanoclaw.sh           # 채널 선택에서 'local CLI' 선택(외부 계정 불필요)
      #   자격증명은 OneCLI 대신 .env 방식을 원하면 setup 중 안내 따름

[B] Ollama provider로 전환 (groups/<folder>/container.json):
      "env": { "ANTHROPIC_BASE_URL": "http://host.docker.internal:11434",
               "ANTHROPIC_API_KEY": "ollama", "NO_PROXY": "host.docker.internal" }
      그리고 .claude-shared/settings.json 에 "model": "<위 OLLAMA_MODEL>"
      (docs/ollama.md 참고)

[C] 공격 데모 (터미널 2개):
      python3 ~/nanoclaw_attack_lab/observe_server.py          # 관측 리스너
      python3 ~/nanoclaw_attack_lab/inject.py --db <세션 inbound.db> --payload A2-roleplay
      # 방어 ON:
      python3 ~/nanoclaw_attack_lab/inject.py --db <세션 inbound.db> --payload A2-roleplay --gate

세션 inbound.db 경로: ~/nanoclaw/data/v2-sessions/<agent-group-id>/<session-id>/inbound.db

이 스크립트는 환경/모델/NanoClaw 빌드까지 자동화합니다. [A]~[C]는 대화식이라
한 단계씩 같이 진행하면 됩니다.
NEXT

echo "DONE."
