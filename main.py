import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

START_TIME = datetime.utcnow()


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        uptime = str(datetime.utcnow() - START_TIME).split(".")[0]
        body = f"status: OK\nuptime: {uptime}\nbot: @Hamhamemzb_bot\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def start_health_server(port=8080):
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    logger.info(f"Health server on port {port}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    start_health_server(port)
    from bot import main
    main()
