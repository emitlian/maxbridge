"""JSON serialization helpers.

These helpers keep serialization behavior explicit for storage and archive
layers while allowing ``orjson`` acceleration when available.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

try:
    import orjson
except ImportError:  # pragma: no cover
    orjson = None

ModelT = TypeVar("ModelT", bound=BaseModel)


def dumps_model(model: BaseModel) -> bytes:
    """Serialize a Pydantic model into JSON bytes."""

    payload = model.model_dump(mode="json")
    if orjson is not None:
        return orjson.dumps(payload)
    return model.model_dump_json().encode("utf-8")


def loads_model(model_type: type[ModelT], payload: bytes | str) -> ModelT:
    """Deserialize JSON into the given model type."""

    if isinstance(payload, bytes):
        raw = payload.decode("utf-8")
    else:
        raw = payload
    return model_type.model_validate_json(raw)
