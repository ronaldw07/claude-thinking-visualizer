#!/usr/bin/env python3
"""Local bridge so the web slider can drive Claude Code's effort level.

A browser page on file:// cannot touch ~/.claude/settings.json. Serving the
same page from here gives it two endpoints:

    GET  /level  -> {"level": "high"}
    POST /level  <- {"level": "max"}

Binds to loopback only and accepts nothing but the five known effort levels,
because the handler writes to a real settings file.

    python3 bridge.py        # then open http://127.0.0.1:7373
"""

import json
import os
import shutil
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = int(os.environ.get("THINKING_BRIDGE_PORT", "7373"))

# Claude Code only stores these. "ultracode" is a picker entry that is
# persisted as xhigh, so the sixth slider rung maps onto it.
VALID_LEVELS = ("low", "medium", "high", "xhigh", "max")
ALIASES = {"ultracode": "xhigh"}

SETTINGS_PATH = os.path.expanduser("~/.claude/settings.json")
BACKUP_PATH = SETTINGS_PATH + ".before-thinking-visualizer"
PAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "index.html")


def read_settings():
    try:
        with open(SETTINGS_PATH) as handle:
            return json.load(handle)
    except (IOError, OSError, ValueError):
        return {}


def write_level(level):
    """Set effortLevel, leaving every other setting untouched."""
    settings = read_settings()
    if not settings:
        raise RuntimeError("could not read {}".format(SETTINGS_PATH))

    if os.path.exists(SETTINGS_PATH) and not os.path.exists(BACKUP_PATH):
        shutil.copyfile(SETTINGS_PATH, BACKUP_PATH)

    updated = dict(settings, effortLevel=level)
    tmp = "{}.{}.tmp".format(SETTINGS_PATH, os.getpid())
    with open(tmp, "w") as handle:
        json.dump(updated, handle, indent=2)
    os.replace(tmp, SETTINGS_PATH)


class BridgeHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if self.path != "/level":            # don't spam the console with polls
            sys.stderr.write("%s\n" % (fmt % args))

    def _send(self, code, body, content_type="application/json"):
        payload = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        if self.path.startswith("/level"):
            level = read_settings().get("effortLevel")
            self._send(200, json.dumps({"level": level}))
            return
        if self.path in ("/", "/index.html"):
            try:
                with open(PAGE_PATH, "rb") as handle:
                    self._send(200, handle.read(), "text/html; charset=utf-8")
            except (IOError, OSError) as error:
                self._send(500, json.dumps({"error": str(error)}))
            return
        self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        if not self.path.startswith("/level"):
            self._send(404, json.dumps({"error": "not found"}))
            return

        length = int(self.headers.get("Content-Length") or 0)
        try:
            requested = json.loads(self.rfile.read(length) or b"{}").get("level")
        except ValueError:
            self._send(400, json.dumps({"error": "invalid json"}))
            return

        level = ALIASES.get(requested, requested)
        if level not in VALID_LEVELS:
            self._send(400, json.dumps({"error": "unknown level", "got": requested}))
            return

        try:
            write_level(level)
        except (RuntimeError, IOError, OSError) as error:
            self._send(500, json.dumps({"error": str(error)}))
            return

        sys.stderr.write("effortLevel -> {}\n".format(level))
        self._send(200, json.dumps({"level": level}))


def main():
    if not os.path.exists(SETTINGS_PATH):
        sys.exit("no settings file at {}".format(SETTINGS_PATH))
    # threaded: the page holds a keep-alive connection open and polls, which
    # would wedge a single-threaded server after the first request
    server = ThreadingHTTPServer((HOST, PORT), BridgeHandler)
    server.daemon_threads = True
    print("Thinking bridge on http://{}:{}  (Ctrl+C to stop)".format(HOST, PORT))
    print("Writing effortLevel to {}".format(SETTINGS_PATH))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
