import http.server,json,datetime
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  result={"time":datetime.datetime.now(datetime.timezone.utc).isoformat(),"client_ip":self.client_address[0],"client_port":self.client_address[1],"server_ip":self.server.server_address[0],"path":self.path}
  print(json.dumps(result),flush=True)
  body=(json.dumps(result)+"\n").encode();self.send_response(200);self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
 def log_message(self,*args):pass
print("LISTEN 192.168.104.4:18555",flush=True)
http.server.HTTPServer(("192.168.104.4",18555),Handler).serve_forever()
