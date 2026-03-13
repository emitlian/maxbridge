"""Project exceptions.

The exception hierarchy is intentionally small so public error handling remains
predictable for CLI flows, bot flows, and future library consumers.
"""


class MaxBridgeError(Exception):
    """Base MAXBRIDGE exception."""


class ConfigError(MaxBridgeError):
    """Invalid or missing configuration."""


class TransportUnavailableError(MaxBridgeError):
    """Raised when a transport adapter is unavailable."""


class AuthorizationUnavailableError(MaxBridgeError):
    """Raised when login/auth integration is unavailable."""


class StorageError(MaxBridgeError):
    """Raised on storage failures."""


class ArchiveError(MaxBridgeError):
    """Raised on archive failures."""


class BridgeBindingError(MaxBridgeError):
    """Raised on bridge binding failures."""


class OwnerAccessDeniedError(MaxBridgeError):
    """Raised when a Telegram user is not allowed to control the bot."""


class ConfirmationRequiredError(MaxBridgeError):
    """Raised when a sensitive action requires confirmation."""


class CommandError(MaxBridgeError):
    """Raised on invalid command input."""
