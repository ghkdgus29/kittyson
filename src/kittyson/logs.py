"""Logging, the same in development and on the server: stderr and data/logs/app.log.

stderr is what `docker compose logs` shows, but it goes away when the container is
recreated. So the lines are also kept in a file under data/, which is a volume.
The file rotates by size and never takes more than log_max_mb x (log_backups + 1).
"""

import logging
import sys
from logging.handlers import RotatingFileHandler

from kittyson.config import settings

FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

# uvicorn puts its own console handlers on these two and stops them passing records on to
# the root logger, so the file handler has to be attached to them as well.
# (uvicorn.error passes its records to uvicorn; attaching there too would write twice.)
UVICORN_LOGGERS = ("uvicorn", "uvicorn.access")


def configure() -> None:
    """Called once, when the app starts."""
    settings.logs.mkdir(parents=True, exist_ok=True)
    to_file = RotatingFileHandler(
        settings.logs / "app.log",
        maxBytes=settings.log_max_mb * 1024 * 1024,
        backupCount=settings.log_backups,
        encoding="utf-8",
    )
    # force: the root logger gets exactly these two handlers, whatever it had before
    logging.basicConfig(
        level=logging.INFO, format=FORMAT, handlers=[logging.StreamHandler(sys.stderr), to_file], force=True
    )
    for name in UVICORN_LOGGERS:
        logger = logging.getLogger(name)
        if not logger.propagate:  # otherwise its records reach the root handlers anyway
            logger.addHandler(to_file)
