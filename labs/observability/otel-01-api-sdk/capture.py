#!/usr/bin/env python3
"""Render verified, pinned upstream source excerpts as local code screenshots."""

import argparse
import hashlib
import html
import json
import re
import struct
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEFAULT_OUTPUT = ROOT / "posts/CS/Observability/otel/images/01"


def download(url):
    request = Request(url, headers={"User-Agent": "Platform-study-source-capture"})
    with urlopen(request, timeout=30) as response:
        return response.read()


def check_tag(repository, tag, expected_commit):
    metadata = json.loads(
        download(f"https://api.github.com/repos/{repository}/git/ref/tags/{tag}")
    )
    obj = metadata["object"]
    while obj["type"] == "tag":
        obj = json.loads(download(obj["url"]))["object"]
    if obj["type"] != "commit" or obj["sha"] != expected_commit:
        raise ValueError(f"Tag {tag} no longer resolves to {expected_commit}")


def render(manifest, capture, lines):
    highlighted = set(capture.get("highlight", []))
    source_rows = []
    for number, line in enumerate(lines, capture["start"]):
        class_name = "line highlighted" if number in highlighted else "line"
        source_rows.append(
            f'<div class="{class_name}"><span class="number">{number}</span>'
            f'<span class="source">{html.escape(line)}</span></div>'
        )
    title = html.escape(Path(capture["path"]).name)
    path = html.escape(capture["path"])
    repository = html.escape(manifest["repository"])
    tag = html.escape(manifest["tag"])
    short_commit = html.escape(manifest["commit"][:12])
    return f"""<!doctype html><html lang="en"><meta charset="utf-8">
<style>
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: #eeeae2; color: #292e35; }}
#capture {{ width: 1320px; padding: 30px; background: #f7f4ee; }}
.card {{ background: #fffdfa; border: 1px solid #ddd7ce; border-radius: 16px;
  overflow: hidden; box-shadow: 0 4px 12px #1e28300b; }}
header {{ padding: 26px 30px 23px; border-bottom: 1px solid #e5dfd5;
  font-family: -apple-system, BlinkMacSystemFont, sans-serif; }}
.repo {{ font-size: 17px; font-weight: 600; color: #5e6270; }}
h1 {{ margin: 11px 0; font-size: 29px; font-weight: 700; }}
.path {{ font-size: 16px; color: #656875; overflow-wrap: anywhere; }}
.revision {{ font-size: 16px; margin-top: 14px; color: #484c5c; }}
.code {{ padding: 21px 0; font: 19px/30px Menlo, Monaco, monospace; }}
.line {{ display: grid; grid-template-columns: 70px minmax(0, 1fr);
  padding-right: 23px; min-height: 30px; }}
.number {{ text-align: right; padding-right: 19px; color: #85848a;
  border-right: 1px solid #ece7de; user-select: none; }}
.source {{ padding-left: 19px; white-space: pre; }}
.highlighted {{ background: #eaeaf8; }}
.highlighted .number {{ border-right-color: #c8c4e0; color: #68618f; }}
footer {{ border-top: 1px solid #e5dfd5; padding: 17px 30px;
  font: 15px/1.5 -apple-system, BlinkMacSystemFont, sans-serif; color: #64646c; }}
</style><div id="capture"><article class="card">
<header><div class="repo">{repository}</div><h1>{title}</h1>
<div class="path">{path}</div><div class="revision">{tag} · {short_commit}
 · L{capture['start']}–L{capture['end']}</div></header>
<div class="code">{''.join(source_rows)}</div>
<footer>Locally rendered upstream source · line numbers preserved · Apache-2.0
 · OpenTelemetry Authors</footer></article></div></html>"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=HERE / "source-manifest.json")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, help="Save generated verification metadata as JSON")
    parser.add_argument("--chrome", default="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    repository, commit = manifest["repository"], manifest["commit"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Expected owner/repository")
    if not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("Expected a full Git commit SHA")
    check_tag(repository, manifest["tag"], commit)
    from playwright.sync_api import sync_playwright

    results = []
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="otel-source-") as temporary:
        cached_sources = {}
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=args.chrome,
                headless=True,
                args=["--disable-background-networking", "--no-first-run"],
            )
            try:
                context = browser.new_context(
                    viewport={"width": 1320, "height": 900}, device_scale_factor=1.5
                )
                page = context.new_page()
                for capture in manifest["captures"]:
                    path = capture["path"]
                    if Path(path).is_absolute() or ".." in Path(path).parts:
                        raise ValueError("Source paths must be repository-relative")
                    if Path(capture["output"]).name != capture["output"]:
                        raise ValueError("Output must be a PNG filename, not a path")
                    if not capture["output"].endswith(".png"):
                        raise ValueError("Output must end in .png")
                    if path not in cached_sources:
                        raw = download(
                            f"https://raw.githubusercontent.com/{repository}/{commit}/{path}"
                        )
                        cached_sources[path] = raw
                        (Path(temporary) / hashlib.sha256(path.encode()).hexdigest()).write_bytes(raw)
                    raw = cached_sources[path]
                    if hashlib.sha256(raw).hexdigest() != capture["sha256"]:
                        raise ValueError(f"Source checksum mismatch: {path}")
                    all_lines = raw.decode("utf-8").splitlines()
                    first, last = capture["start"], capture["end"]
                    if not 1 <= first <= last <= len(all_lines):
                        raise ValueError(f"Invalid source line range: {path}")
                    expected_permalink = (
                        f"https://github.com/{repository}/blob/{commit}/{path}#L{first}-L{last}"
                    )
                    if capture["permalink"] != expected_permalink:
                        raise ValueError(f"Permalink does not match pinned excerpt: {path}")
                    lines = all_lines[first - 1:last]
                    excerpt_hash = hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()
                    if capture.get("excerpt_sha256", excerpt_hash) != excerpt_hash:
                        raise ValueError(f"Excerpt checksum mismatch: {path}")
                    page.set_content(render(manifest, capture, lines), wait_until="load")
                    # The card clips overflow, so checking the outer page alone can miss
                    # truncated source. Fit the actual code rows, preserving every line.
                    fit = page.evaluate("""() => {
                        const code = document.querySelector('.code');
                        const rows = [...document.querySelectorAll('.source')];
                        let size = 19;
                        while (size > 14 && rows.some(el => el.scrollWidth > el.clientWidth)) {
                            size -= 0.5;
                            code.style.fontSize = `${size}px`;
                        }
                        return {font_size: size, overflowing: rows.some(
                            el => el.scrollWidth > el.clientWidth
                        )};
                    }""")
                    if fit["overflowing"]:
                        raise ValueError(f"Source row would be clipped: {path}")
                    rendered = page.locator(".source").all_text_contents()
                    if rendered != lines:
                        raise ValueError(f"Rendering altered source text: {path}")
                    if not page.locator("#capture").evaluate(
                        "el => el.scrollWidth === el.clientWidth"
                    ):
                        raise ValueError(f"Source has horizontal overflow: {path}")
                    output = args.output_dir / capture["output"]
                    page.locator("#capture").screenshot(path=str(output), animations="disabled")
                    width, height = struct.unpack(">II", output.read_bytes()[16:24])
                    results.append({
                        "output": str(output), "width": width, "height": height,
                        "lines": [first, last], "excerpt_sha256": excerpt_hash,
                        "source_font_size": fit["font_size"],
                        "png_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                    })
            finally:
                browser.close()
    report = {"tag_verified": True, "captures": results}
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)


if __name__ == "__main__":
    main()
