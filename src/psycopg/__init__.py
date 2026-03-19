"""Minimal psycopg stub for local test execution in this repository."""


class Error(Exception):
    """Base psycopg error."""


class OperationalError(Error):
    """Operational connection/query error."""


def connect(*args, **kwargs):  # pragma: no cover - exercised via monkeypatch in tests
    raise OperationalError("psycopg is not installed in this environment")
