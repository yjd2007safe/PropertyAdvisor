from __future__ import annotations

"""Comparable selection utilities."""

from typing import Any


def build_comparable_set(
    subject_property: dict[str, Any], candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return an initial comparable set placeholder.

    MVP behavior keeps all candidates and leaves scoring logic for follow-up work.
    """

    _ = subject_property
    return candidates
