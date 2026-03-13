"""Authentication adapter interface.

Authentication remains outside the stable core because a safe public MAX login
flow may not exist or may evolve independently from the rest of the project.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from maxbridge.auth.state import AuthSessionState


class AuthAdapter(ABC):
    """Abstract auth adapter for experimental MAX login flows."""

    @abstractmethod
    async def get_state(self) -> AuthSessionState:
        """Return current auth state."""

    @abstractmethod
    async def start_login(self) -> AuthSessionState:
        """Begin an interactive login flow."""

    @abstractmethod
    async def logout(self) -> None:
        """Log out the active local session."""
