# -*- coding: utf-8 -*-
"""
server.py - Robust multi-threaded HTTP development server for VocabMatrix.
"""

import http.server
import os
import socket
import sys

# Ensure unbuffered UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

PORT = 8080

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        public_dir = os.path.dirname(os.path.abspath(__file__))
        super().__init__(*args, directory=public_dir, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def log_message(self, format, *args):
        # Log to stdout with immediate flush
        sys.stdout.write(f"[{self.log_date_time_string()}] {format % args}\n")
        sys.stdout.flush()

def main():
    port = PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass

    server_address = ("0.0.0.0", port)
    
    # Use ThreadingHTTPServer to handle concurrent browser requests smoothly
    try:
        httpd = http.server.ThreadingHTTPServer(server_address, Handler)
    except AttributeError:
        import socketserver
        class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
            allow_reuse_address = True
        httpd = ThreadedTCPServer(server_address, Handler)

    print("=" * 60, flush=True)
    print("🚀 VocabMatrix English App is running successfully!", flush=True)
    print(f"👉 Local Access:   http://localhost:{port}/", flush=True)
    print(f"👉 IP Access:      http://127.0.0.1:{port}/", flush=True)
    print("=" * 60, flush=True)
    print("Ready to serve requests. Press Ctrl+C to stop.\n", flush=True)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down...", flush=True)
    finally:
        httpd.server_close()

if __name__ == "__main__":
    main()
