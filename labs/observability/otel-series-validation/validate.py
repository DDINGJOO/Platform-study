#!/usr/bin/env python3
"""Read-only OTel series checks; generated reports/previews stay in this directory."""

import argparse
import hashlib
import html
import json
import re
import runpy
import struct
import subprocess
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SERIES = ROOT / "posts/CS/Observability/otel"
LABS = ROOT / "labs/observability"
TEMPLATE = ROOT / ".claude/skills/tistory-sketch-post/assets/template.html"
HTML_CHECK = ROOT / ".codex/skills/tistory-sketch-post/scripts/validate_html.py"
MASK_CHECK = ROOT / ".claude/skills/blog-post-pipeline/assets/mask-check.py"
UPLOADER = ROOT / ".claude/skills/tistory-sketch-post/assets/tistory-upload.py"
TITLES = [
    "API와 SDK는 왜 나뉘어 있을까",
    "스레드가 바뀌면 컨텍스트는 어떻게 이어질까",
    "전송이 밀리면 스팬은 어디서 사라질까",
    "샘플링하면 무엇이 남고 무엇이 빠질까",
    "메트릭은 어디서 집계되고 누가 가져갈까",
    "Collector를 두면 무엇을 중앙에서 바꿀 수 있을까",
    "자동 계측은 애플리케이션을 어디까지 알 수 있을까",
    "같은 요청을 같은 이름으로 기록하려면 무엇이 필요할까",
]
SERIES_TITLE = "OpenTelemetry 구조와 설계 읽기"
CDN_IMAGE_PREFIX = ("https://cdn.jsdelivr.net/gh/DDINGJOO/Platform-study@main/"
                    "posts/CS/Observability/otel/images/")
VOID = set("area base br col embed hr img input link meta param source track wbr".split())


def relative(path):
    return path.relative_to(ROOT).as_posix()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def resolve_image_path(post_path, src):
    """Map only local references or this series' exact public CDN URL to local PNGs."""
    if not src:
        raise ValueError("image src must not be empty")
    if src.startswith(CDN_IMAGE_PREFIX):
        suffix = src[len(CDN_IMAGE_PREFIX):]
        if not re.fullmatch(r"0[1-8]/[A-Za-z0-9][A-Za-z0-9_.-]*\.png", suffix):
            raise ValueError("CDN image must use a canonical series PNG path without query or fragment")
        image = (SERIES / "images" / suffix).resolve()
    else:
        parsed = urlparse(src)
        if parsed.scheme or parsed.netloc:
            raise ValueError("external image URL must use the exact approved series CDN prefix")
        image = (post_path.parent / unquote(parsed.path)).resolve()
    if not image.is_relative_to(SERIES.resolve()):
        raise ValueError("image path escapes the local series directory")
    return image


@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()

    def text(self, exclude=()):
        if self.tag in exclude:
            return ""
        if self.tag == "br":
            return "\n"
        return "".join(c.text(exclude) if isinstance(c, Node) else c for c in self.children)

    def has_class(self, name):
        return name in self.attrs.get("class", "").split()


class Tree(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.stack = [self.root]
        self.feed(source)
        self.close()

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, dict(attrs)))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          capture_output=True, text=True).stdout


def existing_metadata(uploader, current):
    before = json.loads(git("show", "HEAD:tistory-series.json"))
    paths = [ROOT / p for p in git("ls-tree", "-r", "-z", "--name-only", "HEAD", "posts").split("\0")
             if p.endswith(".html")]
    changes = []
    for path in paths:
        if not path.exists():
            changes.append({"path": relative(path), "problem": "tracked article missing"})
            continue
        text = path.read_text(encoding="utf-8")
        old = [uploader[name](path, before, text) if name == "tags_of"
               else uploader[name](path, before)
               for name in ["title_of", "category_of", "tags_of"]]
        new = [uploader[name](path, current, text) if name == "tags_of"
               else uploader[name](path, current)
               for name in ["title_of", "category_of", "tags_of"]]
        if old != new:
            changes.append({"path": relative(path), "before": old, "after": new})
    manifest_unchanged = (ROOT / "tistory-manifest.json").read_text(encoding="utf-8") == git(
        "show", "HEAD:tistory-manifest.json")
    return {"tracked_articles_checked": len(paths), "metadata_changes": changes,
            "tistory_manifest_unchanged_from_HEAD": manifest_unchanged,
            "scope": "HEAD versus current series config, same current article text for both"}


def manifests(verify_sources, active_numbers):
    mappings, reports, cache = {}, [], {}
    for path in sorted(LABS.glob("otel-*/source-manifest.json")):
        match = re.match(r"otel-(\d{2})-", path.parent.name)
        if not match:
            continue
        number = match.group(1)
        if number not in active_numbers:
            continue
        record = {"path": relative(path), "errors": [], "captures": []}
        reports.append(record)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            repository, commit, tag = data["repository"], data["commit"], data["tag"]
            if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
                raise ValueError("invalid repository")
            if not re.fullmatch(r"[a-f0-9]{40}", commit):
                raise ValueError("commit must be full SHA")
            if not tag or not isinstance(tag, str):
                raise ValueError("tag missing")
            for capture in data["captures"]:
                item = {"output": capture["output"], "errors": []}
                record["captures"].append(item)
                source_path, first, last = capture["path"], capture["start"], capture["end"]
                permalink = f"https://github.com/{repository}/blob/{commit}/{source_path}#L{first}-L{last}"
                if capture["permalink"] != permalink:
                    item["errors"].append("permalink does not match full commit/path/range")
                if not (isinstance(first, int) and isinstance(last, int) and 1 <= first <= last):
                    item["errors"].append("invalid consecutive line range")
                if not re.fullmatch(r"[a-f0-9]{64}", capture["sha256"]):
                    item["errors"].append("full-source SHA-256 missing/invalid")
                image = SERIES / "images" / number / capture["output"]
                mappings[image.resolve()] = {"manifest": relative(path), "permalink": permalink}
                if image.exists():
                    raw_image = image.read_bytes()
                    if raw_image[:8] != b"\x89PNG\r\n\x1a\n":
                        item["errors"].append("output is not a PNG")
                    else:
                        item["png_dimensions"] = list(struct.unpack(">II", raw_image[16:24]))
                        item["png_sha256"] = digest(raw_image)
                else:
                    item["errors"].append("PNG output missing")
                if verify_sources:
                    url = f"https://raw.githubusercontent.com/{repository}/{commit}/{source_path}"
                    if url not in cache:
                        request = Request(url, headers={"User-Agent": "Platform-study-series-validation"})
                        with urlopen(request, timeout=30) as response:
                            cache[url] = response.read()
                    raw = cache[url]
                    item["source_hash_verified"] = digest(raw) == capture["sha256"]
                    lines = raw.decode("utf-8").splitlines()
                    if not item["source_hash_verified"]:
                        item["errors"].append("downloaded full-source hash mismatch")
                    if last > len(lines):
                        item["errors"].append("line range exceeds original file")
                    excerpt_hash = digest(("\n".join(lines[first - 1:last]) + "\n").encode())
                    item["excerpt_sha256"] = excerpt_hash
                    if capture.get("excerpt_sha256", excerpt_hash) != excerpt_hash:
                        item["errors"].append("excerpt hash mismatch")
        except (KeyError, OSError, ValueError, TypeError) as exception:
            record["errors"].append(f"{type(exception).__name__}: {exception}")
    return mappings, reports


def check_post(path, number, source_map, uploader, series_config, structure, mask, template_css):
    raw = path.read_text(encoding="utf-8")
    root = Tree(raw).root
    errors, warnings = [], []
    nodes = list(root.walk())
    report = {"number": number, "path": relative(path), "sha256": digest(raw.encode()),
              "errors": errors, "warnings": warnings}
    errors.extend(structure(raw))
    styles = re.findall(r"<style\b[^>]*>(.*?)</style>", raw, re.S | re.I)
    if styles != [template_css]:
        errors.append("style block must exactly equal the unchanged template CSS")
    boxes = [node for node in nodes if node.has_class("obsv-series")]
    if len(boxes) != 1:
        errors.append("expected one common series box")
    else:
        box = boxes[0]
        lines = [line.strip() for line in box.text().splitlines() if line.strip()]
        if not lines or lines.pop(0) != "📚 " + SERIES_TITLE:
            errors.append("series title differs from approved title")
        lines = [line.replace("← 지금 이 글", "").strip() for line in lines]
        expected = [f"{index}편. {TITLES[index - 1]}"
                    for index in range(max(1, number - 2), number + 1)]
        if lines != expected:
            errors.append("series navigation must show only the current and up to two previous posts")
        bold = [node.text().strip() for node in box.walk() if node.tag == "b"]
        if bold != [expected[-1]] or box.text().count("← 지금 이 글") != 1:
            errors.append("current series item must be the only bold item and have one current marker")
    tag_match = re.search(r"<!--\s*tags:\s*(.*?)-->", raw[:4000], re.S)
    own_tags = [tag.strip() for tag in tag_match.group(1).split(",") if tag.strip()] if tag_match else []
    if not 3 <= len(own_tags) <= 5:
        errors.append("article-specific tags must contain 3–5 nonempty items")
    if len({tag.lower() for tag in own_tags}) != len(own_tags):
        errors.append("article-specific tags contain duplicates")
    lead_match = re.search(r"<!--\s*lead:\s*(.*?)-->", raw[:4000], re.S)
    lead = lead_match.group(1).strip() if lead_match else ""
    if not 80 <= len(lead) <= 150:
        errors.append(f"lead must have 80–150 characters; observed {len(lead)}")
    prose = root.text(exclude={"style", "script", "code", "pre"})
    # Class-based code/log blocks are excluded without ignoring headings or SVG labels.
    code_blocks = [node.text() for node in nodes if node.has_class("obsv-code")]
    if "—" in prose:
        only_in_logs = all("—" not in node.text() for node in nodes
                           if node.tag in {"p", "h1", "h2", "h3", "text"})
        if not only_in_logs or not any("—" in block for block in code_blocks):
            errors.append("em dash found in article prose/headings/SVG labels")
    if "—" in path.name:
        errors.append("em dash found in filename/title")
    allow = mask["load_allow"](ROOT / ".mask-allow")
    hits = mask["scan"](raw + "\n" + relative(path), [], allow)
    if hits:
        labels = sorted({hit.split(":", 1)[0].strip() for hit in hits})
        errors.append(f"generic mask scan detected {len(hits)} findings: {', '.join(labels)}")
    images = []
    for node in nodes:
        if node.tag != "img":
            continue
        src = node.attrs.get("src", "")
        entry = {"src": src, "exists": False}
        images.append(entry)
        try:
            image = resolve_image_path(path, src)
        except ValueError as exception:
            errors.append(f"invalid image reference: {exception}")
            continue
        entry["exists"] = image.is_file()
        if not image.is_file():
            errors.append(f"local image missing for reference: {src}")
        if not node.attrs.get("alt", "").strip():
            errors.append(f"image alt text missing: {src}")
        if image not in source_map:
            errors.append(f"source manifest not found for image: {src}")
        elif source_map[image]["permalink"] not in raw:
            errors.append(f"article does not reference the pinned source for image: {src}")
        else:
            entry["manifest"] = source_map[image]["manifest"]
    if not images:
        errors.append("article has no source-code image")
    final_tags = uploader["tags_of"](path, series_config, raw)
    report.update({"style_exact": styles == [template_css], "lead_characters": len(lead),
                   "own_tags": own_tags, "final_tags": final_tags,
                   "title": uploader["title_of"](path, series_config),
                   "category": uploader["category_of"](path, series_config), "images": images,
                   "headings": sum(node.tag == "h2" for node in nodes),
                   "svg_count": sum(node.tag == "svg" for node in nodes)})
    return report


BROWSER_CHECK = r"""() => {
  const width = document.documentElement.clientWidth;
  const selector = el => {
    const parts = [];
    for (let at = el; at && at.tagName && parts.length < 4; at = at.parentElement) {
      let part = at.tagName.toLowerCase();
      if (at.id) part += '#' + at.id;
      else if (typeof at.className === 'string' && at.className.trim())
        part += '.' + at.className.trim().split(/\s+/).join('.');
      if (at.parentElement) part += ':nth-child(' + (Array.from(at.parentElement.children).indexOf(at)+1) + ')';
      parts.unshift(part);
    }
    return parts.join(' > ');
  };
  const allowedScroller = el => {
    for (let at = el.parentElement; at && at !== document.body; at = at.parentElement) {
      const style = getComputedStyle(at), rect = at.getBoundingClientRect();
      if (['auto','scroll'].includes(style.overflowX) && rect.left >= -1 && rect.right <= width+1
          && (at.matches('.obsv-code, pre') || at.querySelector('table'))) return true;
    }
    return false;
  };
  const overflow = Array.from(document.body.querySelectorAll('*')).filter(el => {
    if (el.closest('svg') || allowedScroller(el)) return false;
    const rect = el.getBoundingClientRect();
    return rect.width && (rect.left < -1 || rect.right > width+1);
  }).map(el => {
    const rect = el.getBoundingClientRect(), style = getComputedStyle(el);
    return {selector:selector(el), text:el.textContent.trim().slice(0,130),
      left:rect.left,right:rect.right,width:rect.width,overflowX:style.overflowX,
      overflowWrap:style.overflowWrap,whiteSpace:style.whiteSpace};
  });
  const svgTextOutside = [];
  Array.from(document.querySelectorAll('svg')).forEach((svg,index) => {
    const outer = svg.getBoundingClientRect();
    for (const text of svg.querySelectorAll('text')) {
      const r = text.getBoundingClientRect();
      if (r.left < outer.left-1 || r.right > outer.right+1 || r.top < outer.top-1 || r.bottom > outer.bottom+1)
        svgTextOutside.push({svg:index+1,text:text.textContent,selector:selector(text),
          bounds:{left:r.left,right:r.right,top:r.top,bottom:r.bottom},
          svgBounds:{left:outer.left,right:outer.right,top:outer.top,bottom:outer.bottom}});
    }
  });
  return {clientWidth:width,scrollWidth:document.documentElement.scrollWidth,
    bodyScrollWidth:document.body.scrollWidth,
    images:Array.from(document.images).map(img => ({src:img.getAttribute('src'),
      loaded:img.complete && img.naturalWidth > 0,width:img.naturalWidth,height:img.naturalHeight})),
    fonts:Array.from(document.fonts).map(font => ({family:font.family,status:font.status})),
    overflowElements:overflow.slice(0,25),svgTextOutside,
    allowedHorizontalScrollers:Array.from(document.querySelectorAll('.obsv-code,pre,table')).filter(
      el => el.scrollWidth > el.clientWidth).map(el => ({selector:selector(el),
      clientWidth:el.clientWidth,scrollWidth:el.scrollWidth}))};
}"""


def browser_checks(posts, chrome):
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=chrome, headless=True,
            args=["--disable-background-networking", "--no-first-run"])
        try:
            for name, width, height in [("desktop", 1100, 850), ("mobile", 390, 844)]:
                context = browser.new_context(viewport={"width": width, "height": height},
                                              device_scale_factor=1)
                page = context.new_page()
                page.set_default_timeout(20000)
                for post in posts:
                    path = ROOT / post["path"]
                    record = {"viewport": [width, height], "errors": [], "screenshots": []}
                    post.setdefault("browser", {})[name] = record
                    try:
                        page.goto(path.as_uri(), wait_until="load", timeout=30000)
                        page.evaluate("""async () => {
                          if (!document.querySelector('meta[name=viewport]')) {
                            const meta=document.createElement('meta');meta.name='viewport';
                            meta.content='width=device-width, initial-scale=1';document.head.append(meta);
                          }
                          await document.fonts.ready;
                          await Promise.all(Array.from(document.images).map(img => {
                            img.loading='eager';return img.decode().catch(() => null);
                          }));
                          await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
                        }""")
                        record.update(page.evaluate(BROWSER_CHECK))
                        if record["scrollWidth"] > record["clientWidth"]:
                            record["errors"].append("document has horizontal overflow")
                        if record["svgTextOutside"]:
                            record["errors"].append("SVG text exceeds SVG bounds")
                        if any(not image["loaded"] for image in record["images"]):
                            record["errors"].append("broken or unloaded image")
                        failed_fonts = [font for font in record["fonts"] if font["status"] == "error"]
                        if failed_fonts:
                            record["errors"].append("one or more declared font faces failed to load")
                        for family in ["Gowun Dodum", "Nanum Pen Script"]:
                            if not any(font["family"].strip('"\'') == family and font["status"] == "loaded"
                                       for font in record["fonts"]):
                                record["errors"].append(f"required used font family has no loaded face: {family}")
                        number = post["number"]
                        for section in ["top", "detail"]:
                            if section == "top":
                                page.evaluate("window.scrollTo(0,0)")
                            else:
                                target = page.locator("svg,table").first
                                if target.count():
                                    target.evaluate("el => el.scrollIntoView({block:'center'})")
                            screenshot = HERE / "screenshots" / f"{number:02d}-{name}-{section}.png"
                            screenshot.parent.mkdir(exist_ok=True)
                            page.screenshot(path=str(screenshot), animations="disabled")
                            record["screenshots"].append(screenshot.relative_to(HERE).as_posix())
                    except Exception as exception:
                        record["errors"].append(f"{type(exception).__name__}: {exception}")
                    if digest(path.read_bytes()) != post["sha256"]:
                        record["errors"].append("article changed during validation; rerun needed")
                context.close()
        finally:
            browser.close()


def write_report(report):
    (HERE / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# OTel 시리즈 자동 검사", "", f"상태: **{report['status']}**", "",
             "구조·메타데이터·원본 참조·브라우저 자동 검사다. 독립 퇴고·원자료 사실 감사가 아니다.", "",
             f"현재 {len(report['posts'])}/8편, 대기 {len(report['pending'])}편.", "",
             f"기존 추적 글 {report['existing_metadata']['tracked_articles_checked']}편의 설정 영향 비교: "
             f"변경 {len(report['existing_metadata']['metadata_changes'])}건.", "",
             "| 편 | 정적 오류 | 데스크톱 오류 | 모바일 오류 |", "|---|---:|---:|---:|"]
    for post in report["posts"]:
        browser = post.get("browser", {})
        counts = [str(len(browser[name]["errors"])) if name in browser else "미실행"
                  for name in ["desktop", "mobile"]]
        lines.append(f"| {post['number']} | {len(post['errors'])} | {counts[0]} | {counts[1]} |")
    for post in report["posts"]:
        lines.extend(["", f"## {post['number']}편", "", post["path"], ""])
        lines.extend(f"- {error}" for error in post["errors"])
        for name, browser in post.get("browser", {}).items():
            lines.extend(f"- {name}: {error}" for error in browser["errors"])
            for problem in browser.get("overflowElements", []):
                lines.append(f"- {name} 넘침: `{problem['selector']}` / {problem['text'][:90]}")
            for problem in browser.get("svgTextOutside", []):
                lines.append(f"- {name} SVG 범위: {problem['text']}")
            for screenshot in browser["screenshots"]:
                lines.append(f"- [{name} {Path(screenshot).stem.rsplit('-',1)[-1]}]({screenshot})")
    if report["errors"]:
        lines.extend(["", "## 공통 오류", ""] + [f"- {error}" for error in report["errors"]])
    lines.extend(["", "## 제한", ""] + [f"- {limit}" for limit in report["limits"]])
    (HERE / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final", action="store_true", help="Require all eight articles")
    parser.add_argument("--browser", action="store_true", help="Use existing Playwright/Chrome")
    parser.add_argument("--verify-sources", action="store_true", help="Download pinned raw files and verify hashes")
    parser.add_argument("--chrome", default="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    args = parser.parse_args()
    structure = runpy.run_path(str(HTML_CHECK))["validate_html"]
    mask = runpy.run_path(str(MASK_CHECK))
    uploader = runpy.run_path(str(UPLOADER))  # __main__ is not invoked; no profile/token/remote access.
    series_config = json.loads((ROOT / "tistory-series.json").read_text(encoding="utf-8"))
    template_css = re.findall(r"<style\b[^>]*>(.*?)</style>", TEMPLATE.read_text(encoding="utf-8"), re.S)[0]
    active_numbers = {f"{number:02d}" for number, title in enumerate(TITLES, 1)
                      if (SERIES / f"{number:02d}_{number}편 - {title}.html").exists()}
    source_map, source_reports = manifests(args.verify_sources, active_numbers)
    report = {"kind": "automated-format-source-reference-browser-checks", "errors": [], "pending": [],
              "posts": [], "source_manifests": source_reports,
              "sources_downloaded_and_hashed": args.verify_sources,
              "browser_requested": args.browser,
              "existing_metadata": existing_metadata(uploader, series_config),
              "limits": ["Not an independent editorial review or factual audit",
                         "Public source only; generic mask rules, no organization-specific list",
                         "Local file previews with viewport metadata; not Tistory theme rendering",
                         "No upload, category creation, authentication, commit, or push",
                         "Pinned source tags are recorded; this check verifies raw hashes, not release trust"]}
    configuration = series_config.get(relative(SERIES), {})
    if configuration.get("prefix") != SERIES_TITLE or configuration.get("category") != "Observability/OpenTelemetry":
        report["errors"].append("series prefix/category missing or differs from approved configuration")
    if not 5 <= len(configuration.get("tags", [])) <= 6:
        report["errors"].append("common series tags must contain 5–6 items")
    if report["existing_metadata"]["metadata_changes"]:
        report["errors"].append("existing tracked article metadata would change")
    if not report["existing_metadata"]["tistory_manifest_unchanged_from_HEAD"]:
        report["errors"].append("tistory-manifest.json changed from HEAD")
    for number, title in enumerate(TITLES, 1):
        path = SERIES / f"{number:02d}_{number}편 - {title}.html"
        if not path.exists():
            report["pending"].append(relative(path))
            continue
        report["posts"].append(check_post(path, number, source_map, uploader,
            series_config, structure, mask, template_css))
    known = {post["path"] for post in report["posts"]}
    unexpected = [relative(path) for path in SERIES.glob("*.html") if relative(path) not in known]
    if unexpected:
        report["errors"].append("unexpected filename/number/title: " + ", ".join(unexpected))
    if args.final and report["pending"]:
        report["errors"].append("final validation requires all eight expected articles")
    if args.browser:
        browser_checks(report["posts"], args.chrome)
    failed = bool(report["errors"])
    failed |= any(post["errors"] or any(view["errors"] for view in post.get("browser", {}).values())
                  for post in report["posts"])
    failed |= any(source["errors"] or any(capture["errors"] for capture in source["captures"])
                  for source in source_reports)
    report["status"] = "FAIL" if failed else "PASS_PARTIAL" if report["pending"] else "PASS"
    write_report(report)
    print(f"{report['status']}: {len(report['posts'])}/8 articles; pending={len(report['pending'])}; "
          f"existing-metadata-changes={len(report['existing_metadata']['metadata_changes'])}")
    for post in report["posts"]:
        print(f"{post['number']:02d}: static={len(post['errors'])}; " + "; ".join(
            f"{name}={len(view['errors'])}" for name, view in post.get("browser", {}).items()))
    print(relative(HERE / "report.json"))
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
