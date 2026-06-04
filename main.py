"""
Entry point for Render deployment.
1. Starts the HTTP health-check server (keeps the service alive).
2. Starts the Telegram bot polling loop.
"""

import os
import logging
from health_server import start_health_server

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    start_health_server(port)
    logger.info(f"Health server started on port {port}")

    # Import and run bot (blocking call)
    from bot import main
    main()
