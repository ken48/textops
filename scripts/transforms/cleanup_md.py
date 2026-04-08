from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import mdformat.plugins
from markdown_it import MarkdownIt
from mdformat.renderer import MDRenderer

WRAP_OPTIONS = {"wrap": "keep"}
PARSER_EXTENSIONS = ("gfm",)
THEMATIC_BREAK_MARKUP = "***"

QUOTE_NORMALIZATION = str.maketrans(
    {
        "«": '"',
        "»": '"',
        "„": '"',
        "“": '"',
        "”": '"',
        "‟": '"',
        "’": "'",
        "‘": "'",
        "‚": "'",
        "‛": "'",
    }
)
SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,;:!?])")
SPACE_BEFORE_DOT_RE = re.compile(r"(?<!\d)\s+(\.)")
SPACE_AFTER_PUNCT_RE = re.compile(r"(?<!\d)([,;:!?]+)(?=[0-9A-Za-zА-Яа-яЁё])")
DASH_BETWEEN_WORDS_RE = re.compile(r"(?<=\S)\s+-\s+(?=\S)")
NUM_COLON_RE = re.compile(r"(\d)[ \t]*:[ \t]*(\d)")
MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")
SENTENCE_END_RE = re.compile(r'[.!?][]["»“”)]*$')
WORD_RE = re.compile(r"\w+", re.UNICODE)
COORDINATED_ITEM_SEPARATOR_RE = re.compile(r"\s(?:->|→|=>|:)\s")
TECHNICAL_TOKEN_RE = re.compile(
    r"(?<!\S)("
    r"(?:https?|ftp)://[^\s<>()]+"
    r"|www\.[^\s<>()]+"
    r"|[^\s/@]+(?:\.[^\s/@]+)*@[^\s/@]+\.[^\s/@]+"
    r"|(?:~|/|\./|\.\./)\S*"
    r"|[A-Za-z]:\\\S*"
    r"|\.[^\s/]+(?:/\S*)?"
    r"|(?:[^\W_]+(?:-[^\W_]+)*\.){2,}[^\W_]{2,}"
    r")(?!\S)",
    re.UNICODE,
)
OBSIDIAN_WIKILINK_RE = re.compile(r"\\\[\[(.+?)]\\]")
FULL_BOLD_HEADING_RE = re.compile(
    r"^(?P<prefix>#{1,6}[ \t]+(?:\d+[.)]?[ \t]+)?)\*\*(?P<body>.+?)\*\*(?P<suffix>[ \t]*)$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class CleanupMarkdownOptions:
    """Toggles for markdown prose cleanup."""

    normalize_quotes: bool = True
    normalize_dashes: bool = True
    normalize_time_ranges: bool = True
    normalize_punctuation_spacing: bool = True
    normalize_sentence_dot_spacing: bool = True
    collapse_inline_whitespace: bool = True
    capitalize_sentences: bool = True
    preserve_technical_tokens: bool = True
    preserve_tight_lists: bool = True
    strip_hardbreak_markup: bool = True
    normalize_bold_headings: bool = True
    restore_obsidian_wikilinks: bool = True


@dataclass
class _CollectedListItem:
    paragraph_indices: list[int]
    inline_indices: list[int]
    texts: list[str]
    paragraph_count: int


@dataclass
class _AnalyzedListItem:
    sentence_like: bool
    inline_indices: list[int]
    texts: list[str]
    paragraph_count: int


@dataclass
class _ListContext:
    paragraph_indices: list[int]
    items: list[_AnalyzedListItem]


def _render_thematic_break(_: Any, __: Any) -> str:
    return THEMATIC_BREAK_MARKUP


class _ThematicBreakRendererPlugin:
    CHANGES_AST = False
    RENDERERS = {"hr": _render_thematic_break}
    POSTPROCESSORS: dict[str, Any] = {}

    @staticmethod
    def update_mdit(_: MarkdownIt) -> None:
        return None


def _build_markdown_it(renderer_cls: type[MDRenderer]) -> MarkdownIt:
    def renderer_factory(parser: MarkdownIt) -> Any:
        return renderer_cls(parser)

    markdown_it = MarkdownIt(renderer_cls=renderer_factory)
    markdown_it.options["mdformat"] = WRAP_OPTIONS
    markdown_it.options["store_labels"] = True
    markdown_it.options["parser_extension"] = []

    for extension_name in PARSER_EXTENSIONS:
        plugin = mdformat.plugins.PARSER_EXTENSIONS[extension_name]
        if plugin in markdown_it.options["parser_extension"]:
            continue

        markdown_it.options["parser_extension"].append(plugin)
        plugin.update_mdit(markdown_it)

    markdown_it.options["codeformatters"] = {}
    markdown_it.options["parser_extension"].append(_ThematicBreakRendererPlugin)

    return markdown_it

def _is_word_char(char: str) -> bool:
    return char.isalnum() or char == "_"


def _next_non_space(text: str, start: int) -> tuple[int, str]:
    for index in range(start, len(text)):
        if not text[index].isspace():
            return index, text[index]
    return -1, ""


def _is_sentence_boundary(text: str, index: int) -> bool:
    char = text[index]
    if char not in ".!?":
        return False

    prev_char = text[index - 1] if index > 0 else ""
    next_char = text[index + 1] if index + 1 < len(text) else ""

    if char == "." and (not _is_word_char(prev_char) or _is_word_char(next_char)):
        return False

    if next_char == '"':
        _, after_quote_char = _next_non_space(text, index + 2)
        if after_quote_char and after_quote_char.isalpha() and after_quote_char.islower():
            return False

    return True


def _protect_technical_tokens(text: str) -> tuple[str, list[str]]:
    replacements: list[str] = []

    def replace(match: re.Match[str]) -> str:
        replacements.append(match.group(0))
        return f"\x00{len(replacements) - 1}\x00"

    return TECHNICAL_TOKEN_RE.sub(replace, text), replacements


def _restore_technical_tokens(text: str, replacements: list[str]) -> str:
    for index, original in enumerate(replacements):
        text = text.replace(f"\x00{index}\x00", original)
    return text


def _normalize_dot_spacing(text: str) -> str:
    result: list[str] = []

    for index, char in enumerate(text):
        result.append(char)
        if char != "." or index + 1 >= len(text):
            continue

        prev_char = text[index - 1] if index > 0 else ""
        next_char = text[index + 1]

        if next_char.isspace() or not _is_word_char(prev_char) or not next_char.isalpha():
            continue

        result.append(" ")

    return "".join(result)


def _normalize_fragment_spacing(text: str, options: CleanupMarkdownOptions) -> str:
    if options.normalize_quotes:
        text = text.translate(QUOTE_NORMALIZATION)
    if options.normalize_dashes:
        text = DASH_BETWEEN_WORDS_RE.sub(" — ", text)
    if options.normalize_time_ranges:
        text = NUM_COLON_RE.sub(r"\1:\2", text)
    if options.normalize_punctuation_spacing:
        text = SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)
        text = SPACE_BEFORE_DOT_RE.sub(r"\1", text)
        text = SPACE_AFTER_PUNCT_RE.sub(r"\1 ", text)
    if options.normalize_sentence_dot_spacing:
        text = _normalize_dot_spacing(text)
    if options.collapse_inline_whitespace:
        text = MULTI_SPACE_RE.sub(" ", text)
    return text


def _capitalize_sentences(text: str, sentence_start: bool) -> tuple[str, bool]:
    result: list[str] = []

    for index, char in enumerate(text):
        if sentence_start and char.isalpha():
            result.append(char.upper())
            sentence_start = False
            continue

        result.append(char)

        if _is_sentence_boundary(text, index):
            sentence_start = True
        elif not char.isspace() and char not in "\"'()[]{}":
            sentence_start = False

    return "".join(result), sentence_start


def _format_prose_fragment(
    text: str,
    *,
    sentence_start: bool,
    capitalize: bool,
    options: CleanupMarkdownOptions,
 ) -> tuple[str, bool]:
    replacements: list[str] = []
    if options.preserve_technical_tokens:
        text, replacements = _protect_technical_tokens(text)
    text = _normalize_fragment_spacing(text, options)
    should_capitalize = capitalize and options.capitalize_sentences
    if should_capitalize and not sentence_start:
        text = re.sub(
            r'^([.!?]\s+)([A-Za-zА-Яа-яЁё])',
            lambda match: match.group(1) + match.group(2).upper(),
            text,
            count=1,
        )
    if should_capitalize:
        text, sentence_start = _capitalize_sentences(text, sentence_start)
    else:
        _, sentence_start = _capitalize_sentences(text, sentence_start)
    if options.preserve_technical_tokens:
        text = _restore_technical_tokens(text, replacements)
    return text, sentence_start


def _looks_like_sentence(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False

    if SENTENCE_END_RE.search(stripped):
        return True

    return len(WORD_RE.findall(stripped)) >= 7


def _restore_obsidian_wikilinks(text: str) -> str:
    return OBSIDIAN_WIKILINK_RE.sub(r"[[\1]]", text)


def _strip_full_bold_heading_markup(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        return f"{match.group('prefix')}{match.group('body')}{match.group('suffix')}"

    return FULL_BOLD_HEADING_RE.sub(replace, text)


def _normalize_hardbreak_tokens(tokens: Sequence[Any]) -> None:
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


def _looks_like_coordinated_list(items: list[_AnalyzedListItem]) -> bool:
    if len(items) < 2:
        return False

    texts = [item.texts[0].strip() for item in items if item.texts]
    if len(texts) != len(items):
        return False

    if any(item.paragraph_count != 1 for item in items):
        return False

    if any(not text for text in texts):
        return False

    if any(text[0].isalpha() and text[0].isupper() for text in texts):
        return False

    if all(COORDINATED_ITEM_SEPARATOR_RE.search(text) for text in texts):
        return True

    if not any(text.endswith((",", ";")) for text in texts[:-1]):
        return False

    return all(text.endswith((",", ";")) for text in texts[:-1]) and texts[-1].endswith((".", "!", "?"))


def _looks_like_topic_list(items: list[_AnalyzedListItem]) -> bool:
    if len(items) < 2:
        return False

    texts = [item.texts[0].strip() for item in items if item.texts]
    if len(texts) != len(items):
        return False

    if any(item.paragraph_count != 1 for item in items):
        return False

    if any(not text for text in texts):
        return False

    if any(text[0].isalpha() and text[0].isupper() for text in texts):
        return False

    if any(text.endswith((".", "!", "?", ",", ";", ":")) for text in texts):
        return False

    return True


def _analyze_lists(tokens: Sequence[Any]) -> tuple[dict[int, bool], set[int]]:
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
                topic_list = _looks_like_topic_list(list_context.items)
                is_loose = not coordinated_list and not topic_list and any(
                    item.sentence_like for item in list_context.items
                )

                if coordinated_list or topic_list:
                    for item in list_context.items:
                        skip_capitalization.update(item.inline_indices)

                for paragraph_index in list_context.paragraph_indices:
                    list_looseness[paragraph_index] = is_loose

                continue

            if token.type == "list_item_close":
                collected_item = open_items.pop()
                sentence_like = collected_item.paragraph_count > 1 or any(
                    _looks_like_sentence(text) for text in collected_item.texts
                )

                if not sentence_like:
                    skip_capitalization.update(collected_item.inline_indices)

                analyzed_item = _AnalyzedListItem(
                    sentence_like=sentence_like,
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


class _InlineTextFormatter:
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
        self._sentence_start = True
        capitalize = token_index not in self._skip_capitalization

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
                    capitalize=capitalize,
                    options=self._options,
                )
                continue

            if child.type in {"softbreak", "hardbreak"}:
                self._update_state_from_literal("\n")
                continue

            literal = getattr(child, "content", "")
            if literal:
                self._update_state_from_literal(literal)


@lru_cache(maxsize=1)
def _build_markdown_formatter() -> MarkdownIt:
    return _build_markdown_it(MDRenderer)


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
        _analyze_lists(tokens) if resolved_options.preserve_tight_lists else ({}, set())
    )

    inline_formatter = _InlineTextFormatter(skip_capitalization, resolved_options)

    for index, token in enumerate(tokens):
        if token.type == "paragraph_open" and index in list_looseness:
            token.hidden = not list_looseness[index]
        elif token.type == "paragraph_close" and index in list_looseness:
            token.hidden = not list_looseness[index]

        if token.type == "inline":
            inline_formatter.apply(token, index)

    if resolved_options.strip_hardbreak_markup:
        _normalize_hardbreak_tokens(tokens)

    rendered = formatter.renderer.render(tokens, formatter.options, {})
    rendered = rendered.removesuffix("\n")
    if resolved_options.restore_obsidian_wikilinks:
        rendered = _restore_obsidian_wikilinks(rendered)
    if resolved_options.normalize_bold_headings:
        rendered = _strip_full_bold_heading_markup(rendered)

    return rendered
