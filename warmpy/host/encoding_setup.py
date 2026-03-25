import locale
import os
import sys
import logging

def ensure_utf8_locale() -> None:
    """Best-effort UTF-8 locale & stdio configuration for py2app launches.

    py2app apps can start with LANG/LC_ALL unset, which may cause non-UTF-8
    defaults for some libraries and subprocesses. We set sane defaults and
    reconfigure stdio to UTF-8 where possible.
    """
    # Environment defaults (do not override user-provided values)
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("LANG", "en_US.UTF-8")
    os.environ.setdefault("LC_ALL", "en_US.UTF-8")

    # Apply locale from environment
    try:
        locale.setlocale(locale.LC_ALL, "")
    except Exception:
        # Fall back to a couple of common UTF-8 locales.
        for loc in ("en_US.UTF-8", "C.UTF-8"):
            try:
                locale.setlocale(locale.LC_ALL, loc)
                break
            except Exception:
                continue

    # Ensure stdio uses UTF-8 to avoid UnicodeEncodeError in prints/log pipes.
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        try:
            if stream is not None and hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            # Keep running even if reconfigure fails.
            pass

    try:
        logging.getLogger(__name__).info(
            "LOCALE configured lang=%s lc_all=%s fsenc=%s stdout=%s",
            os.environ.get("LANG"),
            os.environ.get("LC_ALL"),
            sys.getfilesystemencoding(),
            getattr(getattr(sys, "stdout", None), "encoding", None),
        )
    except Exception:
        pass
