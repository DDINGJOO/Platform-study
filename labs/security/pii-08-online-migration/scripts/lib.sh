# 공통 함수. scripts/*.sh 가 source 한다.
set -euo pipefail
LAB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$LAB"
export LAB_KEY="bGFiLW9ubHkta2V5LWZvci1waWktMDgtbWlncmF0biE="   # 실습 전용 32바이트 키
export LAB_DB_PORT=38080
CP="build:lib/mysql-connector-j-9.1.0.jar"
ST="$LAB/state"; OUT="$LAB/out"
mkdir -p "$ST/pids" "$ST/logs" "$OUT"

sql()   { docker compose exec -T mysql mysql -ulab -plabpass --default-character-set=utf8mb4 lab "$@" 2>/dev/null; }
phase() { echo "$1" > "$ST/phase"; echo "  [phase] $1"; }

# 앱 버전 = 읽기 컨버터 + 쓰기 스위치
#   v0      plain   / plain    암호화 없는 원래 코드
#   v1      lenient / plain    읽기만 두 형식을 받는다
#   v2      lenient / encrypt  쓰기 암호화를 켠다
#   v2-off  lenient / plain    v2 인데 쓰기 스위치가 읽히지 않은 인스턴스 (1편의 상황) / 되돌릴 때 쓰기를 끈 판
#   v3      strict  / encrypt  암호문만 읽는다
ver_args() {
  case "$1" in
    v0) echo "--read plain --write plain" ;;
    v1) echo "--read lenient --write plain" ;;
    v2) echo "--read lenient --write encrypt" ;;
    v2-off) echo "--read lenient --write plain" ;;
    v3) echo "--read strict --write encrypt" ;;
  esac
}

start_inst() {   # start_inst <port> <version>
  local port=$1 ver=$2
  # shellcheck disable=SC2046
  java -Xmx192m -cp "$CP" Lab serve --port "$port" --label "$ver" $(ver_args "$ver") > "$ST/logs/$port.log" 2>&1 &
  echo $! > "$ST/pids/$port"
  for _ in $(seq 1 100); do
    curl -sf "http://127.0.0.1:$port/health" >/dev/null 2>&1 && break
    sleep 0.1
  done
  echo "  [start] $(head -1 "$ST/logs/$port.log")"
}

stop_inst() {    # stop_inst <port>  : 자기 PID 파일로만 끈다
  local port=$1
  if [ -f "$ST/pids/$port" ]; then
    kill "$(cat "$ST/pids/$port")" 2>/dev/null || true
    wait "$(cat "$ST/pids/$port")" 2>/dev/null || true
    rm -f "$ST/pids/$port"
  fi
}

pool_set() { printf '%s\n' "$@" > "$ST/pool.tmp"; mv "$ST/pool.tmp" "$ST/pool"; }   # "port:version:pid" ...
entry()    { echo "$1:$2:$(cat "$ST/pids/$1")"; }   # entry <port> <version>
pool_get() { cat "$ST/pool"; }

# 롤링 배포: 한 대씩 새 버전을 띄워 풀에 넣고, 두 버전이 함께 받는 시간을 둔 뒤 옛 대를 뺀다
#   rolling <새 버전> <섞이는 초>  (풀에 있는 대수만큼 반복)
rolling() {
  local newv=$1 mix=$2
  local olds; olds=$(pool_get)
  for old in $olds; do
    local oport=${old%%:*} nport
    for nport in $(seq 38081 38089); do pool_get | grep -q "^$nport:" || [ -f "$ST/pids/$nport" ] || break; done
    start_inst "$nport" "$newv"
    pool_set $(pool_get) "$nport:$newv:$(cat "$ST/pids/$nport")"
    sleep "$mix"
    pool_set $(pool_get | grep -v "^$oport:")
    sleep 1                       # 이미 보낸 요청이 끝나기를 기다린다
    stop_inst "$oport"
  done
}

stop_all() { for f in "$ST"/pids/*; do [ -e "$f" ] && stop_inst "$(basename "$f")"; done; return 0; }

reset_db() {
  sql < sql/schema.sql
  sql < sql/seed.sql
  sql -N -e "SELECT COUNT(*) FROM agent"
}

batch() { java -Xmx256m -cp "$CP" Lab batch "$@"; }

load_start() {   # load_start <이름>
  python3 scripts/loadgen.py --state "$ST" --out "$OUT/$1-req.csv" --expected "$ST/expected.jsonl" > "$OUT/$1-load.log" 2>&1 &
  echo $! > "$ST/load.pid"
  sleep 1
}
load_stop() {
  touch "$ST/stop"
  wait "$(cat "$ST/load.pid")" 2>/dev/null || true
  rm -f "$ST/stop" "$ST/load.pid"
}
