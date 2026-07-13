"""Small durable atomic-JSON writer shared by regeneration fixups."""
import json
import os
from pathlib import Path
import shutil


def atomic_json_dump(path, value, *, indent=None):
    """Fully close a same-directory temporary file before replacing ``path``."""
    destination = Path(path)
    temporary = destination.with_name(destination.name + ".tmp_atomic_write")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=indent)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, destination)


def atomic_file_copy(source, destination):
    """Durably copy a nonempty JSON file without exposing a partial target."""
    source = Path(source)
    destination = Path(destination)
    with source.open("r", encoding="utf-8") as source_json_stream:
        source_value = json.load(source_json_stream)
    if not source_value:
        raise ValueError(f"refusing to copy empty JSON source: {source}")
    temporary = destination.with_name(destination.name + ".tmp_atomic_copy")
    with source.open("rb") as source_stream, temporary.open("wb") as destination_stream:
        shutil.copyfileobj(source_stream, destination_stream)
        destination_stream.flush()
        os.fsync(destination_stream.fileno())
    os.replace(temporary, destination)
    with destination.open("r", encoding="utf-8") as destination_json_stream:
        destination_value = json.load(destination_json_stream)
    if not destination_value:
        raise ValueError(f"atomic copy produced empty JSON destination: {destination}")
    if destination_value != source_value:
        raise ValueError(f"atomic copy JSON mismatch: {source} -> {destination}")


def atomic_binary_copy(source, destination):
    """Durably copy any nonempty file through a same-directory temporary."""
    source = Path(source)
    destination = Path(destination)
    if source.stat().st_size <= 0:
        raise ValueError(f"refusing to copy empty source: {source}")
    temporary = destination.with_name(destination.name + ".tmp_atomic_copy")
    with source.open("rb") as source_stream, temporary.open("wb") as destination_stream:
        shutil.copyfileobj(source_stream, destination_stream)
        destination_stream.flush()
        os.fsync(destination_stream.fileno())
    os.replace(temporary, destination)
    if destination.stat().st_size != source.stat().st_size:
        raise ValueError(f"atomic binary copy size mismatch: {source} -> {destination}")
