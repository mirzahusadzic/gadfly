"""A loopback server for battery tests: it records each request and replies
as told. No model is behind it."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Fake:
    """A loopback server that records each request and replies as told."""

    def __init__(self, reply):
        self.requests, self.reply = [], reply
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers["content-length"])
                headers = {k.lower(): v for k, v in self.headers.items()}
                fake.requests.append((headers, json.loads(self.rfile.read(length))))
                status, headers, body = fake.reply
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
