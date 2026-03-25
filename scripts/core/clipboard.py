import subprocess


def read_clipboard() -> str:
    return subprocess.run(
        ['pbpaste'],
        capture_output=True,
        text=True,
        encoding='utf-8',
        check=False,
    ).stdout


def write_clipboard(text: str) -> None:
    subprocess.run(
        ['pbcopy'],
        input=text,
        text=True,
        encoding='utf-8',
        check=False,
    )
