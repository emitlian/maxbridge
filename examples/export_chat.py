"""Export all locally indexed chats.

This example shows that archive export works from the stable local index rather
than from a live MAX connection.
"""

from __future__ import annotations

import asyncio

from maxbridge.archive.exporter import ArchiveExporter
from maxbridge.core.client import MaxBridgeClient


async def main() -> None:
    """Populate the local index and export all known chats."""

    async with MaxBridgeClient.from_config("config.toml") as client:
        await client.get_chats()
        for chat in await client.get_chats():
            await client.get_history(chat.id, limit=client.config.core.max_batch_size)
        exporter = ArchiveExporter(client.store, client.config.archive.export_dir)
        paths = await exporter.export_all_json()
        for path in paths:
            print(path)


if __name__ == "__main__":
    asyncio.run(main())
