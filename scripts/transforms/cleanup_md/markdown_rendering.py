from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from types import MappingProxyType
from typing import Any

import mdformat.plugins
from markdown_it import MarkdownIt
from mdformat.renderer import DEFAULT_RENDERERS, MDRenderer, RenderContext, RenderTreeNode
from mdformat.renderer._util import get_list_marker_type, is_tight_list, is_tight_list_item

WRAP_OPTIONS = {"wrap": "keep", "number": True}
PARSER_EXTENSIONS = ("gfm",)
THEMATIC_BREAK_MARKUP = "***"


def _render_thematic_break(_: Any, __: Any) -> str:
    return THEMATIC_BREAK_MARKUP


class _ThematicBreakRendererPlugin:
    CHANGES_AST = False
    RENDERERS = {"hr": _render_thematic_break}
    POSTPROCESSORS: dict[str, Any] = {}

    @staticmethod
    def update_mdit(_: MarkdownIt) -> None:
        return None


def _render_list_item(node: Any, context: Any) -> str:
    default_separator = "\n" if is_tight_list_item(node) else "\n\n"
    parts: list[str] = []

    for child in node.children:
        rendered_child = child.render(context)
        if not rendered_child:
            continue

        if parts:
            separator = (
                "\n\n"
                if child.type in {"bullet_list", "ordered_list"}
                else default_separator
            )
            parts.append(separator)

        parts.append(rendered_child)

    text = "".join(parts)
    if not text.strip():
        return ""
    return text


def _list_item_ends_with_nested_list(node: RenderTreeNode) -> bool:
    for child in reversed(node.children):
        if child.type in {"bullet_list", "ordered_list"}:
            return True
        if child.type not in {"softbreak", "hardbreak"}:
            return False
    return False


def _list_block_separator(is_tight: bool, item: RenderTreeNode) -> str:
    if not is_tight or _list_item_ends_with_nested_list(item):
        return "\n\n"
    return "\n"


def _format_list_item_lines(
    list_item_text: str,
    first_line_prefix: str,
    continuation_prefix: str,
) -> str:
    formatted_lines = []
    line_iterator = iter(list_item_text.split("\n"))
    first_line = next(line_iterator)
    formatted_lines.append(
        f"{first_line_prefix}{first_line}" if first_line else first_line_prefix.rstrip()
    )
    for line in line_iterator:
        formatted_lines.append(f"{continuation_prefix}{line}" if line else "")
    return "\n".join(formatted_lines)


def _render_list(
    node: RenderTreeNode,
    context: RenderContext,
    indent_width: int,
    item_prefixes: Sequence[str],
) -> str:
    continuation_prefix = " " * indent_width
    is_tight = is_tight_list(node)
    assert len(item_prefixes) == len(node.children)

    with context.indented(indent_width):
        parts: list[str] = []
        for item_prefix, child in zip(item_prefixes, node.children):
            list_item_text = child.render(context)
            parts.append(
                _format_list_item_lines(
                    list_item_text, item_prefix, continuation_prefix
                )
            )
            parts.append(_list_block_separator(is_tight, child))

    if parts:
        parts.pop()
    return "".join(parts)


def _render_bullet_list(node: RenderTreeNode, context: RenderContext) -> str:
    marker_type = get_list_marker_type(node)
    first_line_indent = " "
    prefix = f"{marker_type}{first_line_indent}"
    indent_width = len(prefix)
    item_prefixes = [prefix] * len(node.children)

    return _render_list(node, context, indent_width, item_prefixes)


def _render_ordered_list(node: RenderTreeNode, context: RenderContext) -> str:
    consecutive_numbering = context.options.get("mdformat", {}).get(
        "number", True
    )
    marker_type = get_list_marker_type(node)
    first_line_indent = " "
    list_len = len(node.children)

    starting_number = node.attrs.get("start")
    if starting_number is None:
        starting_number = 1
    assert isinstance(starting_number, int)

    if consecutive_numbering:
        max_number = list_len + starting_number - 1
        indent_width = len(
            f"{max_number}{marker_type}{first_line_indent}"
        )
        max_width = len(str(max_number))
        item_prefixes = [
            f"{str(starting_number + index).rjust(max_width, '0')}"
            f"{marker_type}{first_line_indent}"
            for index in range(list_len)
        ]
    else:
        indent_width = len(f"{starting_number}{marker_type}{first_line_indent}")
        first_item_marker = f"{starting_number}{marker_type}"
        other_item_marker = "0" * (len(str(starting_number)) - 1) + "1" + marker_type
        item_prefixes = [
            (
                f"{first_item_marker}{first_line_indent}"
                if index == 0
                else f"{other_item_marker}{first_line_indent}"
            )
            for index in range(list_len)
        ]

    return _render_list(node, context, indent_width, item_prefixes)


class _CleanupMDRenderer(MDRenderer):
    def render_tree(
        self,
        tree: RenderTreeNode,
        options: Mapping[str, Any],
        env: MutableMapping,
        *,
        finalize: bool = True,
    ) -> str:
        self._prepare_env(env)

        updated_renderers = {
            "bullet_list": _render_bullet_list,
            "ordered_list": _render_ordered_list,
            "list_item": _render_list_item,
        }
        postprocessors: dict[str, tuple[Any, ...]] = {}
        for plugin in options.get("parser_extension", []):
            for syntax_name, renderer_func in plugin.RENDERERS.items():
                updated_renderers.setdefault(syntax_name, renderer_func)
            for syntax_name, pp in getattr(plugin, "POSTPROCESSORS", {}).items():
                if syntax_name not in postprocessors:
                    postprocessors[syntax_name] = (pp,)
                else:
                    postprocessors[syntax_name] += (pp,)

        renderer_map = MappingProxyType({**DEFAULT_RENDERERS, **updated_renderers})
        postprocessor_map = MappingProxyType(postprocessors)
        render_context = RenderContext(renderer_map, postprocessor_map, options, env)
        text = tree.render(render_context)
        if finalize:
            if env["used_refs"]:
                text += "\n\n"
                text += self._write_references(env)
            if text:
                text += "\n"

        assert "\x00" not in text, "null bytes should be removed by now"
        return text


def build_markdown_it() -> MarkdownIt:
    def renderer_factory(parser: MarkdownIt) -> Any:
        return _CleanupMDRenderer(parser)

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
