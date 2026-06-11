# Internals

This document covers WarmPy's runtime model, script author contract, development mode, and logging. For general usage, see the [README](../README.md).

## Runtime model

WarmPy is intentionally small:

- one app process per user
- one script execution at a time
- fire-and-forget submission from the controller
- no queue, no subprocess worker, no plugin API

There are two parts:

- `host.app` keeps a Python runtime alive, owns a local Unix socket, optionally preloads selected modules, and executes accepted scripts
- `ctl` sends a single request to the socket and exits immediately

Scripts are executed inside the already running app process, on the app main thread, one at a time. If a new request arrives while another script is still running, it is dropped.

## Controller protocol

`warmpyctl` resolves the script and optional clean root to absolute paths, then sends one UTF-8 JSON object over the Unix socket:

```json
{
  "script": "/absolute/path/to/script.py",
  "args": ["--select-all"],
  "clean": false,
  "clean_root": null
}
```

The host validates the field types before dispatching the request. The controller closes the connection after sending the payload and does not wait for execution or return a script result.

The host still accepts the older NUL-separated `script\0arg...` payload for compatibility, but `warmpyctl` uses JSON.

## Clipboard synchronization

The bundled text scripts use `NSPasteboard` directly:

- snapshot every pasteboard item and all available representations before changing it
- record `changeCount` immediately before sending `Cmd+C`
- poll until `changeCount` changes, with a bounded timeout
- abort on timeout instead of reading stale clipboard data
- restore the complete original snapshot after the paste operation

This makes the copy phase respond to the actual pasteboard update rather than a fixed delay, while preserving text, images, file references, and other pasteboard types.

## Script author contract

A WarmPy script should assume:

- it runs inside an already running app process, not in a fresh interpreter
- it shares process-global state with earlier and later runs
- it executes on the app main thread
- it may be rejected if another accepted script is still running

In practice:

- keep runs short and avoid long blocking work on the main thread
- do not assume imports, globals, or singleton state start from a clean process
- do not assume `ctl` success means the script finished successfully
- treat runtime logs as the source of truth for actual execution

## Development mode

Development cleanup mode is a convenience for local script iteration.

Use it when you are editing your own project code and want WarmPy to forget previously imported modules under a selected root before the next run:

```bash
python3 warmpy/ctl/warmpyctl.py --clean script.py
python3 warmpy/ctl/warmpyctl.py --clean --clean-root /abs/path/to/project script.py arg1 arg2
```

`--clean` clears already imported modules only under the selected clean root, so local code can reload while stdlib, site-packages, PyObjC, Quartz, and WarmPy stay intact.

Important boundaries:

- `--clean` is best-effort reload help, not process isolation
- it is intended for local project code, not for resetting the whole app state
- if a script needs a fully fresh interpreter, WarmPy is the wrong execution model for that task

## Logs

Main runtime log:

```text
~/.warmpy/warmpy.log
```

WarmPy rotates this log automatically and keeps a few older files as `warmpy.log.1`, `warmpy.log.2`, and so on.

Log markers:

- `SOCKET started ...`
- `WARMUP start / skip ...`
- `ACCEPT ...`
- `RUN begin / end ...`
- `DONE ...`
- `DROP busy ...`
- `STDOUT / STDERR ...`

Failed extra app launches create audit files in `~/.warmpy/start-attempts/`.

Note: opening the `.app` again through Finder may not create a second process at all. Launching the bundled executable directly from a terminal can create a second process, which then records an `already-running` attempt.

## Menu bar lifecycle

The menu bar item provides:

- **Open Log** -- opens `~/.warmpy/warmpy.log`
- **Restart** -- schedules a fresh bundled app launch after the current process exits
- **Quit** -- terminates the current app process

Restart is enabled only when WarmPy is running from a bundled `.app`.

## Notes

- being inside a real `.app` solves only part of macOS integration; some APIs may still care about thread or event-loop context
- `--clean` is a development convenience and should not be treated as a production runtime guarantee
