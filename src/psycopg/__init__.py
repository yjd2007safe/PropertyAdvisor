"""Lightweight psycopg compatibility shim for test/mock environments."""


class Error(Exception):
    """Base psycopg error."""


class OperationalError(Error):
    """Operational/connectivity error."""


def connect(*args, **kwargs):
    raise OperationalError("psycopg is not installed in this environment")
