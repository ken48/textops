from __future__ import annotations

import time
from typing import Any

from AppKit import NSPasteboard, NSPasteboardItem, NSPasteboardTypeString

# A snapshot is a list of per-item {type: NSData} dicts covering every
# pasteboard representation (text, images, files), not just plain text.
ClipboardSnapshot = list[dict[str, Any]]


def clipboard_change_count() -> int:
    return NSPasteboard.generalPasteboard().changeCount()


def wait_for_clipboard_change(previous_count: int, timeout: float = 0.5) -> str | None:
    """Wait for a new pasteboard write and return its string payload.

    Phase 1: wait up to ``timeout`` for ``changeCount`` to advance past
    ``previous_count`` (the copy may still be in flight).
    Phase 2: once it advances, read the string payload. A pasteboard declares its
    types atomically with the change, so we use the presence of a string type to
    tell a non-text clipboard (an image — give up at once) from a text clipboard
    whose value is still being materialized asynchronously (poll until ready).

    Returns the copied string, or ``None`` if nothing was copied within ``timeout``
    or the new clipboard contents are not text.
    """
    pasteboard = NSPasteboard.generalPasteboard()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pasteboard.changeCount() != previous_count:
            return _read_string_payload(pasteboard, deadline)
        time.sleep(0.01)
    return None


def _read_string_payload(pasteboard: Any, deadline: float) -> str | None:
    while True:
        if pasteboard.availableTypeFromArray_([NSPasteboardTypeString]) is None:
            return None
        value = pasteboard.stringForType_(NSPasteboardTypeString)
        if value is not None:
            return str(value)
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.01)


def read_clipboard() -> str:
    value = NSPasteboard.generalPasteboard().stringForType_(NSPasteboardTypeString)
    return str(value) if value is not None else ''


def write_clipboard(text: str) -> None:
    pasteboard = NSPasteboard.generalPasteboard()
    pasteboard.clearContents()
    pasteboard.setString_forType_(text, NSPasteboardTypeString)


def snapshot_clipboard() -> ClipboardSnapshot:
    snapshot: ClipboardSnapshot = []
    for item in NSPasteboard.generalPasteboard().pasteboardItems() or []:
        data_by_type: dict[str, Any] = {}
        for item_type in item.types() or []:
            data = item.dataForType_(item_type)
            if data is not None:
                data_by_type[str(item_type)] = data
        if data_by_type:
            snapshot.append(data_by_type)
    return snapshot


def restore_clipboard(snapshot: ClipboardSnapshot) -> None:
    pasteboard = NSPasteboard.generalPasteboard()
    pasteboard.clearContents()
    items = []
    for data_by_type in snapshot:
        item = NSPasteboardItem.alloc().init()
        for item_type, data in data_by_type.items():
            item.setData_forType_(data, item_type)
        items.append(item)
    if items:
        pasteboard.writeObjects_(items)
