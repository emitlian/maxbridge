"""Experimental auth placeholder.

The repository intentionally ships a placeholder instead of an unsafe MAX login
flow. This makes the experimental boundary explicit and reviewable.
"""

from __future__ import annotations

from maxbridge.auth.base import AuthAdapter
from maxbridge.auth.state import AuthSessionState, AuthState
from maxbridge.core.exceptions import AuthorizationUnavailableError


class ExperimentalAuthAdapter(AuthAdapter):
    """Placeholder adapter until a safe public auth strategy exists."""

    async def get_state(self) -> AuthSessionState:
        """Return an explicit unsupported state for the experimental auth layer."""

        return AuthSessionState(
            state=AuthState.UNSUPPORTED,
            detail="Interactive MAX login is intentionally left unimplemented in the OSS core.",
        )

    async def start_login(self) -> AuthSessionState:
        """Fail clearly instead of implying hidden MAX login support."""

        raise AuthorizationUnavailableError(
            "No safe public MAX login adapter is included. Provide an explicit local adapter."
        )

    async def logout(self) -> None:
        """No-op placeholder for future explicit logout behavior."""

        return None
