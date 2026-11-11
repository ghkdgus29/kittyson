import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kittyson import logs
from kittyson.config import settings
from kittyson.main import app


def file_handlers(name: str | None = None) -> list[RotatingFileHandler]:
    return [h for h in logging.getLogger(name).handlers if isinstance(h, RotatingFileHandler)]


@pytest.fixture
def log_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    yield tmp_path / "logs"
    for name in (None, *logs.UVICORN_LOGGERS):
        for handler in file_handlers(name):
            logging.getLogger(name).removeHandler(handler)
            handler.close()


@pytest.fixture
def under_uvicorn(monkeypatch: pytest.MonkeyPatch):
    """What uvicorn's own logging setup does before the app starts."""
    for name in logs.UVICORN_LOGGERS:
        monkeypatch.setattr(logging.getLogger(name), "propagate", False)


def test_app_and_uvicorn_lines_reach_the_file(log_dir: Path, under_uvicorn):
    logs.configure()
    logging.getLogger("kittyson.cats").info("cat of the day")
    logging.getLogger("uvicorn.access").info("GET /api/widget 200")
    logging.getLogger("uvicorn.error").info("Application startup complete.")

    lines = (log_dir / "app.log").read_text(encoding="utf-8").splitlines()
    assert [line.split(" ", 2)[2] for line in lines] == [
        "INFO kittyson.cats: cat of the day",
        "INFO uvicorn.access: GET /api/widget 200",
        "INFO uvicorn.error: Application startup complete.",
    ]


def test_uvicorn_lines_are_written_once_when_they_reach_the_root_logger(log_dir: Path):
    logs.configure()
    logging.getLogger("uvicorn.access").info("GET / 200")
    assert (log_dir / "app.log").read_text(encoding="utf-8").count("GET / 200") == 1


def test_file_is_capped_by_the_settings(log_dir: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "log_max_mb", 2)
    monkeypatch.setattr(settings, "log_backups", 1)
    logs.configure()
    (handler,) = file_handlers()
    assert (handler.maxBytes, handler.backupCount) == (2 * 1024 * 1024, 1)


def test_old_lines_are_dropped_once_the_cap_is_reached(log_dir: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "log_backups", 1)
    logs.configure()
    (handler,) = file_handlers()
    handler.maxBytes = 2000  # a small cap, so the test does not have to write megabytes
    for i in range(200):
        logging.getLogger("kittyson").info("line %03d %s", i, "x" * 60)

    files = sorted(p.name for p in log_dir.iterdir())
    assert files == ["app.log", "app.log.1"]
    assert sum(p.stat().st_size for p in log_dir.iterdir()) <= 2 * 2000
    assert "line 199" in (log_dir / "app.log").read_text(encoding="utf-8")


def test_starting_the_app_again_does_not_write_twice(log_dir: Path):
    for _ in range(2):
        with TestClient(app):
            pass
    logging.getLogger("kittyson").info("once")
    assert len(file_handlers()) == 1
    assert (log_dir / "app.log").read_text(encoding="utf-8").count("once") == 1


def test_the_app_logs_while_it_runs(log_dir: Path):
    with TestClient(app):
        logging.getLogger("kittyson").info("running")
    assert "INFO kittyson: running" in (log_dir / "app.log").read_text(encoding="utf-8")
