"""업스트림. 아무 경로에나 200. 경로가 /slow 로 끝나면 1초 뒤에 답한다(처리 중 요청을 만들기 위해)."""
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.rstrip("/").endswith("slow"):
            time.sleep(1.0)
        body = b"ok\n"
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a):
        pass

ThreadingHTTPServer(("", 8080), H).serve_forever()
