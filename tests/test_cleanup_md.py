import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from transforms.cleanup_md import CleanupMarkdownOptions, cleanup_markdown


class CleanupMarkdownTests(unittest.TestCase):
    def test_formats_markdown_prose_without_breaking_structure(self) -> None:
        source = '# heading\n\n- first item\n  - nested item\n\n> "quote" - here\n'
        expected = '# Heading\n\n- first item\n  - nested item\n\n> "Quote" — here'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_keeps_inline_code_fences_and_autolinks_intact(self) -> None:
        source = 'hello `a - b` and [foo - bar](https://x.com/a-b) <https://x.com/a-b>\n\n```py\na - b\nprint("hi")\n```\n'
        expected = 'Hello `a - b` and [foo - bar](https://x.com/a-b) <https://x.com/a-b>\n\n```py\na - b\nprint("hi")\n```'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_formats_plain_prose_as_markdown_fragment(self) -> None:
        source = 'привет. "мир" - это тест и  еще  текст ,да?'
        expected = 'Привет. "Мир" — это тест и еще текст, да?'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_keeps_fragment_lists_tight_and_preserves_case(self) -> None:
        source = '- speed\n- simplicity\n- markdown support\n'
        expected = '- speed\n- simplicity\n- markdown support'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_makes_sentence_lists_loose_and_capitalizes_items(self) -> None:
        source = '- this is a sentence.\n- this is another sentence.\n'
        expected = '- This is a sentence.\n\n- This is another sentence.'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_loose_style_propagates_to_mixed_list(self) -> None:
        source = '- speed\n- this is a longer sentence item that should look like prose.\n'
        expected = '- speed\n\n- This is a longer sentence item that should look like prose.'

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

    def test_capitalizes_after_email_when_sentence_continues_in_next_fragment(self) -> None:
        source = 'Тест почты user@yandex.ru. вот такая у меня крутая почта.'
        expected = 'Тест почты user@yandex.ru. Вот такая у меня крутая почта.'

        self.assertEqual(cleanup_markdown(source), expected)

    def test_keeps_lowercase_conjunction_between_quoted_questions(self) -> None:
        source = 'определить зоны ответственности, чтобы убрать неявные ожидания вроде «почему ты не сделал?» и «почему опять я?».\n'
        expected = 'Определить зоны ответственности, чтобы убрать неявные ожидания вроде "почему ты не сделал?" и "почему опять я?".'

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
