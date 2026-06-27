from __future__ import annotations

from functools import lru_cache
from typing import Any

from markdown_it import MarkdownIt

from .cleanup_options import CleanupMarkdownOptions
from .inline_text_formatter import InlineTextFormatter
from .list_analysis import analyze_lists, normalize_hardbreak_tokens
from .markdown_postprocess import (
    restore_obsidian_wikilinks,
    strip_full_bold_heading_markup,
)
from .markdown_rendering import build_markdown_it
from .sentence_boundaries import _count_sentence_boundaries


@lru_cache(maxsize=1)
def _build_markdown_formatter() -> MarkdownIt:
    return build_markdown_it()


def cleanup_markdown(
    text: str,
    options: CleanupMarkdownOptions | None = None,
) -> str:
    resolved_options = options
    if resolved_options is None:
        resolved_options = CleanupMarkdownOptions()

    formatter = _build_markdown_formatter()
    tokens: list[Any] = formatter.parse(text)

    list_looseness, skip_capitalization = (
        analyze_lists(tokens) if resolved_options.preserve_tight_lists else ({}, set())
    )

    inline_formatter = InlineTextFormatter(skip_capitalization, resolved_options)

    for index, token in enumerate(tokens):
        if token.type == "paragraph_open" and index in list_looseness:
            token.hidden = not list_looseness[index]
        elif token.type == "paragraph_close" and index in list_looseness:
            token.hidden = not list_looseness[index]

        if token.type == "inline":
            inline_formatter.apply(token, index)

    if resolved_options.strip_hardbreak_markup:
        normalize_hardbreak_tokens(tokens)

    rendered = formatter.renderer.render(tokens, formatter.options, {})
    rendered = rendered.removesuffix("\n")
    if resolved_options.restore_obsidian_wikilinks:
        rendered = restore_obsidian_wikilinks(rendered)
    if resolved_options.normalize_bold_headings:
        rendered = strip_full_bold_heading_markup(rendered)

    return rendered
