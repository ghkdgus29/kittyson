"""One record a day, kept in a file named after the day: <directory>/YYYY-MM-DD.json.

This is the only place that knows where a day's files are. Everything else hands a record
to the store, or asks it for one.
"""

import json
import logging
from datetime import date
from itertools import islice
from pathlib import Path

from pydantic import BaseModel

log = logging.getLogger(__name__)


class DayRecord(BaseModel):
    day: date


def write(path: Path, data: bytes) -> None:
    """The whole file or none of it: a reader never finds half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


class DayStore[T: DayRecord]:
    def __init__(self, directory: Path, model: type[T]):
        self._dir = directory
        self._model = model
        self._loaded: dict[date, T] = {}  # a saved record does not change, so it is read from disk once

    def path(self, day: date, suffix: str = ".json") -> Path:
        return self._dir / f"{day.isoformat()}{suffix}"

    def load(self, day: date) -> T | None:
        if day in self._loaded:
            return self._loaded[day]
        path = self.path(day)
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            record = self._model.model_validate({**saved, "day": day})
        except FileNotFoundError:
            return None
        except (ValueError, TypeError) as exc:  # not JSON, or not the fields of this record
            log.warning("unreadable %s: %s", path, exc)
            return None
        self._loaded[day] = record
        return record

    def save(self, record: T) -> None:
        write(self.path(record.day), record.model_dump_json(indent=2).encode())
        self._loaded[record.day] = record

    def days(self) -> list[date]:
        """The saved days, newest first."""
        days = []
        for path in self._dir.glob("*.json"):
            try:
                days.append(date.fromisoformat(path.stem))
            except ValueError:
                continue
        return sorted(days, reverse=True)

    def before(self, day: date, limit: int | None = None) -> list[T]:
        """The records of the days before `day`, newest first."""
        records = (self.load(past) for past in self.days() if past < day)
        return list(islice((record for record in records if record), limit))
