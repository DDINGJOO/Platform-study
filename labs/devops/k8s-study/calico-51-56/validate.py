#!/usr/bin/env python3
"""Validate the six Calico posts and their local image assets without publishing."""
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
        'meta', 'param', 'source', 'track', 'wbr'}


class Structure(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.images, self.ids = [], [], [], []
        self.h2 = self.terms = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag not in VOID:
            self.stack.append(tag)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'img':
            self.images.append(attrs)
        if tag == 'h2':
            self.h2 += 1
        if 'obsv-term' in attrs.get('class', '').split():
            self.terms += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f'unexpected </{tag}>, stack={self.stack[-4:]}')
        else:
            self.stack.pop()


def validate(entry, style):
    path = ROOT / entry['file']
    errors = []
    if not path.exists():
        return {'number': entry['number'], 'errors': ['post missing']}
    text = path.read_text()
    parser = Structure()
    parser.feed(text)
    errors.extend(parser.errors)
    if parser.stack:
        errors.append(f'unclosed tags: {parser.stack}')
    if len(set(parser.ids)) != len(parser.ids):
        errors.append('duplicate element id')
    css = re.search(r'<style>.*?</style>', text, re.S)
    if not css or css.group(0) != style:
        errors.append('template CSS differs')
    svgs = re.findall(r'<svg\b.*?</svg>', text, re.S)
    for i, svg in enumerate(svgs, 1):
        try:
            ElementTree.fromstring(svg)
        except ElementTree.ParseError as exc:
            errors.append(f'SVG {i}: {exc}')
    for label, count, low, high in [('h2', parser.h2, 4, 6),
                                   ('terms', parser.terms, 4, 8),
                                   ('SVG', len(svgs), 2, 4)]:
        if not low <= count <= high:
            errors.append(f'{label} count {count} outside {low}..{high}')
    for comment in ['tags', 'lead']:
        if not re.search(r'<!--\s*' + comment + r':\s*\S.*?-->', text, re.S):
            errors.append(f'missing {comment} comment')
    if '\u2014' in text or '&mdash;' in text:
        errors.append('em dash found')
    if 'obsv-summary' not in text:
        errors.append('summary missing')
    for image in parser.images:
        src = image.get('src', '')
        prefix = 'https://raw.githubusercontent.com/DDINGJOO/Platform-study/main/'
        if src.startswith(prefix):
            asset = ROOT / unquote(urlparse(src).path.split('/main/', 1)[1])
            if not asset.is_file():
                errors.append(f'image missing: {asset}')
        else:
            errors.append(f'unexpected image source: {src}')
        if not image.get('alt'):
            errors.append('image alt missing')
    if not parser.images:
        errors.append('execution capture missing')
    return {'number': entry['number'], 'file': entry['file'],
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'h2': parser.h2, 'terms': parser.terms, 'svg': len(svgs),
            'images': len(parser.images), 'errors': errors}


def main():
    template = (ROOT / '.claude/skills/tistory-sketch-post/assets/template.html').read_text()
    style = re.search(r'<style>.*?</style>', template, re.S).group(0)
    entries = json.loads((HERE / 'manifest.json').read_text())
    report = [validate(entry, style) for entry in entries]
    (HERE / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    for row in report:
        print(f"{row['number']}: " + ('PASS' if not row['errors'] else '; '.join(row['errors'])))
    return int(any(row['errors'] for row in report))


if __name__ == '__main__':
    sys.exit(main())
