from __future__ import annotations

import time
from typing import Any

from AppKit import NSPasteboard, NSPasteboardItem, NSPasteboardTypeString

# A snapshot is a list of per-item {type: NSData} dicts covering every
# pasteboard representation (text, images, files), not just plain text.
ClipboardSnapshot = list[dict[str, Any]]


def clipboard_change_count() -> int:
    return NSPasteboard.generalPasteboard().changeCount()


def wait_for_clipboard_change(previous_count: int, timeout: float = 0.5) -> bool:
    """Wait until the pasteboard is rewritten (e.g. by a pending Cmd+C).

    Returns False if nothing landed on the pasteboard within ``timeout`` —
    the caller should abort instead of reading stale clipboard contents.
    """
    pasteboard = NSPasteboard.generalPasteboard()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pasteboard.changeCount() != previous_count:
            return True
        time.sleep(0.01)
    return False


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
