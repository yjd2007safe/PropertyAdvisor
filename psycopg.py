"""Minimal local psycopg compatibility shim for offline test environments."""

from __future__ import annotations


class Error(Exception):
    """Base psycopg-compatible error."""


class OperationalError(Error):
    """Operational psycopg-compatible error."""


def connect(*args, **kwargs):
    raise OperationalError("psycopg is not installed in this environment.")
