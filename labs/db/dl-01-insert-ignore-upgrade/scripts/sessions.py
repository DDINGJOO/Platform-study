#!/usr/bin/env python3
"""세션 서너 개를 mysql 클라이언트로 열어 두고, 정해진 순서로 한 문장씩 보내며
단계마다 performance_schema.data_locks 를 찍는다. 표준 라이브러리만 쓴다.

  python3 scripts/sessions.py <시나리오> <RR|RC> [first_visit|first_visit_pk]
  python3 scripts/sessions.py list

세션은 `docker compose exec -T mysql mysql ...` 프로세스 하나씩이다. 문장을 보낸 뒤
WAIT 초를 기다리고, 그동안 끝나지 않은 문장은 잠금을 기다리는 중이라고 본다.
"""
import os
import re
import subprocess
import sys
import threading
import time

WAIT = float(os.environ.get("WAIT", "1.0"))
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MYSQL = ["docker", "compose", "exec", "-T", "-e", "MYSQL_PWD=labroot", "mysql",
         "mysql", "-uroot", "lab"]
ISO = {"RR": "REPEATABLE READ", "RC": "READ COMMITTED"}
TABLES = ("first_visit", "first_visit_pk")   # (가) 대리 키 + 보조 유니크, (나) member_id 가 기본 키

INS = "INSERT IGNORE INTO {t} (member_id) VALUES ({m});"
SFU = "SELECT member_id, visit_count FROM {t} WHERE member_id = {m} FOR UPDATE;"
SEL = "SELECT member_id, visit_count FROM {t} WHERE member_id = {m};"
UPD = "UPDATE {t} SET visit_count = visit_count + 1 WHERE member_id = {m};"

# (설명, 미리 넣을 member_id 목록, 세션 수, 단계 목록)
# 단계: (세션 번호, SQL)  세션 번호는 1부터. SQL 의 {m} 은 대상 member_id(=1)
SCENARIOS = {
    "exists-2s": (
        "행이 이미 있다. 두 세션이 INSERT IGNORE 후 같은 행을 SELECT ... FOR UPDATE",
        [1], 2,
        [(1, "BEGIN;"), (2, "BEGIN;"),
         (1, INS), (2, INS),
         (1, SFU), (2, SFU),
         (1, "COMMIT;"), (2, "COMMIT;")]),
    "exists-2s-update": (
        "행이 이미 있다. 두 세션이 INSERT IGNORE 후 같은 행을 UPDATE",
        [1], 2,
        [(1, "BEGIN;"), (2, "BEGIN;"),
         (1, INS), (2, INS),
         (1, UPD), (2, UPD),
         (1, "COMMIT;"), (2, "COMMIT;")]),
    "absent-3s-commit": (
        "행이 없다. 세 세션이 INSERT IGNORE, 먼저 넣은 S1 이 COMMIT, 나머지가 SELECT ... FOR UPDATE",
        [], 3,
        [(1, "BEGIN;"), (2, "BEGIN;"), (3, "BEGIN;"),
         (1, INS), (2, INS), (3, INS),
         (1, "COMMIT;"),
         (2, SFU), (3, SFU),
         (2, "COMMIT;"), (3, "COMMIT;")]),
    "absent-3s-rollback": (
        "행이 없다. 세 세션이 INSERT IGNORE, 먼저 넣은 S1 이 ROLLBACK (그 뒤 아무 문장도 없다)",
        [], 3,
        [(1, "BEGIN;"), (2, "BEGIN;"), (3, "BEGIN;"),
         (1, INS), (2, INS), (3, INS),
         (1, "ROLLBACK;"),
         (2, "COMMIT;"), (3, "COMMIT;")]),
    "absent-2s-commit": (
        "대조군: 행이 없다. 두 세션만 INSERT IGNORE, 먼저 넣은 S1 이 COMMIT, S2 가 FOR UPDATE",
        [], 2,
        [(1, "BEGIN;"), (2, "BEGIN;"),
         (1, INS), (2, INS),
         (1, "COMMIT;"),
         (2, SFU), (2, "COMMIT;")]),
    "absent-2s-rollback": (
        "대조군: 행이 없다. 두 세션만 INSERT IGNORE, 먼저 넣은 S1 이 ROLLBACK",
        [], 2,
        [(1, "BEGIN;"), (2, "BEGIN;"),
         (1, INS), (2, INS),
         (1, "ROLLBACK;"), (2, "COMMIT;")]),
    "other-member": (
        "곁가지: 행이 있다. S1 의 중복 INSERT IGNORE 가 끝나기 전에 S2 가 다른 회원(member_id=2)을 넣는다",
        [1], 2,
        [(1, "BEGIN;"), (2, "BEGIN;"),
         (1, INS), (2, INS.replace("{m}", "2")),
         (1, "COMMIT;"), (2, "COMMIT;")]),
    "fix-forupdate-first": (
        "고친 판: 행이 이미 있다. INSERT IGNORE 없이 SELECT ... FOR UPDATE 로 X 부터 잡는다",
        [1], 2,
        [(1, "BEGIN;"), (2, "BEGIN;"),
         (1, SFU), (2, SFU),
         (1, UPD), (1, "COMMIT;"),
         (2, UPD), (2, "COMMIT;")]),
    "fix-nolock-read": (
        "고친 판: 행이 이미 있다. INSERT IGNORE 다음 잠그지 않는 SELECT 로 읽는다",
        [1], 2,
        [(1, "BEGIN;"), (2, "BEGIN;"),
         (1, INS), (2, INS),
         (1, SEL), (2, SEL),
         (1, "COMMIT;"), (2, "COMMIT;")]),
    "fix-commit-first": (
        "고친 판: 행이 이미 있다. INSERT IGNORE 를 따로 커밋해 S 를 놓은 뒤 새 트랜잭션에서 FOR UPDATE",
        [1], 2,
        [(1, "BEGIN;"), (2, "BEGIN;"),
         (1, INS), (2, INS),
         (1, "COMMIT;"), (2, "COMMIT;"),
         (1, "BEGIN;"), (2, "BEGIN;"),
         (1, SFU), (2, SFU),
         (1, UPD), (1, "COMMIT;"),
         (2, UPD), (2, "COMMIT;")]),
    "absent-forupdate-first": (
        "참고(6편): 행이 없다. 두 세션이 SELECT ... FOR UPDATE 먼저, 그다음 INSERT",
        [], 2,
        [(1, "BEGIN;"), (2, "BEGIN;"),
         (1, SFU), (2, SFU),
         (1, INS), (2, INS),
         (1, "COMMIT;"), (2, "COMMIT;")]),
}


def sh(sql, table=True):
    args = MYSQL + (["--table"] if table else ["-N", "-B"]) + ["-e", sql]
    return subprocess.run(args, cwd=HERE, capture_output=True, text=True).stdout


class Session:
    def __init__(self, name, iso):
        self.name = name
        self.lines = []
        self.seen = 0
        self.p = subprocess.Popen(
            MYSQL + ["--unbuffered", "--force", "--table", "-vvv"], cwd=HERE,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1)
        threading.Thread(target=self._read, daemon=True).start()
        self.send(f"SET SESSION TRANSACTION ISOLATION LEVEL {ISO[iso]};")
        self.send("SELECT CONNECTION_ID() AS conn;")
        deadline = time.time() + 20
        self.conn = None
        while self.conn is None and time.time() < deadline:
            for ln in list(self.lines):
                m = re.match(r"\|\s+(\d+)\s+\|", ln)
                if m:
                    self.conn = int(m.group(1))
            time.sleep(0.1)
        self.seen = len(self.lines)

    def _read(self):
        for ln in self.p.stdout:
            self.lines.append(ln.rstrip("\n"))

    def send(self, sql):
        self.p.stdin.write(sql + "\n")
        self.p.stdin.flush()

    def new_output(self):
        out = self.lines[self.seen:]
        self.seen = len(self.lines)
        # -vvv 가 찍는 구분선과 빈 줄, 문장 되풀이는 빼고 결과만 남긴다
        keep = [l for l in out if l and not l.startswith("-----") and not l.startswith("Bye")]
        return keep

    def close(self):
        try:
            self.p.stdin.close()
        except Exception:
            pass
        self.p.wait(timeout=20)


def locks(sessions):
    # data_locks 문서: ENGINE_TRANSACTION_ID 는 "the owner of the lock" 으로 볼 수 있고,
    # THREAD_ID 는 "the session that created the lock" 이다. 실제로 THREAD_ID 로 붙였을 때
    # S1 이 넣은 새 행의 X 잠금이 S2 이름으로 찍혔다. 그래서 트랜잭션 ID 로 세션을 찾는다.
    case = " ".join(f"WHEN {s.conn} THEN '{s.name}'" for s in sessions)
    return sh(f"""
SELECT CASE x.trx_mysql_thread_id {case} ELSE '?' END AS sess,
       l.INDEX_NAME AS idx, l.LOCK_MODE AS mode, l.LOCK_STATUS AS status, l.LOCK_DATA AS data
FROM performance_schema.data_locks l
LEFT JOIN information_schema.INNODB_TRX x ON x.trx_id = l.ENGINE_TRANSACTION_ID
WHERE l.LOCK_TYPE = 'RECORD'
ORDER BY sess, l.INDEX_NAME, l.LOCK_MODE;""").rstrip() or "(레코드 잠금 없음)"


def deadlocks():
    return int(sh("SELECT COUNT FROM information_schema.INNODB_METRICS "
                  "WHERE NAME='lock_deadlocks';", table=False).strip() or 0)


def run(name, iso, table):
    desc, seed, n, steps = SCENARIOS[name]
    sh(f"TRUNCATE {table};")
    for m in seed:
        sh(f"INSERT INTO {table} (member_id) VALUES ({m});")
    before = deadlocks()
    print(f"### {name} / {iso} / {table}")
    print(f"# {desc}")
    print(f"# 미리 넣은 행: member_id={seed or '없음'}")
    ss = [Session(f"S{i + 1}", iso) for i in range(n)]
    errors = {}
    for i, (who, sql) in enumerate(steps, 1):
        s = ss[who - 1]
        stmt = sql.format(m=1, t=table)
        s.send(stmt)
        time.sleep(WAIT)
        print(f"\n[{i:02d}] {s.name}> {stmt}")
        for t in ss:
            out = t.new_output()
            body = [l for l in out if l.strip() != stmt.strip()]
            for l in body:
                print(f"     {t.name} | {l}")
                if "ERROR 1213" in l:
                    errors.setdefault(t.name, f"@{i:02d}")
            if t is s and not body:
                print(f"     {t.name} | (아직 끝나지 않음: 잠금 대기)")
        if not stmt.startswith("BEGIN"):
            print("     data_locks:")
            for l in locks(ss).splitlines():
                print("       " + l)
    for s in ss:
        s.close()
    after = deadlocks()
    rows = sh(f"SELECT * FROM {table} ORDER BY member_id;")
    print("\n최종 행:")
    print(rows.rstrip() or "(없음)")
    victims = ",".join(f"{k}{v}" for k, v in sorted(errors.items())) or "없음"
    nrows = max(0, len([l for l in rows.splitlines() if l.startswith("|")]) - 1)
    print(f"\nRESULT {name} {iso} {table} 1213={victims} lock_deadlocks+={after - before} rows={nrows}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "list":
        for k, v in SCENARIOS.items():
            print(f"{k:24s} {v[0]}")
        sys.exit(0)
    run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "RR",
        sys.argv[3] if len(sys.argv) > 3 else TABLES[0])
