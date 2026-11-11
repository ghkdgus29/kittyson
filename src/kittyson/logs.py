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

_attached: list[tuple[logging.Logger, logging.Handler]] = []
_root_level: int | None = None


def configure() -> None:
    """Called when the app starts. Calling it again replaces what the last call set up."""
    global _root_level
    close()
    settings.logs.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(FORMAT)

    to_file = RotatingFileHandler(
        settings.logs / "app.log",
        maxBytes=settings.log_max_mb * 1024 * 1024,
        backupCount=settings.log_backups,
        encoding="utf-8",
    )
    to_file.setFormatter(formatter)
    to_stderr = logging.StreamHandler(sys.stderr)
    to_stderr.setFormatter(formatter)

    root = logging.getLogger()
    _root_level = root.level
    root.setLevel(logging.INFO)
    _attach(root, to_stderr)
    _attach(root, to_file)
    for name in UVICORN_LOGGERS:
        logger = logging.getLogger(name)
        if not logger.propagate:  # otherwise its records reach the root handlers anyway
            _attach(logger, to_file)


def _attach(logger: logging.Logger, handler: logging.Handler) -> None:
    logger.addHandler(handler)
    _attached.append((logger, handler))


def close() -> None:
    """Take our handlers off again and close the file."""
    global _root_level
    for logger, handler in _attached:
        logger.removeHandler(handler)
        handler.close()
    _attached.clear()
    if _root_level is not None:
        logging.getLogger().setLevel(_root_level)
        _root_level = None
