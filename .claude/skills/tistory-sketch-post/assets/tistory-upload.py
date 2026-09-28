#!/usr/bin/env python3
"""notion/**/*.html 을 티스토리에 올린다 — 오픈 API 가 2024-02 에 닫혀 브라우저를 조작한다.

    tistory-upload.py login                 # 창을 띄워 사람이 로그인한다 (최초 1회, 만료 시)
    tistory-upload.py plan                  # 무엇을 올릴지 보여 준다. 아무것도 쓰지 않는다
    tistory-upload.py reorder [--apply]     # 이미 만든 글 번호를 발행 순서대로 재배정 (매니페스트만)
    tistory-upload.py sync [--limit N] [--only 경로조각] [--update-linked] [--visibility private|public]

상태는 저장소의 두 파일이 전부다.
  tistory-series.json    폴더 -> 제목 접두어·카테고리·titles(파일명 -> 제목 덮어쓰기)·skip(올리지 않음).
                         제목 = "접두어 " + 파일명(번호_ 뒤). 파일명을 못 바꿀 때 titles 로 고친다
  tistory-manifest.json  경로 -> 글 번호·제목·카테고리·내용 해시. 하나라도 다르면 수정, 없으면 새 글.
                         그래서 제목(파일명·접두어)이나 카테고리를 나중에 바꿔도 같은 글이 고쳐진다.
                         sha256 이 null 인 항목은 손으로 올린 글을 짝지어 둔 것이다.
                         내용이 저장소와 다를 수 있어 --update-linked 없이는 건드리지 않는다.

새 글은 기본 비공개로 저장한다. 공개 발행은 사람이 한다.
기존 글을 수정할 때는 공개 범위를 건드리지 않는다.

틀리기 쉬운 두 가지 (둘 다 겉으로는 성공처럼 보인다):
  - TSSESSION 은 세션 쿠키라 브라우저를 닫으면 사라진다. state.json 에 저장했다가 매번 복원한다.
  - CodeMirror.setValue() 로 넣으면 화면만 바뀌고 **빈 본문으로 저장된다.**
    포커스 후 keyboard.insert_text 로 넣어야 한다. 그래서 저장 뒤 글 페이지를 열어 검증한다.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from urllib.parse import quote
from datetime import datetime, timezone
from pathlib import Path

BLOG = "https://dding-shark.tistory.com"
HOME = Path.home() / ".local/share/tistory-uploader"
PROFILE, STATE = HOME / "profile", HOME / "state.json"
MASK_EXTRA = Path.home() / ".config/blog-mask.txt"
ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "notion"
SERIES = ROOT / "tistory-series.json"
MANIFEST = ROOT / "tistory-manifest.json"
MASK_CHECK = ROOT / ".claude/skills/blog-post-pipeline/assets/mask-check.py"
CM = "[...document.querySelectorAll('.CodeMirror')].find(e => e.offsetParent)"
RADIO = {"private": "#open0", "protected": "#open15", "public": "#open20"}
EXIT_RELOGIN = 3
EXIT_DAILY_LIMIT = 4  # 티스토리는 하루 새 글 50개까지. 초과하면 post.json 이 403 과 안내문을 준다


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rel(p):
    return p.relative_to(ROOT).as_posix()


def load_json(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def save_manifest(m):
    MANIFEST.write_text(json.dumps(dict(sorted(m.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def title_of(path, series):
    """제목 = titles 덮어쓰기 > "접두어 " + 파일명(번호_ 뒤).
    접두어는 파일명이 "N편"·"번외" 로 시작할 때만 붙인다. "Micrometer 1편" 처럼
    하위 시리즈 이름으로 시작하는 파일에 상위 시리즈 이름을 겹쳐 붙이지 않기 위해서다."""
    conf = series.get(rel(path.parent), {})
    stem = re.sub(r"^\d+[a-z]?_", "", path.stem)
    if stem in conf.get("titles", {}):
        return conf["titles"][stem]
    prefix = conf.get("prefix")
    return f"{prefix} {stem}" if prefix and re.match(r"(\d+편|번외)", stem) else stem


def order_key(files):
    """발행 순서 = 처음 커밋된 날짜. 단 같은 시리즈 안에서는 번호가 날짜보다 우선한다.
    (여러 편을 한 커밋에 넣거나 번호와 다른 순서로 커밋한 시리즈가 있다)
    티스토리는 발행일을 과거로 되돌릴 수 없으므로, 목록 순서는 만드는 순서로만 정해진다."""
    first = {}
    for f in files:
        out = subprocess.run(["git", "log", "--follow", "--diff-filter=A", "--format=%aI", "--", str(f)],
                             cwd=ROOT, capture_output=True, text=True).stdout.split()
        first[f] = out[-1] if out else "9999"
    key = {}
    for d in {f.parent for f in files}:
        latest = ""
        for f in sorted(x for x in files if x.parent == d):
            latest = max(latest, first[f])
            key[f] = (latest, rel(f))
    return key


def plan(series, manifest, update_linked=False):
    """(동작, 경로, 제목, 해시, 기존 항목) 목록. 동작: new / update / rename / skip-linked."""
    files = [f for f in SRC.rglob("*.html") if not series.get(rel(f.parent), {}).get("skip")]
    key = order_key(files)
    files.sort(key=key.get)
    present = {rel(f) for f in SRC.rglob("*.html")}
    orphans = {e["sha256"]: k for k, e in manifest.items() if k not in present and e.get("sha256")}
    # 짝지어 둔 글(해시 없음)의 파일이 사라졌다면 이름이 바뀐 것일 수 있다. 해시가 없어
    # 새 파일과 이어 줄 수 없으므로, 그대로 두면 새 글로 중복 발행된다. 사람이 매니페스트 키를 고칠 때까지 막는다.
    lost = [k for k, e in manifest.items() if k not in present and e.get("sha256") is None]
    if lost:
        sys.exit("짝지어 둔 글의 파일이 없다. 이름을 바꿨다면 tistory-manifest.json 의 키를 새 경로로 고칠 것:\n  "
                 + "\n  ".join(lost))
    out = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        h, key, title = sha(text), rel(f), title_of(f, series)
        category = series.get(rel(f.parent), {}).get("category")
        entry = manifest.get(key)
        if entry is None:
            if h in orphans:
                out.append(("rename", f, title, h, (orphans[h], manifest[orphans[h]])))
            else:
                out.append(("new", f, title, h, None))
        elif entry.get("sha256") is None:
            out.append(("update" if update_linked else "skip-linked", f, title, h, (key, entry)))
        elif entry["sha256"] != h or entry.get("title") != title or entry.get("category") != category:
            out.append(("update", f, title, h, (key, entry)))
    return sorted(out, key=lambda r: r[0] == "new")  # 안정 정렬: 순서는 유지하고 수정을 앞으로


def mask_ok(path):
    if not MASK_EXTRA.exists():
        sys.exit(f"조직 목록({MASK_EXTRA})이 없어 마스킹 검사를 할 수 없다. 올리지 않는다.")
    r = subprocess.run([sys.executable, str(MASK_CHECK), str(path), "--extra", str(MASK_EXTRA),
                        "--allow", str(ROOT / ".mask-allow")], capture_output=True, text=True)
    if r.returncode:
        print(r.stdout)
    return r.returncode == 0


def expected(html):
    body = re.sub(r"<(style|script)\b.*?</\1>", "", html, flags=re.S)
    body = re.sub(r"<svg\b.*?</svg>", "", body, flags=re.S)
    text = re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", body))
    return html.count("<svg"), len(text)


# ---------------------------------------------------------------- 브라우저

def open_ctx(p, headless=True):
    ctx = p.chromium.launch_persistent_context(str(PROFILE), channel="chrome", headless=headless)
    if STATE.exists():
        ctx.add_cookies(json.loads(STATE.read_text())["cookies"])
    return ctx


def keep_state(ctx):
    ctx.storage_state(path=str(STATE))
    STATE.chmod(0o600)


def on_dialog(d):
    # "…에 저장된 글이 있습니다" 를 수락하면 예전 임시저장본이 비동기로 복원되며 넣은 본문을 덮는다.
    # 본문은 매번 새로 넣으므로 복원은 거절한다. 모드 변경 확인 등 나머지는 수락한다.
    if "저장된 글" in d.message:
        d.dismiss()
    else:
        d.accept()


def ensure_login(page):
    page.goto(f"{BLOG}/manage/newpost/")
    page.wait_for_load_state("networkidle")
    if "auth/login" not in page.url:
        return
    # 카카오 간편로그인이 살아 있으면 버튼 한 번으로 돌아온다
    page.get_by_text("카카오계정으로 로그인").first.click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)
    page.goto(f"{BLOG}/manage/newpost/")
    page.wait_for_load_state("networkidle")
    if "auth/login" in page.url or "kakao.com" in page.url:
        print(f"재로그인 필요: {sys.argv[0]} login", file=sys.stderr)
        sys.exit(EXIT_RELOGIN)


def pick_category(page, path_name):
    """'상위/하위' 이름으로 카테고리를 고른다. 목록에서 하위는 '- 이름' 으로 나온다."""
    if not path_name:
        return
    page.click("#category-btn")
    page.wait_for_timeout(500)
    items = page.evaluate("() => [...document.querySelectorAll('[id^=category-item-]')].map(e => [e.id, e.innerText.trim()])")
    parent, full = None, {}
    for id_, label in items:
        if label.startswith("- "):
            full[f"{parent}/{label[2:]}"] = id_
        else:
            parent = label
            full[label] = id_
    if path_name not in full:
        sys.exit(f"티스토리에 카테고리 '{path_name}' 가 없다. 먼저 만들거나 tistory-series.json 을 고칠 것.")
    page.click(f"#{full[path_name]}")


def cm_value(page):
    return page.evaluate(f"() => {CM}.CodeMirror.getValue()")


def fill_editor(page, html):
    """본문을 키보드 입력으로 넣는다.

    기존 글을 열면 원래 본문이 모드 전환 뒤에 비동기로 늦게 들어와 넣은 내용을 덮는다.
    그래서 에디터 값이 1초간 변하지 않을 때까지 기다린 뒤 전체를 바꾸고, 다르면 다시 한다."""
    for attempt in range(3):
        prev, still = None, 0
        for _ in range(20):
            page.wait_for_timeout(500)
            cur = cm_value(page)
            still = still + 1 if cur == prev else 0
            prev = cur
            if still >= 2:
                break
        page.evaluate(f"() => {{ const c = {CM}.CodeMirror; c.focus(); c.execCommand('selectAll') }}")
        page.keyboard.insert_text(html)
        for _ in range(20):
            page.wait_for_timeout(500)
            if cm_value(page) == html:
                return
    import difflib
    got = cm_value(page)
    diff = list(difflib.unified_diff(html.splitlines(), got.splitlines(), lineterm="", n=0))[:12]
    raise RuntimeError(f"에디터에 넣은 내용이 원문과 다르다 ({len(got)}/{len(html)}자)\n" + "\n".join(l[:160] for l in diff))


def write_post(page, html, title, category, post_id=None, visibility="private"):
    url = f"{BLOG}/manage/newpost/{post_id}?type=post&returnURL=ENTRY" if post_id else f"{BLOG}/manage/newpost/"
    page.goto(url)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)
    if post_id and f"/newpost/{post_id}" not in page.url:
        # 삭제된 글이면 "잘못된 요청이거나 삭제된 글입니다" 후 빈 새 글 화면으로 튕긴다.
        # 여기서 계속 쓰면 새 글이 엉뚱한 순서로 생기므로 멈춘다
        sys.exit(f"/{post_id} 가 없다(삭제됨?). tistory-manifest.json 에서 이 번호를 빼거나 reorder 할 것")
    page.click("#editor-mode-layer-btn-open")
    page.click("#editor-mode-html")  # 모드 변경 confirm 은 dialog 핸들러가 수락한다
    page.wait_for_timeout(1000)
    page.fill("#post-title-inp", title)
    pick_category(page, category)
    fill_editor(page, html)
    page.click("#publish-layer-btn")
    page.wait_for_timeout(1200)
    # 발행 창의 기본값은 그 글의 현재 공개 범위가 아니라 직전에 저장한 설정일 때가 있다.
    # 그래서 수정할 때도 항상 명시적으로 고른다 (한 번 비공개 글 9편이 공개로 저장됐다)
    page.check(RADIO[visibility])
    page.wait_for_timeout(300)
    page.check(RADIO[visibility])
    page.click("#publish-btn")
    try:
        page.wait_for_url(lambda u: "/manage/newpost" not in u, timeout=30000)
    except Exception:
        shot = HOME / "last-failure.png"
        page.screenshot(path=str(shot))
        toast = page.evaluate("() => [...document.querySelectorAll('[class*=toast],[class*=alert],[class*=layer_]')].map(e => e.innerText.trim()).filter(Boolean).join(' | ')")
        raise RuntimeError(f"저장 후 화면이 넘어가지 않았다. 화면: {shot}  메시지: {toast[:300]}")
    m = re.search(r"tistory\.com/(\d+)$", page.url)
    return m.group(1) if m else None


def find_post_id(page, title, tries=1):
    """관리 목록에서 제목이 정확히 같은 글의 번호. 저장 직후에는 목록 반영이 늦어 여러 번 본다."""
    for n in range(tries):
        if n:
            page.wait_for_timeout(3000)
        page.goto(f"{BLOG}/manage/posts/?searchKeyword={quote(title)}&searchType=title&visibility=all")
        page.wait_for_load_state("networkidle")
        ids = page.evaluate("""t => [...document.querySelectorAll('a')]
            .filter(a => /tistory\\.com\\/\\d+$/.test(a.href) && a.innerText.trim() === t)
            .map(a => +a.href.split('/').pop())""", title)
        if ids:
            return str(max(ids))
    return None


def current_visibility(page, post_id):
    page.goto(f"{BLOG}/{post_id}")
    page.wait_for_load_state("networkidle")
    v = page.evaluate("() => document.querySelector('[data-entry-visibility]')?.dataset.entryVisibility")
    return {"private": "private", "protected": "protected", "public": "public"}.get(v)


def verify(page, post_id, html, visibility):
    want_svg, want_len = expected(html)
    got_vis = current_visibility(page, post_id)
    if got_vis != visibility:
        return False, f"공개 범위가 {got_vis} 다 (목표 {visibility})"
    got = page.evaluate("""() => { const a = document.querySelector('.contents_style');
        if (!a) return null;
        const c = a.cloneNode(true); c.querySelectorAll('svg,style,script').forEach(e => e.remove());
        return { svg: a.querySelectorAll('svg').length, len: c.innerText.replace(/\\s+/g, '').length } }""")
    if not got:
        return False, "본문 영역을 못 찾았다"
    ok = got["svg"] == want_svg and got["len"] >= 0.9 * want_len
    return ok, f"svg {got['svg']}/{want_svg} · 글자 {got['len']}/{want_len}"


# ---------------------------------------------------------------- 명령

def cmd_login(_):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = open_ctx(p, headless=False)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://www.tistory.com/auth/login")
        print("창에서 로그인할 것. 카카오 화면에서 '간편로그인 정보 저장'을 체크하면 만료 시 자동 복구된다.")
        deadline = time.time() + 600
        while time.time() < deadline:
            if any(c["name"] == "TSSESSION" for c in ctx.cookies("https://www.tistory.com")):
                page.goto(f"{BLOG}/manage")
                page.wait_for_load_state("networkidle")
                if "/manage" in page.url and "login" not in page.url:
                    keep_state(ctx)
                    print("로그인 저장됨")
                    ctx.close()
                    return
            time.sleep(3)
        sys.exit("10분 안에 로그인하지 않았다")


def cmd_plan(a):
    series, manifest = load_json(SERIES, {}), load_json(MANIFEST, {})
    rows = plan(series, manifest, a.update_linked)
    for act, f, title, _, _ in rows:
        print(f"{act:12} {title}   [{rel(f.parent)}]")
    counts = {}
    for r in rows:
        counts[r[0]] = counts.get(r[0], 0) + 1
    print("\n" + (" · ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "올릴 것 없음"))
    missing = sorted({rel(f.parent) for _, f, *_ in rows if rel(f.parent) not in series})
    if missing:
        print("tistory-series.json 에 없는 폴더(접두어 없이 파일명만 제목이 된다):", *missing, sep="\n  ")


def cmd_sync(a):
    from playwright.sync_api import sync_playwright
    series, manifest = load_json(SERIES, {}), load_json(MANIFEST, {})
    rows = [r for r in plan(series, manifest, a.update_linked) if r[0] != "skip-linked"]
    if a.only:
        rows = [r for r in rows if a.only in rel(r[1])]
    rows = rows[: a.limit] if a.limit else rows
    if not rows:
        print("올릴 것 없음")
        return
    failed = 0
    with sync_playwright() as p:
        ctx = open_ctx(p)
        page = ctx.new_page()
        page.on("dialog", on_dialog)
        refused = []

        def on_response(r):
            if r.url.endswith("/manage/post.json") and r.status >= 400:
                try:
                    refused.append(r.text()[:200])
                except Exception:
                    refused.append(f"HTTP {r.status}")
        page.on("response", on_response)
        ensure_login(page)
        for i, (act, f, title, h, prev) in enumerate(rows):
            if i:
                time.sleep(a.interval)
            key, html = rel(f), f.read_text(encoding="utf-8")
            if not mask_ok(f):
                print(f"✗ 마스킹 검사 실패, 건너뜀: {key}")
                failed += 1
                continue
            post_id = prev[1]["id"] if prev else None
            if not post_id:
                # 앞선 실행이 저장 후 멈췄다면 글은 이미 있다. 다시 만들지 않고 그 글을 고친다
                post_id = find_post_id(page, title)
                if post_id in {e["id"] for e in manifest.values()}:
                    sys.exit(f"같은 제목의 글 /{post_id} 가 이미 다른 파일에 배정돼 있다. 매니페스트를 확인할 것: {title}")
                if post_id:
                    act = "adopt"
            category = series.get(rel(f.parent), {}).get("category")
            visibility = (prev[1].get("visibility") if prev else None) or \
                (current_visibility(page, post_id) if post_id else a.visibility)
            print(f"… {act} {title}" + (f" (/{post_id})" if post_id else ""))
            try:
                got = write_post(page, html, title, category, post_id, visibility)
            except RuntimeError:
                if refused:
                    print(f"✗ 티스토리가 저장을 거부했다: {refused[-1]}")
                    ctx.close()
                    sys.exit(EXIT_DAILY_LIMIT if "최대" in refused[-1] else 1)
                raise
            post_id = post_id or got or find_post_id(page, title, tries=5)
            if not post_id:
                print("✗ 저장 후 글 번호를 못 찾았다. 중복을 막기 위해 여기서 멈춘다.")
                sys.exit(1)
            ok, detail = verify(page, post_id, html, visibility)
            if act == "rename":
                manifest.pop(prev[0], None)
            # 검증 실패여도 글은 이미 있으므로 번호는 기록한다. 해시를 비워 다음 sync 에서 다시 쓰게 한다.
            manifest[key] = {"id": post_id, "title": title, "category": category, "visibility": visibility,
                             "sha256": h if ok else "",
                             "synced_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            save_manifest(manifest)
            keep_state(ctx)
            print(f"{'✓' if ok else '✗ 검증 실패'} /{post_id}  {detail}")
            failed += not ok
        ctx.close()
    sys.exit(1 if failed else 0)


def cmd_reorder(a):
    """이미 만든 글(짝지은 글 제외)의 번호를 발행 순서대로 다시 배정한다.
    번호가 작은 글에 순서가 앞선 파일을 넣는다. 남는 파일은 다음 sync 가 순서대로 새로 만든다.
    매니페스트만 바꾼다. 실제 글 내용은 다음 sync 가 고친다."""
    series, manifest = load_json(SERIES, {}), load_json(MANIFEST, {})
    slots = sorted((e["id"] for e in manifest.values() if e.get("sha256") is not None), key=int)
    linked = {k for k, e in manifest.items() if e.get("sha256") is None}
    files = [f for f in SRC.rglob("*.html")
             if not series.get(rel(f.parent), {}).get("skip") and rel(f) not in linked]
    key = order_key(files)
    files.sort(key=key.get)
    new = {k: e for k, e in manifest.items() if k in linked}
    for slot, f in zip(slots, files):
        old = next((k for k, e in manifest.items() if e["id"] == slot), None)
        print(f"/{slot}  {title_of(f, series)}" + ("" if old == rel(f) else f"   (이전: {manifest[old]['title']})"))
        # 해시를 비워 다음 sync 가 반드시 다시 쓰게 한다
        new[rel(f)] = {"id": slot, "title": "", "category": None, "sha256": "", "synced_at": None}
    if not a.apply:
        print("\n미리보기다. --apply 로 매니페스트에 쓴다.")
        return
    save_manifest(new)
    print(f"\n{len(slots)}개 재배정. 이제 sync 를 돌릴 것.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("login")
    sub.add_parser("reorder").add_argument("--apply", action="store_true")
    for name in ("plan", "sync"):
        s = sub.add_parser(name)
        s.add_argument("--update-linked", action="store_true", help="손으로 올려 짝지어 둔 글도 저장소 내용으로 덮는다")
    s.add_argument("--limit", type=int)
    s.add_argument("--only", help="경로에 이 문자열이 든 파일만")
    s.add_argument("--visibility", choices=["private", "public"], default="private",
                   help="새 글의 공개 범위. 기존 글은 매니페스트의 visibility, 없으면 현재 값을 유지한다")
    s.add_argument("--interval", type=int, default=15, help="글 사이 대기(초)")
    a = ap.parse_args()
    {"login": cmd_login, "plan": cmd_plan, "sync": cmd_sync, "reorder": cmd_reorder}[a.cmd](a)


if __name__ == "__main__":
    main()
