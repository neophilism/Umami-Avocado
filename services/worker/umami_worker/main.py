import logging
import os
import time

logger = logging.getLogger(__name__)

def tick() -> str:
    """Foundational no-op worker: never contacts or submits to laboratories."""
    return "idle"

def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Umami worker started; laboratory submissions are disabled")
    while True:
        tick()
        time.sleep(float(os.getenv("WORKER_POLL_SECONDS", "30")))

if __name__ == "__main__":
    main()
