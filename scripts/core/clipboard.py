from __future__ import annotations

import time
from typing import Any

from AppKit import NSPasteboard, NSPasteboardItem, NSPasteboardTypeString

# A snapshot is a list of per-item {type: NSData} dicts covering every
# pasteboard representation (text, images, files), not just plain text.
ClipboardSnapshot = list[dict[str, Any]]


class ClipboardError(RuntimeError):
    """Base error for clipboard synchronization failures."""


class ClipboardTimeoutError(ClipboardError):
    pass


class ClipboardContentError(ClipboardError):
    pass


def clipboard_change_count() -> int:
    return NSPasteboard.generalPasteboard().changeCount()


def wait_for_clipboard_change(previous_count: int, timeout: float = 0.5) -> str:
    """Wait for a new pasteboard write and return its string payload.

    Phase 1: wait up to ``timeout`` for ``changeCount`` to advance past
    ``previous_count`` (the copy may still be in flight).
    Phase 2: once it advances, wait for the string payload to become available
    before the same deadline.

    Raises ``ClipboardTimeoutError`` if nothing is copied within ``timeout`` or
    if the string payload is not ready before the deadline. Raises
    ``ClipboardContentError`` if the new clipboard contents are not text.
    """
    pasteboard = NSPasteboard.generalPasteboard()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pasteboard.changeCount() != previous_count:
            return _read_string_payload(pasteboard, deadline, timeout)
        time.sleep(0.01)
    raise ClipboardTimeoutError(
        f'clipboard did not change within {timeout:.3f} sec'
    )


def _read_string_payload(pasteboard: Any, deadline: float, timeout: float) -> str:
    while True:
        has_string_type = (
            pasteboard.availableTypeFromArray_([NSPasteboardTypeString]) is not None
        )
        if has_string_type:
            value = pasteboard.stringForType_(NSPasteboardTypeString)
            if value is not None:
                return str(value)
        if time.monotonic() >= deadline:
            if not has_string_type:
                raise ClipboardContentError(
                    'clipboard changed but contains no text; '
                    f'types={_pasteboard_type_names(pasteboard)}'
                )
            raise ClipboardTimeoutError(
                f'clipboard text was not available within {timeout:.3f} sec'
            )
        time.sleep(0.01)


def _pasteboard_type_names(pasteboard: Any) -> str:
    try:
        types = pasteboard.types() or []
    except Exception:
        return 'unknown'
    return ', '.join(str(item_type) for item_type in types) or 'none'


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
