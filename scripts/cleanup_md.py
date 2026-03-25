#!/usr/bin/env python3

import time
from sys import argv

from core.clipboard import read_clipboard, write_clipboard
from core.keyboard import FastKeyboard
from transforms.cleanup_md import CleanupMarkdownOptions, cleanup_markdown

SELECT_ALL_DELAY = 0.05
COPY_DELAY = 0.15
PASTE_DELAY = 0.05

MARKDOWN_CLEANUP_OPTIONS = CleanupMarkdownOptions(
    normalize_quotes=True,
    normalize_dashes=True,
    normalize_time_ranges=True,
    normalize_punctuation_spacing=True,
    normalize_sentence_dot_spacing=True,
    collapse_inline_whitespace=True,
    capitalize_sentences=True,
    preserve_technical_tokens=True,
    preserve_tight_lists=True,
)


def normalize(select_all: bool = False) -> None:
    start_ts = time.perf_counter()
    keyboard = FastKeyboard()
    original = read_clipboard()

    try:
        if select_all:
            keyboard.send_select_all()
            time.sleep(SELECT_ALL_DELAY)

        keyboard.send_copy()
        time.sleep(COPY_DELAY)

        text = read_clipboard()
        if not text.strip():
            return

        transformed = cleanup_markdown(text, options=MARKDOWN_CLEANUP_OPTIONS)
        write_clipboard(transformed)
        keyboard.send_paste()
        time.sleep(PASTE_DELAY)
    finally:
        write_clipboard(original)
        print(f'duration: {time.perf_counter() - start_ts:.3f} sec.', flush=True)


def main() -> None:
    normalize(
        select_all='--select-all' in argv,
    )


if __name__ == '__main__':
    main()
