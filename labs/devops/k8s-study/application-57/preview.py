#!/usr/bin/env python3
"""Serve local post previews, resolving unpublished raw GitHub images locally."""
import argparse
import html
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ENTRIES = json.loads((HERE / 'manifest.json').read_text())


class Preview(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        route = urlparse(self.path).path
        if route == '/':
            body = '<h1>애플리케이션 배포 57편 로컬 미리보기</h1><ul>'
            for entry in ENTRIES:
                body += '<li><a href="/__post__/{0}">{0}편. {1}</a></li>'.format(
                    entry['number'], html.escape(entry['title']))
            self.send_html(body + '</ul>')
            return
        if route.startswith('/__post__/'):
            number = route.removeprefix('/__post__/')
            entry = next((e for e in ENTRIES if str(e['number']) == number), None)
            if not entry or not (ROOT / entry['file']).is_file():
                self.send_error(404, 'Post is not written yet')
                return
            content = (ROOT / entry['file']).read_text()
            content = content.replace(
                'https://raw.githubusercontent.com/DDINGJOO/Platform-study/main/', '/')
            self.send_html(content)
            return
        super().do_GET()

    def send_html(self, content):
        data = ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width, initial-scale=1">'
                '<title>애플리케이션 배포 로컬 미리보기</title></head><body>' + content +
                '</body></html>').encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=18768)
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Preview)
    print(f'http://127.0.0.1:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
