"""Authentication state models.

These models describe the experimental auth boundary and intentionally keep the
state surface small until a safe MAX login approach is available.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class AuthState(str, Enum):
    """Possible states for the experimental auth layer."""

    LOGGED_OUT = "logged_out"
    PENDING = "pending"
    LOGGED_IN = "logged_in"
    UNSUPPORTED = "unsupported"


class AuthSessionState(BaseModel):
    """Current state of the experimental auth session."""

    model_config = ConfigDict(extra="forbid")

    state: AuthState = AuthState.UNSUPPORTED
    detail: str = "No safe MAX auth adapter installed."
