"""Minimal local psycopg compatibility shim for offline test environments.

This project monkeypatches ``psycopg.connect`` extensively in unit tests. The
real dependency is optional in this repository snapshot, so provide the minimum
surface required for imports and monkeypatching when the wheel is unavailable.
"""

from __future__ import annotations


class Error(Exception):
    """Base psycopg-compatible error."""


class OperationalError(Error):
    """Operational psycopg-compatible error."""


def connect(*args, **kwargs):
    raise OperationalError("psycopg is not installed in this environment.")
