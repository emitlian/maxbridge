"""Media helpers and placeholders.

Media transfer is intentionally left unimplemented until a safe MAX adapter
contract exists for upload and download semantics.
"""

from __future__ import annotations

from maxbridge.core.exceptions import TransportUnavailableError


class MediaAPI:
    """Media layer placeholder pending safe adapter support."""

    async def upload(self) -> None:
        """Raise a clear error for unsupported media upload behavior."""

        raise TransportUnavailableError(
            "Media upload/download support depends on adapter capabilities and is not implemented yet."
        )
