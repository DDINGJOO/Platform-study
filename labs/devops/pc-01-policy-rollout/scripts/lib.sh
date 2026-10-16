# 공통 함수. 다른 스크립트가 source 한다.
LAB=$(cd "$(dirname "$0")/.." && pwd)
cd "$LAB"
GRADLE_IMG=gradle:9.8.1-jdk21

mark() { printf '%.3f %s\n' "$(python3 -c 'import time;print(time.time())')" "$*" >> "$MARKS"; echo "[$(date +%T)] $*"; }

# 스타터를 빌드해 repo/ 에 낸다. publish_starter <버전> <정책이름> <시도 수> <타임아웃ms>
publish_starter() {
  docker run --rm -v "$LAB/starter:/src" -v "$LAB/repo:/repo" -v pc01-gradle:/root/.gradle-cache \
    -e GRADLE_USER_HOME=/root/.gradle-cache -w /src $GRADLE_IMG \
    gradle publish --no-daemon -q -Pversion="$1" -PpolicyName="$2" -PmaxAttempts="$3" -PtimeoutMs="$4" -PrepoDir=/repo
}

# 서비스 이미지 하나. build_svc <svcN> <스타터 버전>
build_svc() {
  docker build -q -f app/Dockerfile --build-arg SVC="$1" --build-arg STARTER_VERSION="$2" \
    --build-arg BUILD_ID="${BUILD_ID:-0}" -t "pc01/$1:$2" . >/dev/null
}

# 포트가 /work 에 200 또는 502 로 답할 때까지(앱이 떴다) 기다린다
wait_up() {
  for _ in $(seq 1 600); do
    c=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$1/policy" || true)
    [ "$c" = 200 ] && return 0
    sleep 0.1
  done
  echo "port $1 not up" >&2; return 1
}
