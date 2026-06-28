#!/usr/bin/env python3

import time

from core.clipboard import (
    clipboard_change_count,
    restore_clipboard,
    snapshot_clipboard,
    wait_for_clipboard_change,
    write_clipboard,
)
from core.input_source import MacInputSourceManager
from core.keyboard import FastKeyboard
from transforms.layout_conversion import (
    LayoutConversionDirection,
    replace_last_layout_mismatched_sequence,
)

LAYOUT_A_TO_B = {
    'q': 'й',
    'w': 'ц',
    'e': 'у',
    'r': 'к',
    't': 'е',
    'y': 'н',
    'u': 'г',
    'i': 'ш',
    'o': 'з',
    'p': 'х',
    'a': 'ф',
    's': 'ы',
    'd': 'в',
    'f': 'а',
    'g': 'п',
    'h': 'р',
    'j': 'о',
    'k': 'л',
    'l': 'д',
    ';': 'ж',
    'z': 'я',
    'x': 'ч',
    'c': 'с',
    'v': 'м',
    'b': 'и',
    'n': 'т',
    'm': 'ь',
    ',': 'б',
    '.': 'ю',
    '/': 'э',
    'Q': 'Й',
    'W': 'Ц',
    'E': 'У',
    'R': 'К',
    'T': 'Е',
    'Y': 'Н',
    'U': 'Г',
    'I': 'Ш',
    'O': 'З',
    'P': 'Х',
    'A': 'Ф',
    'S': 'Ы',
    'D': 'В',
    'F': 'А',
    'G': 'П',
    'H': 'Р',
    'J': 'О',
    'K': 'Л',
    'L': 'Д',
    ':': 'Ж',
    'Z': 'Я',
    'X': 'Ч',
    'C': 'С',
    'V': 'М',
    'B': 'И',
    'N': 'Т',
    'M': 'Ь',
    '<': 'Б',
    '>': 'Ю',
    '?': 'Э',
}
SELECT_LAST_LINE_DELAY = 0.05
COPY_TIMEOUT = 0.5
PASTE_DELAY = 0.05
TARGET_INPUT_SOURCE_ID_BY_MAPPING_DIRECTION = {
    LayoutConversionDirection.A: 'org.sil.ukelele.keyboardlayout.en-sym.en-sym',
    LayoutConversionDirection.B: 'org.sil.ukelele.keyboardlayout.ru-sym.ru-sym'
}
LAST_SEQUENCE_MAX_CHARS = 24
LAST_SEQUENCE_TEST_CHARS = 3


def main() -> None:
    start_ts = time.perf_counter()
    keyboard = FastKeyboard()
    input_manager = MacInputSourceManager()
    original = snapshot_clipboard()

    try:
        keyboard.send_select_last_line()
        time.sleep(SELECT_LAST_LINE_DELAY)

        change_count = clipboard_change_count()
        keyboard.send_copy()
        text = wait_for_clipboard_change(change_count, COPY_TIMEOUT)

        transformed, direction = replace_last_layout_mismatched_sequence(
            text,
            LAYOUT_A_TO_B,
            LAST_SEQUENCE_MAX_CHARS,
            LAST_SEQUENCE_TEST_CHARS,
        )
        write_clipboard(transformed)
        keyboard.send_paste()

        target_input_source_id = TARGET_INPUT_SOURCE_ID_BY_MAPPING_DIRECTION.get(direction)
        if target_input_source_id:
            input_manager.switch_by_id(target_input_source_id)

        time.sleep(PASTE_DELAY)
    finally:
        restore_clipboard(original)
        print(f'duration: {time.perf_counter() - start_ts:.3f} sec.', flush=True)


if __name__ == '__main__':
    main()
