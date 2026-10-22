#!/usr/bin/env python3
"""오픈소스 PR·이슈를 개인 Notion 「오픈소스 PR」 DB 와 맞춘다.

    oss_tracker.py init <부모 페이지 ID>   # DB 를 만들고 ID 를 로컬 설정에 적는다 (최초 1회)
    oss_tracker.py sync [--dry]            # gh 로 내 PR·이슈를 읽어 행을 추가·갱신한다
    oss_tracker.py stale [--days N]        # 리뷰 없이 N일(기본 5) 지난 열린 PR 을 보여 준다

토큰과 DB ID 는 저장소에 두지 않는다. 토큰은 notion-sync 의 Keychain 항목, DB ID 는
~/.claude/notion-sync/state/oss-tracker.json 에 둔다.
스크립트는 상태·날짜·마지막 활동만 쓴다. 다음 행동·기록·회고 글 칸은 사람이 쓰는 칸이라 건드리지 않는다.
"""
import argparse, importlib.machinery, importlib.util, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

GH_USER = "DDINGJOO"
CONF = Path.home() / ".claude/notion-sync/state/oss-tracker.json"
PROJECTS_DB = "9a2313e2-be5b-8268-9cfb-0197785a9a84"   # 개인 「프로젝트 관리」
# 검색에서 먼저 빼는 업무·개인·스터디 저장소 소유자(검색 상한 200 을 피하려고)
SKIP_OWNERS = {"DDINGJOO", "meengi07", "Language-Study-Prooject"}  # 업무 조직명은 로컬 설정 skip_owners 에 둔다
# 마지막 활동자는 사람만 센다. 봇 코멘트는 리뷰가 아니다
BOTS = {"github-actions", "chatgpt-codex-connector", "copilot-pull-request-reviewer", "otelbot", "keycloak-github-bot", "Copilot"}
# owner/repo -> 「프로젝트 관리」의 저장소별 하위 행 이름
PROJECT_OF = {
    "open-telemetry/opentelemetry-java-instrumentation": "OpenTelemetry Java",
    "spinnaker/spinnaker": "Spinnaker",
    "debezium/debezium": "Debezium", "debezium/dbz": "Debezium",
    "antlr/grammars-v4": "ANTLR grammars-v4",
    "redis/lettuce": "Lettuce",
    "keycloak/keycloak": "Keycloak",
    "spring-projects/spring-boot": "Spring Boot",
    "spring-projects/spring-batch": "Spring Batch",
    "spring-cloud/spring-cloud-config": "Spring Cloud Config",
    "spring-projects/spring-ai": "Spring AI",
    "spring-projects/spring-security": "Spring Security",
    "micrometer-metrics/micrometer": "Micrometer",
    "resilience4j/resilience4j": None,   # 프로젝트 행 없이 추적만
}
# 실제로 담는 것은 PROJECT_OF 에 있는 저장소뿐이다(허용 목록). 2026-10-22 제외 목록만 썼다가
# 스터디 저장소 PR 371건이 들어갔다. 새 오픈소스 저장소에 기여하면 여기에 먼저 추가한다.


def notion():
    p = Path.home() / ".claude/notion-sync/bin/nsync"
    loader = importlib.machinery.SourceFileLoader("nsync", str(p))
    spec = importlib.util.spec_from_loader("nsync", loader)
    m = importlib.util.module_from_spec(spec); loader.exec_module(m)
    return m.notion


def gh(*args):
    env = dict(os.environ, GH_TOKEN=subprocess.run(["gh", "auth", "token", "--user", GH_USER],
                                                   capture_output=True, text=True, check=True).stdout.strip())
    return json.loads(subprocess.run(["gh", *args], capture_output=True, text=True, check=True, env=env).stdout)


def txt(s): return [{"type": "text", "text": {"content": str(s)[:2000]}}]
def day(s): return {"date": {"start": s[:10]}} if s else {"date": None}


def init(parent):
    N = notion()
    sel = lambda *o: {"select": {"options": [{"name": x} for x in o]}}
    db = N("databases", "POST", {
        "parent": {"type": "page_id", "page_id": parent},
        "title": txt("오픈소스 PR"),
        "properties": {
            "제목": {"title": {}},
            "종류": sel("PR", "이슈"),
            "상태": sel("리뷰 필요", "변경 요청", "승인", "열림", "머지", "닫힘"),
            "저장소": {"rich_text": {}},
            "번호": {"number": {}},
            "링크": {"url": {}},
            "프로젝트": {"relation": {"database_id": PROJECTS_DB, "single_property": {}}},
            "열린 날": {"date": {}},
            "종료일": {"date": {}},
            "마지막 활동": {"date": {}},
            "마지막 활동자": {"rich_text": {}},
            "다음 행동": {"rich_text": {}},
            "기록": {"rich_text": {}},
            "회고 글": {"rich_text": {}},
        }})
    CONF.write_text(json.dumps({"db": db["id"]}, ensure_ascii=False))
    print("DB", db["id"], db.get("url"))


def project_ids(N):
    out, cur = {}, None
    while True:
        body = {"page_size": 100, **({"start_cursor": cur} if cur else {})}
        r = N(f"databases/{PROJECTS_DB}/query", "POST", body)
        for p in r["results"]:
            out["".join(t["plain_text"] for t in p["properties"]["프로젝트명"]["title"])] = p["id"]
        if not r.get("has_more"): return out
        cur = r["next_cursor"]


def items():
    """내가 연 오픈소스 PR·이슈. 상태와 마지막 활동은 상세 조회로 채운다."""
    fields = "repository,number,title,url,state,createdAt,closedAt,isPullRequest"
    for kind in ("prs", "issues"):
        # 업무 저장소의 PR 이 수백 건이라 검색 상한(200)에 걸린다. 소유자를 검색어에서 뺀다
        extra = json.loads(CONF.read_text()).get("skip_owners", []) if CONF.exists() else []
        q = [f"-owner:{o}" for o in sorted(SKIP_OWNERS | set(extra))]
        for it in gh("search", kind, "--author", GH_USER, "--limit", "200", "--json", fields, "--", *q):
            repo = it["repository"]["nameWithOwner"]
            if repo not in PROJECT_OF or (kind == "issues" and it.get("isPullRequest")):
                continue
            yield kind, repo, it


def detail(kind, repo, it):
    n = str(it["number"])
    if kind == "prs":
        d = gh("pr", "view", n, "-R", repo, "--json", "state,reviewDecision,mergedAt,closedAt,comments,reviews,isDraft")
        acts = [(c["createdAt"], c["author"]["login"]) for c in d["comments"]] + \
               [(r["submittedAt"], r["author"]["login"]) for r in d["reviews"] if r.get("submittedAt")]
        if d["state"] == "MERGED": st = "머지"
        elif d["state"] == "CLOSED": st = "닫힘"
        else: st = {"APPROVED": "승인", "CHANGES_REQUESTED": "변경 요청"}.get(d["reviewDecision"] or "", "리뷰 필요")
        end = d["mergedAt"] or d["closedAt"]
    else:
        d = gh("issue", "view", n, "-R", repo, "--json", "state,closedAt,comments")
        acts = [(c["createdAt"], c["author"]["login"]) for c in d["comments"]]
        st = "열림" if d["state"] == "OPEN" else "닫힘"
        end = d["closedAt"]
    acts = [a for a in acts if a[1] not in BOTS and not a[1].endswith("[bot]")]
    last = max(acts) if acts else (it["createdAt"], GH_USER)
    return st, end, last


def sync(dry):
    N = notion(); db = json.loads(CONF.read_text())["db"]
    rows = {}
    cur = None
    while True:
        r = N(f"databases/{db}/query", "POST", {"page_size": 100, **({"start_cursor": cur} if cur else {})})
        for p in r["results"]:
            rows[p["properties"]["링크"]["url"]] = p
        if not r.get("has_more"): break
        cur = r["next_cursor"]
    pid = project_ids(N)
    for kind, repo, it in items():
        st, end, (last_at, last_by) = detail(kind, repo, it)
        props = {
            "제목": {"title": txt(it["title"])},
            "종류": {"select": {"name": "PR" if kind == "prs" else "이슈"}},
            "상태": {"select": {"name": st}},
            "저장소": {"rich_text": txt(repo)},
            "번호": {"number": it["number"]},
            "링크": {"url": it["url"]},
            "열린 날": day(it["createdAt"]),
            "종료일": day(end),
            "마지막 활동": day(last_at),
            "마지막 활동자": {"rich_text": txt(last_by)},
        }
        proj = PROJECT_OF.get(repo)
        if proj in pid:
            props["프로젝트"] = {"relation": [{"id": pid[proj]}]}
        old = rows.get(it["url"])
        tag = "update" if old else "new"
        if old and old["properties"]["상태"]["select"] and old["properties"]["상태"]["select"]["name"] == st \
                and (old["properties"]["마지막 활동"]["date"] or {}).get("start") == last_at[:10]:
            tag = "same"
        print(f"{tag:6} {st:6} {repo}#{it['number']}  last {last_at[:10]} {last_by}" + ("" if proj else "  (프로젝트 매핑 없음)"))
        if dry or tag == "same": continue
        if old: N(f"pages/{old['id']}", "PATCH", {"properties": props})
        else: N("pages", "POST", {"parent": {"database_id": db}, "properties": props})


def stale(days):
    now = datetime.now(timezone.utc)
    for kind, repo, it in items():
        if kind != "prs" or it["state"] != "open": continue
        st, _, (last_at, last_by) = detail(kind, repo, it)
        age = (now - datetime.fromisoformat(last_at.replace("Z", "+00:00"))).days
        if age >= days and last_by == GH_USER:
            print(f"{age:3}일  {st:6} {repo}#{it['number']}  {it['title'][:60]}")


def prune():
    """허용 목록에 없는 저장소의 행을 보관 처리한다."""
    N = notion(); db = json.loads(CONF.read_text())["db"]; cur = None; n = 0
    while True:
        r = N(f"databases/{db}/query", "POST", {"page_size": 100, **({"start_cursor": cur} if cur else {})})
        for p in r["results"]:
            repo = "".join(t["plain_text"] for t in p["properties"]["저장소"]["rich_text"])
            if repo not in PROJECT_OF:
                N(f"pages/{p['id']}", "PATCH", {"archived": True}); n += 1
        if not r.get("has_more"): break
        cur = r["next_cursor"]
    print("archived", n)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").add_argument("parent")
    sub.add_parser("sync").add_argument("--dry", action="store_true")
    sub.add_parser("stale").add_argument("--days", type=int, default=5)
    sub.add_parser("prune")
    a = ap.parse_args()
    {"init": lambda: init(a.parent), "sync": lambda: sync(a.dry), "stale": lambda: stale(a.days), "prune": prune}[a.cmd]()
