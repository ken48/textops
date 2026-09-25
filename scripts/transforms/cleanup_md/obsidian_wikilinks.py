from __future__ import annotations

from typing import Any

from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline
from mdformat.renderer import RenderContext, RenderTreeNode

TOKEN_TYPE = "obsidian_wikilink"


def _parse_obsidian_wikilink(state: StateInline, silent: bool) -> bool:
    start = state.pos
    if state.src.startswith("![[", start):
        target_start = start + 3
    elif state.src.startswith("[[", start):
        target_start = start + 2
    else:
        return False

    end = state.src.find("]]", target_start)
    if (
        end < 0
        or end == target_start
        or any(char in state.src[target_start:end] for char in "\r\n")
    ):
        return False

    state.pos = end + 2
    if silent:
        return True

    token = state.push(TOKEN_TYPE, "", 0)
    token.content = state.src[start : state.pos]
    return True


def _render_obsidian_wikilink(
    node: RenderTreeNode,
    _: RenderContext,
) -> str:
    return node.content


class ObsidianWikilinkPlugin:
    CHANGES_AST = False
    RENDERERS = {TOKEN_TYPE: _render_obsidian_wikilink}
    POSTPROCESSORS: dict[str, Any] = {}

    @staticmethod
    def update_mdit(markdown_it: MarkdownIt) -> None:
        markdown_it.inline.ruler.before(
            "link",
            TOKEN_TYPE,
            _parse_obsidian_wikilink,
        )
