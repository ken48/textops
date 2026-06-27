from __future__ import annotations

import re

OBSIDIAN_WIKILINK_RE = re.compile(r"\\\[\[(.+?)]\\]")
FULL_BOLD_HEADING_RE = re.compile(
    r"^(?P<prefix>#{1,6}[ \t]+(?:\d+[.)]?[ \t]+)?)\*\*(?P<body>.+?)\*\*(?P<suffix>[ \t]*)$",
    re.MULTILINE,
)


def restore_obsidian_wikilinks(text: str) -> str:
    return OBSIDIAN_WIKILINK_RE.sub(r"[[\1]]", text)


def strip_full_bold_heading_markup(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        return f"{match.group('prefix')}{match.group('body')}{match.group('suffix')}"

    return FULL_BOLD_HEADING_RE.sub(replace, text)
