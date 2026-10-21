#!/usr/bin/env python3
"""Read-only structural checks for the template's explicit HTML/SVG fragments.

This is not an HTML5 conformance checker: it does not model optional end tags,
implicit browser repairs, content models, CSS, or presentation requirements.
Inline SVG must be well-formed XML; use XML entities or numeric references there.
"""

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET


VOID_TAGS = frozenset(
    "area base br col embed hr img input link meta param source track wbr".split()
)


class FragmentParser(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.errors = []
        self.stack = []
        self.svg_depth = 0
        self.svg_start = None
        self.svg_ids = set()
        self.line_offsets = [0] + [m.end() for m in re.finditer("\n", source)]

    def error(self, message):
        line, column = self.getpos()
        self.errors.append(f"line {line}, column {column + 1}: {message}")

    def source_offset(self):
        line, column = self.getpos()
        return self.line_offsets[line - 1] + column

    def check_svg(self, source):
        try:
            root = ET.fromstring(source)
        except ET.ParseError as exc:
            self.error(f"invalid SVG XML: {exc}")
            return
        for element in root.iter():
            identifier = element.get("id")
            if identifier is not None:
                if identifier in self.svg_ids:
                    self.error(f"duplicate SVG id: {identifier!r}")
                self.svg_ids.add(identifier)

    def handle_starttag(self, tag, attrs):
        if tag == "svg":
            if self.svg_depth == 0:
                self.svg_start = self.source_offset()
            self.svg_depth += 1
        if self.svg_depth or tag not in VOID_TAGS:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        if tag == "svg" and self.svg_depth == 0:
            self.check_svg(self.get_starttag_text())
        elif not self.svg_depth and tag not in VOID_TAGS:
            self.error(f"non-void HTML tag <{tag}> cannot be self-closing")

    def handle_endtag(self, tag):
        if not self.stack:
            self.error(f"unexpected closing tag </{tag}>")
        elif self.stack[-1] != tag:
            self.error(f"closing </{tag}> does not match <{self.stack[-1]}>")
            if tag in self.stack:
                del self.stack[self.stack.index(tag):]
        else:
            self.stack.pop()
        if tag == "svg" and self.svg_depth:
            self.svg_depth -= 1
            if self.svg_depth == 0:
                end = self.source.find(">", self.source_offset()) + 1
                self.check_svg(self.source[self.svg_start:end])
                self.svg_start = None

    def handle_data(self, data):
        if not self.svg_depth and (not self.stack or self.stack[-1] not in {"script", "style"}):
            if re.search(r"<(?:/?[A-Za-z]|!--)", data) or (
                data == "<" and re.match(r"<(?:/?[A-Za-z]|!--)", self.source[self.source_offset():])
            ):
                self.error("incomplete or malformed tag in text")


def validate_html(source):
    """Return structural errors without executing or modifying document content."""
    parser = FragmentParser(source)
    try:
        parser.feed(source)
        parser.close()
    except (AssertionError, ValueError) as exc:
        parser.error(f"malformed markup: {exc}")
    if parser.stack:
        parser.errors.append("unclosed tags: " + ", ".join(f"<{tag}>" for tag in parser.stack))
    return parser.errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="UTF-8 HTML files to inspect")
    args = parser.parse_args(argv)
    failed = False
    for path in args.paths:
        try:
            errors = validate_html(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as exc:
            errors = [str(exc)]
        if errors:
            failed = True
            for error in errors:
                print(f"{path}: {error}", file=sys.stderr)
        else:
            print(f"{path}: valid explicit HTML/SVG structure")
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
