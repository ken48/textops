from __future__ import annotations

from typing import Any

from .cleanup_options import CleanupMarkdownOptions
from .prose_cleanup import _format_prose_fragment
from .sentence_boundaries import _capitalize_sentences


class InlineTextFormatter:
    def __init__(
        self,
        skip_capitalization: set[int],
        options: CleanupMarkdownOptions,
    ) -> None:
        self._sentence_start = True
        self._link_stack: list[str | None] = []
        self._skip_capitalization = skip_capitalization
        self._options = options

    def _update_state_from_literal(self, text: str) -> None:
        _, self._sentence_start = _capitalize_sentences(text, self._sentence_start)

    def _inside_link(self) -> bool:
        return bool(self._link_stack)

    def apply(self, inline_token: Any, token_index: int) -> None:
        self._sentence_start = token_index not in self._skip_capitalization

        if not inline_token.children:
            return

        for child in inline_token.children:
            if child.type == "link_open":
                self._link_stack.append((child.attrs or {}).get("href"))
                continue

            if child.type == "link_close":
                if self._link_stack:
                    self._link_stack.pop()
                continue

            if child.type == "text":
                if self._inside_link():
                    self._update_state_from_literal(child.content)
                    continue

                (
                    child.content,
                    self._sentence_start,
                ) = _format_prose_fragment(
                    child.content,
                    sentence_start=self._sentence_start,
                    options=self._options,
                )
                continue

            if child.type in {"softbreak", "hardbreak"}:
                self._update_state_from_literal("\n")
                continue

            literal = getattr(child, "content", "")
            if literal:
                self._update_state_from_literal(literal)
