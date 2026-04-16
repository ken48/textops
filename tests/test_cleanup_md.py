import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from transforms.cleanup_md import CleanupMarkdownOptions, cleanup_markdown


class CleanupMarkdownTests(unittest.TestCase):
    def test_formats_markdown_prose_without_breaking_structure(self) -> None:
        source = '# heading\n\n- first item\n  - nested item\n\n> "quote" - here\n'
        expected = '# Heading\n\n- first item\n\n  - nested item\n\n> "Quote" — here'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_keeps_inline_code_fences_and_autolinks_intact(self) -> None:
        source = 'hello `a - b` and [foo - bar](https://x.com/a-b) <https://x.com/a-b>\n\n```py\na - b\nprint("hi")\n```\n'
        expected = 'Hello `a - b` and [foo - bar](https://x.com/a-b) <https://x.com/a-b>\n\n```py\na - b\nprint("hi")\n```'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_normalizes_thematic_breaks_to_asterisks(self) -> None:
        source = 'text\n\n---\n\nnext\n'
        expected = 'Text\n\n***\n\nNext'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_formats_plain_prose_as_markdown_fragment(self) -> None:
        source = 'привет. "мир" - это тест и  еще  текст ,да?'
        expected = 'Привет. "Мир" — это тест и еще текст, да?'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_normalizes_right_curly_double_quote_to_ascii(self) -> None:
        source = 'заметки для вас не “дисциплина успешного человека”, а канал\n'
        expected = 'Заметки для вас не "дисциплина успешного человека", а канал'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_keeps_fragment_lists_tight_and_preserves_case(self) -> None:
        source = '- speed\n- simplicity\n- markdown support\n'
        expected = '- speed\n- simplicity\n- markdown support'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_keeps_short_sentence_lists_tight(self) -> None:
        source = '- this is a sentence.\n- this is another sentence.\n'
        expected = '- This is a sentence.\n- This is another sentence.'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_loose_style_propagates_to_mixed_list(self) -> None:
        source = '- speed\n- this is a longer sentence item that should look like prose.\n'
        expected = '- speed\n- This is a longer sentence item that should look like prose.'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_keeps_short_sentence_list_items_tight(self) -> None:
        source = '- markdown как формат.\n- github для синхронизации между устройствами.\n- obsidian как редактор.\n'
        expected = '- Markdown как формат.\n- Github для синхронизации между устройствами.\n- Obsidian как редактор.'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_long_sentence_item_with_period_still_makes_list_loose(self) -> None:
        source = (
            '- короткий пункт.\n'
            '- это уже достаточно длинный пункт списка, чтобы считать его отдельным абзацем, а не компактным элементом.\n'
        )
        expected = (
            '- Короткий пункт.\n\n'
            '- Это уже достаточно длинный пункт списка, чтобы считать его отдельным абзацем, а не компактным элементом.'
        )

        self.assertEqual(cleanup_markdown(source), expected)

    def test_separates_nested_lists_with_blank_line_like_other_block_items(self) -> None:
        source = '- из старой статьи взять:\n  - тезис один\n  - тезис два\n'
        expected = '- из старой статьи взять:\n\n  - тезис один\n  - тезис два'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_nested_list_does_not_loosen_other_short_outer_items(self) -> None:
        source = '- короткий\n- вводный\n  - вложенный\n- еще короткий\n'
        expected = '- короткий\n- вводный\n\n  - вложенный\n- еще короткий'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_keeps_hidden_path_segments_lowercase(self) -> None:
        source = '/Users/kirill/Projects/vcs/textops/warmpy/.build\n'
        expected = '/Users/kirill/Projects/vcs/textops/warmpy/.build'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_adds_space_after_sentence_dot(self) -> None:
        source = 'привет.мир\n'
        expected = 'Привет. Мир'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_treats_ambiguous_single_dot_english_text_as_prose(self) -> None:
        source = 'hello.world\n'
        expected = 'Hello. World'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_keeps_explicit_technical_tokens_intact(self) -> None:
        source = 'https://example.com/x.y test@example.com sub.example.com\n'
        expected = 'https://example.com/x.y test@example.com sub.example.com'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_restores_obsidian_wikilink_brackets_after_render(self) -> None:
        source = '[[note]]\n'
        expected = '[[Note]]'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_restores_obsidian_wikilinks_inside_prose(self) -> None:
        source = 'тест [[note]] текст\n'
        expected = 'Тест [[note]] текст'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_strips_full_bold_wrapper_from_heading(self) -> None:
        source = '# **header**\n'
        expected = '# Header'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_strips_bold_wrapper_from_numbered_heading_body(self) -> None:
        source = '#### 2. **запись как форма и разрядка**\n'
        expected = '#### 2. Запись как форма и разрядка'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_preserves_partial_bold_inside_heading(self) -> None:
        source = '# header with **focus**\n'
        expected = '# Header with **focus**'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_can_disable_bold_heading_normalization(self) -> None:
        source = '# **header**\n'
        expected = '# **Header**'

        self.assertEqual(
            cleanup_markdown(
                source,
                CleanupMarkdownOptions(normalize_bold_headings=False),
            ),
            expected,
        )

    def test_can_disable_obsidian_wikilink_restore(self) -> None:
        source = '[[note]]\n'
        expected = '\\[[Note]\\]'

        self.assertEqual(
            cleanup_markdown(
                source,
                CleanupMarkdownOptions(restore_obsidian_wikilinks=False),
            ),
            expected,
        )

    def test_strips_hardbreak_markup_in_ordered_lists(self) -> None:
        source = '1. «заголовок»  \n   продолжение\n'
        expected = '1. "заголовок"\n   продолжение'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_can_disable_hardbreak_markup_stripping(self) -> None:
        source = '1. «заголовок»  \n   продолжение\n'
        expected = '1. "заголовок"\\\n   продолжение'

        self.assertEqual(
            cleanup_markdown(
                source,
                CleanupMarkdownOptions(strip_hardbreak_markup=False),
            ),
            expected,
        )

    def test_capitalizes_after_email_when_sentence_continues_in_next_fragment(self) -> None:
        source = 'Тест почты user@yandex.ru. вот такая у меня крутая почта.'
        expected = 'Тест почты user@yandex.ru. Вот такая у меня крутая почта.'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_keeps_lowercase_conjunction_between_quoted_questions(self) -> None:
        source = 'определить зоны ответственности, чтобы убрать неявные ожидания вроде «почему ты не сделал?» и «почему опять я?».\n'
        expected = 'Определить зоны ответственности, чтобы убрать неявные ожидания вроде "почему ты не сделал?" и "почему опять я?".'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_keeps_lowercase_word_after_quoted_question_inside_sentence(self) -> None:
        source = 'кризис героя: старый ответ на вопрос "кто я?" больше не работает.\n'
        expected = 'Кризис героя: старый ответ на вопрос "кто я?" больше не работает.'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_keeps_coordinated_semicolon_list_tight(self) -> None:
        source = (
            'по сути, здесь нужно прояснить две вещи:\n\n'
            '- кто держит это на себе;\n'
            '- какой уровень исполнения нас обоих устраивает.\n'
        )
        expected = (
            'По сути, здесь нужно прояснить две вещи:\n\n'
            '- кто держит это на себе;\n'
            '- какой уровень исполнения нас обоих устраивает.'
        )

        self.assertEqual(cleanup_markdown(source), expected)

    def test_keeps_arrow_mapping_list_tight_and_lowercase(self) -> None:
        source = (
            'их связь выглядит так:\n\n'
            '- осознание потребности -> стратегия\n\n'
            '- планирование -> тактика\n\n'
            '- действие -> операция\n\n'
            '- оценка результата -> поддержка системы и актуализация стратегии\n'
        )
        expected = (
            'Их связь выглядит так:\n\n'
            '- осознание потребности -> стратегия\n'
            '- планирование -> тактика\n'
            '- действие -> операция\n'
            '- оценка результата -> поддержка системы и актуализация стратегии'
        )

        self.assertEqual(cleanup_markdown(source), expected)

    def test_keeps_topic_list_tight_and_lowercase_even_with_long_item(self) -> None:
        source = (
            'Переход от смысловой части к прикладной:\n\n'
            '- структура папок\n\n'
            '- daily / notes / обзоры\n\n'
            '- роль `agents.md`\n\n'
            '- пример из репозитория\n\n'
            '- как это может выглядеть в реальной работе без лишней теории\n'
        )
        expected = (
            'Переход от смысловой части к прикладной:\n\n'
            '- структура папок\n'
            '- daily / notes / обзоры\n'
            '- роль `agents.md`\n'
            '- пример из репозитория\n'
            '- как это может выглядеть в реальной работе без лишней теории'
        )

        self.assertEqual(cleanup_markdown(source), expected)

    def test_allows_call_site_to_disable_sentence_capitalization(self) -> None:
        source = 'привет. "мир" - это тест\n'
        expected = 'привет. "мир" — это тест'

        self.assertEqual(
            cleanup_markdown(
                source,
                CleanupMarkdownOptions(
                    normalize_quotes=True,
                    normalize_dashes=True,
                    normalize_time_ranges=True,
                    normalize_punctuation_spacing=True,
                    normalize_sentence_dot_spacing=True,
                    collapse_inline_whitespace=True,
                    capitalize_sentences=False,
                    preserve_technical_tokens=True,
                    preserve_tight_lists=True,
                ),
            ),
            expected,
        )


if __name__ == "__main__":
    unittest.main()
