"""A loopback server for battery tests: it records each request and replies
as told. No model is behind it."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Fake:
    """A loopback server that records each request and replies as told: one
    reply for every request, or a list taken in order (the last one repeats)."""

    def __init__(self, reply):
        self.requests, self.reply = [], reply
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers["content-length"])
                headers = {k.lower(): v for k, v in self.headers.items()}
                fake.requests.append((headers, json.loads(self.rfile.read(length))))
                if isinstance(fake.reply, list):
                    reply = fake.reply.pop(0) if len(fake.reply) > 1 else fake.reply[0]
                else:
                    reply = fake.reply
                status, headers, body = reply
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(body)

            do_GET = do_POST

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.url = self.base + "/v1/responses"
        threading.Thread(target=self.server.serve_forever, args=(0.05,), daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
