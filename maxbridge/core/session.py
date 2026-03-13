"""Session state helpers.

Session metadata is stable runtime state. It records which adapter was used and
which account identity was seen without storing opaque adapter internals here.
"""

from __future__ import annotations

from maxbridge.core.models import Session
from maxbridge.utils.ids import stable_id
from maxbridge.utils.time import utc_now


class SessionManager:
    """Maintain local session metadata."""

    def __init__(self, *, session_name: str, adapter: str) -> None:
        """Create a session manager for one named local runtime."""

        self._session_name = session_name
        self._adapter = adapter
        self._session: Session | None = None

    @property
    def current(self) -> Session | None:
        """Return the active session metadata if one exists."""

        return self._session

    def load_or_create(self, account_id: str | None) -> Session:
        """Return the active session record, creating or refreshing it as needed."""

        if self._session is None:
            self._session = Session(
                id=stable_id("session", self._session_name, account_id or "anonymous"),
                account_id=account_id,
                adapter=self._adapter,
            )
        else:
            # Session identity stays stable while account metadata can refresh.
            self._session = self._session.model_copy(
                update={"account_id": account_id, "updated_at": utc_now()}
            )
        return self._session
