"""
Lightweight HTTP server that serves a /health endpoint.
Render (and UptimeRobot) ping this to keep the service alive.
Run this in a separate thread alongside the Telegram bot.
"""

import threading
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

logger = logging.getLogger(__name__)

START_TIME = datetime.utcnow()


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/health"):
            uptime = datetime.utcnow() - START_TIME
            body = (
                f"status: OK\n"
                f"uptime: {str(uptime).split('.')[0]}\n"
                f"bot: @Hamhamemzb_bot\n"
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress default access logs to keep output clean
        pass


def start_health_server(port: int = 8080):
    """Start the health-check HTTP server in a daemon thread."""
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Health server running on port {port}")
    return server
