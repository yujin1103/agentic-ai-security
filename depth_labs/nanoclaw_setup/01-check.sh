#!/usr/bin/env bash
# Ubuntu(WSL2) 환경 점검 — NanoClaw 사전 요구사항
set -u
echo "=== versions ==="
for c in node npm pnpm git curl python3 docker; do
  if command -v "$c" >/dev/null 2>&1; then
    printf "%-8s %s\n" "$c" "$("$c" --version 2>&1 | head -1)"
  else
    printf "%-8s MISSING\n" "$c"
  fi
done

echo "=== docker daemon reachable from Ubuntu? ==="
if command -v docker >/dev/null 2>&1; then
  docker info --format "server={{.ServerVersion}}" 2>&1 | head -3
else
  echo "docker CLI not on PATH inside Ubuntu (Docker Desktop WSL integration likely OFF)"
fi

echo "=== mem (MB) ==="
free -m | awk '/Mem:/{print $2" total / "$7" available"}'

echo "=== apt nodejs candidate ==="
apt-cache policy nodejs 2>/dev/null | sed -n '1,3p'

echo "=== /mnt/e visible? ==="
ls -d /mnt/e/ad_project >/dev/null 2>&1 && echo "yes: /mnt/e/ad_project" || echo "no"
