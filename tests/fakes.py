"""A loopback server for battery tests: it records each request and replies
as told. No model is behind it."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Fake:
    """A loopback server that records each request and replies as told: one
    reply for every request, a list taken in order (the last one repeats), or
    a function of the request's body."""

    def __init__(self, reply, routes=None):
        self.requests, self.reply, self.routes = [], reply, dict(routes or {})
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path in fake.routes:  # a route of its own, not recorded
                    status, headers, body = fake.routes[self.path]
                    self.send_response(status)
                    for key, value in headers.items():
                        self.send_header(key, value)
                    self.end_headers()
                    self.wfile.write(body)
                    return
                length = int(self.headers.get("content-length") or 0)
                headers = {k.lower(): v for k, v in self.headers.items()}
                fake.requests.append((headers, json.loads(self.rfile.read(length) or b"null")))
                if callable(fake.reply):  # a reply worked out from the request
                    reply = fake.reply(fake.requests[-1][1])
                elif isinstance(fake.reply, list):
                    reply = fake.reply.pop(0) if len(fake.reply) > 1 else fake.reply[0]
                else:
                    reply = fake.reply
                status, headers, body = reply
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                status, headers, body = fake.routes.get(self.path, (404, {}, b"{}"))
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.url = self.base + "/v1/responses"
        threading.Thread(target=self.server.serve_forever, args=(0.05,), daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
