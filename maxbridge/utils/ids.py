"""Stable ID and digest helpers.

Stable identifiers are used throughout the repository for sessions, bindings,
artifacts, dedupe records, and audit events.
"""

from __future__ import annotations

import hashlib


def stable_digest(*parts: object) -> str:
    """Return a deterministic digest over a sequence of values."""

    payload = "::".join(str(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def stable_id(prefix: str, *parts: object, length: int = 16) -> str:
    """Return a compact stable identifier."""

    return f"{prefix}_{stable_digest(*parts)[:length]}"
