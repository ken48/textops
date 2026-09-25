from __future__ import annotations

from markdown_it.token import Token

from .cleanup_options import CleanupMarkdownOptions
from .obsidian_wikilinks import TOKEN_TYPE as OBSIDIAN_WIKILINK_TOKEN_TYPE
from .prose_cleanup import (
    DASH_SEPARATOR_RE,
    LEFT_SPACED_HYPHEN_RE,
    TECHNICAL_TOKEN_RE,
)


def _text_token(content: str) -> Token:
    token = Token("text", "", 0)
    token.content = content
    return token


def _move_boundary_spaces(children: list[Token]) -> list[Token]:
    """Keep spaces outside emphasis delimiters so they remain valid Markdown."""
    result: list[Token] = []
    index = 0
    while index < len(children):
        opening = children[index]
        if opening.type not in {"em_open", "strong_open", "s_open"}:
            result.append(opening)
            index += 1
            continue

        closing_type = opening.type.replace("_open", "_close")
        depth = 1
        end = index + 1
        while end < len(children):
            if children[end].type == opening.type:
                depth += 1
            elif children[end].type == closing_type:
                depth -= 1
                if depth == 0:
                    break
            end += 1

        body = _move_boundary_spaces(children[index + 1 : end])
        leading = ""
        trailing = ""
        for token in body:
            if token.type != "text":
                break
            trimmed = token.content.lstrip(" \t")
            leading += token.content[: len(token.content) - len(trimmed)]
            token.content = trimmed
            if trimmed:
                break
        for token in reversed(body):
            if token.type != "text":
                break
            trimmed = token.content.rstrip(" \t")
            trailing = token.content[len(trimmed) :] + trailing
            token.content = trimmed
            if trimmed:
                break

        if leading:
            result.append(_text_token(leading))
        result.extend([opening, *body, children[end]])
        if trailing:
            result.append(_text_token(trailing))
        index = end + 1
    return result


def normalize_inline_dashes(
    children: list[Token], options: CleanupMarkdownOptions
) -> list[Token]:
    """Find edits in unformatted text and map them back to editable characters."""
    chars: list[str] = []
    positions: list[tuple[int, int] | None] = []
    link_depth = 0
    for index, token in enumerate(children):
        if token.type == "link_open":
            link_depth += 1
        elif token.type == "link_close":
            link_depth -= 1
        elif token.type in {"text", "code_inline"}:
            chars.extend(token.content)
            editable = token.type == "text" and not link_depth
            positions.extend(
                (index, offset) if editable else None
                for offset in range(len(token.content))
            )
        elif token.type in {"softbreak", "hardbreak", "html_inline"}:
            # Do not join prose across breaks or opaque HTML.
            chars.append("\n")
            positions.append(None)
        elif token.type in {"image", OBSIDIAN_WIKILINK_TOKEN_TYPE}:
            chars.append("\ufffc")
            positions.append(None)

    text = "".join(chars)
    if options.preserve_technical_tokens:
        for match in TECHNICAL_TOKEN_RE.finditer(text):
            positions[match.start() : match.end()] = [None] * len(match.group())

    fragments = [list(token.content) for token in children]
    occupied: set[int] = set()
    for pattern, replacement in (
        (DASH_SEPARATOR_RE, " — "),
        (LEFT_SPACED_HYPHEN_RE, "-"),
    ):
        for match in pattern.finditer(text):
            start, end = match.span()
            if any(positions[i] is None or i in occupied for i in range(start, end)):
                continue
            # Keep the dash in its original formatting span. Boundary spaces
            # are subsequently moved outside emphasis delimiters.
            dash = next(i for i in range(start, end) if chars[i] in "-—")
            for i in range(start, end):
                position = positions[i]
                assert position is not None
                token_index, offset = position
                fragments[token_index][offset] = replacement if i == dash else ""
            occupied.update(range(start, end))

    if not occupied:
        return children

    for token, fragment in zip(children, fragments):
        token.content = "".join(fragment)
    return _move_boundary_spaces(children)
