# Textops

Textops is a macOS toolkit for fast text transformations in the active input field.

It works across applications rather than inside one specific editor. The focus is on practical everyday operations: correcting text, reformatting it, and adapting the workflow to your own typing habits.

**Example:** you type `ghbdtn` in the wrong keyboard layout, press a hotkey, and it becomes `привет`.

```text
Karabiner hotkey -> warmpyctl -> WarmPy -> script -> active text field
```

## Background

This project started from a practical gap: I wanted small text-transformation tools that worked directly in real macOS input fields, without being tied to one editor. Existing tools did not fit:

- **Punto Switcher** no longer works reliably on current macOS versions.
- **Caramba Switcher** does not provide enough customization around hotkeys and layout-handling behavior.
- **Keyboard Maestro** adds too much latency when running custom scripts. These actions need to feel almost instant (under ~500ms end to end).

So this repository collects the text utilities I actually wanted: small, scriptable, predictable, highly customizable, editor-independent, and fast enough to be used as part of normal typing.

## What Textops provides

Two main user-facing scripts:

- `scripts/auto_layout_fixer.py` -- fixes text typed in the wrong keyboard layout
- `scripts/cleanup_md.py` -- reformats Markdown-aware prose without breaking headings, lists, links, or code blocks

### `auto_layout_fixer.py`

A quick keyboard layout fixer. Typical flow:

- select the last line in the active field
- copy it
- detect the last non-whitespace sequence
- decide whether it was typed in Russian or English layout
- convert it to the opposite layout
- paste the corrected text back
- switch the system input source to match the corrected language

### `cleanup_md.py`

A formatter for Markdown-aware prose. It parses the selected text as Markdown, preserves the existing structure, and formats only prose content where it is safe to do so. It can:

- preserve headings, lists, blockquotes, links, and fenced code blocks
- normalize spacing around punctuation
- capitalize sentence starts
- replace spaced hyphens with em dashes
- normalize curly and locale-specific quotes to plain ASCII quotes
- re-render the Markdown into a consistent structure without rewriting the document outline

Supports `--select-all` to format the full contents of the current field instead of only the selected fragment.

## Requirements

- macOS 13 Ventura or later
- Python 3.11 (for building WarmPy)
- Accessibility permission granted to WarmPy
- Optional: [Karabiner-Elements](https://karabiner-elements.pqrs.org/) for hotkey triggers

## Quick start

### 1. Build WarmPy

```bash
cd /absolute/path/to/textops
WARMPY_PYTHON=$(which python3.11) ./warmpy/build.sh ./scripts/warmpy.yaml
```

`./scripts/warmpy.yaml` is the build config that lists Python dependencies and modules to preload. The built app appears at `warmpy/.build/dist/warmpy.app`.

> If `which python3.11` does not resolve, use the full path to your Python 3.11 binary, e.g. `/opt/homebrew/opt/python@3.11/bin/python3.11` on Homebrew Apple Silicon.

### 2. Grant Accessibility permission

1. Open **System Settings > Privacy & Security > Accessibility**.
2. Add and enable `warmpy.app`.
3. Start (or restart) `warmpy.app` after granting the permission.

### 3. Set up a hotkey

Configure a hotkey trigger (e.g. Karabiner-Elements) to run:

```bash
python3 /absolute/path/to/textops/warmpy/ctl/warmpyctl.py /absolute/path/to/textops/scripts/auto_layout_fixer.py
```

You can pass arguments to scripts:

```bash
python3 /absolute/path/to/textops/warmpy/ctl/warmpyctl.py /absolute/path/to/textops/scripts/cleanup_md.py --select-all
```

## How it works

The system consists of four parts:

- **Textops scripts** -- the actual text transformations
- **WarmPy** -- a menu bar app that keeps a Python runtime warm and executes scripts on demand
- **warmpyctl** -- a small CLI that sends run requests to WarmPy via Unix socket
- **Karabiner-Elements** -- an optional hotkey trigger layer

Scripts work through the system clipboard and keyboard event simulation: read text from the active field, transform it, paste the result back, and restore the original clipboard contents. They operate on the current macOS UI focus, not on stdin.

## Build config

`warmpy/build.sh` takes a path to a `warmpy.yaml` file describing script dependencies.

Minimal example:

```yaml
pip:
  - pyobjc-framework-Cocoa
  - pyobjc-framework-Quartz

modules:
  - Cocoa
  - Quartz
```

- `pip` -- packages to install into the build environment
- `modules` -- modules to bundle and preload at startup

## Writing your own script

WarmPy scripts run inside a shared long-running app process, not in a fresh interpreter. See [docs/internals.md](docs/internals.md) for the full runtime model and script author contract.

The key rules:

- Keep runs short -- avoid long blocking work on the main thread.
- Do not assume a clean process state between runs.
- `warmpyctl` success means the request was sent, not that the script finished. Check `~/.warmpy/warmpy.log` for actual execution results.

## Troubleshooting

**WarmPy does not respond to hotkeys after first launch.**
You likely launched it before granting Accessibility permission. Quit and restart `warmpy.app` after enabling it in System Settings.

**Accessibility permission keeps getting reverted.**
macOS may reset Accessibility permissions after app updates or system upgrades. Re-add `warmpy.app` in System Settings.

**A second WarmPy instance does not start.**
WarmPy enforces one instance per user. If you launch the bundled executable directly from a terminal, it will detect the running instance and exit (logged to `~/.warmpy/start-attempts/`).

## Project structure

```text
scripts/
  auto_layout_fixer.py
  cleanup_md.py
  core/           -- clipboard, keyboard, input source integration
  transforms/     -- reusable text transformation logic
  warmpy.yaml

warmpy/
  build.sh        -- app build entry point
  main.py
  host/           -- WarmPy app sources and runtime
  ctl/            -- warmpyctl request submission tool
  assets/
```

## Further reading

- [docs/internals.md](docs/internals.md) -- runtime model, script author contract, development mode, logs
