#!/usr/bin/env python3
"""Private TLS transport for typed Core endpoints. Loopback only, no public DNS route."""
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
import http.client,ssl,json
runtime=Path(__file__).resolve().parents[2]/'atlas-api/.runtime'
ALLOWED=('/internal/v1/deliveries/','/internal/v1/vip/statuses')
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_POST(self):
  if not any(self.path.startswith(p) for p in ALLOWED) or '?' in self.path:
   self.send_error(404);return
  if self.headers.get('Transfer-Encoding'):
   self.send_error(400);return
  try:size=int(self.headers.get('Content-Length','0'))
  except ValueError:self.send_error(400);return
  if size<0 or size>65536:self.send_error(413);return
  self.connection.settimeout(10)
  try:
   body=self.rfile.read(size)
   if len(body)!=size:self.send_error(400);return
   conn=http.client.HTTPConnection('127.0.0.1',8080,timeout=10)
   conn.request('POST',self.path,body,headers={'Content-Type':'application/json','X-Atlas-Key':self.headers.get('X-Atlas-Key','')})
   r=conn.getresponse();out=r.read(65537)
   if len(out)>65536:raise ValueError()
   self.send_response(r.status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(out)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(out);conn.close()
  except (OSError,ValueError):self.send_error(503)
server=ThreadingHTTPServer(('127.0.0.1',4202),Handler)
context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2
context.load_cert_chain(runtime/'core-tls.crt',runtime/'core-tls.key');server.socket=context.wrap_socket(server.socket,server_side=True)
server.serve_forever()
