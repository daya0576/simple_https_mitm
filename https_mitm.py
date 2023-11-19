import os
import socket
import ssl
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
import time


def p(filename: str, sub_folder: str = "") -> str:
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), sub_folder, filename
    )


CA_KEY = p("ca.key")
CA_CERT = p("ca.crt")
CERT_KEY = p("cert.key")


class SimpleHttpServer(HTTPServer):
    address_family = socket.AF_INET6
    daemon_threads = True


class ProxyRequestHandler(BaseHTTPRequestHandler):
    def do_CONNECT(self):
        # Enter MitM mode
        self.send_response_only(200, "Connection Established")
        self.end_headers()

        # Handshake
        # TODO: Generate cert for every new domain
        certpath = p("certs/baidu.com.crt")
        self.connection = ssl.wrap_socket(
            self.connection,
            keyfile=CERT_KEY,
            certfile=certpath,
            server_side=True,
            # ssl_version=ssl.PROTOCOL_TLSv1_2,
        )

        self.rfile = self.connection.makefile("rb", self.rbufsize)
        self.wfile = self.connection.makefile("wb", self.wbufsize)

        self.close_connection = False

    def do_GET(self):
        req = self

        host = req.headers["Host"]
        url = req.path
        scheme = "https" if isinstance(self.connection, ssl.SSLSocket) else "http"
        if req.path[0] == "/":
            url = f"{scheme}://{host}{req.path}"
        print(f"Hijack req: {url}")
        if "localhost" in url:
            # TODO: welcome page for localhost
            return

        headers = dict(req.headers.items())
        # headers = {}
        resp = requests.get(url, headers=headers, allow_redirects=False)

        time.sleep(1)

        self.send_response(resp.status_code)
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(resp.content)


if __name__ == "__main__":
    host, port = "localhost", 9999
    print(f"Start listen on {host}:{port}...")
    s = SimpleHttpServer((host, port), ProxyRequestHandler)
    s.serve_forever()
