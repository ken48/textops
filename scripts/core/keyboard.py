import time

from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSetFlags,
    kCGHIDEventTap,
)


class FastKeyboard:
    def __init__(self) -> None:
        self.key_codes: dict[str, int] = {
            'a': 0,
            'c': 8,
            'v': 9,
            'left': 123,
        }

        self.modifiers: dict[str, int] = {
            'sft': 0x20000,
            'ctl': 0x40000,
            'opt': 0x80000,
            'cmd': 0x100000,
        }

    def send_key(self, key_name: str, modifier_flags: int = 0) -> None:
        if key_name not in self.key_codes:
            return

        key_code = self.key_codes[key_name]
        event_down = CGEventCreateKeyboardEvent(None, key_code, True)
        if modifier_flags:
            CGEventSetFlags(event_down, modifier_flags)
        CGEventPost(kCGHIDEventTap, event_down)

        time.sleep(0.02)

        event_up = CGEventCreateKeyboardEvent(None, key_code, False)
        if modifier_flags:
            CGEventSetFlags(event_up, modifier_flags)
        CGEventPost(kCGHIDEventTap, event_up)

    def send_copy(self) -> None:
        self.send_key('c', self.modifiers['cmd'])

    def send_paste(self) -> None:
        self.send_key('v', self.modifiers['cmd'])

    def send_select_all(self) -> None:
        self.send_key('a', self.modifiers['cmd'])

    def send_select_last_word(self) -> None:
        self.send_key('left', self.modifiers['sft'] | self.modifiers['opt'])

    def send_select_last_line(self) -> None:
        self.send_key('left', self.modifiers['sft'] | self.modifiers['cmd'])
