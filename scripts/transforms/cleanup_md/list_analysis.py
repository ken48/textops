from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .sentence_boundaries import _count_sentence_boundaries

SHORT_LIST_ITEM_MAX_CHARS = 75
COORDINATED_ITEM_SEPARATOR_RE = re.compile(r"\s(?:->|→|=>|:)\s")


@dataclass
class _CollectedListItem:
    paragraph_indices: list[int]
    inline_indices: list[int]
    texts: list[str]
    paragraph_count: int


@dataclass
class _AnalyzedListItem:
    long_enough_to_loosen: bool
    inline_indices: list[int]
    texts: list[str]
    paragraph_count: int


@dataclass
class _ListContext:
    paragraph_indices: list[int]
    items: list[_AnalyzedListItem]


def normalize_hardbreak_tokens(tokens: Sequence[Any]) -> None:
    for token in tokens:
        children = getattr(token, "children", None)
        if not children:
            continue

        for child in children:
            if child.type != "hardbreak":
                continue

            child.type = "softbreak"
            child.tag = ""
            child.markup = ""


def _coordinated_list_texts(items: list[_AnalyzedListItem]) -> list[str] | None:
    if len(items) < 2:
        return None

    texts = [item.texts[0].strip() for item in items if item.texts]
    if len(texts) != len(items):
        return None

    if any(item.paragraph_count != 1 for item in items):
        return None

    if any(not text for text in texts):
        return None

    return texts


def _looks_like_coordinated_list(items: list[_AnalyzedListItem]) -> bool:
    texts = _coordinated_list_texts(items)
    if texts is None:
        return False

    if all(COORDINATED_ITEM_SEPARATOR_RE.search(text) for text in texts):
        return True

    if not any(text.endswith((",", ";")) for text in texts[:-1]):
        return False

    return all(text.endswith((",", ";")) for text in texts[:-1]) and texts[-1].endswith(
        (".", "!", "?")
    )


def analyze_lists(tokens: Sequence[Any]) -> tuple[dict[int, bool], set[int]]:
    list_looseness: dict[int, bool] = {}
    skip_capitalization: set[int] = set()

    def collect(tokens_list: Sequence[Any]) -> None:
        stack: list[_ListContext] = []
        open_items: list[_CollectedListItem] = []

        for index, token in enumerate(tokens_list):
            if token.type in {"bullet_list_open", "ordered_list_open"}:
                stack.append(_ListContext(paragraph_indices=[], items=[]))
                continue

            if token.type in {"bullet_list_close", "ordered_list_close"}:
                list_context = stack.pop()
                coordinated_list = _looks_like_coordinated_list(list_context.items)
                is_loose = any(
                    item.long_enough_to_loosen for item in list_context.items
                )

                if coordinated_list:
                    for item in list_context.items:
                        skip_capitalization.update(item.inline_indices)

                for paragraph_index in list_context.paragraph_indices:
                    list_looseness[paragraph_index] = is_loose

                continue

            if token.type == "list_item_close":
                collected_item = open_items.pop()
                has_sentence_boundary = any(
                    _count_sentence_boundaries(text) > 0
                    for text in collected_item.texts
                )
                if not has_sentence_boundary:
                    skip_capitalization.update(collected_item.inline_indices)

                analyzed_item = _AnalyzedListItem(
                    long_enough_to_loosen=collected_item.paragraph_count > 1
                    or any(
                        len(text.strip()) > SHORT_LIST_ITEM_MAX_CHARS
                        for text in collected_item.texts
                    ),
                    inline_indices=collected_item.inline_indices,
                    texts=collected_item.texts,
                    paragraph_count=collected_item.paragraph_count,
                )

                stack[-1].items.append(
                    analyzed_item
                )
                stack[-1].paragraph_indices.extend(collected_item.paragraph_indices)

                continue

            if token.type == "list_item_open":
                open_items.append(
                    _CollectedListItem(
                        paragraph_indices=[],
                        inline_indices=[],
                        texts=[],
                        paragraph_count=0,
                    )
                )

                continue

            if token.type == "paragraph_open" and open_items:
                open_items[-1].paragraph_count += 1
                open_items[-1].paragraph_indices.append(index)

                continue

            if token.type == "paragraph_close" and open_items:
                open_items[-1].paragraph_indices.append(index)

                continue

            if token.type == "inline" and open_items:
                open_items[-1].inline_indices.append(index)
                open_items[-1].texts.append(token.content)

    collect(tokens)

    return list_looseness, skip_capitalization
