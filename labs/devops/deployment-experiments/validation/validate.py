#!/usr/bin/env python3
"""Validate the deployment practice articles and, optionally, their browser layout.

This checks presentation/evidence links, not technical truth. Independent review
and source audits are recorded alongside this script.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import struct
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
POSTS = ROOT / "posts/CS/DevOps/deployment-experiments"
SKILL = ROOT / ".codex/skills/tistory-sketch-post"
TEMPLATE = ROOT / ".claude/skills/tistory-sketch-post/assets/template.html"
TITLES = [
    "오래된 A 대신 새 베이스라인 A′와 B를 비교한다",
    "A/B 테스트 사용자는 새로고침해도 같은 그룹이어야 한다",
    "전환율이 높아도 표본과 가드레일부터 확인한다",
]


class Elements(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.images = []
        self.links = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "img":
            self.images.append(attrs)
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])


def load_checker():
    spec = importlib.util.spec_from_file_location("check_html", SKILL / "scripts/validate_html.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate_html


def static(path, number, checker, style):
    source = path.read_text(encoding="utf-8")
    errors = list(checker(source))
    result = {"path": str(path.relative_to(ROOT)), "errors": errors, "images": []}
    styles = re.findall(r"<style>(.*?)</style>", source, re.S)
    if styles != [style]:
        errors.append("template CSS differs")
    if "\u2014" in source or "&mdash;" in source:
        errors.append("em dash present")
    for key in ("lead", "tags"):
        if not re.search(r"<!--\s*" + key + r":\s*\S.+?-->", source, re.S):
            errors.append(f"missing {key} metadata")
    lead = re.search(r"<!--\s*lead:\s*(.*?)\s*-->", source, re.S)
    if lead and not 80 <= len(lead.group(1)) <= 150:
        errors.append(f"lead length outside 80..150: {len(lead.group(1))}")
    series = re.search(r'<div class="obsv-series">(.*?)\n</div>', source, re.S)
    if not series:
        errors.append("series box missing")
    else:
        box = series.group(1)
        expected = TITLES[max(0, number - 3):number]
        actual = [title for title in TITLES if title in box]
        if actual != expected:
            errors.append("series box differs from current plus last two articles")
        if len(re.findall(r"<b>", box)) != 1 or f"{number}편. {TITLES[number - 1]}</b>" not in box:
            errors.append("current article emphasis differs")
    terms = len(re.findall(r'class="obsv-term"', source))
    result["term_boxes"] = terms
    if not 4 <= terms <= 8:
        errors.append(f"term box count outside 4..8: {terms}")
    result["svg_count"] = source.count("<svg")
    if result["svg_count"] < 2:
        errors.append("fewer than two explanatory SVG diagrams")
    if re.search(r"<(?:rect|line|circle)(?:\s|>)", source):
        errors.append("SVG uses geometric shapes forbidden by sketch guide")
    elements = Elements(source)
    if len(elements.images) < 2:
        errors.append("fewer than two executed experiment captures")
    for attrs in elements.images:
        src = attrs.get("src", "")
        parsed = urlparse(src)
        if parsed.scheme or parsed.netloc:
            match = re.fullmatch(r"/gh/DDINGJOO/Platform-study@[0-9a-f]{40}/(posts/CS/DevOps/deployment-experiments/images/.+\.png)", parsed.path)
            if parsed.scheme != "https" or parsed.netloc != "cdn.jsdelivr.net" or not match or parsed.query or parsed.fragment:
                errors.append(f"unexpected image origin: {src}")
                continue
            image = (ROOT / unquote(match.group(1))).resolve()
        else:
            image = (path.parent / unquote(parsed.path)).resolve()
        if not image.is_relative_to(POSTS.resolve()) or not image.is_file():
            errors.append(f"missing or escaping image: {src}")
            continue
        raw = image.read_bytes()
        if raw[:8] != b"\x89PNG\r\n\x1a\n":
            errors.append(f"not a PNG: {src}")
            continue
        width, height = struct.unpack(">II", raw[16:24])
        if not attrs.get("alt", "").strip():
            errors.append(f"missing image alt text: {src}")
        result["images"].append({"path": str(image.relative_to(ROOT)), "width": width,
                                 "height": height, "sha256": hashlib.sha256(raw).hexdigest()})
    for href in elements.links:
        parsed = urlparse(href)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        if not (path.parent / unquote(parsed.path)).exists():
            errors.append(f"local evidence link missing: {href}")
    return result


def browser(paths):
    from playwright.sync_api import sync_playwright
    results = []
    with sync_playwright() as playwright:
        chrome = playwright.chromium.launch(channel="chrome", headless=True)
        for path in paths:
            for width, height, label in ((1100, 850, "desktop"), (390, 844, "mobile")):
                page = chrome.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
                page.goto(path.as_uri(), wait_until="load")
                page.evaluate("document.fonts.ready")
                page.wait_for_timeout(250)
                layout = page.evaluate("""() => ({
                  width: innerWidth, documentWidth: document.documentElement.scrollWidth,
                  brokenImages: [...document.images].filter(i => !i.complete || !i.naturalWidth).map(i => i.src),
                  invisibleFigures: [...document.querySelectorAll('svg,img')].filter(e => {
                    const b=e.getBoundingClientRect(); return b.width<1 || b.height<1;
                  }).length
                })""")
                previews = []
                targets = [page.locator('.obsv-wrap'), *[page.locator('img').nth(i) for i in range(page.locator('img').count())]]
                for index, target in enumerate(targets):
                    target.scroll_into_view_if_needed()
                    if index == 0:
                        page.evaluate("scrollTo(0,0)")
                    name = f"{path.name[:2]}-{label}-{index:02d}.png"
                    page.screenshot(path=str(HERE / name))
                    previews.append(name)
                results.append({"post": path.name, "viewport": label, "layout": layout, "previews": previews,
                                "pass": layout["documentWidth"] <= width and not layout["brokenImages"]
                                        and layout["invisibleFigures"] == 0})
                page.close()
        chrome.close()
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", action="store_true")
    args = parser.parse_args()
    paths = sorted(POSTS.glob("[0-9][0-9]_*.html"))
    if len(paths) != 3:
        print(f"expected 3 posts, found {len(paths)}", file=sys.stderr)
        return 1
    style = re.search(r"<style>(.*?)</style>", TEMPLATE.read_text(), re.S).group(1)
    checker = load_checker()
    report = {"static": [static(path, i, checker, style) for i, path in enumerate(paths, 1)]}
    if args.browser:
        report["browser"] = browser(paths)
    report["pass"] = all(not row["errors"] for row in report["static"]) and all(row["pass"] for row in report.get("browser", []))
    (HERE / "checks.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    for row in report["static"]:
        print(row["path"], "PASS" if not row["errors"] else "FAIL: " + "; ".join(row["errors"]))
    for row in report.get("browser", []):
        print(row["post"], row["viewport"], "PASS" if row["pass"] else "FAIL", row["layout"])
    return int(not report["pass"])


if __name__ == "__main__":
    sys.exit(main())
